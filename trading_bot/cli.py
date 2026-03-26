from __future__ import annotations

import os
import sys
import json
import argparse
from typing import Optional

from bot.logging_config import setup_logging, get_logger, LOG_FILE
from bot.client import BinanceClient, BinanceAPIError
from bot.orders import OrderManager
from bot.validators import validate_order_params, ValidationError

# ── Pretty-print helpers ─────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _color(text: str, code: str) -> str:
    """Apply ANSI colour if stdout is a TTY."""
    if sys.stdout.isatty():
        return f"{code}{text}{RESET}"
    return text


def _section(title: str) -> None:
    print(_color(f"\n{'─' * 50}", CYAN))
    print(_color(f"  {title}", BOLD))
    print(_color("─" * 50, CYAN))


def _print_order_summary(params_dict: dict) -> None:
    _section("Order Request Summary")
    for key, value in params_dict.items():
        if value is not None:
            print(f"  {key:<15} {value}")


def _print_order_result(result: dict) -> None:
    _section("Order Response")
    display_fields = [
        ("orderId", "Order ID"),
        ("symbol", "Symbol"),
        ("side", "Side"),
        ("type", "Type"),
        ("status", "Status"),
        ("origQty", "Orig Quantity"),
        ("executedQty", "Executed Qty"),
        ("avgPrice", "Avg Price"),
        ("price", "Price"),
        ("stopPrice", "Stop Price"),
        ("timeInForce", "Time In Force"),
    ]
    for field, label in display_fields:
        value = result.get(field)
        if value not in (None, "0", "0.00000000", ""):
            print(f"  {label:<16} {value}")


# ── Credential loading ───────────────────────────────────────────────────────

def _load_credentials(api_key: Optional[str], api_secret: Optional[str]):
    """
    Resolve API credentials.
    CLI args > environment variables.
    """
    key = api_key or os.getenv("BINANCE_API_KEY", "")
    secret = api_secret or os.getenv("BINANCE_API_SECRET", "")

    if not key or not secret:
        print(
            _color(
                "\n[ERROR] API credentials not found.\n"
                "  Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables,\n"
                "  or pass --api-key / --api-secret flags.\n",
                RED,
            )
        )
        sys.exit(1)

    return key, secret


# ── Sub-command handlers ─────────────────────────────────────────────────────

def cmd_place_order(args: argparse.Namespace, manager: OrderManager) -> None:
    logger = get_logger("cli.place_order")

    # Validate
    try:
        params = validate_order_params(
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.quantity,
            price=args.price,
            stop_price=getattr(args, "stop_price", None),
        )
    except ValidationError as exc:
        print(_color(f"\n[VALIDATION ERROR] {exc}\n", RED))
        logger.error("Validation error: %s", exc)
        sys.exit(1)

    summary = {
        "Symbol": params.symbol,
        "Side": params.side,
        "Type": params.order_type,
        "Quantity": params.quantity,
        "Price": params.price,
        "Stop Price": params.stop_price,
    }
    _print_order_summary(summary)

    # Place
    try:
        result = manager.place_order(params)
    except BinanceAPIError as exc:
        print(_color(f"\n[API ERROR] {exc}\n", RED))
        logger.error("API error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        print(_color(f"\n[ERROR] {exc}\n", RED))
        logger.error("Unexpected error: %s", exc, exc_info=True)
        sys.exit(1)

    _print_order_result(result)
    print(
        _color(
            f"\n  ✓ Order placed successfully! (orderId={result['orderId']})",
            GREEN,
        )
    )
    print(f"  Log file: {LOG_FILE}\n")


def cmd_open_orders(args: argparse.Namespace, manager: OrderManager) -> None:
    logger = get_logger("cli.open_orders")
    try:
        orders = manager.get_open_orders(symbol=getattr(args, "symbol", None))
    except Exception as exc:
        print(_color(f"\n[ERROR] {exc}\n", RED))
        logger.error("Error fetching open orders: %s", exc, exc_info=True)
        sys.exit(1)

    _section("Open Orders")
    if not orders:
        print("  No open orders found.")
    else:
        print(json.dumps(orders, indent=2))


def cmd_cancel_order(args: argparse.Namespace, manager: OrderManager) -> None:
    logger = get_logger("cli.cancel_order")
    try:
        result = manager.cancel_order(symbol=args.symbol, order_id=args.order_id)
    except BinanceAPIError as exc:
        print(_color(f"\n[API ERROR] {exc}\n", RED))
        logger.error("API error cancelling order: %s", exc)
        sys.exit(1)
    except Exception as exc:
        print(_color(f"\n[ERROR] {exc}\n", RED))
        logger.error("Unexpected error: %s", exc, exc_info=True)
        sys.exit(1)

    _section("Cancel Order Result")
    print(json.dumps(result, indent=2))
    print(_color("\n  ✓ Order cancelled.\n", GREEN))


# ── Argument parser ──────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet CLI Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Global flags
    parser.add_argument("--api-key", metavar="KEY", help="Binance API key (or set BINANCE_API_KEY)")
    parser.add_argument("--api-secret", metavar="SECRET", help="Binance API secret (or set BINANCE_API_SECRET)")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log verbosity (default: INFO)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── place-order ──────────────────────────────────────────────────────────
    po = sub.add_parser("place-order", help="Place a new futures order")
    po.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    po.add_argument(
        "--side", required=True, choices=["BUY", "SELL"], type=str.upper,
        help="Order side: BUY or SELL"
    )
    po.add_argument(
        "--type", required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        type=str.upper,
        help="Order type",
    )
    po.add_argument("--quantity", required=True, type=float, help="Order quantity")
    po.add_argument("--price", type=float, default=None, help="Limit price (required for LIMIT orders)")
    po.add_argument("--stop-price", type=float, default=None, dest="stop_price",
                    help="Stop trigger price (required for STOP_MARKET orders)")

    # ── open-orders ──────────────────────────────────────────────────────────
    oo = sub.add_parser("open-orders", help="List open orders")
    oo.add_argument("--symbol", default=None, help="Filter by symbol (optional)")

    # ── cancel-order ─────────────────────────────────────────────────────────
    co = sub.add_parser("cancel-order", help="Cancel an open order")
    co.add_argument("--symbol", required=True, help="Trading pair")
    co.add_argument("--order-id", required=True, type=int, dest="order_id", help="Order ID to cancel")

    return parser


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Set up logging before anything else
    setup_logging(log_level=args.log_level)
    logger = get_logger("cli.main")
    logger.info("Command invoked: %s", args.command)

    # Resolve credentials and build client + manager
    api_key, api_secret = _load_credentials(args.api_key, args.api_secret)
    client = BinanceClient(api_key=api_key, api_secret=api_secret)
    manager = OrderManager(client)

    # Dispatch
    dispatch = {
        "place-order": cmd_place_order,
        "open-orders": cmd_open_orders,
        "cancel-order": cmd_cancel_order,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args, manager)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
