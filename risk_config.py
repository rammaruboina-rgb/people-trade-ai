# risk_config.py
from typing import Dict

MAX_LEVERAGE_BY_CLASS: Dict[str, int] = {
    "major_l1": 20,      # e.g., SOL, AVAX
    "high_liq_alt": 15,  # e.g., SUI, NEAR, INJ, TON, SEI
    "meme": 10,          # e.g., DOGE, PEPE, WIF, SHIB
}

SYMBOL_CLASS_MAP: Dict[str, str] = {
    "SOL": "major_l1",
    "AVAX": "major_l1",
    "SUI": "high_liq_alt",
    "NEAR": "high_liq_alt",
    "INJ": "high_liq_alt",
    "TON": "high_liq_alt",
    "SEI": "high_liq_alt",
    "DOGE": "meme",
    "PEPE": "meme",
    "WIF": "meme",
    "SHIB": "meme"
}

def get_max_leverage(symbol: str) -> int:
    """Returns strict leverage cap based on symbol asset class"""
    sym_clean = symbol.upper().replace("B-", "").replace("_USDT", "").replace("USDT", "")
    asset_class = SYMBOL_CLASS_MAP.get(sym_clean, "meme")
    return MAX_LEVERAGE_BY_CLASS.get(asset_class, 10)
