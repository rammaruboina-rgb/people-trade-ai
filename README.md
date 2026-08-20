# CoinDCX Autonomous 1m Scalping Futures Trading Engine

Autonomous, high-frequency multi-altcoin futures trading bot built for CoinDCX with real-time OHLCV candlestick price action analysis, zero-loss break-even guards, and strict risk controls.

## Features
- **1m/5m OHLCV Candlestick Trend Filtering**: Real-time candle fetching & MA20 trend confirmation directly from CoinDCX API.
- **LONG & SHORT Futures Execution**: Dynamic order placement with leverage caps (5x major coins, 3x altcoins).
- **Zero-Loss Break-Even Guard**: Automatically moves Stop-Loss to entry price (+0.3% fee buffer) once +0.3% profit is reached.
- **Micro-Capital & Profit Discipline**: Built-in daily profit target ($50/day) and daily max loss limit (-$25/day) circuit breakers.
- **Visual Candlestick Charting**: Integrated `plot_agent.py` for rendering 1m OHLCV charts.

## Quick Start
```bash
# Start Unified Terminal Dashboard
python run_all.py

# Generate Candlestick Chart
python plot_agent.py
```
