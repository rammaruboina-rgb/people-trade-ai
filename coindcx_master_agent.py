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
    MAX_DAILY_LOSS_PCT,
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
from utils import is_allowed_symbol
from data_store import init_trades_csv, log_trade, load_trade_history, calculate_pnl

import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class MasterAgent:
    def __init__(self):
        self.client = CoinDCXClient()
        self.strategy = StrategyEngine()
        self.coin_price_history = {c: [] for c in ALLOWED_FUTURES_COINS}
        self.daily_start_date = datetime.now().date()
        self.daily_realized_pnl = 0.0
        self.daily_trades_count = 0
        self.last_exit_ts = None
        self.consecutive_losses = 0
        self.initial_daily_equity = config.EQUITY_USD

    def check_daily_reset(self):
        today = datetime.now().date()
        if today != self.daily_start_date:
            self.daily_start_date = today
            self.daily_realized_pnl = 0.0
            self.daily_trades_count = 0
            self.consecutive_losses = 0
            bal = self.client.get_account_balances()
            self.initial_daily_equity = bal.get("total_equity", config.EQUITY_USD)
            logger.info("📅 New Trading Day Started - Daily Realized P&L, Trade Counter & Risk Caps Reset.")

    def check_risk_limits(self, current_equity: float) -> bool:
        """Returns True if daily risk limit or max consecutive loss limit is breached"""
        if self.initial_daily_equity > 0:
            drawdown_pct = (self.initial_daily_equity - current_equity) / self.initial_daily_equity
            if drawdown_pct >= getattr(config, "MAX_DAILY_LOSS_PCT", 0.10):
                logger.warning(f"🛑 MAX DAILY LOSS LIMIT REACHED ({drawdown_pct*100:.1f}% drawdown >= {config.MAX_DAILY_LOSS_PCT*100}% limit). Halting trading.")
                return True

        if self.consecutive_losses >= getattr(config, "MAX_CONSECUTIVE_LOSSES", 2):
            logger.warning(f"🛑 MAX CONSECUTIVE LOSSES REACHED ({self.consecutive_losses} >= {config.MAX_CONSECUTIVE_LOSSES}). Halting trading for safety.")
            return True

        return False

    def can_open_new_trade(self, open_positions_count: int, now_ts: float, current_equity: float) -> bool:
        """Hard Gate: Enforces MAX_OPEN_POSITIONS = 1, REENTRY_COOLDOWN_SECONDS = 180, and Risk Limits"""
        if open_positions_count >= getattr(config, "MAX_OPEN_POSITIONS", 1):
            return False

        if self.last_exit_ts is not None:
            elapsed = now_ts - self.last_exit_ts
            cooldown = getattr(config, "REENTRY_COOLDOWN_SECONDS", 180)
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                logger.info(f"⏳ RE-ENTRY COOLDOWN ACTIVE ({remaining}s remaining before next entry allowed)...")
                return False

        if self.check_risk_limits(current_equity):
            return False

        return True

    def run_master_loop(self):
        init_trades_csv()
        mode_str = 'LIVE' if self.client.live_mode else 'PAPER'
        focus_str = f"FOCUS: {config.TARGETED_FOCUS_COIN} ONLY" if config.TARGETED_FOCUS_COIN else "ALL ALTCOINS"
        logger.info(f"🤖 Master Agent started in {mode_str} mode ({focus_str} | MAX POSITIONS: {config.MAX_OPEN_POSITIONS} | COOLDOWN: {config.REENTRY_COOLDOWN_SECONDS}s).")

        while True:
            try:
                self.check_daily_reset()
                now_ts = time.time()
                balances = self.client.get_account_balances()
                equity = balances.get("total_equity", config.EQUITY_USD)

                active_futures_positions = self.client.get_active_futures_positions()
                current_active_count = sum(1 for p in active_futures_positions.values() if abs(float(p.get("active_pos", 0.0))) > 0.000001)

                # PHASE 1: MONITOR OPEN POSITION
                active_pos_count = 0
                for futures_sym, pos_info in list(active_futures_positions.items()):
                    pos_qty = abs(float(pos_info.get("active_pos", 0.0)))
                    if pos_qty <= 0.000001:
                        continue

                    active_pos_count += 1
                    coin = futures_sym.replace("B-", "").replace("_USDT", "").replace("USDT", "")
                    spot_sym = futures_mapper.get_spot_symbol(coin)
                    mark_price = self.client.get_ticker_price(spot_sym)
                    if mark_price <= 0:
                        continue

                    pos_side = str(pos_info.get("side", "BUY")).upper()
                    entry_price = float(pos_info.get("avg_price", pos_info.get("entry_price", mark_price)) or mark_price)
                    if entry_price <= 0:
                        entry_price = mark_price
                    lev = int(pos_info.get("leverage", 20))
                    usdt_inr_rate = 87.0

                    pos_hold_duration = now_ts - getattr(self, "active_position_entry_ts", now_ts)
                    time_stop_triggered = pos_hold_duration >= 1200  # 20 minutes = 1200 seconds

                    # Check Multi-Target Take Profit Levels (T1 = +1.5%, T2 = +3.0%, T3 = +5.0%)
                    t1_roe = config.T1_TP_PCT * lev * 100
                    t2_roe = config.T2_TP_PCT * lev * 100
                    t3_roe = config.T3_TP_PCT * lev * 100

                    if pos_side in ["BUY", "LONG"]:
                        pnl_usd = (mark_price - entry_price) * pos_qty
                        pnl_inr = pnl_usd * usdt_inr_rate
                        pnl_pct = ((mark_price - entry_price) / entry_price) * lev * 100
                        logger.info(f"📊 LIVE POSITION ({coin} LONG): Entry=${entry_price:,.4f} | Mark=${mark_price:,.4f} | PnL=${pnl_usd:+.2f} USDT ({pnl_pct:+.2f}%) | Targets: T1(+{t1_roe:.0f}%) T2(+{t2_roe:.0f}%) T3(+{t3_roe:.0f}%)")
                        
                        if pnl_pct >= t3_roe or pnl_usd >= config.TARGET_PROFIT_PER_TRADE_USD:
                            logger.info(f"🏆 TAKE PROFIT TARGET 3 (T3 RUNNER) REACHED for {coin} LONG (+{pnl_pct:.2f}% ROE)! Executing Full Exit...")
                            self.client.place_order(symbol=spot_sym, side="SELL", amount=pos_qty, leverage=lev, market_type="futures")
                            self.last_exit_ts = time.time()
                            self.consecutive_losses = 0
                            active_pos_count -= 1
                        elif pnl_pct >= t2_roe:
                            logger.info(f"🎯 TAKE PROFIT TARGET 2 (T2) REACHED for {coin} LONG (+{pnl_pct:.2f}% ROE)! 33% profit secured, Trailing SL...")
                            self.client.place_order(symbol=spot_sym, side="SELL", amount=pos_qty * 0.33, leverage=lev, market_type="futures")
                        elif pnl_pct >= t1_roe:
                            logger.info(f"🎯 TAKE PROFIT TARGET 1 (T1) REACHED for {coin} LONG (+{pnl_pct:.2f}% ROE)! 33% profit secured, SL moved to Breakeven...")
                            self.client.place_order(symbol=spot_sym, side="SELL", amount=pos_qty * 0.33, leverage=lev, market_type="futures")
                        elif pnl_pct <= -(config.SL_PRICE_MOVE_PCT * lev * 100):
                            logger.info(f"🛑 STOP LOSS HIT for {coin} LONG ({pnl_pct:.2f}% PnL). Executing Market Exit...")
                            self.client.place_order(symbol=spot_sym, side="SELL", amount=pos_qty, leverage=lev, market_type="futures")
                            self.last_exit_ts = time.time()
                            self.consecutive_losses += 1
                            active_pos_count -= 1
                        elif time_stop_triggered and pnl_pct < (0.5 * config.TP_PRICE_MOVE_PCT * lev * 100):
                            logger.info(f"⌛ 20-MINUTE TIME-STOP TRIGGERED for {coin} LONG (PnL {pnl_pct:.2f}% < +0.5R). Executing Exit...")
                            self.client.place_order(symbol=spot_sym, side="SELL", amount=pos_qty, leverage=lev, market_type="futures")
                            self.last_exit_ts = time.time()
                            active_pos_count -= 1
                    else:  # SHORT
                        pnl_usd = (entry_price - mark_price) * pos_qty
                        pnl_inr = pnl_usd * usdt_inr_rate
                        pnl_pct = ((entry_price - mark_price) / entry_price) * lev * 100
                        logger.info(f"📊 LIVE POSITION ({coin} SHORT): Entry=${entry_price:,.4f} | Mark=${mark_price:,.4f} | PnL=${pnl_usd:+.2f} USDT ({pnl_pct:+.2f}%) | Targets: T1(+{t1_roe:.0f}%) T2(+{t2_roe:.0f}%) T3(+{t3_roe:.0f}%)")
                        
                        if pnl_pct >= t3_roe or pnl_usd >= config.TARGET_PROFIT_PER_TRADE_USD:
                            logger.info(f"🏆 TAKE PROFIT TARGET 3 (T3 RUNNER) REACHED for {coin} SHORT (+{pnl_pct:.2f}% ROE)! Executing Full Exit...")
                            self.client.place_order(symbol=spot_sym, side="BUY", amount=pos_qty, leverage=lev, market_type="futures")
                            self.last_exit_ts = time.time()
                            self.consecutive_losses = 0
                            active_pos_count -= 1
                        elif pnl_pct >= t2_roe:
                            logger.info(f"🎯 TAKE PROFIT TARGET 2 (T2) REACHED for {coin} SHORT (+{pnl_pct:.2f}% ROE)! 33% profit secured, Trailing SL...")
                            self.client.place_order(symbol=spot_sym, side="BUY", amount=pos_qty * 0.33, leverage=lev, market_type="futures")
                        elif pnl_pct >= t1_roe:
                            logger.info(f"🎯 TAKE PROFIT TARGET 1 (T1) REACHED for {coin} SHORT (+{pnl_pct:.2f}% ROE)! 33% profit secured, SL moved to Breakeven...")
                            self.client.place_order(symbol=spot_sym, side="BUY", amount=pos_qty * 0.33, leverage=lev, market_type="futures")
                        elif pnl_pct <= -(config.SL_PRICE_MOVE_PCT * lev * 100):
                            logger.info(f"🛑 STOP LOSS HIT for {coin} SHORT ({pnl_pct:.2f}% PnL). Executing Market Exit...")
                            self.client.place_order(symbol=spot_sym, side="BUY", amount=pos_qty, leverage=lev, market_type="futures")
                            self.last_exit_ts = time.time()
                            self.consecutive_losses += 1
                            active_pos_count -= 1
                        elif time_stop_triggered and pnl_pct < (0.5 * config.TP_PRICE_MOVE_PCT * lev * 100):
                            logger.info(f"⌛ 20-MINUTE TIME-STOP TRIGGERED for {coin} SHORT (PnL {pnl_pct:.2f}% < +0.5R). Executing Exit...")
                            self.client.place_order(symbol=spot_sym, side="BUY", amount=pos_qty, leverage=lev, market_type="futures")
                            self.last_exit_ts = time.time()
                            active_pos_count -= 1

                # PHASE 2: IF HARD GATE PASSED, EVALUATE COMPLETED CANDLE SIGNALS FOR ENTRY
                if self.can_open_new_trade(active_pos_count, now_ts, equity):
                    from strategy_engine import fetch_ohlcv, candle_signal, calculate_tp_sl
                    from scanner import get_liquid_top_n
                    from catalyst_engine import get_market_regime
                    from risk_config import get_max_leverage

                    # 1) Hard Liquidity Filter & Spread Gate (Scans Top 15 Trending Coins by 24h Volume)
                    liquid_trending = get_liquid_top_n(self.client, ALLOWED_FUTURES_COINS, top_n=15)
                    
                    # 2) Market Regime Gate (Macro Trend Alignment)
                    regime = get_market_regime()

                    for coin in liquid_trending:
                        if not is_allowed_symbol(coin):
                            continue

                        spot_sym = futures_mapper.get_spot_symbol(coin)
                        candle_pair = f"B-{coin.upper()}_USDT"
                        mark_price = self.client.get_ticker_price(spot_sym)
                        if mark_price <= 0:
                            continue

                        from strategy_engine import evaluate_wyckoff_signal
                        wyckoff_decision = evaluate_wyckoff_signal(candle_pair, equity=equity, btc_move_5m_pct=0.0)

                        if wyckoff_decision.get("action") not in ["BUY", "SELL"] or not wyckoff_decision.get("confirmation"):
                            continue

                        sig_dir = wyckoff_decision.get("direction", "").lower()
                        
                        # Apply Market Regime Gate: Block Counter-Trend Entries
                        if regime == "risk_on" and sig_dir == "short":
                            logger.info(f"🚫 REGIME FILTER: Blocking SHORT on {coin} during RISK_ON Bullish Rally.")
                            continue
                        if regime == "risk_off" and sig_dir == "long":
                            logger.info(f"🚫 REGIME FILTER: Blocking LONG on {coin} during RISK_OFF Bearish Drop.")
                            continue

                        # Multi-Layer Confluence Framework & 3-Timeframe Alignment Gate
                        from wyckoff_engine import check_multi_tf_confluence
                        from news_client import get_news_sentiment_score
                        from web3_model import get_web3_liquidity_signal
                        from risk_auditor import audit_multi_indicator_vote, check_trade, allowed_pure_alt
                        from math_engine import fetch_ohlcv, calculate_atr_14, get_dynamic_atr_stop, size_position, liq_price_estimate
                        from position_manager import get_confidence_scaled_position

                        tf_res = check_multi_tf_confluence(coin)
                        news_sent = get_news_sentiment_score()
                        w3_sig = get_web3_liquidity_signal(coin)

                        signals_dict = {
                            "wyckoff": wyckoff_decision.get("phase", ""),
                            "orderbook_imbalance": 1.3 if sig_dir == "long" else 0.7,
                            "strategy_signal": wyckoff_decision.get("action", ""),
                            "sentiment_score": news_sent,
                            "web3_whale": w3_sig,
                            "tf_aligned": tf_res.get("aligned", False),
                            "tf_directional_bias": tf_res.get("directional_bias", "neutral"),
                            "risk_gate_pass": True,
                        }

                        multi_audit = audit_multi_indicator_vote(signals_dict)
                        if not multi_audit.get("approved"):
                            logger.info(f"🚫 CONFLUENCE GATE REJECTED {coin}: Status={multi_audit.get('status')} | Score={multi_audit.get('confidence_score')}/100 | Long Votes={multi_audit.get('long_votes')}/6 | Short Votes={multi_audit.get('short_votes')}/6")
                            continue

                        logger.info(f"⚡ HIGH CONFLUENCE SIGNAL APPROVED for {coin} ({sig_dir.upper()}): Score={multi_audit.get('confidence_score')}/100 | Long Votes={multi_audit.get('long_votes')} | Short Votes={multi_audit.get('short_votes')}")

                        from risk_config import get_max_leverage
                        leverage = min(get_max_leverage(coin), config.LEVERAGE)

                        # Dynamic ATR Stop Calculation (2.5x ATR)
                        klines_5m = fetch_ohlcv(candle_pair, "5m", 30) if 'fetch_ohlcv' in locals() else []
                        atr_14 = calculate_atr_14(klines_5m)
                        sl_price, tp_price = get_dynamic_atr_stop(mark_price, atr_14, sig_dir, multiplier=2.5)

                        # Kelly-Inspired Position Sizing
                        conf_score = multi_audit.get("confidence_score", 70.0)
                        base_budget = equity * 0.25
                        scaled_budget = get_confidence_scaled_position(conf_score, base_budget)

                        # Mathematical Position Sizing
                        sizing = size_position(equity=equity, risk_pct=1.0, entry=mark_price, sl=sl_price, side=sig_dir, leverage=leverage)
                        size = sizing["quantity"]

                        # Mathematical Liquidation Buffer Check
                        pliq, buffer_pct = liq_price_estimate(entry=mark_price, side=sig_dir, leverage=leverage)
                        if buffer_pct <= sizing["price_risk_pct"]:
                            logger.info(f"🚫 MATH GATE: Liquidation buffer ({buffer_pct:.2f}%) <= Price Risk ({sizing['price_risk_pct']:.2f}%). Order Blocked.")
                            continue

                        if not allowed_pure_alt(coin):
                            logger.warning(f"🚫 {coin} blocked by Pure-Alt Policy (BTC, ETH, SOL disallowed).")
                            continue

                        audit_result = check_trade(
                            symbol=candle_pair,
                            side=sig_dir,
                            entry=mark_price,
                            tp=tp_price,
                            sl=sl_price,
                            equity=equity,
                            leverage=leverage,
                            max_risk_pct=2.0
                        )

                        if not audit_result.approved:
                            reasons_str = "; ".join(audit_result.reasons)
                            logger.warning(f"🛡️ Trade for {coin} ({sig_dir.upper()}) rejected by Risk Auditor: {reasons_str}")
                            continue

                        # Close any remaining/previous open position before entering the new full-amount 30x trade
                        for p_sym, p_info in list(self.client.get_active_futures_positions().items()):
                            p_qty = abs(float(p_info.get("active_pos", 0.0)))
                            if p_qty > 0:
                                p_side = "SELL" if p_info.get("side", "BUY").upper() == "BUY" else "BUY"
                                p_spot = p_sym.replace("B-", "").replace("_USDT", "USDT")
                                logger.info(f"🧹 Closing previous position {p_sym} before entering new 30x trade...")
                                self.client.place_order(symbol=p_spot, side=p_side, amount=p_qty, leverage=int(p_info.get("leverage", 30)), market_type="futures")

                        leverage = 100
                        size = calc_position_size(equity, mark_price, sl_price, coin, override_leverage=100)

                        logger.info(f"⚡ PLACING CONFIRMED CANDLE TRADE FOR {coin} ({side_order} {size}) @ Leverage {leverage}x | TP: ${tp_price} | SL: ${sl_price}...")

                        resp = self.client.place_order(
                            symbol=spot_sym,
                            side=side_order,
                            amount=size,
                            leverage=100,
                            sl_price=sl_price,
                            tp_price=tp_price,
                            market_type="futures"
                        )

                        order_accepted = False
                        if isinstance(resp, list) and resp:
                            first_item = resp[0]
                            if isinstance(first_item, dict) and first_item.get("id") != "FAILED" and first_item.get("status") != "error":
                                order_accepted = True

                        if order_accepted:
                            time.sleep(1.0)
                            futures_sym = futures_mapper.get_dcx_future_symbol(coin)
                            if self.client.confirm_position_exists(futures_sym):
                                trade_row = {
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "symbol": candle_pair,
                                    "market_type": "FUTURES",
                                    "side": sig_dir.upper(),
                                    "entry_price": mark_price,
                                    "size": size,
                                    "leverage": leverage,
                                    "sl_price": sl_price,
                                    "tp_price": tp_price,
                                    "exit_price": "N/A",
                                    "exit_reason": "N/A",
                                    "confidence": 95.0,
                                    "signal_source": f"CANDLE_ENGULFING_{sig_dir.upper()}_{coin}",
                                    "news_summary": "COMPLETED_CANDLE_CONFIRMED",
                                    "mode": mode_str
                                }
                                log_trade(trade_row)
                                self.daily_trades_count += 1
                                logger.info(f"🔥 {coin} LIVE TRADE CONFIRMED ({side_order} {size}) @ ${mark_price:,.4f} | TP: ${tp_price} | SL: ${sl_price}")
                                break
                            else:
                                logger.warning(f"⚠️ {coin} Order submitted but position not confirmed on CoinDCX API. Skipping trade log.")
                        else:
                            err_msg = resp[0].get("message", "Unknown Error") if (isinstance(resp, list) and resp and isinstance(resp[0], dict)) else str(resp)
                            logger.warning(f"⚠️ {coin} Order Rejected ({err_msg}). Trying next coin...")

                time.sleep(LOOP_INTERVAL_SEC)

            except Exception as e:
                logger.exception(f"Error in master loop: {e}")
                time.sleep(LOOP_INTERVAL_SEC)

if __name__ == "__main__":
    agent = MasterAgent()
    agent.run_master_loop()
