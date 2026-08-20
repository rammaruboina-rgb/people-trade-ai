import json
import os
from pathlib import Path
from state.machine import AgentState, transition

# Helper to load a prompt file as a raw string
def load_prompt(name: str) -> str:
    prompt_path = Path(__file__).parent / "prompts" / name
    return prompt_path.read_text(encoding="utf-8")

# Placeholder LLM call – in production replace with actual API call
def call_llm(system_prompt: str, user_prompt: str, market_state: dict) -> dict:
    """Simulate an LLM response.
    Returns a dict matching the expected output schema for the given user_prompt.
    This stub merely echoes a dummy BUY trade for demonstration.
    """
    # Very naive dummy logic – always approve a sample trade
    if "PRE-TRADE CHECKLIST" in user_prompt:
        return {"decision": "APPROVE", "risk_flags": [], "notes": "All checks passed (demo)"}
    if "ENTRY CONFIRMATION" in user_prompt:
        return {"decision": "APPROVE", "risk_flags": [], "notes": "All levels consistent (demo)"}
    if "in_trade_management" in user_prompt:
        return {
            "action": "HOLD",
            "new_stop_loss_price": None,
            "new_take_profit_price": None,
            "scale_out_fraction": None,
            "reasoning": "Demo hold",
            "risk_flags": []
        }
    if "post_trade_debrief" in user_prompt:
        return {
            "symbol": market_state.get("symbol", "UNKNOWN"),
            "direction": "LONG",
            "entry_date": "2026-08-18",
            "exit_date": "2026-08-18",
            "entry_price": market_state.get("price", 0),
            "exit_price": market_state.get("price", 0) * 1.03,
            "position_size": 1000,
            "pnl_usd": 30,
            "pnl_r_multiple": 3.0,
            "setup_type": "trend_pullback",
            "what_worked": ["trend", "volume"],
            "what_failed": [],
            "lessons": ["stay disciplined"],
            "follow_rule": True,
            "deviations": [],
            "next_action": ["no_change"]
        }
    # Default fallback
    return {}

def main():
    # Load core system prompt (mindset)
    system_prompt_path = Path(__file__).parent / "agent_prompt.txt"
    system_prompt = system_prompt_path.read_text(encoding="utf-8")

    # Load example market state – in a real bot this would come from an API
    market_state = {
        "symbol": "ALT/USDT",
        "price": 1.2345,
        "timeframe": "4h",
        "indicators": {
            "ema_50": 1.18,
            "ema_200": 1.05,
            "rsi_14": 58,
            "atr_14": 0.08,
            "volume_ratio_24h": 1.8,
            "liquidity_score": 0.7
        },
        "market_cap_rank": 120,
        "recent_news_sentiment": "neutral",
        "portfolio": {"equity_usd": 10000, "cash_usd": 8500, "positions": []},
        "regime": "altcoin_trending_up",
        "btc_correlation_warning": False
    }

    # Initial state
    state = AgentState.SCAN
    while True:
        if state == AgentState.SCAN:
            # In a real system, scanning would discover setups – here we force one
            state = transition(state, "setup_detected")
            continue
        if state == AgentState.EVALUATE:
            # Assume thesis is valid for demo
            state = transition(state, "thesis_valid")
            continue
        if state == AgentState.PRE_TRADE_CHECK:
            pre_trade_prompt = load_prompt("pre_trade_check.txt")
            response = call_llm(system_prompt, pre_trade_prompt, market_state)
            if response.get("decision") == "APPROVE":
                state = transition(state, "checks_passed")
                # Record trade proposal (dummy)
                trade = {
                    "symbol": market_state["symbol"],
                    "action": "BUY",
                    "entry_price": market_state["price"],
                    "stop_loss_price": market_state["price"] * 0.95,
                    "take_profit_price": market_state["price"] * 1.05,
                    "position_size": 1000,
                    "confidence": 80
                }
                # Save to open_positions.json
                open_path = Path(__file__).parent / "state" / "open_positions.json"
                open_path.write_text(json.dumps([trade], indent=2))
            else:
                # FLAT – go back to scanning
                state = transition(state, "setup_detected")
                continue
            continue
        if state == AgentState.OPEN:
            # Move to MANAGE after marking position opened
            state = transition(state, "position_opened")
            continue
        if state == AgentState.MANAGE:
            in_trade_prompt = load_prompt("in_trade_management.txt")
            response = call_llm(system_prompt, in_trade_prompt, market_state)
            # For demo we just HOLD and stay in MANAGE – break after one loop
            if response.get("action") == "EXIT":
                state = transition(state, "exit_signal")
            else:
                # Keep managing – in demo we exit after one iteration
                state = transition(state, "exit_signal")
            continue
        if state == AgentState.EXIT:
            # Simulate exit and generate debrief
            post_prompt = load_prompt("post_trade_debrief.txt")
            debrief = call_llm(system_prompt, post_prompt, market_state)
            # Append to trade_log.json
            log_path = Path(__file__).parent / "state" / "trade_log.json"
            existing = json.loads(log_path.read_text())
            existing.append(debrief)
            log_path.write_text(json.dumps(existing, indent=2))
            state = transition(state, "trade_closed")
            continue
        if state == AgentState.REVIEW:
            # After review, loop back to scanning for next trade
            state = transition(state, "review_done")
            # End demo after one full cycle
            print("Demo cycle complete. Check the generated files in ./state/.")
            break

if __name__ == "__main__":
    main()
