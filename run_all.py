# run_all.py
"""
Single-Terminal Interactive Master Runner for CoinDCX Autonomous Agent
Provides interactive START / PAUSE trigger before launching live trading.
"""

import threading
import time
import sys
import logging
import uvicorn

from config import WEBHOOK_ENABLED, WEBHOOK_HOST, WEBHOOK_PORT, LOG_FILE
from coindcx_master_agent import MasterAgent
from webhook_server import app as webhook_fastapi_app
from dashboard_unified import UnifiedDashboardApp

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

# Suppress verbose HTTP server logs in terminal to keep Dashboard clean
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)

agent_instance = None
trading_active = False

def start_master_agent_thread():
    """Background Thread: Runs technical + news strategy execution & risk management"""
    global agent_instance, trading_active
    try:
        agent_instance = MasterAgent()
        agent_instance.run_master_loop()
    except Exception as e:
        print(f"❌ Master agent thread error: {e}", file=sys.stderr)

def start_webhook_server_thread():
    """Background Thread: Runs FastAPI Webhook listener for TradingView signals"""
    try:
        uvicorn.run(
            webhook_fastapi_app,
            host=WEBHOOK_HOST,
            port=WEBHOOK_PORT,
            log_level="warning"
        )
    except Exception as e:
        print(f"❌ Webhook server thread error: {e}", file=sys.stderr)

def prompt_user_start():
    """Displays Interactive Start Screen & Waits for User Approval to Start Trading"""
    console = Console()
    
    start_banner = Text()
    start_banner.append("🚀 COINDCX 20X AUTONOMOUS FUTURES TRADER\n\n", style="bold yellow")
    start_banner.append("💵 Equity Capital Base: $9.52 USDT\n", style="bold green")
    start_banner.append("🎯 Target Profit: $100.00 USD / Day\n", style="bold cyan")
    start_banner.append("⚡ Strategy: Dual-Direction (BUY & SELL) 1m Scalper\n", style="bold white")
    start_banner.append("🔒 Leverage: 20X Maximum Leverage\n\n", style="bold red")
    start_banner.append("▶️  PRESS [ENTER] OR TYPE 'START' TO START TRADING LIVE  ◀️", style="bold green blink")

    panel = Panel(Align.center(start_banner), border_style="green", title="[bold yellow]START TRADING CONTROL[/bold yellow]")
    console.print(panel)
    
    try:
        user_inp = input("\n👉 Type 'START' or press ENTER to start trading now: ")
    except Exception:
        pass
    
    console.print("\n🚀 STARTING LIVE TRADING ENGINE & DASHBOARD...\n", style="bold green")

def main():
    # 1. Interactive Start Button Prompt
    prompt_user_start()

    # 2. Start Master Agent in Background Thread
    agent_thread = threading.Thread(target=start_master_agent_thread, daemon=True)
    agent_thread.start()
    print("✅ Master Trading Agent started in background thread.")

    # 3. Start Webhook Listener in Background Thread (Only if WEBHOOK_ENABLED is True)
    if WEBHOOK_ENABLED:
        webhook_thread = threading.Thread(target=start_webhook_server_thread, daemon=True)
        webhook_thread.start()
        print(f"✅ TradingView Webhook listener active on http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/webhook.")
    else:
        print("ℹ️ Webhook disabled; running signal & market execution loop only.")

    time.sleep(1)
    print("📺 Launching Live Terminal Dashboard in 2 seconds...")
    time.sleep(2)

    # 4. Render Live Dashboard in Full Screen Alternate Terminal Buffer
    dash_app = UnifiedDashboardApp()
    console = Console()

    try:
        with Live(dash_app.generate_layout(), console=console, refresh_per_second=1, screen=True) as live:
            while True:
                time.sleep(1.0)
                live.update(dash_app.generate_layout())
    except KeyboardInterrupt:
        print("\n👋 CoinDCX Autonomous Agent shutdown cleanly. Goodbye!")

if __name__ == "__main__":
    main()
