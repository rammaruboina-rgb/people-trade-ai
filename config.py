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
MAX_OPEN_POSITIONS = 3
MAX_CONCURRENT_TRADES = 3
REENTRY_COOLDOWN_SECONDS = 3
MAX_DAILY_LOSS_PCT = 0.10
BREAKEVEN_PROFIT_PCT = 0.01
PAPER_TRADING = False  # HARDENED REAL CASH LIVE CAPITAL TRADING MODE

# Multi-Trade Mode Configuration
MULTI_TRADE_CONFIG = {
    "enabled": True,
    "max_concurrent_trades": 3,          # Up to 3 simultaneous positions allowed
    "max_per_symbol": 1,                 # Max 1 position per coin symbol
    "risk_per_trade_pct": 1.0,           # 1.0% equity risk per trade
    "max_total_risk_pct": 3.0,           # 3.0% max total risk across all active trades
    "min_overall_score": 70.0,           # Minimum 70/100 overall score required
    "min_engine_score": 60.0,            # Minimum engine score requirement
}

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

# Daily & Weekly Circuit Breakers (Capital Protection)
MAX_DAILY_LOSS_PCT = 0.03       # 3% max daily equity loss limit (hard circuit breaker)
DAILY_LOSS_LIMIT_PCT = 3.0       # 3% daily drawdown stop
WEEKLY_LOSS_LIMIT_PCT = 5.0      # 5% weekly drawdown stop
MAX_CONSECUTIVE_LOSSES = 2       # Halt after 2 consecutive losses

# Multi-Layer Confluence Settings
MIN_CONFLUENCE_SCORE = 70.0      # Minimum 0-100 weighted score required for entry
REQUIRED_VOTES = 4               # Minimum 4 out of 6 engine votes required

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

# 📌 SYSTEM DIRECTIVE NOTE: MAXIMUM FOCUS ON HIGH-VOLATILITY PURE ALTCOINS
PURE_ALTCOIN_DIRECTIVE = "📌 SYSTEM DIRECTIVE: MAXIMUM FOCUS ON HIGH-VOLATILITY PURE ALTCOINS FOR FASTEST PROFIT TARGETS"
EXCLUDED_COINS = ["BTC", "ETH"]  # Exclude heavy low-volatility coins for maximum altcoin focus

# Prioritized Altcoin Universe (High-Volatility Pure Altcoins First)
ALLOWED_FUTURES_COINS = [
    "SUI", "SOL", "AVAX", "NEAR", "PEPE", "WIF", "SEI", "INJ", "XRP", "ADA", "LINK", "DOGE", "BONK", "SHIB", "FLOKI", "TON", "MATIC"
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
