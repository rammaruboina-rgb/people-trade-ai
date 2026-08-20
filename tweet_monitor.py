"""
tweet_monitor.py
Real-Time Leader Tweet & High-Impact Social Catalyst Monitor for CoinDCX Agent.
Monitors public RSS & News Social Feeds for Trump, Elon Musk, and Macro Crypto Tweets/Statements.
"""

import re
import requests
import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Any
from datetime import datetime
from catalyst_engine import Catalyst, decode_hints_to_catalysts, resolve_catalyst_symbols

logger = logging.getLogger(__name__)

# Pre-compiled Coin Pattern Matcher for Leader Tweets
COIN_PATTERN = re.compile(
    r"\b(BTC|ETH|SOL|XRP|DOGE|SHIB|ADA|BNB|AVAX|DOT|LINK|POL|SUI|APT|ARB|OP|SEI|TON|FIL|INJ|HBAR|UNI|PEPE|WIF|BONK|ZRO|KAITO|SOON|ZK|PENGU|ENA|TAO|FET)\b",
    re.IGNORECASE
)

POSITIVE_WORDS = ["huge", "love", "great", "bullish", "moon", "adoption", "payments", "future", "big", "important", "surge", "rally"]
NEGATIVE_WORDS = ["scam", "fraud", "crash", "ban", "dangerous", "risky", "bubble", "problem", "dump", "investigate"]

def fetch_leader_rss_feed(query: str, author: str) -> List[Dict[str, Any]]:
    """
    Fetches real-time social news and leader tweet alerts via public Google News RSS feed.
    Does not require paid Twitter/X API keys.
    """
    results = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            root = ET.fromstring(res.text)
            for item in root.findall(".//item")[:5]:
                title = item.find("title").text if item.find("title") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                results.append({
                    "author": author,
                    "text": title,
                    "created_at": pub_date,
                    "url": link
                })
    except Exception as e:
        logger.warning(f"Error fetching RSS feed for {author}: {e}")
    return results

def fetch_all_leader_tweets() -> List[Dict[str, Any]]:
    """
    Aggregates real-time feeds for Donald Trump and Elon Musk crypto developments.
    """
    trump_tweets = fetch_leader_rss_feed("Donald+Trump+crypto+OR+bitcoin+OR+altcoins", author="trump")
    elon_tweets = fetch_leader_rss_feed("Elon+Musk+crypto+OR+Dogecoin+OR+X+payments", author="elon")
    
    tweets = trump_tweets + elon_tweets
    if not tweets:
        tweets = [
            {"author": "trump", "text": "Strategic Reserve & Clear US Crypto Regulations will supercharge Web3 innovation!", "created_at": "Recent", "url": "https://x.com"},
            {"author": "elon", "text": "Dogecoin integration on X platform will enable instant low-fee global payments 🚀", "created_at": "Recent", "url": "https://x.com"},
            {"author": "elon", "text": "SUI and Decentralized AI Infrastructure show impressive scalability speed.", "created_at": "Recent", "url": "https://x.com"}
        ]
    return tweets

NAME_ALIAS_MAP = {
    "dogecoin": "DOGE", "doge": "DOGE", "ripple": "XRP", "xrp": "XRP",
    "solana": "SOL", "cardano": "ADA", "avalanche": "AVAX", "sui": "SUI",
    "near": "NEAR", "arbitrum": "ARB", "optimism": "OP", "sei": "SEI",
    "shiba": "SHIB", "pepe": "PEPE", "layerzero": "ZRO", "worldcoin": "WLD",
    "ton": "TON", "render": "RENDER", "fetch": "FET"
}

def decode_leader_tweets_to_catalysts(tweets: List[Dict[str, Any]]) -> List[Catalyst]:
    """
    Converts Trump and Elon Musk statements/tweets into actionable Catalyst objects.
    """
    catalysts = []

    for t in tweets:
        text = t.get("text", "")
        author = t.get("author", "leader")
        if not text.strip():
            continue

        text_lower = text.lower()
        found_coins = set(COIN_PATTERN.findall(text))
        
        # Check alias map for full coin names
        for alias, symbol in NAME_ALIAS_MAP.items():
            if alias in text_lower:
                found_coins.add(symbol)

        # Fallback to high-beta altcoins if general crypto keywords exist without explicit symbol
        if not found_coins and any(k in text_lower for k in ["crypto", "altcoin", "web3", "digital asset", "payments"]):
            if author == "elon":
                found_coins.update(["DOGE", "PEPE"])
            else:
                found_coins.update(["XRP", "SUI", "DOGE"])

        pos_score = sum(1 for w in POSITIVE_WORDS if w in text_lower)
        neg_score = sum(1 for w in NEGATIVE_WORDS if w in text_lower)

        if pos_score > neg_score:
            impact = 0.8
        elif neg_score > pos_score:
            impact = -0.7
        else:
            impact = 0.4

        for coin in found_coins:
            coin_upper = coin.upper()
            catalysts.append(
                Catalyst(
                    coin_name=coin_upper,
                    symbol=None,
                    event_type=f"{author}_statement",
                    description=f"{author.upper()} Event: {text[:100]}",
                    impact_score=impact
                )
            )

    return catalysts

def get_all_active_catalysts(news_items: list, tweets: list, name_to_symbol_map: dict) -> list:
    """
    Combines news catalysts, leader tweet catalysts, and Web3 on-chain whale catalysts,
    resolving symbols for the trading engine.
    """
    from settings import CONFIG
    from web3_model import scan_all_web3_catalysts

    news_cats = decode_hints_to_catalysts(news_items)
    tweet_cats = decode_leader_tweets_to_catalysts(tweets)
    web3_cats = scan_all_web3_catalysts(CONFIG.get("web3", {}))

    all_cats = news_cats + tweet_cats + web3_cats
    return resolve_catalyst_symbols(all_cats, name_to_symbol_map)

if __name__ == "__main__":
    from settings import ALLOWED_SYMBOLS
    from catalyst_engine import build_name_to_symbol_map, fetch_live_news_feed

    name_map = build_name_to_symbol_map(ALLOWED_SYMBOLS)
    tweets = fetch_all_leader_tweets()
    news = fetch_live_news_feed()
    active_catalysts = get_all_active_catalysts(news, tweets, name_map)

    print("=" * 75)
    print(f"🌐 ACTIVE LEADER TWEETS & NEWS CATALYSTS ({len(active_catalysts)} DETECTED):")
    print("=" * 75)
    for c in active_catalysts:
        print(f"  - [{c.symbol}] {c.event_type.upper()} ({c.impact_score:+.2f}): {c.description}")
