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
        self.active_positions = {}
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
        logger.info(f"🤖 Master Agent started in {mode_str} mode (HIGH-CONVICTION +20% PROFIT ALTCOINS | CONFLUENCE: >=98% | TARGET: ${DEFAULT_MAX_DAILY_TARGET_USD:,.2f}/DAY).")

        while True:
            try:
                self.check_daily_reset()
                balances = self.client.get_account_balances()
                equity = balances.get("total_equity", 9.65)

                # Fetch daily PnL progress
                trades = load_trade_history()
                eth_price = self.client.get_ticker_price("ETHUSDT")
                realized_pnl, unrealized_pnl, _ = calculate_pnl(trades, eth_price)
                self.daily_realized_pnl = realized_pnl

                # 1) $100.00 Daily Profit Target Circuit Breaker
                if self.daily_realized_pnl >= DEFAULT_MAX_DAILY_TARGET_USD:
                    logger.info(f"🎉 $100.00 DAILY TARGET HIT: Realized P&L (${self.daily_realized_pnl:,.2f}) >= ${DEFAULT_MAX_DAILY_TARGET_USD:,.2f} Target! Pausing new entries today to lock in profit.")
                    time.sleep(LOOP_INTERVAL_SEC * 5)
                    continue

                # 2) Full Account Protection Stop ($9.65)
                if self.daily_realized_pnl <= -DAILY_LOSS_LIMIT_USD:
                    logger.warning(f"🛑 DAILY LOSS LIMIT REACHED (${self.daily_realized_pnl:,.2f} <= -${DAILY_LOSS_LIMIT_USD:,.2f}). Pausing new entries today to preserve capital.")
                    time.sleep(LOOP_INTERVAL_SEC * 5)
                    continue

                # Fetch Top 5 Trending Altcoins (Ranked by 24h/1h momentum, no BTC)
                top_trending_coins = get_top_trending_altcoins(ALLOWED_FUTURES_COINS, top_n=5)

                # Multi-Coin Futures Scalping Loop for Top Trending Altcoins
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

                    # 1) Active Position Risk Management for this coin
                    if coin in self.active_positions:
                        state = self.active_positions[coin]
                        side = state.get("side", "LONG")
                        entry = state.get("entry_price", mark_price)
                        current_sl = state.get("sl_price", 0.0)

                        if side == "LONG":
                            state["highest"] = max(state.get("highest", mark_price), mark_price)
                        else:
                            state["lowest"] = min(state.get("lowest", mark_price), mark_price)

                        # ZERO-LOSS BREAK-EVEN GUARD (+5.0% Profit = SL moved to Entry + Fees)
                        is_breakeven_set = state.get("is_breakeven_set", False)
                        if not is_breakeven_set:
                            if side == "LONG" and mark_price >= entry * 1.05:
                                be_sl = round(entry * 1.03, 2)
                                if be_sl > current_sl:
                                    logger.info(f"🛡️ BREAK-EVEN ACTIVATED ({coin} LONG): Profit +5.0% reached! SL moved to +3.0% profit lock (${be_sl:,.2f})")
                                    state["sl_price"] = be_sl
                                    state["is_breakeven_set"] = True
                            elif side == "SHORT" and mark_price <= entry * 0.95:
                                be_sl = round(entry * 0.97, 2)
                                if current_sl == 0 or be_sl < current_sl:
                                    logger.info(f"🛡️ BREAK-EVEN ACTIVATED ({coin} SHORT): Profit +5.0% reached! SL moved to +3.0% profit lock (${be_sl:,.2f})")
                                    state["sl_price"] = be_sl
                                    state["is_breakeven_set"] = True

                        # Trailing SL update
                        new_sl = calc_trailing_sl(state.get("highest", mark_price), state.get("lowest", mark_price), side, state.get("sl_price", current_sl))
                        if new_sl != state.get("sl_price", current_sl):
                            logger.info(f"📈 TRAILING SL UPGRADED ({coin} {side}): ${state.get('sl_price'):,.2f} ➔ ${new_sl:,.2f}")
                            state["sl_price"] = new_sl

                        # Emergency Pre-Liquidation Guard Check
                        liq_price = state.get("liquidation_price", 0.0)
                        emergency_sl = calc_emergency_sl(liq_price, entry, side)

                        should_emergency_exit = False
                        if side == "LONG" and mark_price <= emergency_sl:
                            should_emergency_exit = True
                        elif side == "SHORT" and mark_price >= emergency_sl:
                            should_emergency_exit = True

                        if should_emergency_exit:
                            logger.warning(f"🚨 PRE-LIQUIDATION SAFETY GUARD TRIGGERED! Exiting {coin} FUTURES {side} at ${mark_price:,.2f}")
                            self.client.place_order(spot_sym, "SELL" if side == "LONG" else "BUY", state.get("size", 0.001), market_type="futures")
                            del self.active_positions[coin]

                        elif (side == "LONG" and mark_price <= state.get("sl_price", 0.0)) or \
                             (side == "SHORT" and mark_price >= state.get("sl_price", 0.0)):
                            logger.warning(f"🛑 STOP-LOSS TRIGGERED ({coin} {side}): ${mark_price:,.2f}")
                            del self.active_positions[coin]
                        elif (side == "LONG" and mark_price >= state.get("tp_price", 0.0)) or \
                             (side == "SHORT" and mark_price <= state.get("tp_price", 0.0)):
                            logger.info(f"🎯 +20% TAKE-PROFIT TRIGGERED ({coin} {side}): ${mark_price:,.2f}")
                            del self.active_positions[coin]

                    # 2) Signal Evaluation for New FUTURES Entries
                    elif coin not in self.active_positions:
                        sig = self.strategy.evaluate_multi_source_signal(mark_price, p_hist, pair=candle_pair)
                        conf = sig["confidence"]
                        side = sig.get("side", "LONG")

                        if sig.get("action") == "EXECUTE" and conf >= 98.0:
                            m_type = "futures"
                            coin_risk = futures_mapper.get_coin_risk_params(coin)
                            leverage = apply_leverage_cap(coin_risk["leverage"])
                            sl_price = sig.get("sl_price", round(mark_price * 0.90, 2))
                            tp_price = sig.get("tp_price", round(mark_price * 1.20, 2))
                            size = calc_position_size(equity, mark_price, sl_price, coin)
                            liq_price = calc_liquidation_price(mark_price, side, leverage)

                            resp = self.client.place_order(
                                symbol=spot_sym,
                                side=side,
                                amount=size,
                                leverage=leverage,
                                sl_price=sl_price,
                                tp_price=tp_price,
                                market_type=m_type
                            )

                            if isinstance(resp, list) and len(resp) > 0 and "id" in resp[0]:
                                order_id = resp[0]["id"]
                                logger.info(f"🚀 {coin} PERFECT +20% ALTCOIN FUTURES ORDER EXECUTED: {side} {size} {coin} @ ${mark_price:,.2f} | Leverage: {leverage}x | Order ID: {order_id}")
                                self.active_positions[coin] = {
                                    "coin": coin,
                                    "side": side,
                                    "entry_price": mark_price,
                                    "size": size,
                                    "leverage": leverage,
                                    "sl_price": sl_price,
                                    "tp_price": tp_price,
                                    "highest": mark_price,
                                    "lowest": mark_price,
                                    "liquidation_price": liq_price,
                                    "confidence": conf,
                                    "is_breakeven_set": False,
                                    "signal_source": f"98%_PERFECT_ALTCOIN_{coin}_20PCT_SCALP",
                                    "news_summary": sig.get("summary", "N/A")
                                }

                time.sleep(LOOP_INTERVAL_SEC)

            except Exception as e:
                logger.exception(f"Error in master loop: {e}")
                time.sleep(LOOP_INTERVAL_SEC)

if __name__ == "__main__":
    agent = MasterAgent()
    agent.run_master_loop()
