# coindcx_agent_futures_stp.py
import hmac
import hashlib
import time
import logging
import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ============ LOGGING SETUP ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_futures_stp.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ CONFIG ============
SYMBOL = 'BTC/USDT:USDT'
CANDLE_PAIR = 'B-BTC_USDT'
MARKET_SYMBOL = 'BTCUSDT'
TRADE_AMOUNT = 0.001       # BTC position size per trade
LEVERAGE = 10              # 10x Leverage
MARGIN_TYPE = 'isolated'   # isolated or cross
CHECK_INTERVAL = 5         # Check market every 5 seconds for SL/TP monitoring

# Thresholds for entry signals
BUY_THRESHOLD = 50000      # Open LONG if price < $50k
SELL_THRESHOLD = 70000     # Open SHORT if price > $70k

# Stop-Loss and Take-Profit Settings
STOP_LOSS_PERCENT = 0.05   # 5% Stop-Loss
TAKE_PROFIT_PERCENT = 0.10 # 10% Take-Profit

# ============ FUTURES STP AGENT CLASS ============
class CoinDCXFuturesSTPAgent:
    BASE_URL = 'https://api.coindcx.com'
    PUBLIC_URL = 'https://public.coindcx.com'

    def __init__(self):
        self.key = os.getenv('COINDCX_API_KEY', '')
        self.secret = os.getenv('COINDCX_API_SECRET', '')
        
        # Position & SL/TP tracking state
        self.position = None         # None, 'LONG', or 'SHORT'
        self.entry_price = 0.0
        self.position_size = 0.0
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0

        if not self.key or not self.secret or self.secret == 'your_api_secret_here':
            logger.warning("⚠️ CoinDCX API Secret not set in .env. Running Futures STP Agent in PAPER TRADING mode.")
            self.live_mode = False
        else:
            logger.info("✅ CoinDCX Futures STP Agent initialized in LIVE TRADING mode.")
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

    def fetch_mark_price(self):
        """Fetch live ticker mark price"""
        try:
            url = f"{self.BASE_URL}/exchange/ticker"
            res = requests.get(url, timeout=5)
            res.raise_for_status()
            for t in res.json():
                if t.get('market') == MARKET_SYMBOL:
                    return float(t.get('last_price', 0))
            return 0.0
        except Exception as e:
            logger.error(f"❌ Error fetching mark price: {e}")
            return 0.0

    def calculate_sl_tp(self, entry_price, side):
        """Calculate Stop-Loss and Take-Profit price levels"""
        if side == 'LONG':
            sl = entry_price * (1 - STOP_LOSS_PERCENT)
            tp = entry_price * (1 + TAKE_PROFIT_PERCENT)
        else:  # SHORT
            sl = entry_price * (1 + STOP_LOSS_PERCENT)
            tp = entry_price * (1 - TAKE_PROFIT_PERCENT)
        return round(sl, 2), round(tp, 2)

    def calculate_liquidation_price(self, entry_price, side):
        """Estimate liquidation price based on leverage"""
        if entry_price == 0:
            return 0.0
        maintenance_margin = 0.005
        if side == 'LONG':
            return entry_price * (1 - (1.0 / LEVERAGE) + maintenance_margin)
        elif side == 'SHORT':
            return entry_price * (1 + (1.0 / LEVERAGE) - maintenance_margin)
        return 0.0

    def open_position(self, side, price, amount=TRADE_AMOUNT):
        """Open a LONG or SHORT futures position and immediately set SL/TP"""
        sl_price, tp_price = self.calculate_sl_tp(price, side)

        if self.live_mode:
            try:
                url = f"{self.BASE_URL}/exchange/v1/derivatives/futures/orders/create"
                body = {
                    'timestamp': int(time.time() * 1000),
                    'pair': CANDLE_PAIR,
                    'order_type': 'market_order',
                    'side': 'buy' if side == 'LONG' else 'sell',
                    'total_quantity': amount,
                    'leverage': LEVERAGE,
                    'margin_type': MARGIN_TYPE
                }
                json_body = json.dumps(body, separators=(',', ':'))
                headers = self._get_headers(json_body)
                res = requests.post(url, data=json_body, headers=headers, timeout=5)
                data = res.json()
                if res.status_code == 200:
                    logger.info(f"🟢 {side} signal triggered: ${price:,.2f}")
                    logger.info(f"✅ Futures order placed: {data.get('orders', [{}])[0].get('id', 'N/A')} | {side} {amount} BTC")
                    logger.info(f"🛑 Stop-Loss set at: ${sl_price:,.2f} ({STOP_LOSS_PERCENT*100}%)")
                    logger.info(f"🎯 Take-Profit set at: ${tp_price:,.2f} ({TAKE_PROFIT_PERCENT*100}%)")

                    self.position = side
                    self.entry_price = price
                    self.position_size = amount
                    self.stop_loss_price = sl_price
                    self.take_profit_price = tp_price
                    self.log_futures_trade('OPEN_' + side, amount, price, "LIVE", sl_price, tp_price)
                    return True
                else:
                    logger.error(f"❌ Futures order failed: {data}")
                    return False
            except Exception as e:
                logger.error(f"❌ Futures order exception: {e}")
                return False
        else:
            logger.info(f"🟢 {side} signal triggered (PAPER): ${price:,.2f}")
            logger.info(f"✅ Futures order placed: PAPER_{int(time.time())} | {side} {amount} BTC @ ${price:,.2f}")
            logger.info(f"🛑 Stop-Loss set at: ${sl_price:,.2f} ({STOP_LOSS_PERCENT*100}%)")
            logger.info(f"🎯 Take-Profit set at: ${tp_price:,.2f} ({TAKE_PROFIT_PERCENT*100}%)")

            self.position = side
            self.entry_price = price
            self.position_size = amount
            self.stop_loss_price = sl_price
            self.take_profit_price = tp_price
            self.log_futures_trade('OPEN_' + side, amount, price, "PAPER", sl_price, tp_price)
            return True

    def close_position(self, price, reason):
        """Close active futures position when SL or TP is triggered"""
        if not self.position:
            return

        active_side = self.position
        if self.live_mode:
            try:
                url = f"{self.BASE_URL}/exchange/v1/derivatives/futures/orders/create"
                body = {
                    'timestamp': int(time.time() * 1000),
                    'pair': CANDLE_PAIR,
                    'order_type': 'market_order',
                    'side': 'sell' if active_side == 'LONG' else 'buy',
                    'total_quantity': self.position_size,
                    'leverage': LEVERAGE,
                    'margin_type': MARGIN_TYPE,
                    'reduce_only': True
                }
                json_body = json.dumps(body, separators=(',', ':'))
                headers = self._get_headers(json_body)
                res = requests.post(url, data=json_body, headers=headers, timeout=5)
                data = res.json()
                order_id = data.get('orders', [{}])[0].get('id', 'N/A') if res.status_code == 200 else 'N/A'
                logger.info(f"✅ Position closed ({reason}): {order_id} | CLOSE {active_side} {self.position_size} BTC @ ${price:,.2f}")
            except Exception as e:
                logger.error(f"❌ Error closing position: {e}")
        else:
            logger.info(f"✅ Position closed ({reason}): PAPER_CLOSE_{int(time.time())} | CLOSE {active_side} {self.position_size} BTC @ ${price:,.2f}")

        self.log_futures_trade('CLOSE_' + active_side, self.position_size, price, "LIVE" if self.live_mode else "PAPER", self.stop_loss_price, self.take_profit_price, reason)
        self.position = None
        self.entry_price = 0.0
        self.position_size = 0.0
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0

    def log_futures_trade(self, action, amount, price, mode, sl=0.0, tp=0.0, reason="ENTRY"):
        trade_data = {
            'timestamp': datetime.now().isoformat(),
            'symbol': SYMBOL,
            'action': action,
            'amount': amount,
            'price': price,
            'leverage': LEVERAGE,
            'stop_loss': sl,
            'take_profit': tp,
            'mode': mode,
            'reason': reason
        }
        with open('trades_futures.csv', 'a') as f:
            f.write(json.dumps(trade_data) + '\n')
        logger.info(f"📝 Futures Trade Logged: {trade_data}")

    def trading_loop(self):
        """Main Futures STP Monitoring Loop"""
        logger.info(f"🚀 Starting CoinDCX Futures STP Agent ({LEVERAGE}x Leverage | SL: {STOP_LOSS_PERCENT*100}% | TP: {TAKE_PROFIT_PERCENT*100}%)...")

        while True:
            try:
                price = self.fetch_mark_price()

                if price > 0:
                    logger.info(f"📊 {SYMBOL} @ ${price:,.2f}")

                    # 1. Active Position SL/TP Checks
                    if self.position == 'LONG':
                        logger.info(f"🛑 Stop-Loss: ${self.stop_loss_price:,.2f} | 🎯 Take-Profit: ${self.take_profit_price:,.2f}")
                        if price <= self.stop_loss_price:
                            logger.warning(f"🛑 STOP-LOSS TRIGGERED: ${price:,.2f} <= ${self.stop_loss_price:,.2f}")
                            self.close_position(price, "STOP_LOSS")
                        elif price >= self.take_profit_price:
                            logger.info(f"🎯 TAKE-PROFIT TRIGGERED: ${price:,.2f} >= ${self.take_profit_price:,.2f}")
                            self.close_position(price, "TAKE_PROFIT")

                    elif self.position == 'SHORT':
                        logger.info(f"🛑 Stop-Loss: ${self.stop_loss_price:,.2f} | 🎯 Take-Profit: ${self.take_profit_price:,.2f}")
                        if price >= self.stop_loss_price:
                            logger.warning(f"🛑 STOP-LOSS TRIGGERED: ${price:,.2f} >= ${self.stop_loss_price:,.2f}")
                            self.close_position(price, "STOP_LOSS")
                        elif price <= self.take_profit_price:
                            logger.info(f"🎯 TAKE-PROFIT TRIGGERED: ${price:,.2f} <= ${self.take_profit_price:,.2f}")
                            self.close_position(price, "TAKE_PROFIT")

                    # 2. Check Signal Entry (If no active position)
                    else:
                        if price < BUY_THRESHOLD:
                            self.open_position('LONG', price)
                        elif price > SELL_THRESHOLD:
                            self.open_position('SHORT', price)
                        else:
                            logger.info(f"⏳ No active position: ${price:,.2f} is between ${BUY_THRESHOLD:,.2f} and ${SELL_THRESHOLD:,.2f}")

                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("⛔ Futures STP agent stopped.")
                break
            except Exception as e:
                logger.error(f"❌ Futures loop error: {e}", exc_info=True)
                time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    agent = CoinDCXFuturesSTPAgent()
    agent.trading_loop()
