from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bot.logging_config import get_logger

logger = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class OrderParams:

    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None


# ── Validation ───────────────────────────────────────────────────────────────


class ValidationError(ValueError):
    pass


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
    stop_price: Optional[float] = None,
) -> OrderParams:

    errors: list[str] = []

    # ── symbol ───────────────────────────────────────────────────────────────
    symbol = symbol.strip().upper()
    if not symbol:
        errors.append("Symbol must not be empty.")
    if not symbol.isalnum():
        errors.append(f"Symbol '{symbol}' contains invalid characters.")

    # ── side ─────────────────────────────────────────────────────────────────
    side = side.strip().upper()
    if side not in VALID_SIDES:
        errors.append(f"Side '{side}' is invalid. Must be one of: {VALID_SIDES}.")

    # ── order type ───────────────────────────────────────────────────────────
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        errors.append(
            f"Order type '{order_type}' is invalid. "
            f"Must be one of: {VALID_ORDER_TYPES}."
        )

    # ── quantity ─────────────────────────────────────────────────────────────
    if quantity is None or quantity <= 0:
        errors.append(f"Quantity must be a positive number (got {quantity}).")

    # ── price (required for LIMIT) ───────────────────────────────────────────
    if order_type == "LIMIT":
        if price is None:
            errors.append("Price is required for LIMIT orders.")
        elif price <= 0:
            errors.append(f"Price must be a positive number (got {price}).")

    if order_type == "MARKET" and price is not None:
        logger.warning("Price is ignored for MARKET orders.")

    # ── stop_price (required for STOP_MARKET) ────────────────────────────────
    if order_type == "STOP_MARKET":
        if stop_price is None:
            errors.append("stop_price is required for STOP_MARKET orders.")
        elif stop_price <= 0:
            errors.append(
                f"stop_price must be a positive number (got {stop_price})."
            )

    if errors:
        joined = " | ".join(errors)
        logger.error("Validation failed: %s", joined)
        raise ValidationError(joined)

    logger.debug(
        "Validation passed — symbol=%s side=%s type=%s qty=%s price=%s stop_price=%s",
        symbol,
        side,
        order_type,
        quantity,
        price,
        stop_price,
    )

    return OrderParams(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )
