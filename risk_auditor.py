# risk_auditor.py
"""
Pre-Trade Risk Auditor & Pure-Altcoin Compliance Inspector
Strictly excludes BTC, ETH, and SOL.
Calculates position sizing based on max equity risk budget, fee estimations,
price risk percentages, and rough liquidation buffer safety.
"""

from dataclasses import dataclass
from typing import Literal, List

Side = Literal["long", "short"]

# Unblocked All Coins Per User Directive: BTC, ETH, SOL allowed
BLOCKED_BASES = set()

@dataclass
class TradeCheck:
    symbol: str
    side: Side
    entry: float
    tp: float
    sl: float
    equity: float
    leverage: float
    risk_pct: float
    notional: float
    margin: float
    price_risk_pct: float
    estimated_loss: float
    estimated_profit: float
    liquidation_buffer_pct: float
    approved: bool
    reasons: List[str]

def base_asset(symbol: str) -> str:
    s = symbol.upper().replace("/", "_").replace("-", "_")
    # Handles B-WLD_USDT, WLDUSDT, WLD_USDT
    s = s.replace("B_", "")
    return s.split("_")[0].split(":")[0].replace("USDT", "")

def allowed_pure_alt(symbol: str) -> bool:
    """Returns True if symbol is a pure altcoin (not BTC, ETH, or SOL)"""
    return base_asset(symbol) not in BLOCKED_BASES

def check_trade(
    symbol: str,
    side: Side,
    entry: float,
    tp: float,
    sl: float,
    equity: float,
    leverage: float = 30.0,
    max_risk_pct: float = 2.0,
    min_liquidation_buffer_pct: float = 1.0,
    taker_fee_each_side_pct: float = 0.059,
) -> TradeCheck:
    reasons = []

    if not allowed_pure_alt(symbol):
        reasons.append("Blocked asset: BTC, ETH, and SOL are not allowed")

    if min(entry, tp, sl, equity, leverage) <= 0:
        reasons.append("All numeric values must be positive")

    side_lower = str(side).lower()

    if side_lower in ["long", "buy"]:
        actual_side: Side = "long"
        if not (sl < entry < tp):
            reasons.append("For long: SL < entry < TP required")
        price_risk_pct = (entry - sl) / entry * 100 if entry > 0 else 0.0
        price_reward_pct = (tp - entry) / entry * 100 if entry > 0 else 0.0
    elif side_lower in ["short", "sell"]:
        actual_side: Side = "short"
        if not (tp < entry < sl):
            reasons.append("For short: TP < entry < SL required")
        price_risk_pct = (sl - entry) / entry * 100 if entry > 0 else 0.0
        price_reward_pct = (entry - tp) / entry * 100 if entry > 0 else 0.0
    else:
        actual_side = "long"
        reasons.append("Side must be long or short")
        price_risk_pct = 0.0
        price_reward_pct = 0.0

    # Position sizing: risk budget allocation
    risk_budget = equity * max_risk_pct / 100
    notional = risk_budget / (price_risk_pct / 100) if price_risk_pct > 0 else 0.0
    margin = notional / leverage if leverage > 0 else 0.0

    round_trip_fee_pct_on_notional = 2 * taker_fee_each_side_pct
    estimated_fee = notional * round_trip_fee_pct_on_notional / 100
    estimated_loss = notional * price_risk_pct / 100 + estimated_fee
    estimated_profit = notional * price_reward_pct / 100 - estimated_fee

    # Conservative leverage buffer estimate
    estimated_liq_buffer_pct = 100 / leverage if leverage > 0 else 0.0

    if price_risk_pct <= 0:
        reasons.append("SL must create positive price risk")

    if estimated_loss > risk_budget * 1.05:
        reasons.append("Estimated loss exceeds risk budget after fees")

    if estimated_liq_buffer_pct <= price_risk_pct:
        reasons.append("SL is at/inside the rough liquidation zone")

    if estimated_liq_buffer_pct < min_liquidation_buffer_pct:
        reasons.append("Very small estimated liquidation buffer")

    approved = len(reasons) == 0

    return TradeCheck(
        symbol=symbol,
        side=actual_side,
        entry=entry,
        tp=tp,
        sl=sl,
        equity=equity,
        leverage=leverage,
        risk_pct=max_risk_pct,
        notional=notional,
        margin=margin,
        price_risk_pct=price_risk_pct,
        estimated_loss=estimated_loss,
        estimated_profit=estimated_profit,
        liquidation_buffer_pct=estimated_liq_buffer_pct,
        approved=approved,
        reasons=reasons,
    )

def print_check(c: TradeCheck):
    print(f"\n{c.symbol} {c.side.upper()}")
    print(f"Entry={c.entry} TP={c.tp} SL={c.sl}")
    print(f"Notional: {c.notional:.4f}")
    print(f"Estimated margin at {c.leverage:g}x: {c.margin:.4f}")
    print(f"Price risk to SL: {c.price_risk_pct:.4f}%")
    print(f"Estimated loss incl. fees: ${c.estimated_loss:.4f}")
    print(f"Estimated profit after fees: ${c.estimated_profit:.4f}")
    print(f"Rough leverage buffer: {c.liquidation_buffer_pct:.4f}%")
    print("APPROVED:", c.approved)
    if c.reasons:
        print("REASONS:")
        for reason in c.reasons:
            print(" -", reason)

if __name__ == "__main__":
    # Test example for pure altcoin (B-WLD_USDT)
    result = check_trade(
        symbol="B-WLD_USDT",
        side="short",
        entry=0.3197,
        tp=0.3090,
        sl=0.3223,
        equity=10.38,
        leverage=30,
        max_risk_pct=2.0,
    )
    print_check(result)
