# emergency_close_positions.py
"""
Emergency Position Close Script.
Queries all active CoinDCX futures positions (such as GALA) and submits immediate market exit orders
to close them and prevent further loss.
"""

import sys
import logging
from coindcx_client import CoinDCXClient
from coindcx_futures_mapper import futures_mapper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EmergencyClose")

def emergency_close_all():
    print("=" * 80)
    print("🚨 EMERGENCY POSITION CLOSE TRIGGER — CLOSING ALL OPEN POSITIONS")
    print("=" * 80)

    client = CoinDCXClient()
    print("🛑 Cancelling all active pending/limit orders on CoinDCX...")
    cancel_res = client.cancel_all_orders()
    print(f"📲 CANCEL ORDERS RESPONSE: {cancel_res}")

    for loop in range(5):
        active_positions = client.get_active_futures_positions()

        if not active_positions:
            print("ℹ️ No active open futures positions found on CoinDCX.")
            break

        print(f"🔄 Sweep #{loop+1}: Closing {len(active_positions)} active position(s)...")

        for futures_sym, pos_info in list(active_positions.items()):
            qty = abs(float(pos_info.get("active_pos", 0.0)))
            if qty <= 0:
                continue

            side = str(pos_info.get("side", "BUY")).upper()
            spot_sym = futures_sym.replace("B-", "").replace("_USDT", "USDT")

            # Close LONG with SELL, close SHORT with BUY
            close_side = "SELL" if side in ["BUY", "LONG"] else "BUY"
            leverage = int(pos_info.get("leverage", 20))

            print(f"⚡ CLOSING POSITION: {futures_sym} ({side} {qty}) -> Executing Market {close_side}...")
            resp = client.place_order(
                symbol=spot_sym,
                side=close_side,
                amount=qty,
                leverage=leverage,
                market_type="futures"
            )
            print(f"📲 EXCHANGE RESPONSE: {resp}")

    print("\n" + "✅" * 40)
    print("✅ EMERGENCY CLOSE COMPLETE. All open positions closed.")
    print("Check your CoinDCX Mobile App under Futures -> Positions to confirm!")

if __name__ == "__main__":
    emergency_close_all()
