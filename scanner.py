# scanner.py
from typing import List, Tuple
import requests

def get_liquid_top_n(
    client,
    allowed_symbols: List[str],
    top_n: int = 10,
    min_quote_volume_24h: float = 5_000_000, # 5M USDT volume threshold
    max_spread_bps: float = 15.0,              # 0.15% max bid-ask spread
) -> List[str]:
    """
    Enforces strict liquidity and spread gates:
    - Excludes coins with 24h volume < $5M USDT
    - Excludes coins with bid-ask spread > 0.15%
    Returns sorted list of top N liquid symbols.
    """
    valid: List[Tuple[str, float]] = []

    for sym in allowed_symbols:
        clean_sym = sym.upper().replace("B-", "").replace("_USDT", "").replace("USDT", "") + "USDT"
        try:
            res = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={clean_sym}", timeout=3)
            if res.status_code == 200:
                ticker = res.json()
                last = float(ticker.get("lastPrice", 0) or 0)
                bid = float(ticker.get("bidPrice", 0) or 0)
                ask = float(ticker.get("askPrice", 0) or 0)
                quote_vol = float(ticker.get("quoteVolume", 0) or 0)

                if last <= 0 or bid <= 0 or ask <= 0:
                    continue

                spread_bps = ((ask - bid) / bid) * 10_000

                if quote_vol < min_quote_volume_24h:
                    continue
                if spread_bps > max_spread_bps:
                    continue

                valid.append((sym, quote_vol))
        except Exception:
            continue

    valid.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in valid[:top_n]]
