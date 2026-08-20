#!/usr/bin/env bash
# autotrade.sh - CoinDCX Autonomous Wyckoff Trading Agent Controller

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON="./venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="python3"
fi

show_menu() {
    echo "================================================================================"
    echo "🚀 COINDCX AUTONOMOUS WYCKOFF FUTURES SCALPER CONTROL PANEL"
    echo "================================================================================"
    echo "  1) 🟢 Start Autonomous Agent in Background"
    echo "  2) 📊 View Active Open Positions & Balance"
    echo "  3) 📜 View Live Scanning Logs (tail -f)"
    echo "  4) ⚡ Execute Immediate Market Trade (Instant Buy)"
    echo "  5) 🔴 Stop Autonomous Agent"
    echo "  6) ❌ Exit Control Panel"
    echo "================================================================================"
}

start_bot() {
    pkill -9 -f coindcx_master_agent >/dev/null 2>&1 || true
    echo "[+] Launching Master Agent in background..."
    nohup "$VENV_PYTHON" -u coindcx_master_agent.py >> trading_bot.log 2>&1 &
    sleep 2
    echo "✅ Agent is running in background! Use option 3 to view live logs."
}

view_positions() {
    echo "[+] Fetching Live Positions & Balance from CoinDCX API..."
    "$VENV_PYTHON" -c "
from coindcx_client import CoinDCXClient
c = CoinDCXClient()
print('💰 BALANCES:', c.get_account_balances())
print('📊 POSITIONS:', c.get_active_futures_positions())
"
}

view_logs() {
    echo "[+] Press Ctrl+C to stop viewing logs."
    tail -n 50 -f trading_bot.log
}

execute_trade() {
    echo "[+] Submitting Immediate Live Market Order..."
    "$VENV_PYTHON" -c "
import time, json
from coindcx_client import CoinDCXClient
client = CoinDCXClient()
mark_price = client.get_ticker_price('SUIUSDT')
qty = 10
leverage = 20
side = 'BUY'
tp_price = round(mark_price * 1.02, 4)
sl_price = round(mark_price * 0.99, 4)
print(f'🔥 EXECUTING LIVE ORDER: {side} {qty} SUI @ ${mark_price}...')
resp = client.place_order(symbol='SUIUSDT', side=side, amount=qty, leverage=leverage, sl_price=sl_price, tp_price=tp_price, market_type='futures')
print('EXCHANGE RESPONSE:', json.dumps(resp, indent=2))
"
}

stop_bot() {
    echo "[+] Stopping all agent processes..."
    pkill -9 -f coindcx_master_agent >/dev/null 2>&1 || true
    echo "🔴 Trading Agent Stopped."
}

if [ "$1" == "start" ]; then
    start_bot
    exit 0
elif [ "$1" == "status" ]; then
    view_positions
    exit 0
elif [ "$1" == "logs" ]; then
    view_logs
    exit 0
elif [ "$1" == "stop" ]; then
    stop_bot
    exit 0
elif [ "$1" == "trade" ]; then
    execute_trade
    exit 0
fi

while true; do
    show_menu
    read -p "Select option [1-6]: " choice
    case $choice in
        1) start_bot ;;
        2) view_positions ;;
        3) view_logs ;;
        4) execute_trade ;;
        5) stop_bot ;;
        6) echo "Exiting control panel."; exit 0 ;;
        *) echo "Invalid option, please try again." ;;
    esac
    echo ""
done
