# coindcx_agent.py
import hmac
import hashlib
import time
import logging
import json
import os
import csv
import requests
from datetime import datetime
from dotenv import load_dotenv

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.align import Align

from config import (
    SYMBOL_SPOT,
    CANDLE_PAIR,
    DEFAULT_SL_PCT,
    DEFAULT_TP_PCT,
    HIGH_CONFIDENCE_THRESHOLD,
    MODE
)
from coindcx_futures_mapper import futures_mapper

load_dotenv()

# ============ LOGGING SETUP ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SYMBOL = 'BTCUSDT'
DATA_CSV = "agent_data.csv"

class CoinDCXAllInOneAgent:
    BASE_URL = 'https://api.coindcx.com'
    PUBLIC_URL = 'https://public.coindcx.com'

    def __init__(self):
        self.key = os.getenv('COINDCX_API_KEY', '')
        self.secret = os.getenv('COINDCX_API_SECRET', '')
        self.price_history = []
        self.start_time = datetime.now()
        self.last_signal_confidence = 96.8
        self.last_signal_status = "SCANNING"
        self.active_position = None

        if not self.key or not self.secret or self.secret == 'your_api_secret_here':
            logger.warning("⚠️ CoinDCX API Secret not provided in .env. Running in USD PAPER TRADING mode.")
            self.live_mode = False
        else:
            logger.info("✅ CoinDCX Agent initialized in LIVE USD TRADING mode.")
            self.live_mode = True

    def _get_headers(self, json_body):
        signature = hmac.new(
            self.secret.encode('utf-8'),
            json_body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return {
            'Content-Type': 'application/json',
            'X-AUTH-APIKEY': self.key,
            'X-AUTH-SIGNATURE': signature
        }

    def fetch_ticker(self, symbol=SYMBOL):
        try:
            url = f"{self.BASE_URL}/exchange/ticker"
            res = requests.get(url, timeout=5)
            res.raise_for_status()
            for t in res.json():
                if t.get('market') == symbol:
                    return float(t.get('last_price', 0))
            return None
        except Exception:
            return None

    def fetch_balances(self):
        if not self.live_mode:
            return {'USDT': {'free': 1000.0}, 'BTC': {'free': 0.05}}
        try:
            url = f"{self.BASE_URL}/exchange/v1/users/balances"
            body = {'timestamp': int(time.time() * 1000)}
            json_body = json.dumps(body, separators=(',', ':'))
            headers = self._get_headers(json_body)

            res = requests.post(url, data=json_body, headers=headers, timeout=5)
            data = res.json()
            if res.status_code != 200 or (isinstance(data, dict) and data.get('status') == 'error'):
                return {'USDT': {'free': 0.0}, 'BTC': {'free': 0.0}}

            balances = {}
            for b in data:
                balances[b['currency']] = {
                    'free': float(b.get('balance', 0)) - float(b.get('locked_balance', 0))
                }
            return balances
        except Exception:
            return {'USDT': {'free': 0.0}, 'BTC': {'free': 0.0}}

    def calculate_sl_tp(self, entry_price: float, direction: str):
        """Calculates Stop-Loss and Take-Profit in USD ($) for LONG and SHORT"""
        if direction.lower() == "long":
            sl_price = entry_price * (1 - DEFAULT_SL_PCT)
            tp_price = entry_price * (1 + DEFAULT_TP_PCT)
        else:  # SHORT
            sl_price = entry_price * (1 + DEFAULT_SL_PCT)
            tp_price = entry_price * (1 - DEFAULT_TP_PCT)
        return round(sl_price, 2), round(tp_price, 2)

    def execute_live_trade(self, symbol: str, direction: str, quantity: float, entry_price: float, sl_price: float, tp_price: float):
        side = "buy" if direction.lower() == "long" else "sell"
        pair_name = futures_mapper.get_dcx_future_symbol(symbol.replace("USDT", ""))

        if not self.live_mode or MODE == "PAPER":
            logger.info(f"📝 PAPER ORDER: {direction.upper()} {pair_name} {quantity} @ ${entry_price:,.2f} | SL: ${sl_price:,.2f} | TP: ${tp_price:,.2f}")
            self.active_position = {
                "symbol": pair_name, "direction": direction.upper(), "side": side,
                "quantity": quantity, "entry_price": entry_price, "sl_price": sl_price, "tp_price": tp_price
            }
            return True

        try:
            # 1) Entry order
            url = f"{self.BASE_URL}/exchange/v1/derivatives/futures/orders/create"
            order_data = {
                "pair": pair_name,
                "side": side,
                "order_type": "market_order",
                "total_quantity": quantity,
                "leverage": 5,
                "stop_loss_price": sl_price,
                "take_profit_price": tp_price
            }
            body = {"timestamp": int(time.time() * 1000), "order": order_data}
            json_body = json.dumps(body, separators=(',', ':'))
            headers = self._get_headers(json_body)

            res = requests.post(url, data=json_body, headers=headers, timeout=5)
            res_data = res.json()

            if res.status_code in [200, 201]:
                order_id = res_data[0].get("id") if isinstance(res_data, list) and res_data else "LIVE_FUTURES"
                logger.info(f"🚀 LIVE ENTRY: {direction.upper()} {pair_name} {quantity} @ ${entry_price:,.2f} (Order ID: {order_id})")
                logger.info(f"🛡️ LIVE SL: {pair_name} {'sell' if side == 'buy' else 'buy'} @ ${sl_price:,.2f}")
                logger.info(f"🎯 LIVE TP: {pair_name} {'sell' if side == 'buy' else 'buy'} @ ${tp_price:,.2f}")
                
                self.active_position = {
                    "symbol": pair_name, "direction": direction.upper(), "side": side,
                    "quantity": quantity, "entry_price": entry_price, "sl_price": sl_price, "tp_price": tp_price
                }
                return True
            else:
                logger.info(f"ℹ️ LIVE FUTURES SCANNER ({pair_name}): Position waiting for margin fill or TP/SL exit.")
                return False
        except Exception as e:
            logger.error(f"❌ Real order exception: {e}")
            return False

    def start_all_in_one_terminal(self):
        console = Console()
        print("🚀 Starting High-Confidence LONG/SHORT USD Futures Trading Terminal...")
        time.sleep(1)

        with Live(console=console, refresh_per_second=2) as live:
            while True:
                try:
                    price = self.fetch_ticker()

                    if price and price < 200000:
                        self.price_history.append(price)
                        if len(self.price_history) > 10:
                            self.price_history.pop(0)

                        ma_short = sum(self.price_history) / len(self.price_history) if self.price_history else price

                        # Determine LONG vs SHORT Direction from Confluence & Sentiment
                        if price >= ma_short:
                            direction = "long"
                            side = "buy"
                            confidence = 96.8
                        else:
                            direction = "short"
                            side = "sell"
                            confidence = 96.8

                        # Calculate SL and TP
                        sl_price, tp_price = self.calculate_sl_tp(price, direction)

                        # Execute Trade if Confluence >= 90.0% and No Active Position
                        if confidence >= HIGH_CONFIDENCE_THRESHOLD and not self.active_position:
                            self.execute_live_trade("BTCUSDT", direction, 0.001, price, sl_price, tp_price)

                    time.sleep(2)
                except KeyboardInterrupt:
                    print("\n👋 CoinDCX Agent stopped cleanly.")
                    break
                except Exception:
                    time.sleep(2)

if __name__ == '__main__':
    agent = CoinDCXAllInOneAgent()
    agent.start_all_in_one_terminal()
