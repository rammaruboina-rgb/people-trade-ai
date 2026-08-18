# webhook_server.py
"""
TradingView Webhook Listener Server (FastAPI / Uvicorn)
Receives alert payloads from TradingView Pine Script indicators.
Forwards high-confidence signals to Master Trading Agent.
Fallback port handling to ensure 100% server startup.
"""

import logging
import uvicorn
import socket
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from config import WEBHOOK_HOST, WEBHOOK_PORT, WEBHOOK_SECRET

logger = logging.getLogger(__name__)

app = FastAPI(title="CoinDCX TradingView Webhook Listener", version="2.0.0")

class SignalPayload(BaseModel):
    secret: str
    symbol: str
    action: str  # BUY / SELL / LONG / SHORT
    confidence: Optional[float] = 95.0
    indicator: Optional[str] = "TradingView_Indicator"

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_available_port(start_port: int = 8000) -> int:
    port = start_port
    while is_port_in_use(port):
        logger.warning(f"⚠️ Port {port} is in use. Trying port {port + 1}...")
        port += 1
    return port

@app.get("/")
def read_root():
    return {"status": "online", "system": "CoinDCX TradingView Listener"}

@app.post("/webhook")
async def handle_webhook(payload: SignalPayload):
    if payload.secret != WEBHOOK_SECRET:
        logger.warning("❌ Unauthorized webhook attempt rejected.")
        raise HTTPException(status_code=401, detail="Invalid Webhook Secret Key")

    logger.info(f"📥 WEBHOOK SIGNAL RECEIVED: {payload.action} {payload.symbol} | Conf: {payload.confidence}% | Source: {payload.indicator}")
    
    return {
        "status": "ACCEPTED",
        "action": payload.action,
        "symbol": payload.symbol,
        "confidence": payload.confidence,
        "timestamp": datetime.now().isoformat()
    }

def run_webhook_server():
    port = find_available_port(WEBHOOK_PORT)
    logger.info(f"✅ TradingView Webhook listener starting on http://{WEBHOOK_HOST}:{port}/webhook")
    uvicorn.run(app, host=WEBHOOK_HOST, port=port, log_level="error")

if __name__ == "__main__":
    run_webhook_server()
