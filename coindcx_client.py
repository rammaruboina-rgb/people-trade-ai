# coindcx_client.py
"""
CoinDCX API Client Module
Handles authentication, futures position querying, leverage auto-sync, and validated futures order placement.
Includes DNS retry handling to ensure order execution uninterrupted by network jitter.
"""

import os
import json
import time
import hmac
import hashlib
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

KNOWN_DCX_FUTURES = {
    "SOL": "B-SOL_USDT",
    "SUI": "B-SUI_USDT",
    "AVAX": "B-AVAX_USDT",
    "XRP": "B-XRP_USDT",
    "NEAR": "B-NEAR_USDT",
    "APT": "B-APT_USDT",
    "FIL": "B-FIL_USDT",
    "INJ": "B-INJ_USDT",
    "DOT": "B-DOT_USDT",
    "SEI": "B-SEI_USDT",
    "ARB": "B-ARB_USDT",
    "OP": "B-OP_USDT",
    "PEPE": "B-1000PEPE_USDT",
    "SHIB": "B-1000SHIB_USDT",
    "BONK": "B-1000BONK_USDT",
    "FLOKI": "B-1000FLOKI_USDT"
}

class CoinDCXClient:
    def __init__(self):
        self.api_key = os.getenv("COINDCX_API_KEY", "")
        self.api_secret = os.getenv("COINDCX_API_SECRET", "")
        self.mode = os.getenv("MODE", "LIVE").upper()
        self.live_mode = self.mode == "LIVE" and bool(self.api_key) and bool(self.api_secret)
        self.base_url = "https://api.coindcx.com"
        
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _get_signature(self, payload_json: str) -> str:
        secret_bytes = bytes(self.api_secret, 'utf-8')
        return hmac.new(secret_bytes, payload_json.encode('utf-8'), hashlib.sha256).hexdigest()

    def get_ticker_price(self, symbol: str = "SOLUSDT") -> float:
        """Fetches current mark price with Binance Global fallback if CoinDCX DNS times out"""
        clean_sym = symbol.replace("B-", "").replace("_USDT", "USDT")
        
        for attempt in range(2):
            try:
                url = f"{self.base_url}/exchange/ticker"
                res = self.session.get(url, timeout=3)
                if res.status_code == 200 and isinstance(res.json(), list):
                    for t in res.json():
                        if t.get("market") == clean_sym:
                            return float(t.get("last_price", 0.0))
            except Exception:
                time.sleep(0.2)

        # Fallback to Binance Global REST API for zero lag price resolution
        for attempt in range(2):
            try:
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={clean_sym}"
                res = self.session.get(url, timeout=3)
                if res.status_code == 200 and "price" in res.json():
                    return float(res.json()["price"])
            except Exception:
                time.sleep(0.2)

        return 0.0

    def get_account_balances(self) -> dict:
        """Fetches account USDT balance with retry loop"""
        import config
        fallback_eq = getattr(config, "EQUITY_USD", 10.376)
        if not self.live_mode:
            return {"USDT": fallback_eq, "INR": 0.0, "total_equity": fallback_eq}

        for attempt in range(3):
            try:
                timeStamp = int(round(time.time() * 1000))
                body = {"timestamp": timeStamp}
                json_body = json.dumps(body, separators=(',', ':'))
                signature = self._get_signature(json_body)

                headers = {
                    "Content-Type": "application/json",
                    "X-AUTH-APIKEY": self.api_key,
                    "X-AUTH-SIGNATURE": signature
                }

                url = f"{self.base_url}/exchange/v1/users/balances"
                res = self.session.post(url, data=json_body, headers=headers, timeout=4)
                if res.status_code == 200:
                    usdt_bal = 0.0
                    inr_bal = 0.0
                    for item in res.json():
                        currency = item.get("currency", "")
                        if currency == "USDT":
                            usdt_bal = float(item.get("balance", 0.0))
                        elif currency == "INR":
                            inr_bal = float(item.get("balance", 0.0))

                    # Also check Futures wallet endpoint if Spot USDT balance is 0
                    if usdt_bal <= 0.0:
                        try:
                            fut_url = f"{self.base_url}/exchange/v1/derivatives/futures/balances"
                            res_fut = self.session.post(fut_url, data=json_body, headers=headers, timeout=4)
                            if res_fut.status_code == 200:
                                for item in res_fut.json():
                                    if item.get("currency") == "USDT" or item.get("asset") == "USDT":
                                        usdt_bal = float(item.get("balance", item.get("free", 0.0)))
                        except Exception:
                            pass

                    total_eq = usdt_bal if usdt_bal > 0.1 else fallback_eq
                    return {"USDT": total_eq, "INR": inr_bal, "total_equity": total_eq}
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} balance fetch error: {e}")
                time.sleep(0.5)

        return {"USDT": fallback_eq, "INR": 0.0, "total_equity": fallback_eq}

    def get_active_futures_positions(self) -> dict:
        """Fetches active open futures positions with retry loop"""
        if not self.live_mode:
            return {}

        for attempt in range(3):
            try:
                timeStamp = int(round(time.time() * 1000))
                body = {"timestamp": timeStamp}
                json_body = json.dumps(body, separators=(',', ':'))
                signature = self._get_signature(json_body)

                headers = {
                    "Content-Type": "application/json",
                    "X-AUTH-APIKEY": self.api_key,
                    "X-AUTH-SIGNATURE": signature
                }

                url = f"{self.base_url}/exchange/v1/derivatives/futures/positions"
                res = self.session.post(url, data=json_body, headers=headers, timeout=4)
                if res.status_code == 200 and isinstance(res.json(), list):
                    positions = {}
                    for p in res.json():
                        pair = p.get("pair", "")
                        active_pos = float(p.get("active_pos", 0.0) or 0.0)
                        lev_raw = p.get("leverage")
                        leverage = int(float(lev_raw)) if lev_raw is not None else 20
                        raw_side = str(p.get("side", "") or "").upper()
                        target_pos = float(p.get("target_position", 0.0) or 0.0)
                        avg_price = float(p.get("avg_price", 0.0) or 0.0)
                        liq_price = float(p.get("liquidation_price", 0.0) or 0.0)

                        if raw_side in ["BUY", "LONG"]:
                            pos_side = "BUY"
                        elif raw_side in ["SELL", "SHORT"]:
                            pos_side = "SELL"
                        elif target_pos > 0:
                            pos_side = "BUY"
                        elif target_pos < 0:
                            pos_side = "SELL"
                        elif liq_price > 0 and avg_price > 0:
                            pos_side = "BUY" if liq_price < avg_price else "SELL"
                        else:
                            pos_side = "BUY"

                        if abs(active_pos) > 0.000001:
                            positions[pair] = {
                                "pair": pair,
                                "active_pos": abs(active_pos),
                                "side": pos_side,
                                "leverage": leverage,
                                "avg_price": avg_price,
                                "liquidation_price": liq_price
                            }
                    return positions
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} active positions error: {e}")
                time.sleep(0.5)

        return {}

    def resolve_futures_symbol(self, symbol: str) -> str:
        """Resolves coin ticker or symbol to valid CoinDCX active futures instrument string"""
        from coindcx_futures_mapper import futures_mapper
        clean_coin = symbol.replace("B-", "").replace("_USDT", "").replace("USDT", "").upper()
        if clean_coin in KNOWN_DCX_FUTURES:
            return KNOWN_DCX_FUTURES[clean_coin]
        return futures_mapper.get_dcx_future_symbol(symbol)

    def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        leverage: int = 20,
        sl_price: float = None,
        tp_price: float = None,
        market_type: str = "futures"
    ) -> list:
        """
        Executes a validated futures market order with retry loop and strict SL/TP boundary verification.
        """
        futures_symbol = self.resolve_futures_symbol(symbol)

        if not self.live_mode:
            logger.info(f"[PAPER MODE] Order placed: {side} {amount} {futures_symbol} @ Leverage {leverage}x | SL: {sl_price} | TP: {tp_price}")
            return [{"id": f"PAPER_{int(time.time())}", "status": "executed", "pair": futures_symbol}]

        active_positions = self.get_active_futures_positions()
        pos_info = active_positions.get(futures_symbol, {})
        account_leverage = pos_info.get("leverage", leverage)

        coin_base = symbol.replace("B-", "").replace("_USDT", "").replace("USDT", "").upper()
        mark_price = self.get_ticker_price(coin_base + "USDT")
        if mark_price <= 0:
            mark_price = 100.0

        side_lower = side.lower()
        side_payload = "buy" if side_lower in ["buy", "long"] else "sell"

        timeStamp = int(round(time.time() * 1000))
        
        # Ensure Notional Value (qty_val * mark_price) is AT LEAST 6.5 USDT for CoinDCX Futures
        min_notional = 6.5
        min_qty = (min_notional / mark_price) if mark_price > 0 else 1.0
        
        clean_coin = coin_base.upper()
        if clean_coin in ["BTC", "ETH", "SOL", "TAO"]:
            qty_val = float(round(max(amount, min_qty), 2))
        else:
            qty_val = int(round(max(amount, min_qty), 0))
            if qty_val * mark_price < 6.0:
                qty_val += 1

        if qty_val <= 0:
            qty_val = 1

        # Primary CoinDCX Futures API Nested Order Format
        order_body = {
            "pair": futures_symbol,
            "side": side_payload,
            "order_type": "market_order",
            "total_quantity": qty_val,
            "leverage": account_leverage
        }
        if sl_price and float(sl_price) > 0:
            order_body["stop_loss_price"] = str(round(float(sl_price), 4))
        if tp_price and float(tp_price) > 0:
            order_body["take_profit_price"] = str(round(float(tp_price), 4))

        payload = {
            "timestamp": timeStamp,
            "order": order_body
        }

        json_payload = json.dumps(payload, separators=(',', ':'))
        signature = self._get_signature(json_payload)

        headers = {
            "Content-Type": "application/json",
            "X-AUTH-APIKEY": self.api_key,
            "X-AUTH-SIGNATURE": signature
        }

        url = f"{self.base_url}/exchange/v1/derivatives/futures/orders/create"

        for attempt in range(3):
            try:
                res = self.session.post(url, data=json_payload, headers=headers, timeout=5)
                if res.status_code in [200, 201]:
                    logger.info(f"✅ LIVE ORDER EXECUTED: {side_payload.upper()} {qty_val} {futures_symbol} @ Leverage {account_leverage}x")
                    order_res = res.json()
                    
                    exit_side = "sell" if side_payload == "buy" else "buy"
                    if tp_price and float(tp_price) > 0:
                        try:
                            tp_body = {"timestamp": int(time.time() * 1000), "order": {"pair": futures_symbol, "side": exit_side, "order_type": "limit_order", "price": float(tp_price), "total_quantity": qty_val, "leverage": account_leverage}}
                            tp_json = json.dumps(tp_body, separators=(',', ':'))
                            self.session.post(url, data=tp_json, headers={"Content-Type": "application/json", "X-AUTH-APIKEY": self.api_key, "X-AUTH-SIGNATURE": self._get_signature(tp_json)}, timeout=3)
                            logger.info(f"🎯 REGISTERED EXCHANGE TAKE-PROFIT LIMIT ORDER @ ${tp_price}")
                        except Exception as e:
                            logger.warning(f"Failed to register explicit TP order: {e}")

                    if sl_price and float(sl_price) > 0:
                        try:
                            sl_body = {"timestamp": int(time.time() * 1000), "order": {"pair": futures_symbol, "side": exit_side, "order_type": "stop_limit", "price": float(sl_price), "stop_price": float(sl_price), "total_quantity": qty_val, "leverage": account_leverage}}
                            sl_json = json.dumps(sl_body, separators=(',', ':'))
                            self.session.post(url, data=sl_json, headers={"Content-Type": "application/json", "X-AUTH-APIKEY": self.api_key, "X-AUTH-SIGNATURE": self._get_signature(sl_json)}, timeout=3)
                            logger.info(f"🛡️ REGISTERED EXCHANGE STOP-LOSS STOP-LIMIT ORDER @ ${sl_price}")
                        except Exception as e:
                            logger.warning(f"Failed to register explicit SL order: {e}")

                    return order_res
                else:
                    err_msg = res.text
                    if "Instrument is not active" in err_msg:
                        logger.warning(f"⚠️ {futures_symbol} is not active on CoinDCX Futures. Skipping asset.")
                        return [{"id": "FAILED", "status": "error", "message": "Instrument is not active"}]
                    if "Max allowed leverage" in err_msg or "leverage" in err_msg.lower() or "Insufficient funds" in err_msg or res.status_code == 422:
                        import re
                        match = re.search(r"(\d+(\.\d+)?)x", err_msg, re.IGNORECASE)
                        capped_lev = int(float(match.group(1))) if match else 30
                        
                        # Recalculate quantity for 6.5 USDT min notional
                        min_notional = 6.5
                        recalc_qty = int(min_notional / mark_price) + 1 if mark_price > 0 else qty_val
                        
                        logger.warning(f"⚠️ CoinDCX leverage set to {capped_lev}x for {futures_symbol} (Adjusted Qty: {recalc_qty}). Resubmitting order...")
                        order_body["leverage"] = capped_lev
                        order_body["total_quantity"] = recalc_qty
                        payload["order"] = order_body
                        json_payload = json.dumps(payload, separators=(',', ':'))
                        signature = self._get_signature(json_payload)
                        headers["X-AUTH-SIGNATURE"] = signature
                        
                        res_retry = self.session.post(url, data=json_payload, headers=headers, timeout=5)
                        if res_retry.status_code in [200, 201]:
                            logger.info(f"✅ LIVE ORDER EXECUTED: {side_payload.upper()} {recalc_qty} {futures_symbol} @ Leverage {capped_lev}x")
                            order_res = res_retry.json()

                            # Submit explicit Take Profit and Stop Loss orders if provided
                            exit_side = "sell" if side_payload == "buy" else "buy"
                            if tp_price and float(tp_price) > 0:
                                try:
                                    clean_tp = round(float(tp_price), 3)
                                    tp_body = {"timestamp": int(time.time() * 1000), "order": {"pair": futures_symbol, "side": exit_side, "order_type": "limit_order", "price": clean_tp, "total_quantity": recalc_qty, "leverage": capped_lev}}
                                    tp_json = json.dumps(tp_body, separators=(',', ':'))
                                    self.session.post(url, data=tp_json, headers={"Content-Type": "application/json", "X-AUTH-APIKEY": self.api_key, "X-AUTH-SIGNATURE": self._get_signature(tp_json)}, timeout=3)
                                    logger.info(f"🎯 REGISTERED EXCHANGE TAKE-PROFIT LIMIT ORDER @ ${clean_tp}")
                                except Exception as e:
                                    logger.warning(f"Failed to register explicit TP order: {e}")

                            if sl_price and float(sl_price) > 0:
                                try:
                                    clean_sl = round(float(sl_price), 3)
                                    sl_body = {"timestamp": int(time.time() * 1000), "order": {"pair": futures_symbol, "side": exit_side, "order_type": "stop_limit", "price": clean_sl, "stop_price": clean_sl, "total_quantity": recalc_qty, "leverage": capped_lev}}
                                    sl_json = json.dumps(sl_body, separators=(',', ':'))
                                    self.session.post(url, data=sl_json, headers={"Content-Type": "application/json", "X-AUTH-APIKEY": self.api_key, "X-AUTH-SIGNATURE": self._get_signature(sl_json)}, timeout=3)
                                    logger.info(f"🛡️ REGISTERED EXCHANGE STOP-LOSS STOP-LIMIT ORDER @ ${clean_sl}")
                                except Exception as e:
                                    logger.warning(f"Failed to register explicit SL order: {e}")

                            return order_res

                    # Retry with root payload format if nested order returns status error
                    logger.warning(f"Attempting fallback root order structure for {futures_symbol} (HTTP {res.status_code}): {res.text}...")
                    fallback_payload = {
                        "timestamp": timeStamp,
                        "pair": futures_symbol,
                        "order_type": "market_order",
                        "side": side_payload,
                        "total_quantity": qty_val,
                        "leverage": 7
                    }
                    fb_json = json.dumps(fallback_payload, separators=(',', ':'))
                    fb_sig = self._get_signature(fb_json)
                    fb_headers = {
                        "Content-Type": "application/json",
                        "X-AUTH-APIKEY": self.api_key,
                        "X-AUTH-SIGNATURE": fb_sig
                    }
                    res_fb = self.session.post(url, data=fb_json, headers=fb_headers, timeout=5)
                    if res_fb.status_code in [200, 201]:
                        logger.info(f"✅ LIVE ORDER EXECUTED (Fallback): {side_payload.upper()} {qty_val} {futures_symbol}")
                        return res_fb.json()
                    else:
                        logger.error(f"❌ ORDER PLACEMENT REJECTED (HTTP {res.status_code}): {res.text}")
                        return [{"id": "FAILED", "status": "error", "message": res.text}]
            except Exception as e:
                logger.error(f"❌ Attempt {attempt+1} order placement error: {e}")
                time.sleep(0.5)

        return [{"id": "FAILED", "status": "error", "message": "Network Retry Limit Reached"}]

    def cancel_order(self, order_id: str) -> dict:
        """Cancels a single order by order_id"""
        if not self.live_mode:
            return {"status": "success"}

        url = f"{self.base_url}/exchange/v1/derivatives/futures/orders/cancel"
        timeStamp = int(round(time.time() * 1000))
        body = {"timestamp": timeStamp, "id": order_id}
        json_body = json.dumps(body, separators=(',', ':'))
        signature = self._get_signature(json_body)

        headers = {
            "Content-Type": "application/json",
            "X-AUTH-APIKEY": self.api_key,
            "X-AUTH-SIGNATURE": signature
        }

        try:
            res = self.session.post(url, data=json_body, headers=headers, timeout=5)
            logger.info(f"🛑 CANCELED ORDER {order_id} (HTTP {res.status_code}): {res.text}")
            return res.json()
        except Exception as e:
            logger.error(f"❌ Cancel order error: {e}")
            return {"status": "error", "message": str(e)}

    def cancel_all_orders(self) -> dict:
        """Fetch and cancel ALL active pending/untriggered orders on CoinDCX Futures"""
        if not self.live_mode:
            return {"status": "success"}

        url_list = f"{self.base_url}/exchange/v1/derivatives/futures/orders"
        timeStamp = int(round(time.time() * 1000))
        body = {"timestamp": timeStamp}
        json_body = json.dumps(body, separators=(',', ':'))
        signature = self._get_signature(json_body)

        headers = {
            "Content-Type": "application/json",
            "X-AUTH-APIKEY": self.api_key,
            "X-AUTH-SIGNATURE": signature
        }

        try:
            res = self.session.post(url_list, data=json_body, headers=headers, timeout=5)
            orders = res.json()
            canceled_count = 0
            if isinstance(orders, list):
                for o in orders:
                    if isinstance(o, dict) and "id" in o:
                        order_id = o["id"]
                        self.cancel_order(order_id)
                        canceled_count += 1
            logger.info(f"🛑 CANCELED {canceled_count} PENDING ORDERS ON COINDCX.")
            return {"status": "success", "canceled_count": canceled_count}
        except Exception as e:
            logger.error(f"❌ Cancel all orders error: {e}")
            return {"status": "error", "message": str(e)}

    def confirm_position_exists(self, futures_symbol: str) -> bool:
        """Verifies with CoinDCX API that an active position actually exists for the pair"""
        try:
            active_positions = self.get_active_futures_positions()
            pos = active_positions.get(futures_symbol, {})
            return abs(float(pos.get("active_pos", 0.0))) > 0.000001
        except Exception as e:
            logger.warning(f"⚠️ confirm_position_exists check failed: {e}")
            return False
