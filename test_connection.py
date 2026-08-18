# test_connection.py
import hmac
import hashlib
import time
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

class CoinDCXClient:
    BASE_URL = 'https://api.coindcx.com'

    def __init__(self, key=None, secret=None):
        self.key = key or os.getenv('COINDCX_API_KEY', '')
        self.secret = secret or os.getenv('COINDCX_API_SECRET', '')

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

    def fetch_ticker(self, symbol='BTCUSDT'):
        """Fetch current ticker price for a symbol"""
        symbol_clean = symbol.replace('/', '').upper()
        url = f"{self.BASE_URL}/exchange/ticker"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        tickers = response.json()
        for t in tickers:
            if t.get('market') == symbol_clean:
                return float(t.get('last_price', 0))
        raise ValueError(f"Symbol {symbol_clean} not found in tickers")

    def fetch_balances(self):
        """Fetch user balances"""
        url = f"{self.BASE_URL}/exchange/v1/users/balances"
        body = {'timestamp': int(time.time() * 1000)}
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self._get_headers(json_body)
        
        response = requests.post(url, data=json_body, headers=headers, timeout=10)
        data = response.json()
        if response.status_code != 200 or isinstance(data, dict) and data.get('status') == 'error':
            raise PermissionError(f"API error: {data.get('message', 'Authentication failed')}")
        
        balances = {}
        if isinstance(data, list):
            for b in data:
                balances[b['currency']] = {
                    'free': float(b.get('balance', 0)) - float(b.get('locked_balance', 0)),
                    'locked': float(b.get('locked_balance', 0)),
                    'total': float(b.get('balance', 0))
                }
        return balances

if __name__ == '__main__':
    print("🔌 Testing CoinDCX API connection...")
    client = CoinDCXClient()
    
    try:
        btc_price = client.fetch_ticker('BTCUSDT')
        print(f"✅ BTC Price: ${btc_price:,.2f}")
    except Exception as e:
        print(f"❌ Failed to fetch BTC price: {e}")

    try:
        balances = client.fetch_balances()
        usdt_balance = balances.get('USDT', {}).get('free', 0.0)
        print(f"✅ USDT Balance: ${usdt_balance}")
        print("✅ API connection successful!")
    except Exception as e:
        print(f"⚠️ Balance check note: {e}")
        print("ℹ️ Note: Update .env with valid CoinDCX_API_KEY & COINDCX_API_SECRET for live balance checks.")

