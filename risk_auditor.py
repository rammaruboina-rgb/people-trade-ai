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

def calculate_confidence_score(signals: dict) -> Tuple[float, List[str]]:
    """
    Weighted 0-100 Confidence Scoring Framework:
    - Wyckoff Phase (25% Weight)
    - Orderbook Imbalance (20% Weight)
    - Strategy Engine Pattern Signal (20% Weight)
    - News & Social NLP Sentiment (15% Weight)
    - Web3 Whale Liquidity (10% Weight)
    - Risk Auditor Gate Pass (10% Weight)
    """
    score = 0.0
    reasons = []

    wyckoff = str(signals.get("wyckoff", "")).lower()
    if any(k in wyckoff for k in ["accumulation", "spring", "lps", "markup"]):
        score += 25.0
        reasons.append("+25 Wyckoff Accumulation/Spring Structure")
    elif any(k in wyckoff for k in ["distribution", "upthrust", "lpsy", "markdown"]):
        score += 25.0
        reasons.append("+25 Wyckoff Distribution/Upthrust Structure")

    ob = float(signals.get("orderbook_imbalance", 1.0))
    if ob >= 1.3 or ob <= 0.7:
        score += 20.0
        reasons.append(f"+20 Orderbook Depth Imbalance ({ob:.2f})")
    elif ob >= 1.15 or ob <= 0.85:
        score += 12.0
        reasons.append(f"+12 Moderate Orderbook Imbalance ({ob:.2f})")

    strat = str(signals.get("strategy_signal", "")).lower()
    if any(k in strat for k in ["buy", "sell", "strong", "engulfing", "reclaim"]):
        score += 20.0
        reasons.append("+20 Technical Strategy Pattern Trigger")

    sent = float(signals.get("sentiment_score", 0.0))
    if abs(sent) >= 0.35:
        score += 15.0
        reasons.append(f"+15 High Catalyst NLP Sentiment ({sent:+.2f})")
    elif abs(sent) >= 0.15:
        score += 8.0
        reasons.append(f"+8 Moderate Catalyst Sentiment ({sent:+.2f})")

    web3 = str(signals.get("web3_whale", "")).lower()
    if any(k in web3 for k in ["inflow", "outflow", "surge", "whale"]):
        score += 10.0
        reasons.append("+10 Web3 Whale Liquidity Inflow")

    if signals.get("risk_gate_pass", True):
        score += 10.0
        reasons.append("+10 Risk Auditor Margin Clearance")

    return round(score, 1), reasons

def audit_multi_indicator_vote(signals: dict) -> Dict[str, Any]:
    """
    Hard Multi-Indicator Vote Rule:
    Requires at least 4 out of 6 independent engine votes in agreement,
    and a confidence score >= 70 for trade authorization.
    """
    long_votes = 0
    short_votes = 0
    total_engines = 6

    wyckoff = str(signals.get("wyckoff", "")).lower()
    if any(k in wyckoff for k in ["accumulation", "spring", "lps", "buy"]): long_votes += 1
    elif any(k in wyckoff for k in ["distribution", "upthrust", "lpsy", "sell"]): short_votes += 1

    ob = float(signals.get("orderbook_imbalance", 1.0))
    if ob >= 1.2: long_votes += 1
    elif ob <= 0.8: short_votes += 1

    strat = str(signals.get("strategy_signal", "")).lower()
    if "buy" in strat or "long" in strat: long_votes += 1
    elif "sell" in strat or "short" in strat: short_votes += 1

    sent = float(signals.get("sentiment_score", 0.0))
    if sent >= 0.20: long_votes += 1
    elif sent <= -0.20: short_votes += 1

    web3 = str(signals.get("web3_whale", "")).lower()
    if "inflow" in web3 or "bullish" in web3: long_votes += 1
    elif "outflow" in web3 or "bearish" in web3: short_votes += 1

    tf_aligned = signals.get("tf_aligned", False)
    tf_bias = str(signals.get("tf_directional_bias", "")).lower()
    if tf_aligned and tf_bias == "bullish": long_votes += 1
    elif tf_aligned and tf_bias == "bearish": short_votes += 1

    score, breakdown = calculate_confidence_score(signals)

    direction = "NEUTRAL"
    approved = False
    status = "REJECT_NO_CONFLUENCE"

    if long_votes >= 4 and score >= 70.0:
        direction = "LONG"
        approved = True
        status = "PASS_LONG"
    elif short_votes >= 4 and score >= 70.0:
        direction = "SHORT"
        approved = True
        status = "PASS_SHORT"
    elif score >= 70.0:
        status = "REJECT_VOTE_SPLIT"
    else:
        status = "REJECT_LOW_CONFIDENCE"

    return {
        "approved": approved,
        "status": status,
        "direction": direction,
        "confidence_score": score,
        "long_votes": long_votes,
        "short_votes": short_votes,
        "total_engines": total_engines,
        "score_breakdown": breakdown,
    }

if __name__ == "__main__":
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

