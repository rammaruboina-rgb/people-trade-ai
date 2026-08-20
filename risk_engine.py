# risk_engine.py
"""
Risk Engine - MAXIMUM 20X LEVERAGE POSITION SIZING & SAFETY GUARDS
Calculates maximum notional position sizing, 20x leverage caps, and pre-liquidation safety stops.
"""

from config import (
    RISK_PER_TRADE_PCT,
    MAX_LEVERAGE_CAP,
    ALTCOIN_LEVERAGE_CAP,
    LIQUIDATION_SAFETY_BUFFER_PCT,
    DEFAULT_SL_PCT,
    DEFAULT_TP_PCT,
    MARGIN_MODE
)

def apply_leverage_cap(requested_leverage: int) -> int:
    """Enforces 100X leverage limit"""
    return min(100, max(1, requested_leverage))

def calc_sl_tp_prices(entry_price: float, side: str = "LONG", sl_pct: float = DEFAULT_SL_PCT, tp_pct: float = DEFAULT_TP_PCT) -> tuple:
    """Calculates strict USD price levels for Stop-Loss and Take-Profit"""
    if side.upper() in ["LONG", "BUY"]:
        sl_price = entry_price * (1.0 - sl_pct)
        tp_price = entry_price * (1.0 + tp_pct)
    else:
        sl_price = entry_price * (1.0 + sl_pct)
        tp_price = entry_price * (1.0 - tp_pct)

    return round(sl_price, 2), round(tp_price, 2)

def calc_position_size(equity_usd: float, entry_price: float, sl_price: float, coin: str = "ACE", override_leverage: int = None) -> float:
    """Calculates position size utilizing requested LEVERAGE with safety collateral buffer"""
    coin_upper = coin.upper()

    if entry_price <= 0:
        return 1.0

    from config import LEVERAGE
    lev = override_leverage if override_leverage is not None else LEVERAGE
    leverage = min(100, max(1, int(lev)))

    # Allocate 90% of allocated per-trade equity to utilize FULL AMOUNT for trade
    safe_margin = max(0.50, equity_usd * 0.90)
    notional_usd = safe_margin * leverage
    raw_qty = notional_usd / entry_price

    if coin_upper in ["PEPE", "SHIB", "BONK", "FLOKI"]:
        return max(1000.0, float(round(raw_qty, 0)))
    elif entry_price >= 100.0:
        return max(0.001, float(round(raw_qty, 3)))
    elif entry_price >= 10.0:
        return max(0.01, float(round(raw_qty, 2)))
    elif entry_price >= 1.0:
        return max(0.1, float(round(raw_qty, 1)))
    else:
        return max(1.0, float(round(raw_qty, 1)))

def calc_liquidation_price(entry_price: float, side: str = "LONG", leverage: int = 20) -> float:
    """Calculates estimated isolated margin liquidation price"""
    if leverage <= 0:
        leverage = 20

    maint_margin_rate = 0.01  # 1% maintenance margin
    if side.upper() in ["LONG", "BUY"]:
        liq_price = entry_price * (1.0 - (1.0 / leverage) + maint_margin_rate)
    else:
        liq_price = entry_price * (1.0 + (1.0 / leverage) - maint_margin_rate)

    return round(max(0.0, liq_price), 2)

def calc_emergency_sl(liq_price: float, entry_price: float, side: str = "LONG") -> float:
    """Calculates emergency pre-liquidation stop-loss price (20% safety distance before liquidation)"""
    if side.upper() in ["LONG", "BUY"]:
        distance = entry_price - liq_price
        emergency_sl = entry_price - (distance * (1.0 - LIQUIDATION_SAFETY_BUFFER_PCT))
    else:
        distance = liq_price - entry_price
        emergency_sl = entry_price + (distance * (1.0 - LIQUIDATION_SAFETY_BUFFER_PCT))

    return round(emergency_sl, 2)

def calc_trailing_sl(highest_price: float, lowest_price: float, side: str = "LONG", current_sl: float = 0.0, trailing_pct: float = 0.03) -> float:
    """Calculates trailing stop-loss price level"""
    if side.upper() in ["LONG", "BUY"]:
        new_sl = round(highest_price * (1.0 - trailing_pct), 2)
        return max(current_sl, new_sl)
    else:
        new_sl = round(lowest_price * (1.0 + trailing_pct), 2)
        return min(current_sl, new_sl) if current_sl > 0 else new_sl
