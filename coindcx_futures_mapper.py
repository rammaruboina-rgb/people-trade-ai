# coindcx_futures_mapper.py
"""
Dynamic CoinDCX Altcoin Futures Instrument Discovery & Risk Mapper
Discovers all 495+ active CoinDCX futures markets dynamically.
Maps coin names (BTC, ETH, SOL, DOGE, XRP, ADA, PEPE, SHIB, etc.) to exact DCX symbols.
Includes automatic local disk caching & fallback protection for zero disruption during network glitches.
"""

import json
import logging
import os
import requests

logger = logging.getLogger(__name__)

ACTIVE_INSTRUMENTS_URL = "https://api.coindcx.com/exchange/v1/derivatives/futures/data/active_instruments"
CACHE_FILE = "coindcx_futures_symbols.json"

class CoinDCXFuturesMapper:
    def __init__(self):
        self.active_instruments = []
        self.coin_map = {}
        self.load_futures_instruments()

    def load_futures_instruments(self):
        """Fetch active futures instruments dynamically from CoinDCX API with disk cache fallback"""
        # Try loading from local disk cache first
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    cached_data = json.load(f)
                    if isinstance(cached_data, dict) and "instruments" in cached_data:
                        self.active_instruments = cached_data["instruments"]
                        self.coin_map = cached_data.get("coin_map", {})
            except Exception:
                pass

        try:
            res = requests.get(ACTIVE_INSTRUMENTS_URL, timeout=4)
            if res.status_code == 200 and isinstance(res.json(), list):
                self.active_instruments = res.json()
                for symbol in self.active_instruments:
                    if symbol.startswith("B-") and symbol.endswith("_USDT"):
                        coin = symbol[2:-5].upper()
                        self.coin_map[coin] = symbol

                # Save updated disk cache
                with open(CACHE_FILE, "w") as f:
                    json.dump({"total": len(self.active_instruments), "instruments": self.active_instruments, "coin_map": self.coin_map}, f, indent=2)
                return
        except Exception:
            pass

        if not self.active_instruments:
            self.active_instruments = self._fallback_instruments()
            for symbol in self.active_instruments:
                if symbol.startswith("B-") and symbol.endswith("_USDT"):
                    coin = symbol[2:-5].upper()
                    self.coin_map[coin] = symbol

    def _fallback_instruments(self):
        return [
            "B-BTC_USDT", "B-ETH_USDT", "B-SOL_USDT", "B-DOGE_USDT", "B-XRP_USDT",
            "B-ADA_USDT", "B-AVAX_USDT", "B-PEPE_USDT", "B-SHIB_USDT", "B-LINK_USDT",
            "B-SUI_USDT", "B-APT_USDT", "B-ARB_USDT", "B-OP_USDT", "B-NEAR_USDT"
        ]

    def get_dcx_future_symbol(self, coin: str) -> str:
        """Map any coin symbol (e.g. BTC, ETH, SOL, DOGE) to exact DCX futures symbol"""
        coin_upper = coin.upper()
        if coin_upper in self.coin_map:
            return self.coin_map[coin_upper]
        return f"B-{coin_upper}_USDT"

    def get_spot_symbol(self, coin: str) -> str:
        """Map coin to spot symbol (e.g. BTCUSDT)"""
        return f"{coin.upper()}USDT"

    def get_coin_risk_params(self, coin: str):
        coin_upper = coin.upper()
        if coin_upper in ["BTC", "ETH"]:
            return {
                "risk_per_trade_pct": 1.5,
                "sl_pct": 0.008,
                "tp_pct": 0.010,
                "leverage": 5,
                "confidence_threshold": 90.0
            }
        else:
            return {
                "risk_per_trade_pct": 1.0,
                "sl_pct": 0.008,
                "tp_pct": 0.010,
                "leverage": 3,
                "confidence_threshold": 90.0
            }

    def get_all_supported_coins(self):
        return list(self.coin_map.keys())

# Singleton Mapper Instance
futures_mapper = CoinDCXFuturesMapper()

if __name__ == "__main__":
    print(f"🚀 Loaded {len(futures_mapper.active_instruments)} CoinDCX Futures Pairs.")
