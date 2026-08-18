# config.py
"""
Centralized Configuration Module for CoinDCX Master Trading Agent
Configured for High-Frequency Pure Altcoin Scalping (20 Trades / Day Target)
"""

import os
from dotenv import load_dotenv

load_dotenv()

# System Execution Parameters
MODE = os.getenv("MODE", "LIVE").upper()
LOG_FILE = "trading_bot.log"
TRADES_CSV = "trades_unified.csv"
LOOP_INTERVAL_SEC = 1.0  # Ultra-fast 1.0s scan rate

# Portfolio & Target Configuration
EQUITY_USD = 9.52
DEFAULT_MAX_DAILY_TARGET_USD = 20.0  # $20.00 USD / day target
MAX_DAILY_TRADES = 20               # 20 Trades per day frequency goal
DAILY_LOSS_LIMIT_USD = 9.52          # Max equity protection stop
MAX_CONCURRENT_TRADES = 3          # Up to 3 multi-trades active at the same time
RISK_PER_TRADE_PCT = 100.0          # Full leverage equity margin sizing
LEVERAGE = 20
MAX_LEVERAGE_CAP = 20
ALTCOIN_LEVERAGE_CAP = 20
LIQUIDATION_SAFETY_BUFFER_PCT = 0.05
DEFAULT_SL_PCT = 0.10
DEFAULT_TP_PCT = 0.20
MARGIN_MODE = "isolated"

# Strategy Rules
TIMEFRAME = "1m"
MIN_CONFLUENCE_PCT = 50.0
PROFIT_TARGET_PCT = 0.20  # +20.0% TP
STOP_LOSS_PCT = 0.10      # -10.0% SL
BREAKEVEN_PROFIT_PCT = 0.05 # Move SL to entry at +5.0% profit

# Webhook Server Parameters
WEBHOOK_ENABLED = os.getenv("WEBHOOK_ENABLED", "false").lower() == "true"
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5000"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "super_secret_webhook_token_123")

# CoinDCX Symbol Defaults (Pure Altcoin Default: SOL)
SYMBOL_SPOT = "SOLUSDT"
SYMBOL_FUTURES = "B-SOL_USDT"
CANDLE_PAIR = "B-SOL_USDT"
CURRENCY = "USDT"

# Explicitly Excluded: BTC, ETH, DOGE, LTC, ADA
EXCLUDED_COINS = ["BTC", "ETH", "DOGE", "LTC", "ADA"]

ALLOWED_FUTURES_COINS = [
    "SOL", "XRP", "AVAX", "SUI", "APT", "NEAR", "DOT", "ATOM", "ARB", "OP",
    "SEI", "TON", "FIL", "INJ", "HBAR", "UNI", "ETC", "ICP", "PEPE", "SHIB",
    "WIF", "BONK", "ONDO", "JUP", "ENA", "FET", "RENDER", "TAO", "CRV", "AAVE", "MKR"
]

def get_dynamic_daily_target_usd(equity_usd: float = 9.52) -> float:
    return DEFAULT_MAX_DAILY_TARGET_USD
