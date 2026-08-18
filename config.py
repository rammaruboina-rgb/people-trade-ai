# config.py
import os

# Explicit CPU execution environment lock (Lightweight & 100% CPU compatible)
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# Trading Execution Mode (LIVE or PAPER)
MODE = os.getenv("MODE", "LIVE").upper()

from coindcx_futures_mapper import futures_mapper

# System Prompt & Core Objective Configuration
AGENT_SYSTEM_PROMPT = """
You are the CoinDCX Max-Safety $50 Daily Profit Scalping Trading Brain for FUTURES only across BTC & Altcoins.

CORE OBJECTIVE:
- Daily Profit Target: $50.00 USD / day.
- Daily Max Loss Limit: -$25.00 USD / day (Stop trading if -$25 loss reached).
- Risk Per Trade: 5.0% of equity per scalp.

SIGNAL & ENTRY RULES:
- Confluence score >= 90%.
- 1m Candle Trend & Net-5-Candle Momentum filter.
- Microstructure filter must pass.
- Fully automated LIVE futures execution.

PROFIT & LOSS TARGETS:
- Take-Profit (TP): +1.0%
- Stop-Loss (SL): -0.5%
- Breakeven Trigger: +0.3% (locks in profit)

DISPLAY:
- Show all values in USD ($): balance, P&L, position size, profit/loss.
- Mode must display as LIVE once funds are available and API keys are configured.
"""

# Base Currency & Symbol Configuration (USD Trading)
CURRENCY = "USD"
CURRENCY_SYMBOL = "$"

# Dynamic Allowed Altcoin Futures Symbols & Coins
ALLOWED_FUTURES_COINS = [
    "BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "AVAX", "MATIC", "LINK", "PEPE", "SHIB", "SUI", "APT"
]
ALLOWED_FUTURES_SYMBOLS = futures_mapper.active_instruments

SYMBOL_SPOT = "BTCUSDT"
SYMBOL_FUTURES = futures_mapper.get_dcx_future_symbol("BTC")
CANDLE_PAIR = "B-BTC_USDT"

# Strategy Settings ($50/Day Profit Target)
HIGH_CONFIDENCE_THRESHOLD = 90.0  # Confluence Gate set to >= 90%
EQUITY_USD = 10.0                 # Futures Account Capital
RISK_PER_TRADE_PCT = 5.0          # 5.0% risk per trade
DEFAULT_MAX_DAILY_TARGET_USD = 50.0 # $50.00 USD Daily Profit Target
DAILY_LOSS_LIMIT_USD = 25.0       # -$25.00 USD Daily Loss Limit Guard

def get_dynamic_daily_target_usd(equity_usd: float) -> float:
    """Returns $50.00 USD daily profit target"""
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
MARGIN_MODE = "isolated"          # isolated margin mode (zero cross-account risk)
MAX_FUTURES_MARGIN_UTILIZATION = 0.5  # Max 50% margin utilization

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
