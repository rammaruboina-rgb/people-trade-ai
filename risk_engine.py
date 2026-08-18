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
    """Enforces MAXIMUM 20X leverage limit"""
    return min(20, max(1, requested_leverage))

def calc_sl_tp_prices(entry_price: float, side: str = "LONG", sl_pct: float = DEFAULT_SL_PCT, tp_pct: float = DEFAULT_TP_PCT) -> tuple:
    """Calculates strict USD price levels for Stop-Loss and Take-Profit"""
    if side.upper() in ["LONG", "BUY"]:
        sl_price = entry_price * (1.0 - sl_pct)
        tp_price = entry_price * (1.0 + tp_pct)
    else:
        sl_price = entry_price * (1.0 + sl_pct)
        tp_price = entry_price * (1.0 - tp_pct)

    return round(sl_price, 2), round(tp_price, 2)

def calc_position_size(equity_usd: float, entry_price: float, sl_price: float, coin: str = "ETH") -> float:
    """Calculates position size utilizing MAXIMUM 20X LEVERAGE"""
    coin_upper = coin.upper()

    # Full 100% Margin Utilization ($9.659 USD)
    effective_equity = max(9.659, equity_usd)
    risk_amount_usd = effective_equity * 1.0  # 100% margin

    # Apply 20x Leverage Notional Size
    leverage = 20
    notional_usd = risk_amount_usd * leverage
    raw_qty = notional_usd / entry_price

    if coin_upper == "ETH":
        return max(0.013, round(raw_qty, 3))
    elif coin_upper == "SOL":
        return max(0.1, round(raw_qty, 2))
    elif coin_upper in ["PEPE", "SHIB", "BONK", "FLOKI"]:
        return max(1000000.0, round(raw_qty, 0))
    elif coin_upper == "TAO":
        return max(0.01, round(raw_qty, 2))
    else:
        return max(10.0, round(raw_qty, 1))

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
