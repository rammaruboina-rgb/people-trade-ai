# dashboard_server.py
import os
import sys
import time
import json
import requests
import subprocess
from flask import Flask, jsonify, render_template_string, request
from coindcx_client import CoinDCXClient
from orderbook_engine import analyze_order_book
from wyckoff_engine import analyze_wyckoff_phase, predict_pre_breakout
from news_client import get_global_crypto_news_feed

app = Flask(__name__)
client = CoinDCXClient()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 PeopleTrade AI - Built for People. Powered by AI.</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js" defer></script>
    <style>
        :root {
            --bg-primary: #0a0c10;
            --bg-card: rgba(18, 24, 38, 0.85);
            --border-card: rgba(255, 255, 255, 0.08);
            --accent-blue: #3b82f6;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-purple: #8b5cf6;
            --accent-yellow: #eab308;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
        }

        body {
            background-color: var(--bg-primary);
            background-image: 
                radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.12) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(139, 92, 246, 0.12) 0px, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 2rem;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-card);
        }

        .logo-section h1 {
            font-size: 1.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, #60a5fa, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .status-badge {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--accent-green);
            padding: 0.4rem 1rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--accent-green);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--accent-green);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }

        /* 24/7 Agent Master Control Bar */
        .agent-control-panel {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.9));
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 1rem;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            backdrop-filter: blur(12px);
        }

        .agent-info {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .agent-status-text {
            font-size: 1.1rem;
            font-weight: 700;
        }

        .btn-agent-start {
            background: linear-gradient(135deg, #10b981, #059669);
            color: #fff;
            border: none;
            padding: 0.75rem 1.75rem;
            border-radius: 0.5rem;
            font-weight: 800;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
        }

        .btn-agent-stop {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: #fff;
            border: none;
            padding: 0.75rem 1.75rem;
            border-radius: 0.5rem;
            font-weight: 800;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
        }

        .btn-agent-start:hover, .btn-agent-stop:hover {
            transform: translateY(-2px);
            opacity: 0.9;
        }

        .grid-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }

        .stat-card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-card);
            border-radius: 1rem;
            padding: 1.25rem;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .stat-label {
            color: var(--text-muted);
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.4rem;
        }

        .stat-value {
            font-size: 1.35rem;
            font-weight: 700;
            color: var(--text-main);
            word-wrap: break-word;
            overflow-wrap: break-word;
        }

        .stat-subtext {
            font-size: 0.8rem;
            font-weight: 600;
            margin-top: 0.3rem;
            word-break: break-word;
        }

        /* Wyckoff Banner Panel */
        .wyckoff-panel {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(59, 130, 246, 0.1));
            backdrop-filter: blur(12px);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 1rem;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .wyckoff-title {
            font-size: 1.1rem;
            font-weight: 800;
            color: var(--accent-green);
        }

        .wyckoff-desc {
            font-size: 0.9rem;
            color: var(--text-main);
            margin-top: 0.25rem;
        }

        /* API Key Panel */
        .api-panel {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 1rem;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }

        .api-header {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--accent-cyan);
        }

        .form-group {
            display: grid;
            grid-template-columns: 1fr 1fr auto auto;
            gap: 1rem;
            align-items: center;
        }

        @media (max-width: 768px) {
            .form-group {
                grid-template-columns: 1fr;
            }
        }

        input[type="text"], input[type="password"] {
            width: 100%;
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--border-card);
            color: var(--text-main);
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            font-size: 0.9rem;
            font-family: 'JetBrains Mono', monospace;
        }

        .btn-toggle {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-card);
            color: var(--text-muted);
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            font-weight: 600;
            cursor: pointer;
        }

        .btn-save {
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            color: #fff;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            font-weight: 700;
            cursor: pointer;
        }

        /* Chart Panel */
        .chart-panel {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-card);
            border-radius: 1rem;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .coin-selector {
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
            padding-bottom: 0.5rem;
        }

        .coin-btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-card);
            color: var(--text-muted);
            padding: 0.4rem 0.8rem;
            border-radius: 0.5rem;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
        }

        .coin-btn.active, .coin-btn:hover {
            background: var(--accent-blue);
            color: #fff;
            border-color: var(--accent-blue);
        }

        #tv-chart {
            width: 100%;
            height: 400px;
            border-radius: 0.75rem;
            overflow: hidden;
        }

        .legend {
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 0.75rem;
            color: var(--text-muted);
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .legend-box {
            width: 12px;
            height: 12px;
            border-radius: 3px;
        }

        .panel-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }

        @media (max-width: 968px) {
            .panel-grid {
                grid-template-columns: 1fr;
            }
        }

        .panel {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-card);
            border-radius: 1rem;
            padding: 1.5rem;
        }

        .panel-header {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .tape-box {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 0.5rem;
            padding: 1rem;
            height: 300px;
            overflow-y: auto;
            color: #d1d5db;
            line-height: 1.6;
        }

        .tape-item {
            display: flex;
            justify-content: space-between;
            padding: 0.25rem 0.4rem;
            border-radius: 0.25rem;
            margin-bottom: 0.2rem;
        }

        .tape-buy { background: rgba(16, 185, 129, 0.12); color: #34d399; }
        .tape-sell { background: rgba(239, 68, 68, 0.12); color: #f87171; }
        .tape-whale { font-weight: 700; border: 1px solid rgba(255, 255, 255, 0.2); }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-section">
                <h1 style="font-size: 2.1rem; font-weight: 900; background: linear-gradient(135deg, #60a5fa, #c084fc, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    🤖 PeopleTrade AI
                </h1>
                <div style="font-size: 0.88rem; font-weight: 700; color: #34d399; margin-top: 0.2rem; letter-spacing: 0.5px;">
                    ✨ “Built for People. Powered by AI.”
                </div>
            </div>
            <div style="display: flex; gap: 0.75rem; align-items: center;">
                <div class="status-badge" style="background: rgba(16, 185, 129, 0.2); border-color: rgba(16, 185, 129, 0.5); color: #34d399; font-weight: 800;">
                    <span>💵 REAL CASH MODE: ENABLED</span>
                </div>
                <div class="status-badge">
                    <div class="status-dot"></div>
                    <span>PEOPLETRADE AGENT ONLINE (PID <span id="pid">LIVE</span>)</span>
                </div>
            </div>
        </header>

        <!-- 24/7 Master Agent Control Panel -->
        <div class="agent-control-panel">
            <div class="agent-info">
                <div class="status-dot" id="agent-dot" style="width: 14px; height: 14px;"></div>
                <div>
                    <div class="agent-status-text" id="agent-status-title" style="color: var(--accent-green);">🤖 PEOPLETRADE AI: ONLINE & RUNNING</div>
                    <div style="font-size: 0.85rem; color: var(--text-muted);" id="agent-status-sub">“Built for People. Powered by AI.” | 20x Safe Wyckoff Execution</div>
                </div>
            </div>
            <div style="display: flex; gap: 0.75rem; align-items: center;">
                <button class="btn-agent-start" id="btn-start" onclick="startAgent()">▶️ START AGENT</button>
                <button class="btn-agent-stop" id="btn-stop" onclick="stopAgent()">⏹️ STOP AGENT</button>
            </div>
        </div>

        <!-- Live Market Cycle Phase & Schematic Classifier Banner -->
        <div class="wyckoff-panel">
            <div>
                <div class="wyckoff-title" id="wyckoff-phase-title">🏛️ MARKET CYCLE PHASE: PHASE C (SPRING RECOVERY)</div>
                <div class="wyckoff-desc" id="wyckoff-phase-desc">Smart Money Accumulation: Spring sweep of liquidity detected.</div>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
                <span class="status-badge" style="font-size: 0.85rem; background: rgba(16,185,129,0.15); border-color: rgba(16,185,129,0.4); color: #34d399;" id="tp-targets-badge">🎯 TAKE PROFITS: T1 (+15% ROE) | T2 (+30% ROE) | T3 (+50% ROE)</span>
                <span class="status-badge" style="font-size: 0.9rem;" id="wyckoff-action-badge">ACTION: BUY / LONG 🟢</span>
            </div>
        </div>

        <!-- CoinDCX API Key & Secret Management Panel -->
        <div class="api-panel">
            <div class="api-header">
                <span>🔐 CoinDCX API Credentials Configuration</span>
                <span id="api-status-msg" style="font-size: 0.85rem; color: var(--accent-green);">STATUS: KEYS HIDDEN & ENCRYPTED 🔒</span>
            </div>
            <form id="api-form" onsubmit="saveApiKeys(event)">
                <div class="form-group">
                    <div>
                        <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">COINDCX API KEY</label>
                        <input type="password" id="input-api-key" placeholder="••••••••••••••••••••••••" required>
                    </div>
                    <div>
                        <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">COINDCX API SECRET</label>
                        <input type="password" id="input-api-secret" placeholder="••••••••••••••••••••••••" required>
                    </div>
                    <div style="align-self: flex-end;">
                        <button type="button" class="btn-toggle" onclick="toggleKeyVisibility()">👁️ SHOW / HIDE</button>
                    </div>
                    <div style="align-self: flex-end;">
                        <button type="submit" class="btn-save">💾 SAVE KEYS</button>
                    </div>
                </div>
            </form>
        </div>

        <div class="grid-stats">
            <div class="stat-card">
                <div class="stat-label">Wallet Equity</div>
                <div class="stat-value" id="equity-usd">$20.00</div>
                <div class="stat-subtext" style="color: var(--accent-green);" id="equity-sub">Live 1m Sync ⚡</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Prime Trading Hours</div>
                <div class="stat-value" style="color: var(--accent-green);" id="prime-window-val">PRIME WINDOW 🔥</div>
                <div class="stat-subtext" style="color: var(--accent-green);" id="prime-window-sub">US & London Liquidity Peak</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Selected Symbol</div>
                <div class="stat-value" style="color: var(--accent-cyan);" id="chart-symbol">BTCUSDT</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Pre-Breakout Prediction</div>
                <div class="stat-value" style="color: var(--accent-yellow);" id="prebreakout-val">NO PRE-BREAKOUT ⚖️</div>
                <div class="stat-subtext" style="color: var(--text-muted);" id="prebreakout-sub">(STABLE VOLATILITY)</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Bid / Ask Ratio</div>
                <div class="stat-value" style="color: var(--accent-purple);" id="ob-ratio-val">1.82</div>
                <div class="stat-subtext" style="color: var(--accent-purple);" id="ob-ratio-sub">(BULLISH BUY WALL)</div>
            </div>
        </div>

        <!-- Real-Time TradingView Candlestick Graph -->
        <div class="chart-panel">
            <div class="chart-header">
                <h3>📈 Live Candlestick Graph & Pre-Breakout Predictor Signals</h3>
                <div class="coin-selector">
                    <button class="coin-btn active" onclick="changeCoin('BTCUSDT', this)">BTC</button>
                    <button class="coin-btn" onclick="changeCoin('ETHUSDT', this)">ETH</button>
                    <button class="coin-btn" onclick="changeCoin('SOLUSDT', this)">SOL</button>
                    <button class="coin-btn" onclick="changeCoin('SUIUSDT', this)">SUI</button>
                    <button class="coin-btn" onclick="changeCoin('DOGEUSDT', this)">DOGE</button>
                    <button class="coin-btn" onclick="changeCoin('AVAXUSDT', this)">AVAX</button>
                    <button class="coin-btn" onclick="changeCoin('NEARUSDT', this)">NEAR</button>
                    <button class="coin-btn" onclick="changeCoin('PEPEUSDT', this)">PEPE</button>
                    <button class="coin-btn" onclick="changeCoin('WIFUSDT', this)">WIF</button>
                    <button class="coin-btn" onclick="changeCoin('SEIUSDT', this)">SEI</button>
                    <button class="coin-btn" onclick="changeCoin('INJUSDT', this)">INJ</button>
                    <button class="coin-btn" onclick="changeCoin('XRPUSDT', this)">XRP</button>
                    <button class="coin-btn" onclick="changeCoin('ADAUSDT', this)">ADA</button>
                    <button class="coin-btn" onclick="changeCoin('LINKUSDT', this)">LINK</button>
                </div>
            </div>

            <!-- 🚨 HIGH ALERT BOT ENTRY & SIGNAL BANNER -->
            <div id="high-alert-banner" style="display: none; background: linear-gradient(135deg, rgba(239, 68, 68, 0.25), rgba(245, 158, 11, 0.25)); border: 2px solid #ef4444; border-radius: 0.75rem; padding: 0.75rem 1.25rem; margin-bottom: 1rem; align-items: center; justify-content: space-between; box-shadow: 0 0 20px rgba(239, 68, 68, 0.4);">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-size: 1.6rem;">🚨</span>
                    <div>
                        <div id="high-alert-title" style="font-weight: 800; font-size: 1.05rem; color: #ff4d4d; letter-spacing: 0.5px;">HIGH ALERT: BOT ENTRY DETECTED</div>
                        <div id="high-alert-sub" style="font-size: 0.88rem; color: #f3f4f6;">PeopleTrade AI Agent active entry on chart</div>
                    </div>
                </div>
                <span class="status-badge" style="background: #ef4444; color: #fff; font-weight: 800; font-size: 0.85rem;" id="high-alert-badge">HIGH ALERT 🚨</span>
            </div>

            <div id="tv-chart"></div>

            <div class="legend">
                <div class="legend-item"><div class="legend-box" style="background: linear-gradient(135deg, #00ff66, #ff0055); border: 1.5px solid #ffffff; box-shadow: 0 0 8px #00ff66;"></div> 👑⚡ BOT HIGH ALERT ENTRY (Unique 20x Position Marker)</div>
                <div class="legend-item"><div class="legend-box" style="background: #ef4444;"></div> FUTURES SELL / SHORT 🔴 (Optimal Downward Entry / T1 T2 T3 Targets 📉)</div>
                <div class="legend-item"><div class="legend-box" style="background: #10b981;"></div> FUTURES BUY / LONG 🟢 (Optimal Upward Entry Signal)</div>
                <div class="legend-item"><div class="legend-box" style="background: #00e676;"></div> 🟢 Live Tape Purchase (Who Buy What)</div>
                <div class="legend-item"><div class="legend-box" style="background: #ff1744;"></div> 🔴 Live Tape Sale (Who Sell What)</div>
                <div class="legend-item"><div class="legend-box" style="background: #c084fc;"></div> 🐋 Live Whale Trade ($1,000+)</div>
                <div class="legend-item"><div class="legend-box" style="background: #f97316;"></div> Bull Trap 🪤 (Upthrust Fakeout / Short Entry 🔴)</div>
                <div class="legend-item"><div class="legend-box" style="background: #eab308;"></div> Bear Trap 🪤 (Liquidity Sweep / Buy Entry 🟢)</div>
                <div class="legend-item"><div class="legend-box" style="background: #a855f7;"></div> Pre-Breakdown Dump Prediction (Early Short ⚠️)</div>
                <div class="legend-item"><div class="legend-box" style="background: #06b6d4;"></div> Pre-Breakout Pump Prediction (Early Buy ⚡)</div>
            </div>
        </div>

        <!-- ALL COIN PRE-BREAKOUT RADAR PANEL -->
        <div class="panel-grid" style="margin-bottom: 1.5rem;">
            <div class="panel" style="grid-column: 1 / -1;">
                <div class="panel-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <span>⚡ ALL COINS PRE-BREAKOUT & MARKET RADAR SCANNER</span>
                    <button class="btn-start" id="btn-live-scan" onclick="triggerLiveScan()" style="padding: 0.4rem 1.1rem; font-size: 0.85rem; border-radius: 6px; box-shadow: 0 0 12px rgba(16,185,129,0.4); cursor: pointer;">
                        🔍 TRIGGER LIVE SCAN (14 ALTCOINS) 📡
                    </button>
                </div>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 0.88rem; text-align: left;">
                        <thead>
                            <tr style="border-bottom: 1px solid var(--border-card); color: var(--text-muted); text-transform: uppercase; font-size: 0.75rem;">
                                <th style="padding: 0.75rem 1rem;">Asset</th>
                                <th style="padding: 0.75rem 1rem;">Pre-Breakout Status</th>
                                <th style="padding: 0.75rem 1rem;">Market Cycle Phase</th>
                                <th style="padding: 0.75rem 1rem;">Order Book Imbalance</th>
                                <th style="padding: 0.75rem 1rem;">Action</th>
                            </tr>
                        </thead>
                        <tbody id="radar-tbody">
                            <tr>
                                <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">Scanning All 14 Coins for Pre-Breakout Compressors...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="panel-grid" style="margin-bottom: 1.5rem;">
            <div class="panel" style="grid-column: 1 / -1;">
                <div class="panel-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <span>🌐 LIVE WORLD & CRYPTO MARKET NEWS FEED (5m Auto Refresh ⚡ | SENTIMENT: <span id="news-bias" style="color: var(--accent-cyan);">LOADING...</span>)</span>
                    <span style="font-size: 0.85rem; color: var(--accent-green);" id="news-meter">SENTIMENT: 80% BULLISH 🟢</span>
                </div>
                <div class="tape-box" id="news-feed-box" style="height: 260px;">
                    <div style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading Global Crypto Headlines...</div>
                </div>
            </div>
        </div>

        <div class="panel-grid">
            <div class="panel">
                <div class="panel-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <span>🟢 WHO BUY WHAT & 🔴 WHO SELL WHAT (LIVE TAPE)</span>
                    <span style="font-size: 0.75rem; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 700;">
                        📍 PURCHASES & SELLS PLOTTED ON GRAPH
                    </span>
                </div>
                <div class="tape-box" id="trade-tape-box">
                    <div style="text-align: center; color: var(--text-muted); padding: 2rem;">Connecting to Live Trade Stream...</div>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <span>📋 Live Master Agent Console Logs</span>
                </div>
                <div class="tape-box" id="log-box">
                    <div style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading Agent Console Logs...</div>
                </div>
            </div>
        </div>

        <!-- INTERACTIVE TEXT WITH AGENT CHAT CONSOLE -->
        <div class="panel-grid" style="margin-top: 1.5rem; margin-bottom: 1.5rem;">
            <div class="panel" style="grid-column: 1 / -1; background: linear-gradient(180deg, var(--bg-card) 0%, rgba(17, 24, 39, 0.95) 100%); border: 1px solid var(--border-card);">
                <div class="panel-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <span>💬 TEXT WITH AGENT (INTERACTIVE AI TRADING CONSOLE)</span>
                    <span style="font-size: 0.8rem; background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 700;">
                        🤖 24/7 ACTIVE COPILOT
                    </span>
                </div>
                
                <!-- Quick Command Badges -->
                <div style="display: flex; gap: 0.5rem; margin-bottom: 0.8rem; flex-wrap: wrap;">
                    <button class="btn-toggle" onclick="sendPresetChat('Analyze current Wyckoff structure')" style="font-size: 0.75rem; padding: 0.3rem 0.6rem; background: rgba(139, 92, 246, 0.15); color: #c084fc; border-color: rgba(139, 92, 246, 0.3);">🏛️ Analyze Wyckoff</button>
                    <button class="btn-toggle" onclick="sendPresetChat('What is my wallet balance?')" style="font-size: 0.75rem; padding: 0.3rem 0.6rem; background: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.3);">💰 Wallet Status</button>
                    <button class="btn-toggle" onclick="sendPresetChat('Check High-Win Signal Gate')" style="font-size: 0.75rem; padding: 0.3rem 0.6rem; background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.3);">🎯 High-Win Gate</button>
                    <button class="btn-toggle" onclick="sendPresetChat('What is market news bias?')" style="font-size: 0.75rem; padding: 0.3rem 0.6rem; background: rgba(56, 189, 248, 0.15); color: #38bdf8; border-color: rgba(56, 189, 248, 0.3);">📰 Market Sentiment</button>
                </div>

                <!-- Agent Chat Messages Window -->
                <div id="agent-chat-window" style="height: 200px; overflow-y: auto; background: rgba(0,0,0,0.4); border: 1px solid var(--border-card); border-radius: 8px; padding: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.88rem; display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 0.8rem;">
                    <div style="background: rgba(56, 189, 248, 0.1); border-left: 3px solid #38bdf8; padding: 0.6rem 0.8rem; border-radius: 4px; color: #e2e8f0;">
                        🤖 <strong>PeopleTrade AI Agent</strong>: Welcome! Type any prompt below to text with me directly. Ask about Wyckoff phases, high-win gates, wallet equity, or coin analysis!
                    </div>
                </div>

                <!-- Chat Input Form -->
                <form id="agent-chat-form" onsubmit="handleAgentChatSubmit(event)" style="display: flex; gap: 0.75rem;">
                    <input type="text" id="agent-chat-input" placeholder="💬 Text with Agent (e.g. 'Analyze SUI', 'Wallet balance', 'Check high-win signal gate')..." style="flex: 1; padding: 0.65rem 1rem; background: rgba(0,0,0,0.5); border: 1px solid var(--border-card); border-radius: 6px; color: #fff; font-size: 0.88rem;" required>
                    <button type="submit" style="padding: 0.65rem 1.5rem; background: linear-gradient(135deg, #3b82f6, #6366f1); border: none; border-radius: 6px; color: #fff; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 0.4rem;">
                        <span>SEND TEXT</span> 🚀
                    </button>
                </form>
            </div>
        </div>
    <script>
        let currentSymbol = 'BTCUSDT';
        let chart, candlestickSeries, emaSeries;
        let keysLoaded = false;
        let lastWyckoffState = {};
        let lastPreBreakoutState = {};
        let currentKlineMarkers = [];
        let liveTapeMarkers = [];
        let botEntryMarkers = [];
        let highAlertActive = false;

        // Silent NO-OP for Voice Alerts (Voice Completely Removed per User Directive)
        function speakMessage(text, alertType = "info") {
            return;
        }

        function updateCombinedGraphMarkers() {
            if (!candlestickSeries) return;
            const combinedMap = {};
            for (const m of currentKlineMarkers) {
                combinedMap[m.time] = { ...m };
            }
            for (const m of liveTapeMarkers) {
                if (combinedMap[m.time]) {
                    if (!combinedMap[m.time].text.includes(m.text)) {
                        combinedMap[m.time].text = `${combinedMap[m.time].text} | ${m.text}`;
                    }
                } else {
                    combinedMap[m.time] = { ...m };
                }
            }
            for (const m of botEntryMarkers) {
                if (combinedMap[m.time]) {
                    combinedMap[m.time].text = `${m.text} || ${combinedMap[m.time].text}`;
                    combinedMap[m.time].color = m.color;
                    combinedMap[m.time].shape = m.shape;
                } else {
                    combinedMap[m.time] = { ...m };
                }
            }
            const sorted = Object.values(combinedMap).sort((a, b) => a.time - b.time);
            try {
                candlestickSeries.setMarkers(sorted);
            } catch (err) {
                console.error("setMarkers error:", err);
            }
        }

        function appendChatMessage(sender, text, isUser = false) {
            const chatWin = document.getElementById('agent-chat-window');
            if (!chatWin) return;
            const msgDiv = document.createElement('div');
            msgDiv.style.padding = '0.6rem 0.8rem';
            msgDiv.style.borderRadius = '4px';
            msgDiv.style.color = '#e2e8f0';
            msgDiv.style.whiteSpace = 'pre-wrap';

            if (isUser) {
                msgDiv.style.background = 'rgba(139, 92, 246, 0.15)';
                msgDiv.style.borderRight = '3px solid #c084fc';
                msgDiv.style.alignSelf = 'flex-end';
                msgDiv.style.maxWidth = '85%';
                msgDiv.innerHTML = `👤 <strong>You</strong>: ${text}`;
            } else {
                msgDiv.style.background = 'rgba(56, 189, 248, 0.1)';
                msgDiv.style.borderLeft = '3px solid #38bdf8';
                msgDiv.style.alignSelf = 'flex-start';
                msgDiv.style.maxWidth = '90%';
                msgDiv.innerHTML = text.split(String.fromCharCode(10)).join('<br>');
            }

            chatWin.appendChild(msgDiv);
            chatWin.scrollTop = chatWin.scrollHeight;
        }

        async function handleAgentChatSubmit(e) {
            if (e) e.preventDefault();
            const input = document.getElementById('agent-chat-input');
            if (!input) return;
            const text = input.value ? input.value.trim() : '';
            if (!text) return;

            appendChatMessage('You', text, true);
            input.value = '';

            try {
                const res = await fetch('/api/agent/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: text, symbol: currentSymbol })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    appendChatMessage('Agent', data.response, false);
                } else {
                    appendChatMessage('Agent', `⚠️ Error: ${data.response || 'Failed to process prompt'}`, false);
                }
            } catch (err) {
                appendChatMessage('Agent', `⚠️ Network Error: Could not communicate with Agent.`, false);
            }
        }

        function sendPresetChat(promptText) {
            const input = document.getElementById('agent-chat-input');
            if (input) {
                input.value = promptText;
                handleAgentChatSubmit(null);
            }
        }

        function initChart() {
            const chartContainer = document.getElementById('tv-chart');
            if (!chartContainer) return;
            if (typeof LightweightCharts === 'undefined') {
                chartContainer.innerHTML = '<div style="text-align: center; color: var(--accent-yellow); padding: 5rem 1rem; font-weight: 700; font-size: 1rem;">⚠️ TradingView Chart Library Loading... If blocked, refresh page or check internet connection.</div>';
                return;
            }
            try {
                chart = LightweightCharts.createChart(chartContainer, {
                width: chartContainer.clientWidth,
                height: 400,
                layout: {
                    background: { type: 'solid', color: '#0f172a' },
                    textColor: '#94a3b8',
                },
                grid: {
                    vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal,
                },
                timeScale: {
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    timeVisible: true,
                    secondsVisible: false,
                },
            });

            candlestickSeries = chart.addCandlestickSeries({
                upColor: '#10b981',
                downColor: '#ef4444',
                borderDownColor: '#ef4444',
                borderUpColor: '#10b981',
                wickDownColor: '#ef4444',
                wickUpColor: '#10b981',
            });

            emaSeries = chart.addLineSeries({
                color: '#3b82f6',
                lineWidth: 2,
            });

            window.addEventListener('resize', () => {
                chart.applyOptions({ width: chartContainer.clientWidth });
            });

            loadCandles(currentSymbol);
            } catch (err) {
                console.error("Chart init error:", err);
            }
        }

        async function startAgent() {
            try {
                const res = await fetch('/api/agent/start', { method: 'POST' });
                const data = await res.json();
                speakMessage("24/7 Master Trading Agent is now active and scanning markets.");
                alert(data.message);
                fetchDashboardData();
            } catch (err) {
                console.error("Start agent error:", err);
                alert("Failed to start agent.");
            }
        }

        async function stopAgent() {
            try {
                const res = await fetch('/api/agent/stop', { method: 'POST' });
                const data = await res.json();
                speakMessage("24/7 Master Trading Agent has been stopped.");
                alert(data.message);
                fetchDashboardData();
            } catch (err) {
                console.error("Stop agent error:", err);
                alert("Failed to stop agent.");
            }
        }

        function toggleKeyVisibility() {
            const kInput = document.getElementById('input-api-key');
            const sInput = document.getElementById('input-api-secret');

            if (kInput.type === 'password') {
                kInput.type = 'text';
                sInput.type = 'text';
            } else {
                kInput.type = 'password';
                sInput.type = 'password';
            }
        }

        async function saveApiKeys(event) {
            event.preventDefault();
            const apiKey = document.getElementById('input-api-key').value.trim();
            const apiSecret = document.getElementById('input-api-secret').value.trim();

            if (!apiKey || !apiSecret) {
                alert('Please enter both API Key and API Secret!');
                return;
            }

            try {
                const res = await fetch('/api/save_keys', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key: apiKey, api_secret: apiSecret })
                });

                const data = await res.json();
                if (data.status === 'success') {
                    document.getElementById('input-api-key').type = 'password';
                    document.getElementById('input-api-secret').type = 'password';
                    document.getElementById('input-api-key').value = data.masked_key || '••••••••••••••••••••••••';
                    document.getElementById('input-api-secret').value = '••••••••••••••••••••••••';
                    document.getElementById('api-status-msg').innerText = '✅ API KEYS SAVED & HIDDEN 🔒';
                    alert('CoinDCX API Keys Saved & Hidden!');
                } else {
                    alert('Error saving API keys: ' + data.message);
                }
            } catch (err) {
                console.error("Save keys error:", err);
                alert('Failed to save API keys.');
            }
        }

        async function loadCandles(symbol) {
            try {
                const res = await fetch(`/api/klines/${symbol}`);
                const payload = await res.json();

                if (candlestickSeries && payload && payload.candles && payload.candles.length > 0) {
                    candlestickSeries.setData(payload.candles);
                    if (emaSeries && payload.ema && payload.ema.length > 0) {
                        emaSeries.setData(payload.ema);
                    }
                    if (payload.markers) {
                        currentKlineMarkers = payload.markers;
                        updateCombinedGraphMarkers();
                    }
                }

                    if (payload.pre_breakout) {
                        const pbValEl = document.getElementById('prebreakout-val');
                        const pbSubEl = document.getElementById('prebreakout-sub');

                        pbValEl.innerText = payload.pre_breakout.prediction;
                        pbSubEl.innerText = payload.pre_breakout.subtext;

                        if (payload.pre_breakout.status === 'PRE_BREAKOUT_BULLISH') {
                            pbValEl.style.color = '#eab308';
                            pbSubEl.style.color = '#eab308';
                            if (lastPreBreakoutState[symbol] !== 'PRE_BREAKOUT_BULLISH') {
                                speakMessage(`Bullish Pre Breakout predicted on ${symbol.replace('USDT','')}`);
                                lastPreBreakoutState[symbol] = 'PRE_BREAKOUT_BULLISH';
                            }
                        } else if (payload.pre_breakout.status === 'PRE_BREAKDOWN_BEARISH') {
                            pbValEl.style.color = '#f97316';
                            pbSubEl.style.color = '#f97316';
                            if (lastPreBreakoutState[symbol] !== 'PRE_BREAKDOWN_BEARISH') {
                                speakMessage(`Warning! Bearish Pre Breakdown alert on ${symbol.replace('USDT','')}`);
                                lastPreBreakoutState[symbol] = 'PRE_BREAKDOWN_BEARISH';
                            }
                        } else if (payload.pre_breakout.status === 'VOLATILITY_SQUEEZE') {
                            pbValEl.style.color = '#06b6d4';
                            pbSubEl.style.color = '#06b6d4';
                            lastPreBreakoutState[symbol] = 'VOLATILITY_SQUEEZE';
                        } else {
                            pbValEl.style.color = '#9ca3af';
                            pbSubEl.style.color = '#9ca3af';
                            lastPreBreakoutState[symbol] = 'NEUTRAL';
                        }
                    }
            } catch (err) {
                console.error("Error loading candles:", err);
            }
        }

        async function fetchWyckoffAnalysis(symbol) {
            try {
                const res = await fetch(`/api/wyckoff/${symbol}`);
                const w = await res.json();

                const cleanPhase = (w.phase || '').replace(/WYCKOFF\s*/gi, '');
                document.getElementById('wyckoff-phase-title').innerText = '🏛️ MARKET CYCLE PHASE: ' + cleanPhase;
                document.getElementById('wyckoff-phase-desc').innerText = w.description;
                document.getElementById('wyckoff-action-badge').innerText = 'ACTION: ' + w.action;

                const tpBadge = document.getElementById('tp-targets-badge');
                if (tpBadge && w.confidence_pct) {
                    tpBadge.innerText = `⚡ 6-ENGINE CONFLUENCE: ${w.confidence_pct.toFixed(0)}% MATCH`;
                    if (w.confidence_pct >= 75.0) {
                        tpBadge.style.color = '#34d399';
                        tpBadge.style.borderColor = 'rgba(16,185,129,0.4)';
                    } else {
                        tpBadge.style.color = '#eab308';
                        tpBadge.style.borderColor = 'rgba(234,179,8,0.4)';
                    }
                }

                const currentStateKey = symbol + '_' + w.phase;

                if (w.signal.includes('BULLISH') || w.signal.includes('SPRING') || w.signal.includes('MARKUP')) {
                    document.getElementById('wyckoff-phase-title').style.color = '#10b981';
                    if (lastWyckoffState[symbol] !== currentStateKey) {
                        speakMessage(`Market Phase ${cleanPhase} detected on ${symbol.replace('USDT','')}. Recommendation ${w.action}`);
                        lastWyckoffState[symbol] = currentStateKey;
                    }
                } else if (w.signal.includes('BEARISH') || w.signal.includes('UTAD') || w.signal.includes('MARKDOWN')) {
                    document.getElementById('wyckoff-phase-title').style.color = '#ef4444';
                    if (lastWyckoffState[symbol] !== currentStateKey) {
                        speakMessage(`Market Cycle Warning on ${symbol.replace('USDT','')}. ${cleanPhase} in progress.`);
                        lastWyckoffState[symbol] = currentStateKey;
                    }
                } else {
                    document.getElementById('wyckoff-phase-title').style.color = '#3b82f6';
                    lastWyckoffState[symbol] = currentStateKey;
                }
            } catch (err) {
                console.error("Wyckoff fetch error:", err);
            }
        }

        async function fetchLiveTrades(symbol) {
            try {
                const res = await fetch(`/api/trades/${symbol}`);
                const trades = await res.json();

                const tapeBox = document.getElementById('trade-tape-box');
                if (trades && trades.length > 0) {
                    let html = '';
                    let topBuy = null;
                    let topSell = null;

                    for (const t of trades) {
                        const isBuy = t.is_buy;
                        const isWhale = t.value_usd >= 1000.0;
                        const cls = (isBuy ? 'tape-buy' : 'tape-sell') + (isWhale ? ' tape-whale' : '');
                        const icon = isBuy ? (isWhale ? '🐋 BUY' : '🟢 BUY') : (isWhale ? '🐋 SELL' : '🔴 SELL');
                        
                        html += `
                            <div class="tape-item ${cls}">
                                <span>${icon} ${t.qty} ${symbol.replace('USDT','')}</span>
                                <span>@ $${t.price.toFixed(4)} ($${t.value_usd.toFixed(2)})</span>
                                <span>${t.time}</span>
                            </div>
                        `;

                        if (isBuy) {
                            if (!topBuy || t.value_usd > topBuy.value_usd) topBuy = t;
                        } else {
                            if (!topSell || t.value_usd > topSell.value_usd) topSell = t;
                        }
                    }
                    tapeBox.innerHTML = html;

                    const nowSec = Math.floor(Date.now() / 1000);
                    const currentCandleTime = nowSec - (nowSec % 60);

                    liveTapeMarkers = [];

                    if (topBuy && topBuy.value_usd > 10.0) {
                        const isWhale = topBuy.value_usd >= 1000.0;
                        liveTapeMarkers.push({
                            time: currentCandleTime,
                            position: 'belowBar',
                            color: isWhale ? '#00e676' : '#10b981',
                            shape: isWhale ? 'circle' : 'arrowUp',
                            text: isWhale ? `🐋 WHALE BUY $${Math.round(topBuy.value_usd)}` : `BUY 🟢 $${Math.round(topBuy.value_usd)}`
                        });
                    }

                    if (topSell && topSell.value_usd > 10.0) {
                        const isWhale = topSell.value_usd >= 1000.0;
                        liveTapeMarkers.push({
                            time: currentCandleTime,
                            position: 'aboveBar',
                            color: isWhale ? '#ff1744' : '#ef4444',
                            shape: isWhale ? 'circle' : 'arrowDown',
                            text: isWhale ? `🐋 WHALE SELL $${Math.round(topSell.value_usd)}` : `SELL 🔴 $${Math.round(topSell.value_usd)}`
                        });
                    }

                    updateCombinedGraphMarkers();
                }
            } catch (err) {
                console.error("Trade tape fetch error:", err);
            }
        }

        async function fetchOrderBookPrediction(symbol) {
            try {
                const res = await fetch(`/api/orderbook/${symbol}`);
                const ob = await res.json();

                const predEl = document.getElementById('ob-prediction');
                const ratioValEl = document.getElementById('ob-ratio-val');
                const ratioSubEl = document.getElementById('ob-ratio-sub');

                predEl.innerText = ob.prediction;
                if (ob.signal === 'BULLISH_BUY_PRESSURE') {
                    predEl.style.color = '#10b981';
                    ratioValEl.style.color = '#10b981';
                    ratioSubEl.style.color = '#10b981';
                } else if (ob.signal === 'BEARISH_SELL_PRESSURE' || ob.signal === 'HEAVY_SELL_WALL') {
                    predEl.style.color = '#ef4444';
                    ratioValEl.style.color = '#ef4444';
                    ratioSubEl.style.color = '#ef4444';
                } else {
                    predEl.style.color = '#9ca3af';
                    ratioValEl.style.color = '#8b5cf6';
                    ratioSubEl.style.color = '#8b5cf6';
                }

                ratioValEl.innerText = ob.imbalance_ratio.toFixed(2);
                ratioSubEl.innerText = '(' + ob.signal.replace('_PRESSURE', '').replace('_', ' ') + ')';
            } catch (err) {
                console.error("OB fetch error:", err);
            }
        }

        function changeCoin(symbol, btn) {
            currentSymbol = symbol;
            document.getElementById('chart-symbol').innerText = symbol;

            document.querySelectorAll('.coin-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');

            loadCandles(symbol);
            fetchOrderBookPrediction(symbol);
            fetchWyckoffAnalysis(symbol);
            fetchLiveTrades(symbol);
        }

        async function fetchWorldNews() {
            try {
                const res = await fetch('/api/news');
                const data = await res.json();

                if (data && data.headlines && data.headlines.length > 0) {
                    const biasEl = document.getElementById('news-bias');
                    const meterEl = document.getElementById('news-meter');

                    biasEl.innerText = data.market_bias;
                    meterEl.innerText = `SENTIMENT METER: ${data.bull_pct}% BULLISH 🟢`;

                    if (data.market_bias.includes('BULLISH')) {
                        biasEl.style.color = '#10b981';
                        meterEl.style.color = '#10b981';
                    } else if (data.market_bias.includes('BEARISH')) {
                        biasEl.style.color = '#ef4444';
                        meterEl.style.color = '#ef4444';
                    } else {
                        biasEl.style.color = '#3b82f6';
                        meterEl.style.color = '#3b82f6';
                    }

                    const newsBox = document.getElementById('news-feed-box');
                    let html = '';
                    for (const n of data.headlines) {
                        const isBull = n.sentiment.includes('BULLISH');
                        const isBear = n.sentiment.includes('BEARISH');
                        const cls = isBull ? 'tape-buy' : (isBear ? 'tape-sell' : '');
                        const catTag = n.category ? `<span style="background: rgba(255,255,255,0.08); padding: 0.1rem 0.4rem; border-radius: 4px; margin-right: 0.4rem; font-size: 0.75rem; color: var(--accent-cyan);">${n.category}</span>` : '';
                        
                        html += `
                            <div class="tape-item ${cls}">
                                <span>${catTag}📰 <strong>[${n.source}]</strong> ${n.title}</span>
                                <span><span style="font-weight: 600;">${n.sentiment}</span> (${n.time})</span>
                            </div>
                        `;
                    }
                    newsBox.innerHTML = html;
                }
            } catch (err) {
                console.error("News fetch error:", err);
            }
        }

        function updatePrimeTradingWindow() {
            const now = new Date();
            const utcMinutes = now.getUTCHours() * 60 + now.getUTCMinutes();
            const istMinutes = (utcMinutes + 330) % 1440; // IST is UTC + 5:30 (330 mins)

            const windowValEl = document.getElementById('prime-window-val');
            const windowSubEl = document.getElementById('prime-window-sub');

            // 1. GOLDEN OVERLAP (London + US Wall Street Peak): 6:30 PM - 10:30 PM IST | 1:00 PM - 5:00 PM UTC | 8:00 AM - 12:00 PM EST
            if (istMinutes >= 1110 && istMinutes <= 1350) {
                windowValEl.innerText = "GOLDEN OVERLAP 🌟";
                windowValEl.style.color = "#10b981";
                windowSubEl.innerText = "Max Global Volatility (London + Wall Street Overlap: 6:30 PM - 10:30 PM IST | 1:00 PM - 5:00 PM UTC)";
                windowSubEl.style.color = "#10b981";
            }
            // 2. US NEW YORK SESSION (Late US): 10:30 PM - 2:30 AM IST | 5:00 PM - 9:00 PM UTC | 12:00 PM - 4:00 PM EST
            else if (istMinutes > 1350 || istMinutes < 150) {
                windowValEl.innerText = "US NY SESSION 🚀";
                windowValEl.style.color = "#3b82f6";
                windowSubEl.innerText = "Wall Street Afternoon Trading (10:30 PM - 2:30 AM IST | 5:00 PM - 9:00 PM UTC)";
                windowSubEl.style.color = "#3b82f6";
            }
            // 3. SYDNEY / PACIFIC SESSION: 2:30 AM - 5:30 AM IST | 9:00 PM - 12:00 AM UTC | 4:00 PM - 7:00 PM EST
            else if (istMinutes >= 150 && istMinutes < 330) {
                windowValEl.innerText = "PACIFIC / SYDNEY 🌊";
                windowValEl.style.color = "#c084fc";
                windowSubEl.innerText = "Sydney Open & Daily Close Reset (2:30 AM - 5:30 AM IST | 9:00 PM - 12:00 AM UTC)";
                windowSubEl.style.color = "#c084fc";
            }
            // 4. ASIAN SESSION (Tokyo / HK / Singapore): 5:30 AM - 1:30 PM IST | 12:00 AM - 8:00 AM UTC | 7:00 PM - 3:00 AM EST
            else if (istMinutes >= 330 && istMinutes < 810) {
                windowValEl.innerText = "ASIA / TOKYO ⛩️";
                windowValEl.style.color = "#eab308";
                windowSubEl.innerText = "Tokyo & Hong Kong Range Building (5:30 AM - 1:30 PM IST | 12:00 AM - 8:00 AM UTC)";
                windowSubEl.style.color = "#eab308";
            }
            // 5. LONDON / EUROPEAN SESSION: 1:30 PM - 6:30 PM IST | 8:00 AM - 1:00 PM UTC | 3:00 AM - 8:00 AM EST
            else if (istMinutes >= 810 && istMinutes < 1110) {
                windowValEl.innerText = "LONDON OPEN ⚡";
                windowValEl.style.color = "#06b6d4";
                windowSubEl.innerText = "European Breakout Volume (1:30 PM - 6:30 PM IST | 8:00 AM - 1:00 PM UTC)";
                windowSubEl.style.color = "#06b6d4";
            }
            else {
                windowValEl.innerText = "24/7 ACTIVE 🌐";
                windowValEl.style.color = "#34d399";
                windowSubEl.innerText = "Continuous Crypto Trading Window Active";
                windowSubEl.style.color = "#34d399";
            }
        }

        async function triggerLiveScan() {
            const btn = document.getElementById('btn-live-scan');
            if (btn) {
                btn.innerText = "🔄 SCANNING ALL 14 ALTCOINS NOW...";
                btn.style.opacity = "0.7";
                btn.disabled = true;
            }
            speakMessage("Initiating live market radar scan across all 14 altcoins for Wyckoff setups and orderbook imbalance.");
            await fetchRadarData();
            if (btn) {
                btn.innerText = "✅ SCAN COMPLETE (14 COINS) 📡";
                btn.style.opacity = "1";
                setTimeout(() => {
                    btn.innerText = "🔍 TRIGGER LIVE SCAN (14 ALTCOINS) 📡";
                    btn.disabled = false;
                }, 3000);
            }
        }

        async function fetchRadarData() {
            try {
                const res = await fetch('/api/radar');
                const data = await res.json();
                
                if (data && data.radar && data.radar.length > 0) {
                    const tbody = document.getElementById('radar-tbody');
                    let html = '';
                    for (const r of data.radar) {
                        const isBull = r.status === 'PRE_BREAKOUT_BULLISH';
                        const isBear = r.status === 'PRE_BREAKDOWN_BEARISH';
                        const isSqueeze = r.status === 'VOLATILITY_SQUEEZE';
                        
                        let badgeColor = '#9ca3af';
                        if (isBull) badgeColor = '#eab308';
                        else if (isBear) badgeColor = '#f97316';
                        else if (isSqueeze) badgeColor = '#06b6d4';
                        
                        let wyColor = '#9ca3af';
                        if (r.wyckoff_action.includes('BUY') || r.wyckoff_action.includes('LONG')) wyColor = '#10b981';
                        else if (r.wyckoff_action.includes('SELL') || r.wyckoff_action.includes('SHORT')) wyColor = '#ef4444';
                        
                        html += `
                            <tr style="border-bottom: 1px solid var(--border-card); transition: background 0.2s ease;">
                                <td style="padding: 0.75rem 1rem; font-weight: 700; color: var(--accent-cyan);">${r.symbol}</td>
                                <td style="padding: 0.75rem 1rem; font-weight: 700; color: ${badgeColor};">${r.prediction} <span style="font-size:0.75rem; color:var(--text-muted); font-weight:400;">${r.subtext}</span></td>
                                <td style="padding: 0.75rem 1rem; font-weight: 600;">${r.wyckoff_phase}</td>
                                <td style="padding: 0.75rem 1rem; font-family: 'JetBrains Mono', monospace;">${r.imbalance_ratio.toFixed(2)}x</td>
                                <td style="padding: 0.75rem 1rem;">
                                    <button class="coin-btn" onclick="changeCoin('${r.raw_symbol}', this)" style="padding: 0.2rem 0.6rem; font-size: 0.75rem;">SELECT 📈</button>
                                </td>
                            </tr>
                        `;
                    }
                    tbody.innerHTML = html;
                }
            } catch (err) {
                console.error("Radar fetch error:", err);
            }
        }

        async function fetchDashboardData() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();

                document.getElementById('equity-usd').innerText = '$' + data.equity.toFixed(2);
                const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                const eqSub = document.getElementById('equity-sub');
                if (eqSub) eqSub.innerText = `Synced at ${timeStr} (1m Live Sync ⚡)`;
                document.getElementById('pid').innerText = data.pid;

                const statusTitle = document.getElementById('agent-status-title');
                const statusSub = document.getElementById('agent-status-sub');
                const dot = document.getElementById('agent-dot');

                if (data.agent_running) {
                    statusTitle.innerText = "🤖 24/7 AUTO AGENT: ONLINE & RUNNING (PID " + data.pid + ")";
                    statusTitle.style.color = "#10b981";
                    statusSub.innerText = "Scanning all unblocked coins 24/7 for 10X safe Wyckoff trades...";
                    dot.style.backgroundColor = "#10b981";
                    dot.style.boxShadow = "0 0 10px #10b981";
                } else {
                    statusTitle.innerText = "🛑 24/7 AUTO AGENT: STOPPED";
                    statusTitle.style.color = "#ef4444";
                    statusSub.innerText = "Agent is offline. Click ▶️ START 24/7 AUTO AGENT to enable auto trading.";
                    dot.style.backgroundColor = "#ef4444";
                    dot.style.boxShadow = "0 0 10px #ef4444";
                }

                if (data.masked_key && !keysLoaded) {
                    document.getElementById('input-api-key').value = data.masked_key;
                    document.getElementById('input-api-secret').value = '••••••••••••••••••••••••';
                    keysLoaded = true;
                }

                if (data.logs && data.logs.length > 0) {
                    const logBox = document.getElementById('log-box');
                    logBox.innerHTML = data.logs.map(l => `<div style="margin-bottom: 0.3rem;">${l}</div>`).join('');
                    logBox.scrollTop = logBox.scrollHeight;

                    // Parse last 3 log entries for filled or rejected trade announcements
                    const recentLogs = data.logs.slice(-3);
                    for (const logLine of recentLogs) {
                        if (logLine.includes("Order Placed") || logLine.includes("SUCCESSFULLY EXECUTED") || logLine.includes("ORDER FILLED")) {
                            speakMessage("Alert! Order Filled! Futures trade executed successfully on CoinDCX.");
                        } else if (logLine.includes("rejected by Risk Auditor") || logLine.includes("Order Blocked") || logLine.includes("REGIME FILTER")) {
                            // Extract coin symbol if present
                            let coinMatch = logLine.match(/Trade for ([A-Z0-9_]+)/i) || logLine.match(/([A-Z0-9_]+USDT)/i);
                            let coinName = coinMatch ? coinMatch[1].replace('USDT','') : 'market setup';
                            speakMessage(`Order Rejected. ${coinName} trade blocked by Risk Auditor to preserve capital.`);
                        }
                    }
                }

                // Map active bot position to graph marker & high alert banner
                if (data.positions && data.positions[currentSymbol]) {
                    const pos = data.positions[currentSymbol];
                    const nowSec = Math.floor(Date.now() / 1000);
                    const currentCandleTime = nowSec - (nowSec % 60);

                    const isLong = (pos.side === 'LONG' || pos.side === 'BUY');
                    botEntryMarkers = [{
                        time: currentCandleTime,
                        position: isLong ? 'belowBar' : 'aboveBar',
                        color: isLong ? '#00ff66' : '#ff0055',
                        shape: 'circle',
                        text: `👑⚡ BOT ENTRY: ${isLong ? 'LONG 🟢' : 'SHORT 🔴'} @ $${pos.price || ''} (20X)`
                    }];

                    const banner = document.getElementById('high-alert-banner');
                    if (banner) {
                        banner.style.display = 'flex';
                        document.getElementById('high-alert-title').innerText = `🚨 HIGH ALERT: BOT ENTRY ON ${currentSymbol.replace('USDT','')}`;
                        document.getElementById('high-alert-sub').innerText = `PeopleTrade AI active position: ${pos.side} @ $${pos.price} (20x Leverage)`;
                        document.getElementById('high-alert-badge').innerText = `👑⚡ BOT ENTRY (20X)`;
                    }

                    if (!highAlertActive) {
                        speakMessage(`High Alert! PeopleTrade AI Bot Entry active on ${currentSymbol.replace('USDT','')}`);
                        highAlertActive = true;
                    }
                } else {
                    botEntryMarkers = [];
                    const banner = document.getElementById('high-alert-banner');
                    if (banner) banner.style.display = 'none';
                    highAlertActive = false;
                }

                // Fast Updates (1.5s): Status, Candles, Tape
                loadCandles(currentSymbol);
                fetchLiveTrades(currentSymbol);
                updatePrimeTradingWindow();

            } catch (err) {
                console.error("Dashboard fetch error:", err);
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            fetchDashboardData();
            fetchOrderBookPrediction(currentSymbol);
            fetchWyckoffAnalysis(currentSymbol);
            fetchRadarData();
            fetchWorldNews();

            // Try initializing chart immediately or retry after 500ms if script is deferred
            if (typeof LightweightCharts !== 'undefined') {
                initChart();
            } else {
                setTimeout(initChart, 500);
                setTimeout(initChart, 1500);
            }

            // 1. Fast stream (1.5s) for status & live chart
            setInterval(fetchDashboardData, 1500);

            // 2. Medium stream (4s) for orderbook depth & Wyckoff phase analysis
            setInterval(() => {
                fetchOrderBookPrediction(currentSymbol);
                fetchWyckoffAnalysis(currentSymbol);
            }, 4000);

            // 3. Slow background stream (10s) for 14-coin Radar Scanner
            setInterval(fetchRadarData, 10000);

            // 4. News stream (Every 5 Minutes / 300,000 ms per user directive)
            setInterval(fetchWorldNews, 300000);
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/news')
def news_api():
    try:
        data = get_global_crypto_news_feed()
        return jsonify(data)
    except Exception as e:
        return jsonify({"headlines": [], "market_bias": "NEUTRAL ⚖️", "sentiment_score": 0.0})

@app.route('/api/radar')
def radar_api():
    coins = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'SUIUSDT', 'DOGEUSDT', 'AVAXUSDT', 'NEARUSDT', 'PEPEUSDT', 'WIFUSDT', 'SEIUSDT', 'INJUSDT', 'XRPUSDT', 'ADAUSDT', 'LINKUSDT']
    
    def process_coin(coin):
        try:
            binance_sym = "1000PEPEUSDT" if coin == "PEPEUSDT" else coin
            url = f"https://api.binance.com/api/v3/klines?symbol={binance_sym}&interval=1m&limit=50"
            res = requests.get(url, timeout=2)
            if res.status_code == 200:
                raw = res.json()
                candles = [{'time': c[0]/1000, 'open': float(c[1]), 'high': float(c[2]), 'low': float(c[3]), 'close': float(c[4])} for c in raw]
                ob = analyze_order_book(coin)
                imb_ratio = ob.get('imbalance_ratio', 1.0)
                pb = predict_pre_breakout(candles, imb_ratio)
                wy = analyze_wyckoff_phase(coin)
                
                return {
                    "symbol": coin.replace('USDT',''),
                    "raw_symbol": coin,
                    "prediction": pb.get('prediction', 'STABLE'),
                    "status": pb.get('status', 'NEUTRAL'),
                    "subtext": pb.get('subtext', ''),
                    "wyckoff_phase": wy.get('phase', 'PHASE B'),
                    "wyckoff_action": wy.get('action', 'WAIT'),
                    "imbalance_ratio": imb_ratio
                }
        except Exception:
            pass
        return None

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=14) as executor:
        results = list(executor.map(process_coin, coins))
    
    radar_results = [r for r in results if r is not None]
    return jsonify({"radar": radar_results})

@app.route('/api/agent/start', methods=['POST'])
def start_agent():
    try:
        # Check if agent is already running
        out = subprocess.check_output("ps aux | grep coindcx_master_agent | grep -v grep || true", shell=True).decode()
        if out.strip():
            return jsonify({"status": "already_running", "message": "🤖 24/7 Auto Agent is ALREADY running!"})

        cmd = "nohup ./venv/bin/python -u coindcx_master_agent.py >> trading_bot.log 2>&1 &"
        subprocess.Popen(cmd, shell=True, cwd="/home/deepikamaruboina/Desktop/coindcxagent")
        return jsonify({"status": "started", "message": "🚀 24/7 AUTO AGENT STARTED SUCCESSFULLY!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/agent/stop', methods=['POST'])
def stop_agent():
    try:
        subprocess.run("pkill -9 -f coindcx_master_agent || true", shell=True)
        return jsonify({"status": "stopped", "message": "⏹️ 24/7 AUTO AGENT STOPPED CLEANLY!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/wyckoff/<symbol>')
def wyckoff_api(symbol):
    w_data = analyze_wyckoff_phase(symbol)
    return jsonify(w_data)

from catalyst_engine import get_market_regime

def check_liquidity_and_spread(symbol):
    clean_sym = symbol.replace("B-", "").replace("_USDT", "").replace("USDT", "")
    binance_sym = "1000PEPEUSDT" if clean_sym == "PEPE" else clean_sym + "USDT"
    try:
        res = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_sym}", timeout=3)
        if res.status_code == 200:
            ticker = res.json()
            quote_vol = float(ticker.get("quoteVolume", 0) or 0)
            bid = float(ticker.get("bidPrice", 0) or 0)
            ask = float(ticker.get("askPrice", 0) or 0)
            mid = (bid + ask) / 2.0 if (bid and ask) else 0

            min_vol = 5_000_000   # $5M USDT 24h volume threshold
            max_spread_bps = 15   # 0.15% max bid-ask spread

            if mid == 0:
                return True, True

            spread_bps = ((ask - bid) / mid) * 10_000
            liq_ok = quote_vol >= min_vol
            spread_ok = spread_bps <= max_spread_bps
            return liq_ok, spread_ok
    except Exception:
        pass
    return True, True

def get_chart_bias(symbol):
    clean_sym = symbol.replace("B-", "").replace("_USDT", "").replace("USDT", "")
    binance_sym = "1000PEPEUSDT" if clean_sym == "PEPE" else clean_sym + "USDT"
    try:
        res = requests.get(f"https://api.binance.com/api/v3/klines?symbol={binance_sym}&interval=1m&limit=30", timeout=3)
        if res.status_code == 200:
            klines = res.json()
            closes = [float(k[4]) for k in klines]
            if len(closes) >= 21:
                ema9 = sum(closes[-9:]) / 9.0
                ema21 = sum(closes[-21:]) / 21.0
                curr = closes[-1]
                if curr >= ema9 and ema9 >= ema21:
                    return "bullish"
                elif curr <= ema9 and ema9 <= ema21:
                    return "bearish"
                else:
                    return "neutral"
    except Exception:
        pass
    return "bullish"

@app.route('/api/high_win_signal/<symbol>')
def high_win_signal_api(symbol):
    # 1) Wyckoff / market cycle
    wyckoff = analyze_wyckoff_phase(symbol)
    confluence_pct = wyckoff.get("confidence_pct", 0.0)
    action = wyckoff.get("action", "HOLD")
    phase = wyckoff.get("phase", "UNKNOWN")

    # 2) Order book imbalance
    ob = analyze_order_book(symbol)
    imb = ob.get("imbalance_ratio", 1.0)

    # 3) Additional strict filters
    liq_ok, spread_ok = check_liquidity_and_spread(symbol)
    regime = get_market_regime()  # "risk_on", "risk_off", "neutral"
    bias = get_chart_bias(symbol)  # "bullish", "bearish", "neutral"

    # --- Strict A+ setup rules ---
    min_conf_pass = confluence_pct >= 80.0
    action_pass = action in ["BUY", "SELL"]

    ob_pass = (
        (action == "BUY" and imb >= 1.20) or
        (action == "SELL" and imb <= 0.83)
    )

    liq_pass = liq_ok and spread_ok

    regime_pass = (
        (regime == "risk_on" and action == "BUY") or
        (regime == "risk_off" and action == "SELL") or
        (regime == "risk_on" and action == "SELL" and confluence_pct >= 90.0) or
        (regime == "risk_off" and action == "BUY" and confluence_pct >= 90.0) or
        (regime == "neutral")
    )

    bias_pass = (
        (bias == "bullish" and action == "BUY") or
        (bias == "bearish" and action == "SELL") or
        (bias == "neutral" and confluence_pct >= 85.0)
    )

    trade_allowed = (
        min_conf_pass
        and action_pass
        and ob_pass
        and liq_pass
        and regime_pass
        and bias_pass
    )

    return jsonify({
        "symbol": symbol.upper(),
        "trade_allowed": trade_allowed,
        "action": action if trade_allowed else "WAIT",
        "confluence_pct": confluence_pct,
        "market_cycle_phase": phase,
        "orderbook_imbalance": imb,
        "liquidity_ok": liq_ok,
        "spread_ok": spread_ok,
        "regime": regime,
        "chart_bias": bias,
        "filters": {
            "min_confluence_80pct": min_conf_pass,
            "orderbook_pressure_aligned": ob_pass,
            "valid_action_signal": action_pass,
            "liquidity_spread_ok": liq_pass,
            "regime_aligned": regime_pass,
            "bias_aligned": bias_pass,
        }
    })

@app.route('/api/agent/chat', methods=['POST'])
def agent_chat_api():
    try:
        data = request.get_json() or {}
        msg = data.get('message', '').strip().lower()
        symbol = data.get('symbol', 'SUIUSDT').upper()

        if not msg:
            return jsonify({"status": "success", "response": "🤖 PeopleTrade AI Agent: How can I assist your trading strategy today?"})

        if "win rate" in msg or "performance" in msg or "stats" in msg:
            resp = "🎯 **Institutional Gate Win-Rate Status**:\n- High-Win Gate Confluence Requirement: **80%++**\n- Core Altcoin Focus: Pure High-Vol Altcoins (BTC/ETH Excluded)\n- Targeted R:R Ratio: 1:3 (TP1 +15%, TP2 +30%, TP3 +50% ROE)\n- Risk Auditor Gate: Active 24/7."

        elif "balance" in msg or "wallet" in msg or "equity" in msg or "funds" in msg:
            bal_data = client.get_account_balances()
            total_eq = bal_data.get("total_equity", 0.0)
            avail_margin = bal_data.get("available_margin", 0.0)
            resp = f"💰 **Live Wallet Equity Summary**:\n- Total Equity: **${total_eq:.2f} USDT**\n- Available Margin: **${avail_margin:.2f} USDT**\n- 1-Min Auto Sync: Active 🟢"

        elif "wyckoff" in msg or "phase" in msg or "structure" in msg or "analyze" in msg:
            w = analyze_wyckoff_phase(symbol)
            resp = f"🏛️ **Wyckoff Structural Analysis for {symbol}**:\n- Market Phase: **{w.get('phase')}**\n- Strategic Action: **{w.get('action')}**\n- Confluence Score: **{w.get('confidence_pct')}%**\n- Smart Money Activity: {w.get('event')}"

        elif "gate" in msg or "high win" in msg or "signal" in msg:
            res = high_win_signal_api(symbol).get_json() or {}
            allowed = "ALLOWED 🟢" if res.get("trade_allowed") else "REJECTED 🔴"
            resp = f"🎯 **High-Win Signal Gate Check [{symbol}]**:\n- Trade Status: **{allowed}**\n- Wyckoff Confluence: {res.get('confluence_pct')}%\n- Order Book Imbalance: {res.get('orderbook_imbalance')}x\n- Market Regime: {res.get('regime')}\n- Chart Bias: {res.get('chart_bias')}"

        elif "news" in msg or "sentiment" in msg or "bias" in msg:
            news = get_global_crypto_news_feed()
            resp = f"📰 **Live Global Market Sentiment**:\n- Market Bias: **{news.get('market_bias')}**\n- Bullish Ratio: **{news.get('bull_pct')}%**\n- Live Headlines Tracked: {news.get('total_count')} items"

        elif "start" in msg:
            start_res = start_agent_api().get_json()
            resp = f"🚀 **Master Agent Command**: {start_res.get('message')}"

        elif "stop" in msg:
            stop_res = stop_agent_api().get_json()
            resp = f"⏹️ **Master Agent Command**: {stop_res.get('message')}"

        else:
            w = analyze_wyckoff_phase(symbol)
            resp = f"🤖 **PeopleTrade AI Agent**: I am actively monitoring **{symbol}**.\n- Current Wyckoff Structure: **{w.get('phase')}** ({w.get('action')})\n- Confluence Confidence: **{w.get('confidence_pct')}%**\n- Altcoin Strategy: Pure Altcoins (BTC/ETH Blocked)\n\nType *'wallet'*, *'wyckoff'*, *'gate'*, *'news'*, or *'start'* for specific controls!"

        return jsonify({"status": "success", "response": resp})
    except Exception as e:
        return jsonify({"status": "error", "response": f"⚠️ Agent Error: {str(e)}"}), 500

@app.route('/api/save_keys', methods=['POST'])
def save_keys():
    try:
        data = request.get_json() or {}
        new_key = data.get('api_key', '').strip()
        new_secret = data.get('api_secret', '').strip()

        if not new_key or not new_secret or '••••' in new_key:
            return jsonify({"status": "error", "message": "Please enter a valid unmasked API Key and Secret"}), 400

        env_path = "/home/deepikamaruboina/Desktop/coindcxagent/.env"
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()

        new_lines = []
        key_found = False
        secret_found = False

        for line in lines:
            if line.startswith("COINDCX_API_KEY="):
                new_lines.append(f"COINDCX_API_KEY={new_key}\n")
                key_found = True
            elif line.startswith("COINDCX_API_SECRET="):
                new_lines.append(f"COINDCX_API_SECRET={new_secret}\n")
                secret_found = True
            else:
                new_lines.append(line)

        if not key_found:
            new_lines.append(f"COINDCX_API_KEY={new_key}\n")
        if not secret_found:
            new_lines.append(f"COINDCX_API_SECRET={new_secret}\n")

        with open(env_path, 'w') as f:
            f.writelines(new_lines)

        os.environ["COINDCX_API_KEY"] = new_key
        os.environ["COINDCX_API_SECRET"] = new_secret

        global client
        client = CoinDCXClient()

        masked = new_key[:6] + "..." + new_key[-4:] if len(new_key) > 10 else "••••••••"

        return jsonify({
            "status": "success",
            "message": "✅ API Keys connected! Click '🚀 START AGENT' to launch live trading.",
            "masked_key": masked
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/trades/<symbol>')
def live_trades(symbol):
    clean_sym = symbol.upper().replace("B-", "").replace("_USDT", "").replace("USDT", "") + "USDT"
    try:
        url = f"https://api.binance.com/api/v3/trades?symbol={clean_sym}&limit=25"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            raw = res.json()
            formatted = []
            for t in reversed(raw):
                qty = float(t.get("qty", 0))
                price = float(t.get("price", 0))
                val_usd = qty * price
                is_buyer_maker = t.get("isBuyerMaker", False)
                is_buy = not is_buyer_maker
                ts = time.strftime('%H:%M:%S', time.localtime(t.get("time", 0) / 1000))

                formatted.append({
                    "qty": round(qty, 2),
                    "price": price,
                    "value_usd": round(val_usd, 2),
                    "is_buy": is_buy,
                    "time": ts
                })
            return jsonify(formatted)
    except Exception as e:
        print("Trades fetch error:", e)
    return jsonify([])

def analyze_order_book(symbol: str) -> dict:
    clean_sym = symbol.upper().replace("B-", "").replace("_USDT", "").replace("USDT", "") + "USDT"
    try:
        url = f"https://api.binance.com/api/v3/depth?symbol={clean_sym}&limit=100"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            bids = sum(float(b[1]) * float(b[0]) for b in data.get("bids", []))
            asks = sum(float(a[1]) * float(a[0]) for a in data.get("asks", []))
            ratio = bids / max(0.0001, asks)

            if ratio >= 1.4:
                sig = "BULLISH_BUY_PRESSURE"
                pred = "BULLISH BUY WALL 🟢"
            elif ratio <= 0.7:
                sig = "BEARISH_SELL_PRESSURE"
                pred = "BEARISH SELL WALL 🔴"
            else:
                sig = "BALANCED"
                pred = "BALANCED LIQUIDITY ⚖️"

            return {"symbol": clean_sym, "imbalance_ratio": round(ratio, 2), "signal": sig, "prediction": pred}
    except Exception:
        pass
    return {"symbol": clean_sym, "imbalance_ratio": 1.0, "signal": "BALANCED", "prediction": "BALANCED LIQUIDITY ⚖️"}

@app.route('/api/orderbook/<symbol>')
def orderbook_api(symbol):
    ob_data = analyze_order_book(symbol)
    return jsonify(ob_data)

@app.route('/api/klines/<symbol>')
def klines(symbol):
    try:
        clean_sym = symbol.upper().replace("B-", "").replace("_USDT", "").replace("USDT", "")
        clean_sym = f"{clean_sym}USDT"

        raw = None
        # Primary Source: Binance Spot API
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={clean_sym}&interval=1m&limit=100"
            res = requests.get(url, timeout=3)
            if res.status_code == 200 and isinstance(res.json(), list) and len(res.json()) > 0:
                raw = res.json()
        except Exception:
            pass

        # Secondary Fallback: Binance Futures API
        if not raw:
            try:
                fsym = "1000PEPEUSDT" if clean_sym == "PEPEUSDT" else clean_sym
                url = f"https://fapi.binance.com/fapi/v1/klines?symbol={fsym}&interval=1m&limit=100"
                res = requests.get(url, timeout=3)
                if res.status_code == 200 and isinstance(res.json(), list) and len(res.json()) > 0:
                    raw = res.json()
            except Exception:
                pass

        if raw:
            candles = []
            ema = []
            markers = []
            closes = []

            for i, c in enumerate(raw):
                ts = int(c[0] / 1000)
                op = float(c[1])
                hi = float(c[2])
                lo = float(c[3])
                cl = float(c[4])
                candles.append({"time": ts, "open": op, "high": hi, "low": lo, "close": cl})
                closes.append(cl)

                if len(closes) >= 20:
                    k = 2 / 21
                    if len(ema) == 0:
                        val = sum(closes[-20:]) / 20
                    else:
                        val = (cl * k) + (ema[-1]["value"] * (1 - k))
                    ema.append({"time": ts, "value": val})

                    if i >= 10:
                        r_high = max(x["high"] for x in candles[i-10:i])
                        r_low = min(x["low"] for x in candles[i-10:i])
                        c_range = max(0.00001, hi - lo)
                        lower_wick = (min(op, cl) - lo) / c_range
                        upper_wick = (hi - max(op, cl)) / c_range

                        # 🟢 BUY / ENTER LONG SIGNAL (Wyckoff Spring Recovery or Bullish SOS Breakout)
                        if (lo < r_low and cl >= r_low and cl > op) or (cl > r_high and cl > op and (cl - op) / op > 0.0008):
                            markers.append({
                                "time": ts,
                                "position": "belowBar",
                                "color": "#10b981",
                                "shape": "arrowUp",
                                "text": "FUTURES BUY / LONG 🟢"
                            })
                        # 🔴 FUTURES SELL / SHORT SIGNAL (Wyckoff UTAD Rejection or Bearish SOW Breakdown)
                        elif (hi > r_high and cl <= r_high and cl < op) or (cl < r_low and op > cl and (op - cl) / op > 0.0008):
                            markers.append({
                                "time": ts,
                                "position": "aboveBar",
                                "color": "#ef4444",
                                "shape": "arrowDown",
                                "text": "FUTURES SELL / SHORT 🔴 (T1/T2/T3 📉)"
                            })
                        # 🪤 BEAR TRAP (Liquidity Sweep Reversal)
                        elif lower_wick >= 0.45:
                            markers.append({
                                "time": ts,
                                "position": "belowBar",
                                "color": "#eab308",
                                "shape": "circle",
                                "text": "BEAR TRAP 🪤"
                            })
                        # 🪤 BULL TRAP (Upthrust Short Entry)
                        elif upper_wick >= 0.45:
                            markers.append({
                                "time": ts,
                                "position": "aboveBar",
                                "color": "#f97316",
                                "shape": "circle",
                                "text": "BULL TRAP 🪤 (SHORT 🔴)"
                            })

            ob = analyze_order_book(symbol)
            imb_ratio = ob.get("imbalance_ratio", 1.0) if isinstance(ob, dict) else 1.0
            pre_breakout_res = predict_pre_breakout(candles, imb_ratio) or {"status": "NEUTRAL", "prediction": "NO PRE-BREAKOUT ⚖️", "subtext": "(STABLE VOLATILITY)"}

            if isinstance(pre_breakout_res, dict) and pre_breakout_res.get("status") == "PRE_BREAKOUT_BULLISH" and len(candles) > 0:
                markers.append({
                    "time": candles[-1]["time"],
                    "position": "belowBar",
                    "color": "#eab308",
                    "shape": "arrowUp",
                    "text": "PRE-BREAKOUT ⚡"
                })
            elif pre_breakout_res["status"] == "PRE_BREAKDOWN_BEARISH" and len(candles) > 0:
                markers.append({
                    "time": candles[-1]["time"],
                    "position": "aboveBar",
                    "color": "#f97316",
                    "shape": "arrowDown",
                    "text": "PRE-BREAKDOWN ⚠️"
                })

            clean_markers = {}
            for m in markers:
                clean_markers[m["time"]] = m
            sorted_markers = sorted(clean_markers.values(), key=lambda x: x["time"])

            return jsonify({
                "candles": candles,
                "ema": ema,
                "markers": sorted_markers[-10:],
                "pre_breakout": pre_breakout_res
            })
    except Exception as e:
        print("Klines fetch error:", e)
    return jsonify({"candles": [], "ema": [], "markers": [], "pre_breakout": {"status": "NEUTRAL", "prediction": "NO PRE-BREAKOUT ⚖️", "subtext": "(STABLE VOLATILITY)"}})

@app.route('/api/status')
def status():
    try:
        bal = client.get_account_balances()
        eq = bal.get("total_equity", 20.0)
    except Exception:
        eq = 20.0

    try:
        pos = client.get_active_futures_positions()
    except Exception:
        pos = {}

    logs = []
    if os.path.exists("trading_bot.log"):
        with open("trading_bot.log", "r") as f:
            lines = f.readlines()
            logs = [l.strip() for l in lines[-15:]]

    pid_str = "OFFLINE"
    agent_running = False
    try:
        out = subprocess.check_output("ps aux | grep coindcx_master_agent | grep -v grep || true", shell=True).decode()
        if out.strip():
            pid_str = out.split()[1]
            agent_running = True
    except Exception:
        pass

    raw_key = os.getenv("COINDCX_API_KEY", "")
    masked = raw_key[:6] + "..." + raw_key[-4:] if len(raw_key) > 10 else "••••••••"

    return jsonify({
        "equity": eq,
        "positions": pos,
        "pid": pid_str,
        "agent_running": agent_running,
        "masked_key": masked,
        "logs": logs
    })

if __name__ == "__main__":
    print("🚀 DASHBOARD SERVER WITH 24/7 AUTO AGENT CONTROLS LAUNCHING ON http://localhost:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)
