"""
Utility modules for CoinDCX Autonomous Agent
Contains symbol guard and validation rules.
"""

def is_allowed_symbol(symbol: str) -> bool:
    """
    Enforces strict rules:
      - No BTC, SOL, ETH unless explicitly allowed in settings/config
      - Only symbols in ALLOWED_SYMBOLS if PURE_ALTCOINS_ONLY is True
    """
    from settings import (
        TRADE_BTC,
        TRADE_SOL,
        TRADE_ETH,
        PURE_ALTCOINS_ONLY,
        ALLOWED_SYMBOLS,
    )

    upper = symbol.upper().strip()

    # Block BTC
    if not TRADE_BTC and ("BTC" in upper):
        return False

    # Block SOL
    if not TRADE_SOL and ("SOL" in upper):
        return False

    # Block ETH
    if not TRADE_ETH and ("ETH" in upper):
        return False

    # If pure altcoins only, symbol must be in allowed list or match asset ticker
    if PURE_ALTCOINS_ONLY:
        allowed_clean = [
            s.upper().replace("B-", "").replace("_USDT", "").replace("USDT", "").strip()
            for s in ALLOWED_SYMBOLS
        ]
        target_clean = upper.replace("B-", "").replace("_USDT", "").replace("USDT", "").strip()

        if target_clean not in allowed_clean:
            return False

    return True
