# run_all.py
"""
Single-Terminal Master Runner for CoinDCX Autonomous Agent
Runs:
1. Autonomous Master Trading Loop (Background Thread)
2. TradingView Webhook Listener Server (Background Thread - Optional via WEBHOOK_ENABLED)
3. Live Rich Terminal Dashboard (Foreground Single Terminal Window with Full-Screen Screen Refresh)
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

# Suppress verbose HTTP server logs in terminal to keep Dashboard clean
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)

def start_master_agent_thread():
    """Background Thread: Runs technical + news strategy execution & risk management"""
    try:
        agent = MasterAgent()
        agent.run_master_loop()
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

def main():
    print("🚀 Initializing CoinDCX All-In-One Autonomous Trading Terminal...")

    # 1. Start Master Agent in Background Thread
    agent_thread = threading.Thread(target=start_master_agent_thread, daemon=True)
    agent_thread.start()
    print("✅ Master Trading Agent started in background thread.")

    # 2. Start Webhook Listener in Background Thread (Only if WEBHOOK_ENABLED is True)
    if WEBHOOK_ENABLED:
        webhook_thread = threading.Thread(target=start_webhook_server_thread, daemon=True)
        webhook_thread.start()
        print(f"✅ TradingView Webhook listener active on http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/webhook.")
    else:
        print("ℹ️ Webhook disabled; running signal & market execution loop only.")

    time.sleep(1)
    print("📺 Launching Unified Dashboard in 2 seconds...")
    time.sleep(2)

    # 3. Render Live Dashboard in Full Screen Alternate Terminal Buffer (No Line Stacking)
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
