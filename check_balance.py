import sys
import os
from coindcx_client import CoinDCXClient
from data_store import load_trade_history, calculate_pnl

def check_account_balance_status():
    client = CoinDCXClient()
    balances = client.get_account_balances()
    positions = client.get_active_futures_positions()
    trades = load_trade_history()
    
    sui_price = client.get_ticker_price("SUIUSDT")
    realized_pnl, unrealized_pnl, win_rate = calculate_pnl(trades, sui_price)

    import config
    print("=" * 70)
    print("💰 COINDCX AGENT REAL-TIME BALANCE & PORTFOLIO STATUS")
    print("=" * 70)
    print(f"  • Execution Mode       : {client.mode}")
    print(f"  • Total Portfolio Equity: ${balances.get('total_equity', config.EQUITY_USD):,.2f} USD")
    print(f"  • Available USDT Balance: ${balances.get('USDT', 0.0):,.2f} USDT")
    print(f"  • INR Fiat Balance     : ₹{balances.get('INR', 0.0):,.2f} INR")
    print("-" * 70)
    print(f"  • Total Realized P&L   : ${realized_pnl:+.2f} USD")
    print(f"  • Current Open P&L     : ${unrealized_pnl:+.2f} USD")
    print(f"  • Execution Win Rate   : {win_rate:.1f}%")
    print(f"  • Recorded Trades Count: {len(trades)}")
    print(f"  • Active Open Positions: {len(positions)}")
    print("=" * 70)

if __name__ == "__main__":
    check_account_balance_status()
