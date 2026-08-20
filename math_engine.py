# math_engine.py
from typing import Dict, Tuple

def size_position(
    equity: float,
    risk_pct: float,
    entry: float,
    sl: float,
    side: str,
    leverage: float,
) -> Dict[str, float]:
    """
    Computes position size from risk-per-trade budget:
    - Calculates price risk %
    - Computes budget in USDT
    - Computes position quantity & initial margin
    """
    side_clean = side.lower()
    if side_clean in ["long", "buy"]:
        rp = (entry - sl) / entry
    else:
        rp = (sl - entry) / entry

    if rp <= 0:
        rp = 0.005 # Safety fallback for invalid SL

    budget = equity * (risk_pct / 100.0)
    notional = budget / rp
    qty = notional / entry
    margin = notional / leverage

    return {
        "price_risk_pct": rp * 100,
        "risk_budget_usd": budget,
        "notional_usd": notional,
        "quantity": qty,
        "initial_margin_usd": margin,
    }

def roe_for_targets(
    entry: float,
    tp: float,
    sl: float,
    side: str,
    leverage: float
) -> Dict[str, float]:
    """
    Calculates expected ROE for TP and SL targets.
    """
    side_clean = side.lower()
    if side_clean in ["long", "buy"]:
        dp_tp = (tp - entry) / entry
        dp_sl = (sl - entry) / entry
    else:
        dp_tp = (entry - tp) / entry
        dp_sl = (sl - entry) / entry

    roe_tp = dp_tp * leverage
    roe_sl = dp_sl * leverage

    return {
        "price_move_to_tp_pct": dp_tp * 100,
        "price_move_to_sl_pct": dp_sl * 100,
        "roe_to_tp_pct": roe_tp * 100,
        "roe_to_sl_pct": roe_sl * 100,
    }

def pnl_with_costs(
    notional: float,
    dp: float,
    taker_fee_rate: float = 0.00059,
    funding_rate_8h: float = 0.0001,
    holding_hours: float = 1.0,
) -> Dict[str, float]:
    """
    Computes net PnL after subtracting CoinDCX taker fees and funding costs.
    """
    fee_usd = notional * taker_fee_rate * 2
    funding_usd = notional * funding_rate_8h * (holding_hours / 8.0)
    pnl_gross = notional * dp
    pnl_net = pnl_gross - fee_usd - funding_usd
    return {
        "fee_usd": fee_usd,
        "funding_usd": funding_usd,
        "pnl_gross_usd": pnl_gross,
        "pnl_net_usd": pnl_net,
    }

def liq_price_estimate(
    entry: float,
    side: str,
    leverage: float,
    maintenance_rate: float = 0.005,
    extra_buffer: float = 0.002
) -> Tuple[float, float]:
    """
    Calculates isolated liquidation price and buffer %.
    """
    m0 = 1.0 / leverage
    ell = max(0.0, m0 - maintenance_rate - extra_buffer)

    side_clean = side.lower()
    if side_clean in ["long", "buy"]:
        pliq = entry * (1 - ell)
    else:
        pliq = entry * (1 + ell)

    buffer_pct = ell * 100
    return pliq, buffer_pct

def expectancy(win_rate: float, avg_win_usd: float, avg_loss_usd: float) -> float:
    """
    Calculates expected USD return per trade based on historical edge.
    """
    return (win_rate * avg_win_usd) - ((1.0 - win_rate) * avg_loss_usd)
