import sys
import requests
from config import ALLOWED_FUTURES_COINS
from strategy_engine import get_top_trending_altcoins, fetch_ohlcv, calculate_rsi
from news_client import get_catalyst_event_score, get_global_crypto_news_feed

def analyze_why_trending():
    top_coins = get_top_trending_altcoins(ALLOWED_FUTURES_COINS, top_n=8)
    
    # Fetch 24h ticker data from Binance API
    binance_data = {}
    try:
        res = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=5)
        if res.status_code == 200:
            for item in res.json():
                sym = item.get("symbol", "").replace("USDT", "")
                binance_data[sym] = {
                    "priceChangePercent": float(item.get("priceChangePercent", 0.0)),
                    "volumeUSD": float(item.get("quoteVolume", 0.0)),
                    "highPrice": float(item.get("highPrice", 0.0)),
                    "lowPrice": float(item.get("lowPrice", 0.0)),
                    "lastPrice": float(item.get("lastPrice", 0.0))
                }
    except Exception as e:
        print("Warning fetching 24h ticker details:", e)

    print("=" * 75)
    print("🔍 AGENT DIAGNOSTIC REPORT: WHY THESE ALTCOINS ARE TRENDING RIGHT NOW")
    print("=" * 75)

    for idx, coin in enumerate(top_coins, 1):
        pair = f"B-{coin}_USDT"
        candles = fetch_ohlcv(pair=pair, interval="1m", limit=30)
        closes = [c[4] for c in candles] if candles else []
        rsi_val = calculate_rsi(closes, period=min(14, len(closes)-1)) if len(closes) > 5 else 50.0
        
        info = binance_data.get(coin, {})
        pct_change = info.get("priceChangePercent", 0.0)
        vol_usd = info.get("volumeUSD", 0.0)
        price = info.get("lastPrice", closes[-1] if closes else 0.0)
        
        cat = get_catalyst_event_score(coin)
        
        reasons = []
        if abs(pct_change) >= 5.0:
            reasons.append(f"High 24h Price Move ({pct_change:+.2f}%)")
        elif abs(pct_change) >= 2.0:
            reasons.append(f"Active Price Surge ({pct_change:+.2f}%)")
        else:
            reasons.append(f"Moderate Price Movement ({pct_change:+.2f}%)")
            
        if vol_usd > 50_000_000:
            reasons.append(f"Massive Liquidity (${vol_usd/1e6:.1f}M 24h Vol)")
        elif vol_usd > 10_000_000:
            reasons.append(f"Strong Volume (${vol_usd/1e6:.1f}M 24h Vol)")
            
        if rsi_val >= 65:
            reasons.append(f"Bullish RSI Momentum ({rsi_val:.1f})")
        elif rsi_val <= 35:
            reasons.append(f"Oversold RSI Dip ({rsi_val:.1f})")
            
        if cat.get("has_catalyst"):
            reasons.append(f"Catalyst Event: {cat.get('event_description')}")
            
        reason_str = " | ".join(reasons)
        print(f"{idx}. [{coin}] (${price}) -> Rationale: {reason_str}")

if __name__ == "__main__":
    analyze_why_trending()
