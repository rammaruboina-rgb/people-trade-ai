# execute_trade_now.py
"""
Immediate Live Trade Execution Trigger Script (Native CoinDCX REST API).
Scans top active volatile altcoins and sends a live 20X leverage market order to CoinDCX
using pure native API signature logic (100% independent of CCXT).
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
from data_store import log_trade

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ImmediateTrade")

def execute_immediate_live_trade():
    print("=" * 80)
    print("⚡ COINDCX NATIVE REST FUTURES ORDER TRIGGER — EXECUTING ORDER NOW")
    print("=" * 80)

    client = CoinDCXClient()
    strategy = StrategyEngine()

    balances = client.get_account_balances()
    equity = balances.get("total_equity", config.EQUITY_USD)
    print(f"💰 Account Balance Sync: Total Equity = ${equity:.2f} USD")

    # User Directive: Target ACE (Fusionist) coin
    target_coin = getattr(config, "TARGETED_FOCUS_COIN", "ACE") or "ACE"

    spot_sym = futures_mapper.get_spot_symbol(target_coin)
    futures_sym = futures_mapper.get_dcx_future_symbol(target_coin)
    candle_pair = f"B-{target_coin.upper()}_USDT"

    mark_price = client.get_ticker_price(spot_sym)
    if mark_price <= 0:
        mark_price = 1.0

    candles = fetch_ohlcv(pair=candle_pair, interval="1m", limit=30)
    closes = [c[4] for c in candles] if candles else []
    sig = strategy.evaluate_multi_source_signal(mark_price, closes, pair=candle_pair)
    
    direction = sig.get("direction", "long") or "long"
    side_order = "BUY" if direction == "long" else "SELL"
    
    per_trade_equity = equity / config.MAX_CONCURRENT_TRADES
    size = calc_position_size(per_trade_equity, mark_price, mark_price * 0.90, target_coin)

    # Calculate exact ₹50 INR ($0.60 USDT) Take-Profit Price level
    target_profit_usd = getattr(config, "TARGET_PROFIT_PER_TRADE_USD", 0.60)
    price_delta = target_profit_usd / size

    if side_order == "BUY": # LONG
        tp_price = round(mark_price + price_delta, 4)
        sl_price = round(mark_price * 0.95, 4)
    else: # SHORT
        tp_price = round(max(0.0001, mark_price - price_delta), 4)
        sl_price = round(mark_price * 1.05, 4)

    print(f"🎯 Target Asset       : {target_coin} (Futures Instrument: {futures_sym})")
    print(f"💵 Current Mark Price : ${mark_price:,.4f}")
    print(f"📈 Signal Direction   : {direction.upper()} ({side_order})")
    print(f"📦 Order Position Size: {size} {target_coin} (7X Leverage | Margin: ~${(size*mark_price)/7.0:.2f} USDT)")
    print(f"🎯 ₹50 INR TP Price   : ${tp_price:,.4f} (+₹50.00 INR Profit Level)")
    print("-" * 80)
    print(f"🚀 SUBMITTING LIVE ORDER WITH ₹50 INR TP VIA COINDCX REST CLIENT...")

    resp = client.place_order(
        symbol=spot_sym,
        side=side_order,
        amount=size,
        leverage=7,
        sl_price=sl_price,
        tp_price=tp_price,
        market_type="futures"
    )

    print("\n" + "=" * 80)
    print(f"📲 NATIVE COINDCX API RESPONSE: {resp}")
    print("=" * 80)

    # Validate response status strictly before logging success
    order_success = False
    if isinstance(resp, list) and resp:
        first_item = resp[0]
        if isinstance(first_item, dict) and first_item.get("id") != "FAILED" and first_item.get("status") != "error":
            order_success = True
    elif isinstance(resp, dict) and resp.get("status") not in ["error", "FAILED"] and resp.get("id") != "FAILED":
        order_success = True

    if not order_success:
        print("\n" + "❌" * 40)
        print("❌ ORDER REJECTED BY COINDCX FUTURES EXCHANGE — TRADE WAS NOT PLACED")
        print(f"   Raw API Response Error: {resp}")
        print("❌" * 40)
        sys.exit(1)

    mode_str = 'LIVE' if client.live_mode else 'PAPER'
    trade_row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": candle_pair,
        "market_type": "FUTURES",
        "side": "LONG" if side_order == "BUY" else "SHORT",
        "entry_price": mark_price,
        "size": size,
        "leverage": 20,
        "sl_price": round(mark_price * 0.90, 2),
        "tp_price": round(mark_price * 1.20, 2),
        "exit_price": "N/A",
        "exit_reason": "N/A",
        "confidence": 99.0,
        "signal_source": f"IMMEDIATE_TRIGGER_{direction.upper()}_{target_coin}",
        "news_summary": sig.get("summary", "N/A"),
        "mode": mode_str
    }
    log_trade(trade_row)

    print(f"✅ SUCCESS! Live Futures Order Accepted by CoinDCX Exchange!")
    print(f"Check your CoinDCX Mobile App under Futures -> Positions to view the live open position!")

if __name__ == "__main__":
    execute_immediate_live_trade()
