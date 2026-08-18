# dashboard_futures.py
import os
import sys
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.align import Align

load_dotenv()

SYMBOL = 'BTC/USDT:USDT'
MARKET_SYMBOL = 'BTCUSDT'
BASE_URL = 'https://api.coindcx.com'

class FuturesDashboardApp:
    def __init__(self):
        self.start_time = datetime.now()
        self.key = os.getenv('COINDCX_API_KEY', '')
        self.secret = os.getenv('COINDCX_API_SECRET', '')
        self.live_mode = bool(self.key and self.secret and self.secret != 'your_api_secret_here')

    def fetch_mark_price(self):
        try:
            res = requests.get(f"{BASE_URL}/exchange/ticker", timeout=5)
            if res.status_code == 200:
                for t in res.json():
                    if t.get('market') == MARKET_SYMBOL:
                        return float(t.get('last_price', 0))
        except Exception:
            pass
        return 0.0

    def load_futures_trades(self):
        trades = []
        filename = 'trades_futures.csv'
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

    def calculate_futures_stats(self, trades, current_price):
        realized_pnl = 0.0
        active_position = None  # None, 'LONG', 'SHORT'
        entry_price = 0.0
        position_size = 0.0
        leverage = 10

        for t in trades:
            action = str(t.get('action', ''))
            try:
                amt = float(t.get('amount', 0))
                price = float(t.get('price', 0))
                lev = int(t.get('leverage', 10))
            except (ValueError, TypeError):
                continue

            leverage = lev

            if action == 'OPEN_LONG':
                active_position = 'LONG'
                entry_price = price
                position_size = amt
            elif action == 'OPEN_SHORT':
                active_position = 'SHORT'
                entry_price = price
                position_size = amt
            elif action.startswith('CLOSE_'):
                if active_position == 'LONG':
                    realized_pnl += ((price - entry_price) * position_size)
                elif active_position == 'SHORT':
                    realized_pnl += ((entry_price - price) * position_size)
                active_position = None
                entry_price = 0.0
                position_size = 0.0

        unrealized_pnl = 0.0
        liq_price = 0.0
        pnl_pct = 0.0

        if active_position and entry_price > 0 and current_price > 0:
            if active_position == 'LONG':
                unrealized_pnl = (current_price - entry_price) * position_size
                pnl_pct = ((current_price - entry_price) / entry_price) * leverage * 100
                liq_price = entry_price * (1 - (1.0 / leverage) + 0.005)
            elif active_position == 'SHORT':
                unrealized_pnl = (entry_price - current_price) * position_size
                pnl_pct = ((entry_price - current_price) / entry_price) * leverage * 100
                liq_price = entry_price * (1 + (1.0 / leverage) - 0.005)

        total_pnl = realized_pnl + unrealized_pnl
        return realized_pnl, unrealized_pnl, total_pnl, active_position, entry_price, position_size, liq_price, pnl_pct, leverage

    def generate_layout(self):
        current_price = self.fetch_mark_price()
        trades = self.load_futures_trades()
        realized_pnl, unrealized_pnl, total_pnl, pos, entry_price, pos_size, liq_price, pnl_pct, leverage = self.calculate_futures_stats(trades, current_price)

        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]

        # Header
        header_text = Text()
        header_text.append("⚡ CoinDCX Futures Trading Dashboard ", style="bold yellow")
        header_text.append(f"| ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ", style="cyan")
        header_text.append(f"| ⏱️ Uptime: {uptime_str} ", style="green")
        header_panel = Panel(Align.center(header_text), style="bold white on magenta", expand=True)

        # Position Panel
        pos_styled = "[bold green]🟢 LONG[/bold green]" if pos == 'LONG' else ("[bold red]🔴 SHORT[/bold red]" if pos == 'SHORT' else "[dim]NONE[/dim]")
        
        pos_table = Table.grid(padding=(0, 2))
        pos_table.add_column(style="bold white")
        pos_table.add_column(style="bold")

        pos_table.add_row("⚡ Futures Pair:", SYMBOL)
        pos_table.add_row("📊 Active Position:", pos_styled)
        pos_table.add_row("🏋️ Leverage:", f"[yellow]{leverage}x (Isolated)[/yellow]")
        pos_table.add_row("📈 Size:", f"{pos_size:.6f} BTC" if pos else "0.000000 BTC")
        pos_table.add_row("💵 Entry Price:", f"${entry_price:,.2f}" if entry_price > 0 else "N/A")
        pos_table.add_row("📊 Current Mark Price:", f"${current_price:,.2f}")
        pos_table.add_row("⚠️ Est. Liquidation Price:", f"[bold red]${liq_price:,.2f}[/bold red]" if liq_price > 0 else "N/A")

        position_panel = Panel(pos_table, title="[bold yellow]Active Futures Position[/bold yellow]", border_style="yellow")

        # P&L Panel
        r_color = "green" if realized_pnl >= 0 else "red"
        u_color = "green" if unrealized_pnl >= 0 else "red"
        t_color = "green" if total_pnl >= 0 else "red"

        pnl_table = Table.grid(padding=(0, 2))
        pnl_table.add_column(style="bold white")
        pnl_table.add_column(style="bold")

        pnl_table.add_row("⏳ Position PnL (%):", f"[{u_color}]{pnl_pct:+.2f}%[/{u_color}]" if pos else "0.00%")
        pnl_table.add_row("⏳ Unrealized P&L ($):", f"[{u_color}]${unrealized_pnl:+,.2f}[/{u_color}]")
        pnl_table.add_row("✅ Realized P&L ($):", f"[{r_color}]${realized_pnl:+,.2f}[/{r_color}]")
        pnl_table.add_row("📈 Total P&L ($):", f"[{t_color}]${total_pnl:+,.2f}[/{t_color}]")
        pnl_table.add_row("🔒 Execution Mode:", "[bold green]LIVE[/bold green]" if self.live_mode else "[bold yellow]PAPER / SIMULATION[/bold yellow]")

        pnl_panel = Panel(pnl_table, title="[bold green]Futures P&L & Return[/bold green]", border_style="green")

        # Recent Trades Table
        trades_table = Table(expand=True, header_style="bold cyan")
        trades_table.add_column("Time", style="dim", width=20)
        trades_table.add_column("Action", width=14)
        trades_table.add_column("Amount", justify="right")
        trades_table.add_column("Price", justify="right")
        trades_table.add_column("Leverage", justify="center")
        trades_table.add_column("Note", justify="center")

        recent_trades = trades[-8:] if len(trades) > 8 else trades
        for t in reversed(recent_trades):
            ts = str(t.get('timestamp', 'N/A'))[:19].replace('T', ' ')
            action = str(t.get('action', '')).upper()
            try:
                amt = float(t.get('amount', 0))
                prc = float(t.get('price', 0))
                amt_str = f"{amt:.6f}"
                prc_str = f"${prc:,.2f}"
            except Exception:
                amt_str, prc_str = "N/A", "N/A"

            if "LONG" in action:
                act_styled = f"[bold green]🟢 {action}[/bold green]"
            elif "SHORT" in action:
                act_styled = f"[bold red]🔴 {action}[/bold red]"
            else:
                act_styled = action

            lev_str = f"{t.get('leverage', 10)}x"
            note_str = str(t.get('note', ''))

            trades_table.add_row(ts, act_styled, amt_str, prc_str, lev_str, note_str)

        trades_panel = Panel(trades_table, title="[bold cyan]Recent Futures Trades[/bold cyan]", border_style="cyan")

        # Main Layout
        layout = Layout()
        layout.split(
            Layout(header_panel, size=3),
            Layout(name="body", size=10),
            Layout(trades_panel, ratio=1)
        )
        layout["body"].split_row(
            Layout(position_panel, ratio=1),
            Layout(pnl_panel, ratio=1)
        )
        return layout

def main():
    app = FuturesDashboardApp()
    console = Console()
    
    with Live(app.generate_layout(), console=console, refresh_per_second=1) as live:
        while True:
            time.sleep(2)
            live.update(app.generate_layout())

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Futures Dashboard closed.")
