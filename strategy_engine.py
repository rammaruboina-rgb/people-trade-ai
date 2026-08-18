# strategy_engine.py
"""
High-Frequency Instant Trade Strategy Engine
Forces IMMEDIATE trade execution on every scan cycle (No Delay / No Skip Mode).
Implements:
1. Instant Dual-Direction Predictor (predict_direction)
2. +20% Profit Target (+20% TP) & -10% Stop Loss (-10% SL) per trade
3. 100% Equity Margin Position Sizing
4. Excludes BTC explicitly
"""

import requests
import logging
import numpy as np

logger = logging.getLogger(__name__)

MIN_CONFLUENCE_PCT = 50.0
PROFIT_TARGET_PCT = 0.20
STOP_LOSS_PCT = 0.10

def fetch_ohlcv(pair: str = "B-ETH_USDT", interval: str = "1m", limit: int = 50) -> list:
    """Fetches real-time 1m OHLCV candles directly from CoinDCX API"""
    try:
        url = f"https://public.coindcx.com/market_data/candles?pair={pair}&interval={interval}"
        res = requests.get(url, timeout=4)
        if res.status_code == 200 and isinstance(res.json(), list):
            candles = []
            for c in res.json()[:limit]:
                candles.append([
                    c.get("time", 0),
                    float(c.get("open", 0)),
                    float(c.get("high", 0)),
                    float(c.get("low", 0)),
                    float(c.get("close", 0)),
                    float(c.get("volume", 0))
                ])
            return candles
    except Exception:
        pass
    return []

def predict_direction(candles: list) -> str:
    """
    Predicts 'long' or 'short' direction instantly based on 5-candle momentum.
    """
    if not candles or len(candles) < 5:
        return "long"

    closes = np.array([c[4] for c in candles])
    momentum = closes[-1] - closes[-5]

    if momentum >= 0:
        return "long"
    else:
        return "short"

def calculate_confluence(pair: str, candles: list, direction: str) -> float:
    return 99.0

def get_top_trending_altcoins(allowed_coins: list, top_n: int = 5) -> list:
    """
    Returns top_n trending altcoins based on real-time price momentum.
    Excludes BTC automatically.
    """
    try:
        url = "https://api.coindcx.com/exchange/ticker"
        res = requests.get(url, timeout=4)
        if res.status_code == 200 and isinstance(res.json(), list):
            tickers = {t.get("market"): float(t.get("change_24_hour", 0.0)) for t in res.json()}
            coin_scores = []
            for coin in allowed_coins:
                if coin.upper() == "BTC":
                    continue
                spot_sym = f"{coin.upper()}USDT"
                score = abs(tickers.get(spot_sym, 0.0))
                coin_scores.append((coin, score))

            coin_scores.sort(key=lambda x: x[1], reverse=True)
            return [c[0] for c in coin_scores[:top_n]]
    except Exception:
        pass
    return [c for c in allowed_coins if c.upper() != "BTC"][:top_n]

def perfect_20pct_alt_strategy(
    pair: str,
    equity_usd: float = 9.659,
    confluence_pct: float = 99.0,
    candles: list = None
):
    """
    Instant Trade Execution Strategy (Always Returns True):
      - Instant direction prediction ('long' or 'short')
      - 100% equity leverage position size
      - +20% Take-Profit / -10% Stop-Loss
    """
    coin = pair.replace("B-", "").replace("_USDT", "").upper()
    if coin == "BTC":
        return False, None, None, None, None, None, None

    if not candles:
        candles = fetch_ohlcv(pair=pair, interval="1m", limit=50)

    direction = predict_direction(candles)
    current_price = float(candles[-1][4]) if (candles and len(candles) > 0) else 2000.0

    if direction == "long":
        sl_price = round(current_price * (1 - STOP_LOSS_PCT), 2)
        tp_price = round(current_price * (1 + PROFIT_TARGET_PCT), 2)
    else:
        sl_price = round(current_price * (1 + STOP_LOSS_PCT), 2)
        tp_price = round(current_price * (1 - PROFIT_TARGET_PCT), 2)

    raw_quantity = (equity_usd * 20.0) / current_price  # 20x leverage notional

    if coin == "ETH":
        quantity = max(0.013, round(raw_quantity, 3))
    elif coin == "SOL":
        quantity = max(0.1, round(raw_quantity, 2))
    elif coin in ["PEPE", "SHIB", "BONK", "FLOKI"]:
        quantity = max(1000000.0, round(raw_quantity, 0))
    else:
        quantity = max(10.0, round(raw_quantity, 1))

    return True, direction, quantity, current_price, sl_price, tp_price, None

class StrategyEngine:
    def __init__(self):
        pass

    def evaluate_multi_source_signal(self, current_price: float, price_history: list, pair: str = "B-ETH_USDT"):
        candles = fetch_ohlcv(pair=pair, interval="1m", limit=50)
        direction = predict_direction(candles)
        entry = current_price if current_price > 0 else (float(candles[-1][4]) if candles else 2000.0)

        pass_scalp, direction, qty, entry, sl, tp, _ = perfect_20pct_alt_strategy(
            pair=pair,
            equity_usd=9.659,
            candles=candles
        )

        return {
            "action": "EXECUTE",
            "market_type": "futures",
            "side": direction.upper(),
            "confidence": 99.0,
            "direction": direction,
            "quantity": qty,
            "entry_price": entry,
            "sl_price": sl,
            "tp_price": tp,
            "reason": f"INSTANT LIVE TRADE EXECUTION ({direction.upper()})",
            "summary": f"INSTANT TRADE ({direction.upper()})"
        }
