# position_manager.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class PositionPlan:
    symbol: str
    side: str
    entry: float
    size: float
    leverage: int
    t1_price: float
    t2_price: float
    t3_price: float
    sl_price: float
    t1_hit: bool = False
    t2_hit: bool = False
    t3_hit: bool = False
    sl_moved_to_be: bool = False
    t1_frac: float = 0.40  # 40% at T1
    t2_frac: float = 0.30  # 30% at T2
    t3_frac: float = 0.30  # 30% at T3

def evaluate_position_exits(
    pos_plan: PositionPlan,
    current_price: float
) -> dict:
    """
    Evaluates position scale-outs and SL breakeven moves:
    - T1 (+15% ROE): Scale out 40% & move SL to entry ($0.00 Risk).
    - T2 (+30% ROE): Scale out 30% & lock green profit SL.
    - T3 (+45% ROE): Final 30% scale-out.
    """
    action = {"close_frac": 0.0, "update_sl": None, "reason": None}

    side = pos_plan.side.upper()
    entry = pos_plan.entry

    if side == "BUY": # LONG
        # Stop Loss Check
        if current_price <= pos_plan.sl_price:
            action["close_frac"] = 1.0
            action["reason"] = "STOP_LOSS"
            return action

        # T1 Check
        if not pos_plan.t1_hit and current_price >= pos_plan.t1_price:
            pos_plan.t1_hit = True
            pos_plan.sl_price = entry # Move SL to Entry (Breakeven!)
            pos_plan.sl_moved_to_be = True
            action["close_frac"] = pos_plan.t1_frac
            action["update_sl"] = entry
            action["reason"] = "T1_HIT_BREAKEVEN_LOCKED"
            return action

        # T2 Check
        if pos_plan.t1_hit and not pos_plan.t2_hit and current_price >= pos_plan.t2_price:
            pos_plan.t2_hit = True
            pos_plan.sl_price = pos_plan.t1_price # Move SL to T1 price
            action["close_frac"] = pos_plan.t2_frac
            action["update_sl"] = pos_plan.t1_price
            action["reason"] = "T2_HIT_PROFIT_LOCKED"
            return action

        # T3 Check
        if pos_plan.t2_hit and not pos_plan.t3_hit and current_price >= pos_plan.t3_price:
            pos_plan.t3_hit = True
            action["close_frac"] = pos_plan.t3_frac
            action["reason"] = "T3_HIT_FULL_EXIT"
            return action

    else: # SHORT
        # Stop Loss Check
        if current_price >= pos_plan.sl_price:
            action["close_frac"] = 1.0
            action["reason"] = "STOP_LOSS"
            return action

        # T1 Check
        if not pos_plan.t1_hit and current_price <= pos_plan.t1_price:
            pos_plan.t1_hit = True
            pos_plan.sl_price = entry # Move SL to Entry
            pos_plan.sl_moved_to_be = True
            action["close_frac"] = pos_plan.t1_frac
            action["update_sl"] = entry
            action["reason"] = "T1_HIT_BREAKEVEN_LOCKED"
            return action

        # T2 Check
        if pos_plan.t1_hit and not pos_plan.t2_hit and current_price <= pos_plan.t2_price:
            pos_plan.t2_hit = True
            pos_plan.sl_price = pos_plan.t1_price
            action["close_frac"] = pos_plan.t2_frac
            action["update_sl"] = pos_plan.t1_price
            action["reason"] = "T2_HIT_PROFIT_LOCKED"
            return action

        # T3 Check
        if pos_plan.t2_hit and not pos_plan.t3_hit and current_price <= pos_plan.t3_price:
            pos_plan.t3_hit = True
            action["close_frac"] = pos_plan.t3_frac
            action["reason"] = "T3_HIT_FULL_EXIT"
            return action

    return action

def get_confidence_scaled_position(
    confidence_score: float,
    base_risk_budget_usd: float,
    min_confidence: float = 70.0
) -> float:
    """
    Kelly-Inspired Position Sizing:
    - Score >= 80: High Conviction -> 1.5x Base Risk Allocation
    - Score >= 60: Normal Conviction -> 1.0x Base Risk Allocation
    - Score < 60: Low Conviction -> 0.5x Base Risk Allocation
    """
    if confidence_score < min_confidence:
        return base_risk_budget_usd * 0.5

    if confidence_score >= 80.0:
        return base_risk_budget_usd * 1.5
    elif confidence_score >= 60.0:
        return base_risk_budget_usd * 1.0
    else:
        return base_risk_budget_usd * 0.5

