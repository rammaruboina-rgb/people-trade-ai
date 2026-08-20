"""
web3_model.py
On-Chain Web3 Whale Transfer & Smart Contract Event Monitor for CoinDCX Agent.
Monitors Ethereum & BNB Chain ERC20/BEP20 Transfer logs to decode exchange inflows/outflows as catalyst signals.
"""

import requests
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
from catalyst_engine import Catalyst

logger = logging.getLogger(__name__)

# Standard ERC20 Transfer event signature: Transfer(address,address,uint256)
TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

def scan_erc20_transfers_via_jsonrpc(
    rpc_url: str,
    token_address: str,
    exchange_addresses: List[str],
    coin_name: str,
    min_amount_tokens: float = 50000.0,
    decimals: int = 18
) -> List[Catalyst]:
    """
    Scans ERC20 Transfer events via standard JSON-RPC without hard web3 dependency.
    Decodes transfers to/from exchange wallets into Catalyst impact scores.
    """
    catalysts = []
    if not rpc_url or not token_address or token_address == "0x0000000000000000000000000000000000000000":
        return catalysts

    try:
        # Get latest block number
        payload_block = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
        res_b = requests.post(rpc_url, json=payload_block, timeout=4)
        if res_b.status_code != 200:
            return catalysts
            
        latest_block = int(res_b.json().get("result", "0x0"), 16)
        from_block = hex(max(1, latest_block - 30))
        to_block = hex(latest_block)

        payload_logs = {
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "address": token_address,
                "fromBlock": from_block,
                "toBlock": to_block,
                "topics": [TRANSFER_EVENT_TOPIC]
            }],
            "id": 2
        }

        res_l = requests.post(rpc_url, json=payload_logs, timeout=5)
        if res_l.status_code == 200:
            logs = res_l.json().get("result", [])
            exchanges_lower = set(a.lower() for a in exchange_addresses)

            for log in logs:
                topics = log.get("topics", [])
                if len(topics) < 3:
                    continue
                from_addr = "0x" + topics[1][-40:].lower()
                to_addr = "0x" + topics[2][-40:].lower()
                
                val_hex = log.get("data", "0x0")
                raw_val = int(val_hex, 16) if val_hex != "0x" else 0
                amount = raw_val / (10 ** decimals)

                if amount < min_amount_tokens:
                    continue

                direction = None
                if from_addr in exchanges_lower:
                    direction = "from_exchange" # Bullish withdrawal
                elif to_addr in exchanges_lower:
                    direction = "to_exchange"   # Bearish deposit dump

                if direction:
                    impact = 0.65 if direction == "from_exchange" else -0.55
                    desc = f"On-Chain Whale {direction.replace('_', ' ').title()}: {amount:,.0f} {coin_name}"
                    catalysts.append(
                        Catalyst(
                            coin_name=coin_name,
                            symbol=None,
                            event_type="web3_whale_transfer",
                            description=desc,
                            impact_score=impact
                        )
                    )
    except Exception as e:
        logger.warning(f"Error scanning Web3 transfers for {coin_name}: {e}")

    return catalysts

def scan_all_web3_catalysts(web3_config: Dict[str, Any]) -> List[Catalyst]:
    """
    Scans configured Web3 tokens across Ethereum & BSC RPC networks.
    """
    if not web3_config or not web3_config.get("enabled", False):
        return []

    catalysts = []
    eth_rpc = web3_config.get("ethereum_rpc", "https://cloudflare-eth.com")
    bsc_rpc = web3_config.get("bsc_rpc", "https://bsc-dataseed.binance.org")
    watch_tokens = web3_config.get("watch_tokens", [])

    for t in watch_tokens:
        coin = t.get("coin_name", "")
        token_addr = t.get("address", "")
        exchanges = t.get("exchange_addresses", [])
        min_amt = float(t.get("min_amount_raw", 50000))
        decimals = int(t.get("decimals", 18))
        chain = t.get("chain", "ethereum").lower()

        rpc_url = bsc_rpc if chain == "bsc" else eth_rpc

        token_cats = scan_erc20_transfers_via_jsonrpc(
            rpc_url=rpc_url,
            token_address=token_addr,
            exchange_addresses=exchanges,
            coin_name=coin,
            min_amount_tokens=min_amt,
            decimals=decimals
        )
        catalysts.extend(token_cats)

    return catalysts

if __name__ == "__main__":
    sample_config = {
        "enabled": True,
        "ethereum_rpc": "https://cloudflare-eth.com",
        "bsc_rpc": "https://bsc-dataseed.binance.org",
        "watch_tokens": [
            {
                "coin_name": "LINK",
                "chain": "ethereum",
                "address": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
                "exchange_addresses": ["0x28C6c06298d514Db089934071355E5743bf21d60"],
                "min_amount_raw": 10000,
                "decimals": 18
            }
        ]
    }
    cats = scan_all_web3_catalysts(sample_config)
    print("=" * 70)
    print(f"🌐 WEB3 ON-CHAIN CATALYSTS DETECTED ({len(cats)}):")
    print("=" * 70)
    for c in cats:
        print(f"  - [{c.coin_name}] {c.event_type}: {c.description} ({c.impact_score:+.2f})")
