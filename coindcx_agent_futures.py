# coindcx_agent_futures.py
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
        logging.FileHandler('trading_futures.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ CONFIG ============
SYMBOL = 'BTC/USDT:USDT'
CANDLE_PAIR = 'B-BTC_USDT'
TRADE_AMOUNT = 0.001       # BTC position size per trade
LEVERAGE = 10              # 10x Leverage
MARGIN_TYPE = 'isolated'   # isolated or cross
CHECK_INTERVAL = 10        # Check every 10 seconds
RSI_PERIOD = 14
RSI_LONG_LEVEL = 40.0      # Open LONG when RSI <= 40 (Oversold)
RSI_SHORT_LEVEL = 60.0     # Open SHORT when RSI >= 60 (Overbought)
STOP_LOSS_PCT = 0.02       # 2% Stop Loss
TAKE_PROFIT_PCT = 0.04     # 4% Take Profit

# ============ FUTURES AGENT CLASS ============
class CoinDCXFuturesAgent:
    BASE_URL = 'https://api.coindcx.com'
    PUBLIC_URL = 'https://public.coindcx.com'

    def __init__(self):
        self.key = os.getenv('COINDCX_API_KEY', '')
        self.secret = os.getenv('COINDCX_API_SECRET', '')
        
        # Position state tracking
        self.position = None  # None, 'LONG', or 'SHORT'
        self.entry_price = 0.0
        self.position_size = 0.0

        if not self.key or not self.secret or self.secret == 'your_api_secret_here':
            logger.warning("⚠️ CoinDCX API Secret not set in .env. Running Futures Agent in PAPER TRADING mode.")
            self.live_mode = False
        else:
            logger.info("✅ CoinDCX Futures Agent initialized in LIVE TRADING mode.")
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
        """Fetch live ticker mark price for BTC futures"""
        try:
            url = f"{self.BASE_URL}/exchange/ticker"
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            for t in res.json():
                if t.get('market') == 'BTCUSDT':
                    return float(t.get('last_price', 0))
            return 0.0
        except Exception as e:
            logger.error(f"❌ Error fetching mark price: {e}")
            return 0.0

    def fetch_rsi(self, period=RSI_PERIOD):
        """Calculate RSI from 1m candles"""
        try:
            url = f"{self.PUBLIC_URL}/market_data/candles?pair={CANDLE_PAIR}&interval=1m"
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            candles = res.json()
            if len(candles) < period + 1:
                return 50.0

            closes = [float(c['close']) for c in reversed(candles[:period + 15])]
            gains, losses = [], []
            for i in range(1, len(closes)):
                delta = closes[i] - closes[i - 1]
                if delta >= 0:
                    gains.append(delta)
                    losses.append(0.0)
                else:
                    gains.append(0.0)
                    losses.append(abs(delta))

            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            if avg_loss == 0:
                return 100.0
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
            return round(rsi, 2)
        except Exception as e:
            logger.error(f"❌ Error fetching RSI: {e}")
            return 50.0

    def calculate_liquidation_price(self, entry_price, side):
        """Estimate liquidation price based on leverage"""
        if entry_price == 0:
            return 0.0
        maintenance_margin = 0.005  # 0.5% approx
        if side == 'LONG':
            return entry_price * (1 - (1.0 / LEVERAGE) + maintenance_margin)
        elif side == 'SHORT':
            return entry_price * (1 + (1.0 / LEVERAGE) - maintenance_margin)
        return 0.0

    def open_position(self, side, price, amount=TRADE_AMOUNT):
        """Open a LONG or SHORT futures position"""
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
                res = requests.post(url, data=json_body, headers=headers, timeout=10)
                data = res.json()
                if res.status_code == 200:
                    logger.info(f"🚀 LIVE FUTURES POSITION OPENED: {side} {amount} BTC @ ${price:,.2f} ({LEVERAGE}x)")
                    self.position = side
                    self.entry_price = price
                    self.position_size = amount
                    self.log_futures_trade('OPEN_' + side, amount, price, "LIVE")
                    return True
                else:
                    logger.error(f"❌ Futures order failed: {data}")
                    return False
            except Exception as e:
                logger.error(f"❌ Futures order exception: {e}")
                return False
        else:
            logger.info(f"🎮 PAPER FUTURES POSITION OPENED: {side} {amount} BTC @ ${price:,.2f} ({LEVERAGE}x)")
            self.position = side
            self.entry_price = price
            self.position_size = amount
            self.log_futures_trade('OPEN_' + side, amount, price, "PAPER")
            return True

    def close_position(self, price, reason="TARGET"):
        """Close active futures position"""
        if not self.position:
            return
        
        side = 'SHORT' if self.position == 'LONG' else 'LONG'
        if self.live_mode:
            try:
                url = f"{self.BASE_URL}/exchange/v1/derivatives/futures/orders/create"
                body = {
                    'timestamp': int(time.time() * 1000),
                    'pair': CANDLE_PAIR,
                    'order_type': 'market_order',
                    'side': 'sell' if self.position == 'LONG' else 'buy',
                    'total_quantity': self.position_size,
                    'leverage': LEVERAGE,
                    'margin_type': MARGIN_TYPE
                }
                json_body = json.dumps(body, separators=(',', ':'))
                headers = self._get_headers(json_body)
                res = requests.post(url, data=json_body, headers=headers, timeout=10)
                if res.status_code == 200:
                    logger.info(f"🛑 LIVE FUTURES POSITION CLOSED ({reason}): Closed {self.position} @ ${price:,.2f}")
                    self.log_futures_trade('CLOSE_' + self.position, self.position_size, price, "LIVE", reason)
                    self.position = None
                    self.entry_price = 0.0
                    self.position_size = 0.0
            except Exception as e:
                logger.error(f"❌ Error closing position: {e}")
        else:
            logger.info(f"🎮 PAPER FUTURES POSITION CLOSED ({reason}): Closed {self.position} @ ${price:,.2f}")
            self.log_futures_trade('CLOSE_' + self.position, self.position_size, price, "PAPER", reason)
            self.position = None
            self.entry_price = 0.0
            self.position_size = 0.0

    def log_futures_trade(self, action, amount, price, mode, note=""):
        trade_data = {
            'timestamp': datetime.now().isoformat(),
            'symbol': SYMBOL,
            'action': action,
            'amount': amount,
            'price': price,
            'leverage': LEVERAGE,
            'mode': mode,
            'note': note
        }
        with open('trades_futures.csv', 'a') as f:
            f.write(json.dumps(trade_data) + '\n')
        logger.info(f"📝 Futures Trade Logged: {trade_data}")

    def trading_loop(self):
        """Autonomous Futures Trading Loop"""
        logger.info(f"🚀 Starting CoinDCX Futures Agent ({LEVERAGE}x Leverage)...")

        while True:
            try:
                price = self.fetch_mark_price()
                rsi = self.fetch_rsi()

                if price > 0:
                    liq_price = self.calculate_liquidation_price(self.entry_price, self.position) if self.position else 0.0
                    pnl_pct = 0.0
                    if self.position == 'LONG':
                        pnl_pct = ((price - self.entry_price) / self.entry_price) * LEVERAGE * 100
                    elif self.position == 'SHORT':
                        pnl_pct = ((self.entry_price - price) / self.entry_price) * LEVERAGE * 100

                    logger.info(f"📊 {SYMBOL} @ ${price:,.2f} | 📈 RSI: {rsi} | Pos: {self.position or 'NONE'} | Entry: ${self.entry_price:,.2f} | PnL: {pnl_pct:+.2f}% | Mode: {'LIVE' if self.live_mode else 'PAPER'}")

                    # 1. Check Stop Loss & Take Profit for active position
                    if self.position == 'LONG':
                        if price <= self.entry_price * (1 - STOP_LOSS_PCT):
                            self.close_position(price, "STOP_LOSS")
                        elif price >= self.entry_price * (1 + TAKE_PROFIT_PCT):
                            self.close_position(price, "TAKE_PROFIT")

                    elif self.position == 'SHORT':
                        if price >= self.entry_price * (1 + STOP_LOSS_PCT):
                            self.close_position(price, "STOP_LOSS")
                        elif price <= self.entry_price * (1 - TAKE_PROFIT_PCT):
                            self.close_position(price, "TAKE_PROFIT")

                    # 2. Check Signals to Open Positions (if no position active)
                    if not self.position:
                        if rsi <= RSI_LONG_LEVEL:
                            logger.info(f"🟢 OVERSOLD FUTURES SIGNAL: RSI {rsi} <= {RSI_LONG_LEVEL} -> Opening LONG ({LEVERAGE}x)")
                            self.open_position('LONG', price)
                        elif rsi >= RSI_SHORT_LEVEL:
                            logger.info(f"🔴 OVERBOUGHT FUTURES SIGNAL: RSI {rsi} >= {RSI_SHORT_LEVEL} -> Opening SHORT ({LEVERAGE}x)")
                            self.open_position('SHORT', price)

                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("⛔ Futures trading agent stopped.")
                break
            except Exception as e:
                logger.error(f"❌ Futures loop exception: {e}", exc_info=True)
                time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    agent = CoinDCXFuturesAgent()
    agent.trading_loop()
