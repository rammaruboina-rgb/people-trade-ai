# config.py
import os

# Explicit CPU execution environment lock (Lightweight & 100% CPU compatible)
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# Trading Execution Mode (LIVE or PAPER)
MODE = os.getenv("MODE", "LIVE").upper()

from coindcx_futures_mapper import futures_mapper

# System Prompt & Core Objective Configuration
AGENT_SYSTEM_PROMPT = """
You are the CoinDCX Ultra-Aggressive 1m Altcoin Scalping Trading Brain.

CORE OBJECTIVE:
- Initial Equity: $9.65 USD
- Ultra-Aggressive Risk Per Trade: 50% of equity per trade
- Daily Profit Target: $100.00 USD / day
- Daily Max Loss Limit: $9.65 USD (Full account protection stop)
- Target Assets: Top 5 Trending Altcoins (ETH, SOL, XRP, DOGE, AVAX, LINK, PEPE, SHIB, SUI, APT, etc. Excludes BTC).

SIGNAL & ENTRY RULES:
- Confluence score >= 90%.
- 1m Candle Trend & MA20 filter.
- Top 5 Trending Altcoins 1h momentum ranking.
- Fully automated LIVE futures execution.

PROFIT & LOSS TARGETS:
- Take-Profit (TP): +1.0%
- Stop-Loss (SL): -0.5%
- Breakeven Trigger: +0.3% (locks in profit)
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

# Ultra-Aggressive Strategy Settings
HIGH_CONFIDENCE_THRESHOLD = 90.0  # Confluence Gate >= 90%
EQUITY_USD = 9.65                 # $9.65 USD Initial Balance
RISK_PER_TRADE_PCT = 50.0         # 50% equity risk per scalp
DEFAULT_MAX_DAILY_TARGET_USD = 100.0 # $100.00 USD Daily Profit Target
DAILY_LOSS_LIMIT_USD = 9.65       # $9.65 USD Daily Loss Limit Guard
MAX_TRADES_PER_DAY = 50

def get_dynamic_daily_target_usd(equity_usd: float) -> float:
    return DEFAULT_MAX_DAILY_TARGET_USD

# Risk & Protection (1m Scalp Parameters)
DEFAULT_SL_PCT = 0.005            # -0.5% Stop-Loss
DEFAULT_TP_PCT = 0.010            # +1.0% Take-Profit
BREAKEVEN_PROFIT_PCT = 0.003      # +0.3% Breakeven Trigger
TRAILING_STOP_PCT = 0.003         # 0.3% Trailing Stop distance
LIQUIDATION_SAFETY_BUFFER_PCT = 0.20  # 20% safety distance before liquidation

# Leverage & Margin
MAX_LEVERAGE_CAP = 5              # 5x leverage cap for major coins
ALTCOIN_LEVERAGE_CAP = 3          # 3x leverage cap for altcoins
MARGIN_MODE = "isolated"          # isolated margin mode
MAX_FUTURES_MARGIN_UTILIZATION = 0.5

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
