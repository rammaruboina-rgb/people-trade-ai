# check_ccxt_symbols.py
import os
import sys
import json
import ccxt
from dotenv import load_dotenv

load_dotenv()

def inspect_coindcx_futures():
    print("=" * 80)
    print("🔍 INSPECTING COINDCX FUTURES MARKETS VIA CCXT")
    print("=" * 80)

    api_key = os.getenv("COINDCX_API_KEY", "")
    api_secret = os.getenv("COINDCX_API_SECRET", "")

    exchange = ccxt.coindcx({
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,
        "options": {"defaultType": "future"}
    })

    try:
        markets = exchange.load_markets()
        print(f"✅ Loaded {len(markets)} total markets from CoinDCX.")
        futures_markets = {sym: m for sym, m in markets.items() if m.get("future") or "B-" in sym or ":USDT" in sym}
        print(f"📊 Found {len(futures_markets)} Futures Markets:")
        for sym, m in list(futures_markets.items())[:15]:
            print(f"   • CCXT Symbol: {sym:<15} | Id: {m.get('id'):<15} | Base: {m.get('base'):<5} | Min Qty: {m.get('limits', {}).get('amount', {}).get('min')}")
    except Exception as e:
        print(f"❌ CCXT load_markets error: {e}")

if __name__ == "__main__":
    inspect_coindcx_futures()
