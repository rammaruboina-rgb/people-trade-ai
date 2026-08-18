# coindcx_master_agent.py
import time
import logging
from datetime import datetime

import config
from config import (
    LOOP_INTERVAL_SEC,
    ALLOWED_FUTURES_COINS,
    get_dynamic_daily_target_usd,
    DEFAULT_MAX_DAILY_TARGET_USD,
    MAX_DAILY_TRADES,
    DAILY_LOSS_LIMIT_USD,
    MAX_CONCURRENT_TRADES,
    BREAKEVEN_PROFIT_PCT,
    LOG_FILE
)
from coindcx_client import CoinDCXClient
from coindcx_futures_mapper import futures_mapper
from risk_engine import (
    calc_sl_tp_prices,
    calc_position_size,
    apply_leverage_cap,
    calc_trailing_sl,
    calc_liquidation_price,
    calc_emergency_sl
)
from strategy_engine import StrategyEngine, get_top_trending_altcoins
from data_store import init_trades_csv, log_trade, load_trade_history, calculate_pnl

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger().addHandler(console_handler)

logger = logging.getLogger(__name__)

class MasterAgent:
    def __init__(self):
        self.client = CoinDCXClient()
        self.strategy = StrategyEngine()
        self.coin_price_history = {c: [] for c in ALLOWED_FUTURES_COINS}
        self.daily_start_date = datetime.now().date()
        self.daily_realized_pnl = 0.0
        self.daily_trades_count = 0

    def check_daily_reset(self):
        today = datetime.now().date()
        if today != self.daily_start_date:
            self.daily_start_date = today
            self.daily_realized_pnl = 0.0
            self.daily_trades_count = 0
            logger.info("📅 New Trading Day Started - Daily Realized P&L & Trade Counter Reset to 0.")

    def run_master_loop(self):
        init_trades_csv()
        mode_str = 'LIVE' if self.client.live_mode else 'PAPER'
        focus_str = f"FOCUS: {config.TARGETED_FOCUS_COIN} ONLY" if config.TARGETED_FOCUS_COIN else "ALL ALTCOINS"
        logger.info(f"🤖 Master Agent started in {mode_str} mode ({focus_str} | GOAL: {MAX_DAILY_TRADES} TRADES/DAY | TARGET: ${DEFAULT_MAX_DAILY_TARGET_USD:,.2f}/DAY).")

        while True:
            try:
                self.check_daily_reset()
                balances = self.client.get_account_balances()
                equity = balances.get("total_equity", 9.52)

                active_futures_positions = self.client.get_active_futures_positions()
                current_active_count = sum(1 for p in active_futures_positions.values() if p.get("active_pos", 0.0) != 0.0)

                trades = load_trade_history()
                sui_price = self.client.get_ticker_price("SUIUSDT")
                realized_pnl, unrealized_pnl, _ = calculate_pnl(trades, sui_price)
                self.daily_realized_pnl = realized_pnl
                self.daily_trades_count = len([t for t in trades if t.get("timestamp", "").startswith(datetime.now().strftime("%Y-%m-%d"))])

                # 1) Targeted Coin Focus Mode Filter
                if config.TARGETED_FOCUS_COIN:
                    top_trending_coins = [config.TARGETED_FOCUS_COIN]
                else:
                    top_trending_coins = get_top_trending_altcoins(ALLOWED_FUTURES_COINS, top_n=10)

                for coin in top_trending_coins:
                    if current_active_count >= MAX_CONCURRENT_TRADES:
                        break

                    spot_sym = futures_mapper.get_spot_symbol(coin)
                    futures_sym = futures_mapper.get_dcx_future_symbol(coin)
                    candle_pair = f"B-{coin.upper()}_USDT"

                    mark_price = self.client.get_ticker_price(spot_sym)
                    if mark_price <= 0:
                        continue

                    p_hist = self.coin_price_history.setdefault(coin, [])
                    p_hist.append(mark_price)
                    if len(p_hist) > 10:
                        p_hist.pop(0)

                    pos_info = active_futures_positions.get(futures_sym, {})
                    has_active_pos = pos_info.get("active_pos", 0.0) != 0.0

                    if not has_active_pos:
                        sig = self.strategy.evaluate_multi_source_signal(mark_price, p_hist, pair=candle_pair)
                        direction = sig.get("direction", "long") or "long"
                        side_order = "BUY" if direction == "long" else "SELL"

                        coin_risk = futures_mapper.get_coin_risk_params(coin)
                        leverage = pos_info.get("leverage", coin_risk.get("leverage", 20))
                        sl_price = sig.get("sl_price", round(mark_price * (0.90 if direction == "long" else 1.10), 2))
                        tp_price = sig.get("tp_price", round(mark_price * (1.20 if direction == "long" else 0.80), 2))
                        
                        per_trade_equity = equity / MAX_CONCURRENT_TRADES
                        size = calc_position_size(per_trade_equity, mark_price, sl_price, coin)

                        logger.info(f"⚡ INSTANT EXECUTION TRIGGERED FOR {coin} ({side_order}). Placing Live Order...")

                        resp = self.client.place_order(
                            symbol=spot_sym,
                            side=side_order,
                            amount=size,
                            leverage=leverage,
                            sl_price=sl_price,
                            tp_price=tp_price,
                            market_type="futures"
                        )

                        order_id = resp[0]["id"] if (isinstance(resp, list) and len(resp) > 0 and "id" in resp[0]) else "LIVE_ORDER"
                        trade_row = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "symbol": candle_pair,
                            "market_type": "FUTURES",
                            "side": "LONG" if side_order == "BUY" else "SHORT",
                            "entry_price": mark_price,
                            "size": size,
                            "leverage": leverage,
                            "sl_price": sl_price,
                            "tp_price": tp_price,
                            "exit_price": "N/A",
                            "exit_reason": "N/A",
                            "confidence": 99.0,
                            "signal_source": f"FOCUS_MODE_{direction.upper()}_{coin}",
                            "news_summary": sig.get("summary", "N/A"),
                            "mode": mode_str
                        }
                        log_trade(trade_row)
                        current_active_count += 1
                        self.daily_trades_count += 1
                        logger.info(f"🔥 {coin} LIVE FUTURES ORDER EXECUTED ({side_order}): {size} {coin} @ ${mark_price:,.2f} | Leverage: {leverage}x | Trade #{self.daily_trades_count}/{MAX_DAILY_TRADES}")

                time.sleep(LOOP_INTERVAL_SEC)

            except Exception as e:
                logger.exception(f"Error in master loop: {e}")
                time.sleep(LOOP_INTERVAL_SEC)

if __name__ == "__main__":
    agent = MasterAgent()
    agent.run_master_loop()
