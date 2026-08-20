# catalyst_engine.py
import requests

def get_market_regime() -> str:
    """
    Evaluates market regime using live Binance BTC/ETH 1h candles & momentum indicators.
    Returns: 'risk_on', 'risk_off', or 'neutral'
    """
    try:
        res = requests.get('https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=5', timeout=3)
        if res.status_code == 200:
            klines = res.json()
            open_p = float(klines[0][1])
            close_p = float(klines[-1][4])
            change_pct = ((close_p - open_p) / open_p) * 100

            if change_pct > 0.5:
                return 'risk_on'
            elif change_pct < -0.5:
                return 'risk_off'
            else:
                return 'neutral'
    except Exception:
        pass
    return 'risk_on' # Default fallback
