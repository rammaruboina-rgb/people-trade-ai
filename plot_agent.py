# plot_agent.py
"""
OHLCV Candlestick & Trade Chart Generator
Fetches live OHLCV candle data from CoinDCX and plots candlestick price charts with MA20 indicator.
Saves chart to candles_chart.png.
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def fetch_and_plot_candles(pair="B-BTC_USDT", interval="1m", limit=60):
    print(f"📊 Fetching {limit} OHLCV candles for {pair} from CoinDCX...")
    url = f"https://public.coindcx.com/market_data/candles?pair={pair}&interval={interval}"
    res = requests.get(url, timeout=5)

    if res.status_code != 200 or not isinstance(res.json(), list):
        print("❌ Failed to fetch candle data from CoinDCX.")
        return

    raw_candles = res.json()[:limit]
    candles = []
    for c in reversed(raw_candles):
        dt = datetime.fromtimestamp(c.get("time", 0) / 1000.0)
        candles.append({
            "timestamp": dt,
            "open": float(c.get("open", 0)),
            "high": float(c.get("high", 0)),
            "low": float(c.get("low", 0)),
            "close": float(c.get("close", 0)),
            "volume": float(c.get("volume", 0))
        })

    df = pd.DataFrame(candles)
    df["ma20"] = df["close"].rolling(window=20).mean()

    # Create Candlestick Plot
    plt.figure(figsize=(12, 6))
    plt.style.use("dark_background")

    # Plot Green/Red Candlestick Bodies & Wicks
    up = df[df.close >= df.open]
    down = df[df.close < df.open]

    plt.vlines(up.timestamp, up.low, up.high, color="#26a69a", linewidth=1)
    plt.vlines(down.timestamp, down.low, down.high, color="#ef5350", linewidth=1)

    plt.vlines(up.timestamp, up.open, up.close, color="#26a69a", linewidth=4)
    plt.vlines(down.timestamp, down.open, down.close, color="#ef5350", linewidth=4)

    # Plot MA20 Moving Average
    plt.plot(df.timestamp, df.ma20, color="#ffeb3b", label="MA20 Trend Line", linewidth=1.5)

    plt.title(f"🔥 CoinDCX {pair} Real-Time Candlestick Chart (1m OHLCV)", fontsize=14, color="white", fontweight="bold")
    plt.xlabel("Time", color="white")
    plt.ylabel("Price (USD)", color="white")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.legend(loc="upper left")
    plt.tight_layout()

    out_filename = "candles_chart.png"
    plt.savefig(out_filename, dpi=120)
    plt.close()
    print(f"✅ Candlestick Chart saved to {out_filename}!")

if __name__ == "__main__":
    fetch_and_plot_candles()
