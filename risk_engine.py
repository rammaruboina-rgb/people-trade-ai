# risk_engine.py
from config import (
    RISK_PER_TRADE_PCT,
    DEFAULT_SL_PCT,
    DEFAULT_TP_PCT,
    TRAILING_STOP_PCT,
    LIQUIDATION_SAFETY_BUFFER_PCT,
    MAX_LEVERAGE_CAP,
)

# CoinDCX Futures Minimum Notional Order Values (USD)
MIN_ORDER_VALUE_USD = {
    "BTC": 10.0,
    "ETH": 24.5,
    "SOL": 7.5,
    "DOGE": 6.5,
    "XRP": 6.5,
    "ADA": 6.5,
    "AVAX": 6.5,
    "MATIC": 6.5,
    "LINK": 6.5,
    "PEPE": 6.5,
    "SHIB": 6.5,
    "SUI": 6.5,
    "APT": 6.5
}

def calc_sl_tp_prices(entry_price: float, side: str):
    if side.upper() == "LONG":
        sl = entry_price * (1 - DEFAULT_SL_PCT)
        tp = entry_price * (1 + DEFAULT_TP_PCT)
    else:  # SHORT
        sl = entry_price * (1 + DEFAULT_SL_PCT)
        tp = entry_price * (1 - DEFAULT_TP_PCT)
    return round(sl, 2), round(tp, 2)

def calc_position_size(equity: float, entry_price: float, sl_price: float, coin: str = "BTC"):
    """
    Calculates position size formatted to CoinDCX Futures minimum order value rules:
    - BTC: 0.001 BTC (~$64.40 notional)
    - ETH: min $24.5 USDT notional (~0.013 ETH)
    - SOL: 0.1 SOL (~$7.60 notional)
    - Altcoins: min $6.5 USDT notional
    """
    coin_upper = coin.upper()
    min_notional = MIN_ORDER_VALUE_USD.get(coin_upper, 6.5)

    if entry_price <= 0:
        return 0.001 if coin_upper == "BTC" else 0.1

    raw_qty = min_notional / entry_price

    if coin_upper == "BTC":
        return max(0.001, round(raw_qty, 3))
    elif coin_upper == "ETH":
        return max(0.013, round(raw_qty, 3))
    elif coin_upper == "SOL":
        return max(0.1, round(raw_qty, 2))
    elif coin_upper in ["PEPE", "SHIB"]:
        return max(1000000.0, round(raw_qty, 0))
    else:
        return max(10.0, round(raw_qty, 1))

def apply_leverage_cap(requested_leverage: int) -> int:
    return min(requested_leverage, MAX_LEVERAGE_CAP)

def calc_trailing_sl(highest_price: float, lowest_price: float, side: str, current_sl: float):
    if side.upper() == "LONG":
        new_sl = highest_price * (1 - TRAILING_STOP_PCT)
        if new_sl > current_sl:
            return round(new_sl, 2)
    else:  # SHORT
        new_sl = lowest_price * (1 + TRAILING_STOP_PCT)
        if current_sl == 0 or new_sl < current_sl:
            return round(new_sl, 2)
    return round(current_sl, 2)

def calc_liquidation_price(entry_price: float, side: str, leverage: int = 10) -> float:
    if entry_price == 0:
        return 0.0
    maint_margin = 0.005  # 0.5% approx
    if side.upper() == "LONG":
        return round(entry_price * (1 - (1.0 / leverage) + maint_margin), 2)
    elif side.upper() == "SHORT":
        return round(entry_price * (1 + (1.0 / leverage) - maint_margin), 2)
    return 0.0

def calc_emergency_sl(liquidation_price: float, entry_price: float, side: str) -> float:
    if side.upper() == "LONG":
        buffer = (entry_price - liquidation_price) * LIQUIDATION_SAFETY_BUFFER_PCT
        return round(liquidation_price + buffer, 2)
    else:  # SHORT
        buffer = (liquidation_price - entry_price) * LIQUIDATION_SAFETY_BUFFER_PCT
        return round(liquidation_price - buffer, 2)
