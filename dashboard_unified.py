# dashboard_unified.py
"""
Unified Terminal Dashboard for CoinDCX Master Trading Agent
Renders real-time Wallet Equity, Active Futures Positions, Live Signals, Trade Ledger & Search/Focus Bar.
"""

import os
import time
from datetime import datetime

import config
from config import LOG_FILE, TRADES_CSV, MAX_CONCURRENT_TRADES
from coindcx_client import CoinDCXClient
from data_store import load_trade_history, calculate_pnl

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

from news_client import get_global_crypto_news_feed

class UnifiedDashboardApp:
    def __init__(self):
        self.client = CoinDCXClient()
        self.start_time = datetime.now()

    def generate_header(self) -> Panel:
        uptime = str(datetime.now() - self.start_time).split(".")[0]
        header_text = Text()
        header_text.append("🚀 COINDCX 20X AUTONOMOUS FUTURES TRADER  |  ", style="bold yellow")
        
        if config.TARGETED_FOCUS_COIN:
            header_text.append(f"🎯 TARGETED FOCUS: {config.TARGETED_FOCUS_COIN} ONLY  |  ", style="bold green reverse")
        else:
            header_text.append("🌐 MODE: MULTI-ALTCOIN BASKET  |  ", style="bold cyan")

        header_text.append(f"⏱️ Uptime: {uptime}  |  ", style="bold white")
        header_text.append(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="bold dim white")
        return Panel(Align.center(header_text), border_style="cyan", style="on black")

    def generate_account_panel(self, balances: dict, realized_pnl: float, unrealized_pnl: float) -> Panel:
        table = Table(expand=True, box=None, show_header=True, header_style="bold yellow")
        table.add_column("USDT Balance", justify="center")
        table.add_column("Realized P&L", justify="center")
        table.add_column("Unrealized P&L", justify="center")
        table.add_column("Total Net Profit", justify="center")

        total_pnl = realized_pnl + unrealized_pnl
        real_style = "bold green" if realized_pnl >= 0 else "bold red"
        unreal_style = "bold green" if unrealized_pnl >= 0 else "bold red"
        tot_style = "bold green" if total_pnl >= 0 else "bold red"

        table.add_row(
            f"${balances.get('total_equity', config.EQUITY_USD):,.2f}",
            f"[{real_style}]${realized_pnl:,.2f}[/{real_style}]",
            f"[{unreal_style}]${unrealized_pnl:,.2f}[/{unreal_style}]",
            f"[{tot_style}]${total_pnl:,.2f}[/{tot_style}]"
        )
        return Panel(table, border_style="green", title="[bold yellow]ACCOUNT CAPITAL & P&L PERFORMANCE[/bold yellow]")

    def generate_positions_table(self, positions: dict) -> Panel:
        table = Table(expand=True, box=None, show_header=True, header_style="bold cyan")
        table.add_column("Pair", justify="center")
        table.add_column("Side", justify="center")
        table.add_column("Size", justify="center")
        table.add_column("Leverage", justify="center")
        table.add_column("Entry Price", justify="center")
        table.add_column("Liq Price", justify="center")

        active_count = 0
        for pair, p in positions.items():
            pos_size = float(p.get("active_pos", 0.0))
            if pos_size != 0.0:
                active_count += 1
                side = p.get("side", "NONE").upper()
                side_style = "bold green" if side == "BUY" or side == "LONG" else "bold red"
                table.add_row(
                    pair,
                    f"[{side_style}]{side}[/{side_style}]",
                    f"{abs(pos_size):,.2f}",
                    f"{p.get('leverage', 20)}X",
                    f"${float(p.get('avg_price', 0.0)):,.2f}",
                    f"${float(p.get('liquidation_price', 0.0)):,.2f}"
                )

        if active_count == 0:
            table.add_row("No Active Positions", "-", "-", "-", "-", "-")

        title_str = f"[bold yellow]ACTIVE FUTURES POSITIONS ({active_count}/{MAX_CONCURRENT_TRADES})[/bold yellow]"
        return Panel(table, border_style="yellow", title=title_str)

    def generate_recent_trades_table(self, trades: list) -> Panel:
        table = Table(expand=True, box=None, show_header=True, header_style="bold magenta")
        table.add_column("Time", justify="center")
        table.add_column("Symbol", justify="center")
        table.add_column("Side", justify="center")
        table.add_column("Price", justify="center")
        table.add_column("Size", justify="center")
        table.add_column("Signal Source", justify="center")

        recent = list(reversed(trades[-5:])) if trades else []
        for t in recent:
            side = t.get("side", "LONG")
            side_style = "bold green" if side == "LONG" or side == "BUY" else "bold red"
            table.add_row(
                t.get("timestamp", "").split(" ")[-1],
                t.get("symbol", "N/A"),
                f"[{side_style}]{side}[/{side_style}]",
                f"${float(t.get('entry_price', 0.0)):,.2f}",
                f"{float(t.get('size', 0.0)):,.2f}",
                t.get("signal_source", "LIVE")
            )

        if not recent:
            table.add_row("-", "-", "-", "-", "-", "-")

        return Panel(table, border_style="magenta", title="[bold yellow]RECENT EXECUTION LEDGER[/bold yellow]")

    def generate_global_news_panel(self) -> Panel:
        news_data = get_global_crypto_news_feed()
        bias = news_data.get("market_bias", "NEUTRAL ⚖️")
        headlines = news_data.get("headlines", [])
        next_sec = news_data.get("next_refresh_sec", 300)
        
        mins = next_sec // 60
        secs = next_sec % 60
        countdown_str = f"{mins}m {secs:02d}s"
        
        table = Table(expand=True, box=None, show_header=True, header_style="bold blue")
        table.add_column("Time", justify="center", style="dim white")
        table.add_column("Source", justify="center", style="bold cyan")
        table.add_column("Global Crypto Headline / Macro Event", justify="left")
        table.add_column("Impact", justify="center")

        for item in headlines:
            sent = item.get("sentiment", "NEUTRAL ⚖️")
            sent_style = "bold green" if "BULLISH" in sent else ("bold red" if "BEARISH" in sent else "bold yellow")
            table.add_row(
                item.get("time", "Now"),
                item.get("source", "Crypto"),
                item.get("title", ""),
                f"[{sent_style}]{sent}[/{sent_style}]"
            )
        if not headlines:
            table.add_row("-", "-", "Fetching 5-min global crypto market news...", "-")

        title_str = f"[bold yellow]🌐 GLOBAL CRYPTO NEWS TICKER (REFRESH IN: {countdown_str}) | MARKET SENTIMENT: [{bias}][/bold yellow]"
        return Panel(table, border_style="blue", title=title_str)

    def generate_search_bar_panel(self) -> Panel:
        search_text = Text()
        search_text.append("💬 INTERACTIVE AGENT TERMINAL CHAT: ", style="bold yellow")
        search_text.append("Run `./chat.sh` to chat live with your agent! ", style="bold green")
        
        if config.TARGETED_FOCUS_COIN:
            search_text.append(f"| [FOCUSED ON: {config.TARGETED_FOCUS_COIN}] ", style="bold green reverse")
        else:
            search_text.append("| [MODE: ALL 125+ ALTCOINS & MEMES SCANNER] ", style="bold cyan reverse")

        return Panel(Align.center(search_text), border_style="yellow", title="[bold cyan]🤖 INTERACTIVE TERMINAL CHATBOX & COIN SEARCH CONTROL[/bold cyan]")

    def generate_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="search_bar", size=3)
        )
        layout["main"].split_column(
            Layout(name="account", size=5),
            Layout(name="positions", ratio=1),
            Layout(name="trades", ratio=1),
            Layout(name="news", size=6)
        )

        balances = self.client.get_account_balances()
        positions = self.client.get_active_futures_positions()
        trades = load_trade_history()
        
        sui_price = self.client.get_ticker_price("SUIUSDT")
        realized_pnl, unrealized_pnl, _ = calculate_pnl(trades, sui_price)

        layout["header"].update(self.generate_header())
        layout["account"].update(self.generate_account_panel(balances, realized_pnl, unrealized_pnl))
        layout["positions"].update(self.generate_positions_table(positions))
        layout["trades"].update(self.generate_recent_trades_table(trades))
        layout["news"].update(self.generate_global_news_panel())
        layout["search_bar"].update(self.generate_search_bar_panel())

        return layout

