# data_store.py
import csv
import os
import json
from config import TRADES_CSV

CSV_FIELDS = [
    "timestamp", "symbol", "market_type", "side", "entry_price",
    "size", "leverage", "sl_price", "tp_price", "exit_price",
    "exit_reason", "confidence", "signal_source", "news_summary", "mode"
]

def init_trades_csv():
    if not os.path.exists(TRADES_CSV):
        with open(TRADES_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()

def log_trade(row: dict):
    init_trades_csv()
    with open(TRADES_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        record = {k: row.get(k, "N/A") for k in CSV_FIELDS}
        writer.writerow(record)

def load_trade_history():
    init_trades_csv()
    trades = []
    if os.path.exists(TRADES_CSV):
        with open(TRADES_CSV, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(row)
    return trades

def calculate_pnl(trades, current_price):
    realized_pnl = 0.0
    open_buy_price = None
    open_buy_size = 0.0

    for t in trades:
        side = str(t.get("side", "")).upper()
        try:
            price = float(t.get("entry_price", t.get("price", 0)))
            size = float(t.get("size", t.get("amount", 0)))
        except Exception:
            continue

        if price > 200000: # Skip legacy INR trades
            continue

        if side in ["BUY", "LONG"]:
            open_buy_price = price
            open_buy_size = size
        elif side in ["SELL", "SHORT"] and open_buy_price:
            realized_pnl += (price - open_buy_price) * min(10.0, size)
            open_buy_price = None

    unrealized_pnl = 0.0
    if open_buy_price and current_price and current_price < 200000 and open_buy_price > 0:
        raw_pnl = ((current_price - open_buy_price) / open_buy_price) * 9.659 * 20.0
        unrealized_pnl = max(-9.659, min(100.0, raw_pnl))

    total_pnl = realized_pnl + unrealized_pnl
    return round(realized_pnl, 2), round(unrealized_pnl, 2), round(total_pnl, 2)
