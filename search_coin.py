import requests
import json

def search_coindcx_for_symbol(search_term="NTDA"):
    print("=" * 70)
    print(f"🔍 SEARCHING COINDCX MARKETS FOR: '{search_term}'")
    print("=" * 70)
    
    url = "https://api.coindcx.com/exchange/ticker"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200 and isinstance(res.json(), list):
            all_markets = res.json()
            matches = []
            exact_matches = []
            
            for m in all_markets:
                market = m.get("market", "")
                if search_term.upper() in market.upper():
                    matches.append(m)
                if market.upper().startswith(search_term.upper()):
                    exact_matches.append(m)
                    
            if matches:
                print(f"✅ FOUND {len(matches)} MATCHES ON COINDCX:")
                for item in matches[:10]:
                    print(f"  • Market: {item.get('market')} | Last Price: {item.get('last_price')} | 24h Vol: {item.get('volume')}")
            else:
                print(f"❌ EXACT TICKER '{search_term}' NOT FOUND ON COINDCX FUTURES/SPOT MARKETS.")
                print("\n🔎 SUGGESTING SIMILAR ACTIVE TICKERS ON COINDCX:")
                similar = [m for m in all_markets if any(char in m.get('market', '') for char in ["NTD", "NDA", "NOT", "NTR"])]
                seen = set()
                count = 0
                for s in similar:
                    m_name = s.get('market')
                    if m_name not in seen and count < 8:
                        seen.add(m_name)
                        print(f"  • {m_name} | Price: {s.get('last_price')}")
                        count += 1
        else:
            print("HTTP Response Error from CoinDCX API:", res.status_code)
    except Exception as e:
        print("Error connecting to CoinDCX API:", e)

if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "NTDA"
    search_coindcx_for_symbol(query)
