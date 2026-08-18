# coindcx_master_agent.py
import time
import logging
from datetime import datetime

from config import (
    LOOP_INTERVAL_SEC,
    ALLOWED_FUTURES_COINS,
    get_dynamic_daily_target_usd,
    DEFAULT_MAX_DAILY_TARGET_USD,
    DAILY_LOSS_LIMIT_USD,
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

    def check_daily_reset(self):
        today = datetime.now().date()
        if today != self.daily_start_date:
            self.daily_start_date = today
            self.daily_realized_pnl = 0.0
            logger.info("📅 New Trading Day Started - Daily Realized P&L Reset to $0.00 USD.")

    def run_master_loop(self):
        init_trades_csv()
        mode_str = 'LIVE' if self.client.live_mode else 'PAPER'
        logger.info(f"🤖 Master Agent started in {mode_str} mode (DUAL-DIRECTION BUY & SELL FUTURES | LEVERAGE AUTO-SYNC | TARGET: ${DEFAULT_MAX_DAILY_TARGET_USD:,.2f}/DAY).")

        while True:
            try:
                self.check_daily_reset()
                balances = self.client.get_account_balances()
                equity = balances.get("total_equity", 9.52)

                # Fetch active open futures positions directly from CoinDCX API
                active_futures_positions = self.client.get_active_futures_positions()

                # Fetch daily PnL progress
                trades = load_trade_history()
                eth_price = self.client.get_ticker_price("ETHUSDT")
                realized_pnl, unrealized_pnl, _ = calculate_pnl(trades, eth_price)
                self.daily_realized_pnl = realized_pnl

                # 1) $100.00 Daily Profit Target Circuit Breaker
                if self.daily_realized_pnl >= DEFAULT_MAX_DAILY_TARGET_USD:
                    logger.info(f"🎉 $100.00 DAILY TARGET HIT: Realized P&L (${self.daily_realized_pnl:,.2f}) >= ${DEFAULT_MAX_DAILY_TARGET_USD:,.2f} Target!")
                    time.sleep(LOOP_INTERVAL_SEC * 5)
                    continue

                # Fetch Top 5 Trending Altcoins
                top_trending_coins = get_top_trending_altcoins(ALLOWED_FUTURES_COINS, top_n=5)

                # Execute trades across top trending altcoins
                for coin in top_trending_coins:
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

                    # If no active position on CoinDCX for this pair, execute new order
                    if not has_active_pos:
                        sig = self.strategy.evaluate_multi_source_signal(mark_price, p_hist, pair=candle_pair)
                        direction = sig.get("direction", "long")
                        side_order = "BUY" if direction == "long" else "SELL"

                        coin_risk = futures_mapper.get_coin_risk_params(coin)
                        leverage = pos_info.get("leverage", coin_risk.get("leverage", 20))
                        sl_price = sig.get("sl_price", round(mark_price * (0.90 if direction == "long" else 1.10), 2))
                        tp_price = sig.get("tp_price", round(mark_price * (1.20 if direction == "long" else 0.80), 2))
                        size = calc_position_size(equity, mark_price, sl_price, coin)

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
                            "signal_source": f"20X_FUTURES_{direction.upper()}_{coin}",
                            "news_summary": sig.get("summary", "N/A"),
                            "mode": mode_str
                        }
                        log_trade(trade_row)
                        logger.info(f"🚀 {coin} LIVE FUTURES ORDER EXECUTED ({side_order}): {size} {coin} @ ${mark_price:,.2f} | Leverage: {leverage}x | Order ID: {order_id}")

                time.sleep(LOOP_INTERVAL_SEC)

            except Exception as e:
                logger.exception(f"Error in master loop: {e}")
                time.sleep(LOOP_INTERVAL_SEC)

if __name__ == "__main__":
    agent = MasterAgent()
    agent.run_master_loop()
