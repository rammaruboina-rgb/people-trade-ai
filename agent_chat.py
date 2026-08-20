"""
agent_chat.py
Interactive Terminal Chatbot Console for CoinDCX Trading Agent.
Allows direct real-time natural language commands and queries with live market data feedback.
"""

import sys
import os
import time
import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from coindcx_client import CoinDCXClient
from config import (
    ALLOWED_FUTURES_COINS,
    EXCLUDED_COINS,
    set_focus_coin,
    TARGETED_FOCUS_COIN,
    DEFAULT_MAX_DAILY_TARGET_USD,
    MAX_CONCURRENT_TRADES
)
from strategy_engine import get_top_trending_altcoins, fetch_ohlcv, calculate_rsi
from news_client import get_global_crypto_news_feed, get_catalyst_event_score
from tweet_monitor import fetch_all_leader_tweets, decode_leader_tweets_to_catalysts, get_all_active_catalysts
from catalyst_engine import build_name_to_symbol_map
from data_store import load_trade_history, calculate_pnl

console = Console()

def render_banner():
    console.print()
    banner = Panel.fit(
        "[bold cyan]🤖 COINDCX AUTONOMOUS AGENT INTERACTIVE TERMINAL CHATBOX[/bold cyan]\n"
        "[dim]Type commands like: [yellow]'balance'[/yellow], [yellow]'trending'[/yellow], [yellow]'news'[/yellow], [yellow]'tweets'[/yellow], [yellow]'focus SUI'[/yellow], [yellow]'focus ALL'[/yellow], [yellow]'status'[/yellow], or [yellow]'exit'[/yellow][/dim]",
        border_style="magenta"
    )
    console.print(banner)

def handle_query(query: str):
    q = query.strip().lower()
    if not q:
        return

    client = CoinDCXClient()

    # 1. BALANCE & EQUITY QUERY
    if any(k in q for k in ["balance", "equity", "pnl", "portfolio", "money", "account"]):
        balances = client.get_account_balances()
        positions = client.get_active_futures_positions()
        trades = load_trade_history()
        sui_price = client.get_ticker_price("SUIUSDT")
        realized_pnl, unrealized_pnl, win_rate = calculate_pnl(trades, sui_price)

        t = Table(show_header=True, header_style="bold green", expand=True)
        t.add_column("Parameter", style="cyan")
        t.add_column("Live Value", style="bold white")

        import config
        t.add_row("Execution Mode", client.mode)
        t.add_row("Total Equity", f"${balances.get('total_equity', config.EQUITY_USD):,.2f} USD")
        t.add_row("Available USDT", f"${balances.get('USDT', 0.0):,.2f} USDT")
        t.add_row("Fiat INR", f"₹{balances.get('INR', 0.0):,.2f} INR")
        t.add_row("Realized P&L", f"${realized_pnl:+.2f} USD")
        t.add_row("Open P&L", f"${unrealized_pnl:+.2f} USD")
        t.add_row("Win Rate", f"{win_rate:.1f}%")
        t.add_row("Active Positions", str(len(positions)))

        console.print(Panel(t, title="[bold yellow]💰 Portfolio Balance & PnL Status[/bold yellow]", border_style="green"))

    # 2. TOP TRENDING COINS QUERY
    elif any(k in q for k in ["trending", "top", "scanned", "meme", "coins"]):
        top_coins = get_top_trending_altcoins(ALLOWED_FUTURES_COINS, top_n=10)
        t = Table(show_header=True, header_style="bold blue", expand=True)
        t.add_column("Rank", style="bold yellow", justify="center")
        t.add_column("Symbol", style="bold cyan")
        t.add_column("CoinDCX Futures Instrument", style="white")
        t.add_column("Catalyst Status", style="magenta")

        for idx, coin in enumerate(top_coins, 1):
            cat = get_catalyst_event_score(coin)
            event_str = cat.get("event_description", "Standard Volatility") if cat.get("has_catalyst") else "Active Scanned"
            t.add_row(str(idx), coin, f"B-{coin}_USDT", event_str)

        console.print(Panel(t, title="[bold yellow]🔥 Top 10 Trending Altcoins & Meme Coins[/bold yellow]", border_style="blue"))

    # 3. GLOBAL NEWS TICKER QUERY
    elif any(k in q for k in ["news", "headline", "market news", "feed"]):
        news_data = get_global_crypto_news_feed()
        bias = news_data.get("market_bias", "NEUTRAL ⚖️")
        headlines = news_data.get("headlines", [])

        t = Table(show_header=True, header_style="bold blue", expand=True)
        t.add_column("Time", style="dim white")
        t.add_column("Source", style="bold cyan")
        t.add_column("Headline", style="white")
        t.add_column("Sentiment", style="bold yellow")

        for item in headlines:
            t.add_row(item.get("time", ""), item.get("source", ""), item.get("title", ""), item.get("sentiment", ""))

        console.print(Panel(t, title=f"[bold yellow]🌐 Live Global Crypto News | Market Bias: [{bias}][/bold yellow]", border_style="cyan"))

    # 4. TWEET & LEADER CATALYSTS QUERY
    elif any(k in q for k in ["tweet", "trump", "elon", "social", "leader"]):
        name_map = build_name_to_symbol_map(ALLOWED_FUTURES_COINS)
        tweets = fetch_all_leader_tweets()
        cats = decode_leader_tweets_to_catalysts(tweets)

        t = Table(show_header=True, header_style="bold red", expand=True)
        t.add_column("Event Type", style="bold red")
        t.add_column("Impact Score", style="bold yellow", justify="center")
        t.add_column("Statement / Tweet Summary", style="white")

        for c in cats[:8]:
            t.add_row(c.event_type.upper(), f"{c.impact_score:+.2f}", c.description)

        console.print(Panel(t, title="[bold yellow]🐦 Donald Trump & Elon Musk Tweet Catalysts[/bold yellow]", border_style="red"))

    # 5. FOCUS COIN COMMAND (e.g. "focus SUI" or "focus ALL")
    elif "focus" in q:
        parts = q.split()
        if len(parts) >= 2:
            target = parts[1].upper()
            set_focus_coin(target)
            if target in ["ALL", "NONE", "CLEAR", "RESET"]:
                console.print("[bold green]✅ Agent focus reset: Now scanning ALL 110+ pure altcoins![/bold green]")
            else:
                console.print(f"[bold green]🎯 Agent focus locked onto: {target} ONLY![/bold green]")
        else:
            console.print("[yellow]Usage: type 'focus SUI', 'focus PEPE', or 'focus ALL'[/yellow]")

    # 6. SYSTEM STATUS & HARD GUARDS QUERY
    elif any(k in q for k in ["status", "rule", "guard", "setting", "config"]):
        t = Table(show_header=True, header_style="bold magenta", expand=True)
        t.add_column("Guard / Setting", style="cyan")
        t.add_column("Rule Value", style="bold white")

        excluded_str = f"NO {', NO '.join(EXCLUDED_COINS)}" if EXCLUDED_COINS else "NONE"
        sol_status = "SOL ENABLED ✅" if "SOL" in ALLOWED_FUTURES_COINS else "SOL BLOCKED ⛔"
        t.add_row("Asset Hard Guard", f"{sol_status} | Excluded: {excluded_str}")
        t.add_row("Allowed Universe", f"{len(ALLOWED_FUTURES_COINS)} Pure Altcoins & Meme Tokens")
        t.add_row("Leverage", "20X Isolated Margin")
        t.add_row("Profit Target (TP)", "+20.0% (+ Breakeven Stop @ +5.0%)")
        t.add_row("Stop Loss (SL)", "-10.0%")
        t.add_row("Max Concurrent Trades", f"{MAX_CONCURRENT_TRADES} Simultaneous Active Trades")
        t.add_row("Daily Profit Goal", f"${DEFAULT_MAX_DAILY_TARGET_USD:,.2f} USD")

        console.print(Panel(t, title="[bold yellow]🛡️ Master System Safeguards & Rules[/bold yellow]", border_style="magenta"))

    # 7. GENERAL AI RESPONSE
    else:
        console.print(f"[bold cyan]🤖 Agent Response:[/bold cyan] I received your command '[bold yellow]{query}[/bold yellow]'. I am continuously monitoring market liquidity, Trump/Elon tweets, and candlestick patterns for 110+ altcoins. Type '[yellow]trending[/yellow]', '[yellow]balance[/yellow]', '[yellow]news[/yellow]', or '[yellow]status[/yellow]' for real-time diagnostics.")

def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        handle_query(query)
        return

    render_banner()
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]👤 You[/bold cyan]")
            if user_input.strip().lower() in ["exit", "quit", "q", "bye"]:
                console.print("[bold yellow]👋 Exiting Agent Chat Console. Agent continues running in background![/bold yellow]")
                break
            handle_query(user_input)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Exiting chat console...[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error processing command: {e}[/bold red]")

if __name__ == "__main__":
    main()
