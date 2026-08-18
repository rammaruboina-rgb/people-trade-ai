# dashboard.py
import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.align import Align

load_dotenv()

SYMBOL = 'BTCUSDT'
BASE_URL = 'https://api.coindcx.com'

class DashboardApp:
    def __init__(self):
        self.start_time = datetime.now()
        self.key = os.getenv('COINDCX_API_KEY', '')
        self.secret = os.getenv('COINDCX_API_SECRET', '')
        self.live_mode = bool(self.key and self.secret and self.secret != 'your_api_secret_here')

    def fetch_current_price(self):
        try:
            res = requests.get(f"{BASE_URL}/exchange/ticker", timeout=5)
            if res.status_code == 200:
                for t in res.json():
                    if t.get('market') == SYMBOL:
                        return float(t.get('last_price', 0))
        except Exception:
            pass
        return 0.0

    def load_trades(self):
        trades = []
        filename = 'trades.csv'
        if not os.path.exists(filename):
            return trades

        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    trade = json.loads(line)
                    trades.append(trade)
                except Exception:
                    continue
        return trades

    def calculate_pnl(self, trades, current_price):
        realized_pnl = 0.0
        btc_holdings = 0.0
        total_cost = 0.0

        for t in trades:
            side = str(t.get('side', '')).lower()
            try:
                amount = float(t.get('amount', 0))
                price = float(t.get('price', 0))
            except (ValueError, TypeError):
                continue

            if side == 'buy':
                btc_holdings += amount
                total_cost += amount * price
            elif side == 'sell':
                if btc_holdings > 0:
                    avg_cost = total_cost / btc_holdings if btc_holdings > 0 else price
                    sold_cost = amount * avg_cost
                    revenue = amount * price
                    realized_pnl += (revenue - sold_cost)
                    btc_holdings -= amount
                    total_cost -= sold_cost
                    if btc_holdings < 0:
                        btc_holdings = 0
                        total_cost = 0

        unrealized_pnl = 0.0
        if btc_holdings > 0 and current_price > 0:
            avg_price = total_cost / btc_holdings if btc_holdings > 0 else 0
            unrealized_pnl = (current_price - avg_price) * btc_holdings

        total_pnl = realized_pnl + unrealized_pnl
        return realized_pnl, unrealized_pnl, total_pnl, btc_holdings

    def generate_layout(self):
        current_price = self.fetch_current_price()
        trades = self.load_trades()
        realized_pnl, unrealized_pnl, total_pnl, btc_holdings = self.calculate_pnl(trades, current_price)

        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]

        # 1. Header
        header_text = Text()
        header_text.append("🚀 CoinDCX Live Trading Dashboard ", style="bold cyan")
        header_text.append(f"| ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ", style="yellow")
        header_text.append(f"| ⏱️ Uptime: {uptime_str} ", style="green")
        header_panel = Panel(Align.center(header_text), style="bold white on blue", expand=True)

        # 2. Portfolio Panel
        usdt_balance = 1000.0 if not self.live_mode else 0.0
        btc_value = btc_holdings * current_price

        port_table = Table.grid(padding=(0, 2))
        port_table.add_column(style="bold white")
        port_table.add_column(style="bold yellow")

        port_table.add_row("💰 USDT Balance:", f"${usdt_balance:,.2f}")
        port_table.add_row("₿ BTC Holdings:", f"{btc_holdings:.6f} BTC")
        port_table.add_row("📊 BTC/USDT Price:", f"${current_price:,.2f}")
        port_table.add_row("💵 BTC Value:", f"${btc_value:,.2f}")
        port_table.add_row("🔒 Mode:", "[bold green]LIVE[/bold green]" if self.live_mode else "[bold yellow]PAPER / DRY-RUN[/bold yellow]")

        portfolio_panel = Panel(port_table, title="[bold cyan]Portfolio & Balance[/bold cyan]", border_style="cyan")

        # 3. P&L Panel
        r_color = "green" if realized_pnl >= 0 else "red"
        u_color = "green" if unrealized_pnl >= 0 else "red"
        t_color = "green" if total_pnl >= 0 else "red"

        pnl_table = Table.grid(padding=(0, 2))
        pnl_table.add_column(style="bold white")
        pnl_table.add_column(style="bold")

        pnl_table.add_row("✅ Realized P&L:", f"[{r_color}]${realized_pnl:+,.2f}[/{r_color}]")
        pnl_table.add_row("⏳ Unrealized P&L:", f"[{u_color}]${unrealized_pnl:+,.2f}[/{u_color}]")
        pnl_table.add_row("📈 Total P&L:", f"[{t_color}]${total_pnl:+,.2f}[/{t_color}]")
        pnl_table.add_row("📝 Total Executed Trades:", f"{len(trades)}")

        pnl_panel = Panel(pnl_table, title="[bold green]Profit & Loss (P&L)[/bold green]", border_style="green")

        # 4. Recent Trades Table
        trades_table = Table(expand=True, header_style="bold magenta")
        trades_table.add_column("Time", style="dim", width=20)
        trades_table.add_column("Type", width=10)
        trades_table.add_column("Amount", justify="right")
        trades_table.add_column("Price", justify="right")
        trades_table.add_column("Total ($)", justify="right")
        trades_table.add_column("Mode", justify="center")

        recent_trades = trades[-8:] if len(trades) > 8 else trades
        for t in reversed(recent_trades):
            ts = str(t.get('timestamp', 'N/A'))[:19].replace('T', ' ')
            side = str(t.get('side', '')).upper()
            try:
                amt = float(t.get('amount', 0))
                prc = float(t.get('price', 0))
                total = amt * prc
                amt_str = f"{amt:.6f}"
                prc_str = f"${prc:,.2f}"
                tot_str = f"${total:,.2f}"
            except Exception:
                amt_str, prc_str, tot_str = "N/A", "N/A", "N/A"

            side_styled = "[bold green]🟢 BUY[/bold green]" if side == "BUY" else "[bold red]🔴 SELL[/bold red]"
            mode_styled = str(t.get('mode', 'PAPER'))

            trades_table.add_row(ts, side_styled, amt_str, prc_str, tot_str, mode_styled)

        trades_panel = Panel(trades_table, title="[bold magenta]Recent Executed Trades[/bold magenta]", border_style="magenta")

        # Main Layout
        layout = Layout()
        layout.split(
            Layout(header_panel, size=3),
            Layout(name="body", size=9),
            Layout(trades_panel, ratio=1)
        )
        layout["body"].split_row(
            Layout(portfolio_panel, ratio=1),
            Layout(pnl_panel, ratio=1)
        )
        return layout

def main():
    app = DashboardApp()
    console = Console()
    
    with Live(app.generate_layout(), console=console, refresh_per_second=1) as live:
        while True:
            time.sleep(2)
            live.update(app.generate_layout())

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Dashboard closed.")
