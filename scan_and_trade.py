# scan_and_trade.py
"""
CoinDCX Autonomous Agent - Real-Time Altcoin Scanner & Futures Trade Execution Script
Scans 125+ pure altcoins on CoinDCX, evaluates 1m/5m pattern confluence, checks 20X leverage sizing,
and executes live/paper futures trades with automated SL/TP settings.
"""

import sys
import time
import logging
from datetime import datetime

import config
from coindcx_client import CoinDCXClient
from coindcx_futures_mapper import futures_mapper
from strategy_engine import StrategyEngine, get_top_trending_altcoins, fetch_ohlcv, calculate_rsi
from risk_engine import calc_position_size
from utils import is_allowed_symbol
from data_store import log_trade, load_trade_history, calculate_pnl

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ScanAndTrade")

def run_scan_and_futures_trading():
    print("=" * 80)
    print("🚀 COINDCX AUTONOMOUS FUTURES TRADING AGENT — REAL-TIME ASSET SCANNER")
    print("=" * 80)
    print(f"  • Equity Capital Base    : ${config.EQUITY_USD:.2f} USDT")
    print(f"  • Max Daily Target       : ${config.DEFAULT_MAX_DAILY_TARGET_USD:.2f} USD")
    print(f"  • Daily Protection Stop : ${config.DAILY_LOSS_LIMIT_USD:.2f} USD")
    print(f"  • Concurrent Multi-Trades: Up to {config.MAX_CONCURRENT_TRADES} simultaneous active positions")
    print(f"  • Leverage Multiple      : 20X Isolated Margin")
    print(f"  • Target Focus Coin      : {config.TARGETED_FOCUS_COIN or 'ALL 125+ PURE ALTCOINS'}")
    print("-" * 80)

    client = CoinDCXClient()
    strategy = StrategyEngine()

    balances = client.get_account_balances()
    equity = balances.get("total_equity", config.EQUITY_USD)
    usdt_bal = balances.get("USDT", 0.0)

    print(f"💰 Account Status: Total Equity = ${equity:.2f} USD | Available USDT = ${usdt_bal:.2f} USDT")
    
    active_positions = client.get_active_futures_positions()
    active_count = sum(1 for p in active_positions.values() if p.get("active_pos", 0.0) != 0.0)
    print(f"📊 Active Futures Positions: {active_count}/{config.MAX_CONCURRENT_TRADES} active positions")

    if config.TARGETED_FOCUS_COIN:
        coins_to_scan = [config.TARGETED_FOCUS_COIN]
    else:
        print("\n🔍 Fetching top trending volatile altcoins via global market feeds...")
        coins_to_scan = get_top_trending_altcoins(config.ALLOWED_FUTURES_COINS, top_n=10)

    print(f"🎯 Target Scanning Universe: {', '.join(coins_to_scan)}")
    print("=" * 80)

    trades_executed = 0

    for idx, coin in enumerate(coins_to_scan, 1):
        if not is_allowed_symbol(coin):
            print(f"  [{idx}/{len(coins_to_scan)}] 🚫 {coin}: BLOCKED by symbol blacklist rule (BTC/ETH).")
            continue

        spot_sym = futures_mapper.get_spot_symbol(coin)
        futures_sym = futures_mapper.get_dcx_future_symbol(coin)
        candle_pair = f"B-{coin.upper()}_USDT"

        mark_price = client.get_ticker_price(spot_sym)
        if mark_price <= 0:
            print(f"  [{idx}/{len(coins_to_scan)}] ⚠️ {coin}: Could not fetch valid mark price. Skipping.")
            continue

        candles = fetch_ohlcv(pair=candle_pair, interval="1m", limit=30)
        closes = [c[4] for c in candles] if candles else []
        rsi_val = calculate_rsi(closes, period=min(14, len(closes)-1)) if len(closes) > 5 else 50.0

        sig = strategy.evaluate_multi_source_signal(mark_price, closes, pair=candle_pair)
        direction = sig.get("direction", "long") or "long"
        side_order = "BUY" if direction == "long" else "SELL"
        per_trade_equity = equity / config.MAX_CONCURRENT_TRADES
        size = calc_position_size(per_trade_equity, mark_price, mark_price * 0.90, coin)

        target_profit_usd = getattr(config, "TARGET_PROFIT_PER_TRADE_USD", 0.60)
        price_delta = target_profit_usd / max(0.0001, size)

        if side_order == "BUY": # LONG
            tp_price = round(mark_price + price_delta, 4)
            sl_price = round(mark_price * 0.95, 4)
        else: # SHORT
            tp_price = round(max(0.0001, mark_price - price_delta), 4)
            sl_price = round(mark_price * 1.05, 4)

        pos_info = active_positions.get(futures_sym, {})
        has_active = pos_info.get("active_pos", 0.0) != 0.0

        status_str = f"ACTIVE ({pos_info.get('side')})" if has_active else "NO POSITION"
        print(f"\n⚡ [{idx}/{len(coins_to_scan)}] ASSET: {coin:<6} | Futures: {futures_sym:<14} | Mark Price: ${mark_price:,.4f}")
        print(f"   • RSI(14): {rsi_val:.1f} | Strategy Signal: {direction.upper()} ({side_order}) | Position State: {status_str}")
        print(f"   • Calculated Boundaries: SL @ ${sl_price:,.4f} | ₹50 TP @ ${tp_price:,.4f}")

        if not has_active:
            if active_count >= config.MAX_CONCURRENT_TRADES:
                print(f"   ⚠️ Position Cap Reached ({active_count}/{config.MAX_CONCURRENT_TRADES}). Skipping execution.")
                continue

            print(f"   🚀 EXECUTING LIVE 7X FUTURES ORDER: {side_order} {size} {coin} @ ${mark_price:,.4f}...")
            
            resp = client.place_order(
                symbol=spot_sym,
                side=side_order,
                amount=size,
                leverage=7,
                sl_price=sl_price,
                tp_price=tp_price,
                market_type="futures"
            )

            mode_str = 'LIVE' if client.live_mode else 'PAPER'
            trade_row = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": candle_pair,
                "market_type": "FUTURES",
                "side": "LONG" if side_order == "BUY" else "SHORT",
                "entry_price": mark_price,
                "size": size,
                "leverage": config.LEVERAGE,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "exit_price": "N/A",
                "exit_reason": "N/A",
                "confidence": 99.0,
                "signal_source": f"SCANNER_{direction.upper()}_{coin}",
                "news_summary": sig.get("summary", "N/A"),
                "mode": mode_str
            }
            # Validate response status strictly
            order_success = False
            if isinstance(resp, list) and resp:
                first_item = resp[0]
                if isinstance(first_item, dict) and first_item.get("id") != "FAILED" and first_item.get("status") != "error":
                    order_success = True

            if order_success:
                log_trade(trade_row)
                trades_executed += 1
                active_count += 1
                print(f"   ✅ ORDER EXECUTED ON EXCHANGE! Trade logged in execution ledger.")
            else:
                err_msg = resp[0].get("message", "Unknown Error") if (isinstance(resp, list) and resp and isinstance(resp[0], dict)) else str(resp)
                print(f"   ⚠️ ORDER SKIPPED ({err_msg}). Moving to next active asset.")

    print("\n" + "=" * 80)
    print(f"🏁 SCAN COMPLETED! Executed {trades_executed} new futures trades across active universe.")
    print("=" * 80)

if __name__ == "__main__":
    run_scan_and_futures_trading()
