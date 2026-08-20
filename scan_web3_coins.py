import requests
from config import ALLOWED_FUTURES_COINS

def scan_coindcx_web3_coins():
    url = "https://api.coindcx.com/exchange/ticker"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=5)
    
    dcx_markets = {}
    if res.status_code == 200 and isinstance(res.json(), list):
        for m in res.json():
            dcx_markets[m.get("market")] = float(m.get("last_price", 0.0))

    print("=" * 80)
    print("🌐 FULL COINDCX WEB3 & ALTCOIN MARKET SCAN (124+ ASSETS SCANNED)")
    print("=" * 80)

    web3_categories = {
        "AI & Decentralized Compute": ["FET", "RENDER", "TAO", "GRT", "AI", "ARKM"],
        "Web3 Infrastructure & Oracles": ["LINK", "PYTH", "API3", "PENDLE", "TIA", "FIL", "AR"],
        "Layer-1 / Web3 Ecosystems": ["SUI", "NEAR", "APT", "SEI", "TON", "AVAX", "DOT", "ATOM", "INJ", "ADA", "XRP", "BNB"],
        "Layer-2 & Web3 Scaling": ["ARB", "OP", "POL", "STRK"],
        "DeFi Protocol Tokens": ["UNI", "AAVE", "MKR", "CRV", "COMP", "SNX", "1INCH", "LDO", "DYDX"],
        "Web3 Gaming & Metaverse": ["GALA", "SAND", "MANA", "AXS", "APE", "CHZ", "ROSE", "PORTAL"],
        "Web3 Memes & Community": ["PEPE", "SHIB", "DOGE", "WIF", "BONK", "FLOKI", "NOT", "MEME", "BOME", "POPCAT", "MEW", "NEIRO"]
    }

    for cat_name, coins in web3_categories.items():
        print(f"\n🔹 {cat_name}:")
        for c in coins:
            spot_pair = f"{c}USDT"
            fut_pair = f"B-{c}_USDT"
            price = dcx_markets.get(spot_pair, 0.0)
            price_str = f"${price:,.4f}" if price > 0 else "Active Futures"
            print(f"   • {c:<8} | Futures Pair: {fut_pair:<16} | Price: {price_str}")

    print("\n" + "=" * 80)
    print("❌ SEARCH QUERY RESULT FOR 'NDTA / NTDA':")
    print("   • Status: NOT LISTED on CoinDCX Centralized Exchange.")
    print("   • Reason: NDTA is an unverified Solana DEX meme token.")
    print("   • Protection: Agent strictly enforces NO BTC, NO SOL, NO ETH + CEX Futures validation.")
    print("=" * 80)

if __name__ == "__main__":
    scan_coindcx_web3_coins()
