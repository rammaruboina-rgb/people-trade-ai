# news_client.py
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# CryptoCompare / Shingou / Public Crypto News Endpoints
CRYPTO_NEWS_URL = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"

# Bullish / Bearish Keyword Lexicon for sentiment scoring
BULLISH_KEYWORDS = [
    "approval", "approved", "surge", "rally", "breakout", "bullish", "adoption",
    "partnership", "record high", "upgrade", "institutional", "etf", "accumulate"
]
BEARISH_KEYWORDS = [
    "hack", "hacked", "sec", "lawsuit", "ban", "banned", "crash", "plunge",
    "bearish", "investigation", "exploit", "insolvent", "liquidation", "shutdown"
]

def fetch_crypto_news(symbol: str = "BTC") -> Optional[Dict[str, Any]]:
    """
    Fetches real-time crypto news and calculates sentiment score (-1.0 to +1.0)
    """
    try:
        res = requests.get(CRYPTO_NEWS_URL, timeout=5)
        if res.status_code == 200:
            data = res.json()
            articles = data.get("Data", [])
            
            relevant_articles = []
            symbol_upper = symbol.upper()

            for a in articles[:15]:
                body = (a.get("title", "") + " " + a.get("body", "")).lower()
                categories = a.get("categories", "").upper()
                if symbol_upper in categories or symbol_upper in body.upper() or "CRYPTO" in categories:
                    relevant_articles.append(body)

            if not relevant_articles:
                return {
                    "symbol": symbol_upper,
                    "score": 0.0,
                    "confidence": 0.5,
                    "news_count": 0,
                    "dominant_event": "Neutral Market"
                }

            bullish_count = 0
            bearish_count = 0

            for article in relevant_articles:
                for kw in BULLISH_KEYWORDS:
                    if kw in article:
                        bullish_count += 1
                for kw in BEARISH_KEYWORDS:
                    if kw in article:
                        bearish_count += 1

            total_hits = bullish_count + bearish_count
            if total_hits == 0:
                score = 0.0
            else:
                score = round((bullish_count - bearish_count) / total_hits, 2)

            confidence = round(min(1.0, len(relevant_articles) / 10.0), 2)
            dominant = "Bullish News Surge" if score > 0.3 else ("Bearish News Alert" if score < -0.3 else "Neutral Sentiment")

            return {
                "symbol": symbol_upper,
                "score": score,
                "confidence": confidence,
                "news_count": len(relevant_articles),
                "dominant_event": dominant
            }

    except Exception as e:
        logger.error(f"❌ Error fetching news sentiment: {e}")

    return {
        "symbol": symbol.upper(),
        "score": 0.0,
        "confidence": 0.0,
        "news_count": 0,
        "dominant_event": "No Data"
    }

# Alias for compatibility
fetch_news_sentiment = fetch_crypto_news

if __name__ == "__main__":
    sentiment = fetch_crypto_news("BTC")
    print("BTC News Sentiment Result:", sentiment)
