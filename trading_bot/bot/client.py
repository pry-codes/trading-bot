from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from typing import Any, Dict, Optional

import requests

from bot.logging_config import get_logger

logger = get_logger(__name__)

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_RECV_WINDOW = 5_000


class BinanceAPIError(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceClient:
    """
    Thin wrapper around the Binance Futures Testnet REST API.

    Usage::

        client = BinanceClient(api_key="...", api_secret="...")
        response = client.post("/fapi/v1/order", params={...})
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        recv_window: int = DEFAULT_RECV_WINDOW,
        timeout: int = 10,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")

        self._api_key = api_key
        self._api_secret = api_secret.encode()
        self._base_url = base_url.rstrip("/")
        self._recv_window = recv_window
        self._timeout = timeout

        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info("BinanceClient initialised (base_url=%s)", self._base_url)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _sign(self, query_string: str) -> str:
        return hmac.new(
            self._api_secret,
            query_string.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _signed_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params["timestamp"] = self._timestamp()
        params["recvWindow"] = self._recv_window
        query_string = urllib.parse.urlencode(params)
        params["signature"] = self._sign(query_string)
        return params

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        logger.debug(
            "HTTP %s %s → status=%s body=%s",
            response.request.method,
            response.url,
            response.status_code,
            response.text[:500],
        )
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            return {}

        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            raise BinanceAPIError(data["code"], data.get("msg", "Unknown error"))

        response.raise_for_status()
        return data

    # ── Public methods ───────────────────────────────────────────────────────

    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, signed: bool = False
    ) -> Dict[str, Any]:
        """Send a signed or unsigned GET request."""
        params = params or {}
        if signed:
            params = self._signed_params(params)

        url = f"{self._base_url}{endpoint}"
        logger.info("GET %s params=%s", endpoint, {k: v for k, v in params.items() if k != "signature"})

        try:
            resp = self._session.get(url, params=params, timeout=self._timeout)
            return self._handle_response(resp)
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error on GET %s: %s", endpoint, exc)
            raise
        except requests.exceptions.Timeout:
            logger.error("Request timed out: GET %s", endpoint)
            raise

    def post(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a signed POST request."""
        params = self._signed_params(params)
        url = f"{self._base_url}{endpoint}"
        safe_params = {k: v for k, v in params.items() if k not in ("signature",)}
        logger.info("POST %s params=%s", endpoint, safe_params)

        try:
            resp = self._session.post(url, data=params, timeout=self._timeout)
            return self._handle_response(resp)
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error on POST %s: %s", endpoint, exc)
            raise
        except requests.exceptions.Timeout:
            logger.error("Request timed out: POST %s", endpoint)
            raise

    def ping(self) -> bool:
        try:
            self.get("/fapi/v1/ping")
            logger.info("Ping successful.")
            return True
        except Exception as exc:
            logger.error("Ping failed: %s", exc)
            return False
