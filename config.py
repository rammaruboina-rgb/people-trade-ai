# config.py
"""
Centralized Configuration Module for CoinDCX Master Trading Agent
Configured for Multi-Trade Concurrent Scalping (Up to 5 Simultaneous Active Trades)
Target: $20.00 USD / Day Profit Goal | Pure High-Volatility Altcoins
Supports Targeted Coin Focus Mode (e.g. Focus on SUI only)
SOL HAS BEEN PERMANENTLY EXCLUDED PER USER DIRECTIVE.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# System Execution Parameters
MODE = os.getenv("MODE", "LIVE").upper()
LOG_FILE = "trading_bot.log"
TRADES_CSV = "trades_unified.csv"
LOOP_INTERVAL_SEC = 1.0  # Ultra-fast 1.0s scan rate

# Execution Engine Mode
PAPER_TRADING = False  # LIVE REAL CAPITAL TRADING ENABLED PER USER DIRECTIVE
EQUITY_USD = float(os.getenv("EQUITY_USD", "10.00"))  # Real Account Equity Calibration
DEFAULT_MAX_DAILY_TARGET_USD = 10000.0  # Unlimited daily profit mode
MAX_DAILY_TRADES = 999999               # Unlimited trades per day
# Position Gate & Cooldown Rules
MAX_OPEN_POSITIONS = 1
MAX_CONCURRENT_TRADES = 1
REENTRY_COOLDOWN_SECONDS = 3
MAX_DAILY_LOSS_PCT = 0.10
BREAKEVEN_PROFIT_PCT = 0.01
PAPER_TRADING = False  # HARDENED REAL CASH LIVE CAPITAL TRADING MODE

# Risk Engine & Leverage Parameters (SAFE CONSERVATIVE 10X LEVERAGE | A+ SETUPS ONLY)
RISK_PER_TRADE_PCT = 25.0           # Conservative margin per trade (25% of equity)
LEVERAGE = 10                       # Safe 10x Isolated Leverage
MAX_LEVERAGE_CAP = 10
ALTCOIN_LEVERAGE_CAP = 10
MARGIN_MODE = "isolated"
LIQUIDATION_SAFETY_BUFFER_PCT = 0.20 # 20% safe buffer above liquidation price
DEFAULT_SL_PCT = 0.010              # -1.0% price move Stop Loss (-10% ROE)
DEFAULT_TP_PCT = 0.030              # +3.0% price move Take Profit (+30% ROE)

# Multi-Target Partial Take Profit Parameters (T1, T2, T3 Scalping)
T1_TP_PCT = 0.015   # T1 Target: +1.5% Price Move (+15% ROE @ 10X) -> Partial 33% Exit & SL to Breakeven
T2_TP_PCT = 0.030   # T2 Target: +3.0% Price Move (+30% ROE @ 10X) -> Partial 33% Exit & SL to T1
T3_TP_PCT = 0.050   # T3 Target: +5.0% Price Move (+50% ROE @ 10X) -> Runner 34% Exit (Full Trade Complete)
TP_PRICE_MOVE_PCT = 0.030   # Default TP target
SL_PRICE_MOVE_PCT = 0.010   # -1.0% price stop (-10% ROE at 10X)
TARGET_PROFIT_PER_TRADE_USD = 3.00  # $3.00 USD profit per trade towards $10->$20 target

# Daily Safety Risk Limits (HARD CAPITAL PROTECTION)
MAX_DAILY_LOSS_PCT = 0.05      # 5% max daily equity loss limit (hard halt)
MAX_CONSECUTIVE_LOSSES = 2     # Halt after 2 consecutive losses

# Targeted Coin Focus Mode (None = Multi-Trade All Top Altcoins)
TARGETED_FOCUS_COIN = None

# Strategy Rules (HIGH CONFLUENCE A+ SETUPS ONLY)
TIMEFRAME = "1m"
MIN_CONFLUENCE_PCT = 75.0      # Strict 75% minimum signal confidence
PROFIT_TARGET_PCT = 0.30       # +30.0% ROE TP
STOP_LOSS_PCT = 0.10           # -10.0% ROE SL
BREAKEVEN_PROFIT_PCT = 0.05 # Move SL to entry at +5.0% profit

# Webhook Server Parameters
WEBHOOK_ENABLED = os.getenv("WEBHOOK_ENABLED", "false").lower() == "true"
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5000"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "super_secret_webhook_token_123")

# Default Pure Altcoin Symbol: SUI
SYMBOL_SPOT = "SUIUSDT"
SYMBOL_FUTURES = "B-SUI_USDT"
CANDLE_PAIR = "B-SUI_USDT"
CURRENCY = "USDT"

# Unblocked All Coins Per User Directive: BTC, ETH, SOL, SUI, DOGE, etc.
EXCLUDED_COINS = []

# Full Multi-Coin Universe Including BTC, ETH, SOL & Top Altcoins
ALLOWED_FUTURES_COINS = [
    "BTC", "ETH", "SOL", "SUI", "DOGE", "AVAX", "NEAR", "PEPE", "WIF", "SEI", "INJ", "TON", "BONK", "SHIB", "FLOKI", "XRP", "ADA", "LINK", "MATIC"
]

def set_focus_coin(coin_name: str):
    global TARGETED_FOCUS_COIN
    if not coin_name or coin_name.upper().strip() in ["START", "ALL", "NONE", ""]:
        TARGETED_FOCUS_COIN = None
    else:
        clean = (
            coin_name.upper()
            .replace("FOCUS", "")
            .replace("B-", "")
            .replace("_USDT", "")
            .replace("USDT", "")
            .strip()
        )
        if clean in EXCLUDED_COINS:
            print(f"⚠️ {clean} is in EXCLUDED_COINS blacklist! Reverting to ALL coins mode.")
            TARGETED_FOCUS_COIN = None
        else:
            TARGETED_FOCUS_COIN = clean


def get_dynamic_daily_target_usd(equity_usd: float = 9.52) -> float:
    return DEFAULT_MAX_DAILY_TARGET_USD
