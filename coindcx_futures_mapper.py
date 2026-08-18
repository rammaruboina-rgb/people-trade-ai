# coindcx_futures_mapper.py
"""
CoinDCX Futures Symbol Mapper & Risk Parameter Store
Maps spot tickers (e.g. ETHUSDT) to CoinDCX Derivatives Futures contracts (e.g. B-ETH_USDT)
Enforces MAXIMUM 20X LEVERAGE across all pairs.
"""

import json
import os
import requests
import logging

logger = logging.getLogger(__name__)

CACHE_FILE = "coindcx_futures_symbols.json"

class CoinDCXFuturesMapper:
    def __init__(self):
        self.spot_to_future_map = {}
        self.coin_to_future_map = {}
        self.risk_params = {}

        self.load_cache()
        if not self.spot_to_future_map:
            self.fetch_active_instruments()

    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    data = json.load(f)
                    self.spot_to_future_map = data.get("spot_to_future", {})
                    self.coin_to_future_map = data.get("coin_to_future", {})
                    self.risk_params = data.get("risk_params", {})
            except Exception as e:
                logger.warning(f"Failed to load futures cache: {e}")

    def save_cache(self):
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({
                    "spot_to_future": self.spot_to_future_map,
                    "coin_to_future": self.coin_to_future_map,
                    "risk_params": self.risk_params
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save futures cache: {e}")

    def fetch_active_instruments(self):
        url = "https://api.coindcx.com/exchange/v1/derivatives/futures/data/active_instruments"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200 and isinstance(res.json(), list):
                instruments = res.json()
                for inst in instruments:
                    if isinstance(inst, str):
                        pair = inst
                        base = inst.replace("B-", "").replace("_USDT", "").replace("USDT", "").upper()
                    elif isinstance(inst, dict):
                        pair = inst.get("pair")
                        base = inst.get("target_currency_short_name", "").upper()
                    else:
                        continue

                    if pair and base:
                        spot_sym = f"{base}USDT"
                        self.spot_to_future_map[spot_sym] = pair
                        self.coin_to_future_map[base] = pair

                        # Force MAXIMUM 20X Leverage for all coins
                        self.risk_params[base] = {
                            "leverage": 20,
                            "min_qty": 0.001,
                            "step_size": 0.001,
                            "max_leverage": 20
                        }
                self.save_cache()
                return
        except Exception as e:
            logger.warning(f"⚠️ Error fetching CoinDCX futures pairs ({e}). Using cached/fallback instruments.")

        # Default fallback symbols with MAXIMUM 20X Leverage
        default_coins = [
            "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE", "TRX", "LTC", "BCH", "EOS",
            "LINK", "AVAX", "DOT", "ATOM", "NEAR", "APT", "SUI", "ARB", "OP", "SEI",
            "TON", "FIL", "INJ", "HBAR", "UNI", "ETC", "ICP", "PEPE", "SHIB", "WIF",
            "BONK", "ONDO", "JUP", "ENA", "FET", "RENDER", "TAO", "CRV", "AAVE", "MKR"
        ]
        for c in default_coins:
            fut = f"B-{c}_USDT"
            self.spot_to_future_map[f"{c}USDT"] = fut
            self.coin_to_future_map[c] = fut
            self.risk_params[c] = {"leverage": 20, "min_qty": 0.001, "step_size": 0.001, "max_leverage": 20}

    def get_dcx_future_symbol(self, coin_or_spot: str) -> str:
        clean = coin_or_spot.replace("USDT", "").replace("B-", "").split("_")[0].upper()
        if clean in self.coin_to_future_map:
            return self.coin_to_future_map[clean]
        return f"B-{clean}_USDT"

    def get_spot_symbol(self, coin_or_future: str) -> str:
        clean = coin_or_future.replace("USDT", "").replace("B-", "").split("_")[0].upper()
        return f"{clean}USDT"

    def get_coin_risk_params(self, coin: str) -> dict:
        clean = coin.upper()
        return self.risk_params.get(clean, {"leverage": 20, "min_qty": 0.001, "step_size": 0.001, "max_leverage": 20})

futures_mapper = CoinDCXFuturesMapper()
