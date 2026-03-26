from __future__ import annotations

from typing import Any, Dict, Optional

from bot.client import BinanceClient, BinanceAPIError
from bot.validators import OrderParams
from bot.logging_config import get_logger

logger = get_logger(__name__)

ORDER_ENDPOINT = "/fapi/v1/order"


def _build_order_payload(params: OrderParams) -> Dict[str, Any]:
    """Construct the raw payload dict to send to the API."""
    payload: Dict[str, Any] = {
        "symbol": params.symbol,
        "side": params.side,
        "type": params.order_type,
        "quantity": params.quantity,
    }

    if params.order_type == "LIMIT":
        payload["price"] = params.price
        payload["timeInForce"] = "GTC"

    if params.order_type == "STOP_MARKET":
        payload["stopPrice"] = params.stop_price

    return payload


def _parse_order_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "orderId": raw.get("orderId"),
        "symbol": raw.get("symbol"),
        "side": raw.get("side"),
        "type": raw.get("type"),
        "status": raw.get("status"),
        "origQty": raw.get("origQty"),
        "executedQty": raw.get("executedQty"),
        "avgPrice": raw.get("avgPrice"),
        "price": raw.get("price"),
        "stopPrice": raw.get("stopPrice"),
        "timeInForce": raw.get("timeInForce"),
        "updateTime": raw.get("updateTime"),
    }


class OrderManager:
    def __init__(self, client: BinanceClient) -> None:
        self._client = client

    def place_order(self, params: OrderParams) -> Dict[str, Any]:
        payload = _build_order_payload(params)

        logger.info(
            "Placing %s %s order — symbol=%s qty=%s price=%s stop=%s",
            params.side,
            params.order_type,
            params.symbol,
            params.quantity,
            params.price,
            params.stop_price,
        )

        try:
            raw_response = self._client.post(ORDER_ENDPOINT, payload)
        except BinanceAPIError:
            raise
        except Exception as exc:
            logger.error("Unexpected error while placing order: %s", exc, exc_info=True)
            raise

        result = _parse_order_response(raw_response)
        logger.info(
            "Order placed successfully — orderId=%s status=%s executedQty=%s avgPrice=%s",
            result["orderId"],
            result["status"],
            result["executedQty"],
            result["avgPrice"],
        )
        return result

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Fetch currently open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()
        logger.info("Fetching open orders (symbol=%s)", symbol)
        return self._client.get(ORDER_ENDPOINT, params=params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order by symbol and orderId."""
        logger.info("Cancelling orderId=%s for symbol=%s", order_id, symbol)
        params = {"symbol": symbol.upper(), "orderId": order_id}
        params = self._client._signed_params(params)
        resp = self._client._session.delete(
            f"{self._client._base_url}{ORDER_ENDPOINT}",
            params=params,
            timeout=self._client._timeout,
        )
        return self._client._handle_response(resp)
