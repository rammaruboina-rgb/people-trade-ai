# config.py
import os

# Explicit CPU execution environment lock (Lightweight & 100% CPU compatible)
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# Trading Execution Mode (LIVE or PAPER)
MODE = os.getenv("MODE", "LIVE").upper()

from coindcx_futures_mapper import futures_mapper

# System Prompt & Core Objective Configuration
AGENT_SYSTEM_PROMPT = """
You are the CoinDCX High-Conviction +20% Profit Altcoin Futures Trading Brain.

CORE OBJECTIVE:
- Initial Equity: $9.65 USD
- Full Margin / Max Leverage Utilization: 100% of equity per trade
- Target Profit Per Trade: +20.0%
- Stop-Loss Per Trade: -10.0%
- Strict Confluence Gate: >= 98.0% (Perfect setups only)
- Daily Profit Goal: $100.00 USD / day
- Target Assets: Top 5 Trending Altcoins (Excludes BTC)
"""

# Base Currency Configuration
CURRENCY = "USD"
CURRENCY_SYMBOL = "$"

# Ultra-Aggressive Altcoin Futures List (Excludes BTC)
ALLOWED_FUTURES_COINS = [
    "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE", "TRX", "LTC", "BCH", "EOS",
    "LINK", "AVAX", "DOT", "ATOM", "NEAR", "APT", "SUI", "ARB", "OP", "SEI",
    "TON", "FIL", "INJ", "HBAR", "UNI", "ETC", "ICP", "PEPE", "SHIB", "WIF",
    "BONK", "ONDO", "JUP", "ENA", "FET", "RENDER", "TAO", "CRV", "AAVE", "MKR",
    "GRT", "COMP", "SNX", "1INCH", "ZEC", "XLM", "ALGO", "VET", "FLOW", "KAS"
]

ALLOWED_FUTURES_SYMBOLS = [futures_mapper.get_dcx_future_symbol(c) for c in ALLOWED_FUTURES_COINS]

SYMBOL_SPOT = "ETHUSDT"
SYMBOL_FUTURES = futures_mapper.get_dcx_future_symbol("ETH")
CANDLE_PAIR = "B-ETH_USDT"

# High-Conviction Strategy Settings
MIN_CONFLUENCE_PCT = 98.0         # Strict 98%+ Confluence Gate for Perfect Setups
HIGH_CONFIDENCE_THRESHOLD = 98.0
EQUITY_USD = 9.65                 # $9.65 USD Balance
RISK_PER_TRADE_PCT = 100.0        # 100% Equity / Max Leverage Utilization
PROFIT_TARGET_PCT = 0.20          # +20.0% Profit Target Per Trade
STOP_LOSS_PCT = 0.10              # -10.0% Stop-Loss Per Trade
DEFAULT_MAX_DAILY_TARGET_USD = 100.0 # $100.00 USD Daily Target
DAILY_LOSS_LIMIT_USD = 9.65       # $9.65 USD Daily Loss Stop
MAX_TRADES_PER_DAY = 20

def get_dynamic_daily_target_usd(equity_usd: float) -> float:
    return DEFAULT_MAX_DAILY_TARGET_USD

# Risk & Protection Parameters
DEFAULT_SL_PCT = 0.10             # -10.0% Stop-Loss
DEFAULT_TP_PCT = 0.20             # +20.0% Take-Profit
BREAKEVEN_PROFIT_PCT = 0.05       # +5.0% Breakeven Trigger
TRAILING_STOP_PCT = 0.03          # 3.0% Trailing Stop distance
LIQUIDATION_SAFETY_BUFFER_PCT = 0.20  # 20% safety distance before liquidation

# Leverage & Margin
MAX_LEVERAGE_CAP = 10             # Max 10x leverage cap for major coins
ALTCOIN_LEVERAGE_CAP = 5          # Max 5x leverage cap for altcoins
MARGIN_MODE = "isolated"          # isolated margin mode
MAX_FUTURES_MARGIN_UTILIZATION = 1.0  # Full 100% margin utilization

# Webhook Server Configuration
WEBHOOK_ENABLED = os.getenv("WEBHOOK_ENABLED", "false").lower() == "true"
WEBHOOK_SECRET = "your_tradingview_secret_key_123"
WEBHOOK_PORT = 8000
WEBHOOK_HOST = "0.0.0.0"

# Execution Loop
LOOP_INTERVAL_SEC = 2

# File Paths
TRADES_CSV = "trades_unified.csv"
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "agent.log")

os.makedirs(LOG_DIR, exist_ok=True)
