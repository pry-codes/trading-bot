# Binance Futures Testnet Trading Bot

A clean, structured Python CLI trading bot for **Binance USDT-M Futures Testnet**.

## Features

- Place **Market**, **Limit**, and **Stop-Market** orders
- Supports **BUY** and **SELL** sides
- Input validation with clear error messages
- Rotating file logger + console logger (separate concerns)
- Structured code: `client.py` (HTTP layer) → `orders.py` (business logic) → `cli.py` (user interface)
- No third-party Binance SDK required — uses raw `requests` only

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST client (signing, HTTP)
│   ├── orders.py          # Order placement / cancellation logic
│   ├── validators.py      # Input validation + OrderParams dataclass
│   └── logging_config.py  # Rotating file + console log setup
├── cli.py                 # CLI entry point (argparse)
├── logs/
│   └── trading_bot.log    # Auto-created on first run
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone / extract the project

```bash
git clone https://github.com/<your-username>/trading-bot.git
cd trading_bot
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get Binance Futures Testnet credentials

1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in / register (GitHub login supported)
3. Generate an **API Key** and **Secret** from the API Management section

### 5. Set credentials (two options)

**Option A — Environment variables (recommended)**

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

On Windows (PowerShell):
```powershell
$env:BINANCE_API_KEY = "your_api_key_here"
$env:BINANCE_API_SECRET = "your_api_secret_here"
```

**Option B — CLI flags**

```bash
python cli.py --api-key YOUR_KEY --api-secret YOUR_SECRET place-order ...
```

---

## Usage

### Place a Market Order

```bash
# BUY 0.001 BTC at market price
python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# SELL 0.01 ETH at market price
python cli.py place-order --symbol ETHUSDT --side SELL --type MARKET --quantity 0.01
```

### Place a Limit Order

```bash
# BUY 0.001 BTC with a limit price of 75000 USDT
python cli.py place-order --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 75000

# SELL 0.001 BTC at 90000 USDT
python cli.py place-order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 90000
```

### Place a Stop-Market Order (Bonus)

```bash
# Trigger a BUY if BTC reaches 95000 USDT (breakout entry)
python cli.py place-order --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 95000

# Trigger a SELL (stop-loss) if BTC drops to 80000 USDT
python cli.py place-order --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 80000
```

### List Open Orders

```bash
# All open orders for BTCUSDT
python cli.py open-orders --symbol BTCUSDT

# All open orders across all symbols
python cli.py open-orders
```

### Cancel an Order

```bash
python cli.py cancel-order --symbol BTCUSDT --order-id 4751841027
```

### Verbose Debug Logging

```bash
python cli.py --log-level DEBUG place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

---

## Example Output

```
──────────────────────────────────────────────────
  Order Request Summary
──────────────────────────────────────────────────
  Symbol          BTCUSDT
  Side            BUY
  Type            MARKET
  Quantity        0.001

──────────────────────────────────────────────────
  Order Response
──────────────────────────────────────────────────
  Order ID         4751829310
  Symbol           BTCUSDT
  Side             BUY
  Type             MARKET
  Status           FILLED
  Orig Quantity    0.001
  Executed Qty     0.001
  Avg Price        84612.70000

  ✓ Order placed successfully! (orderId=4751829310)
  Log file: /path/to/trading_bot/logs/trading_bot.log
```

---

## Logging

All activity is logged to `logs/trading_bot.log` (rotating, max 5 MB × 3 backups).

Each log line follows the format:

```
YYYY-MM-DD HH:MM:SS | LEVEL    | module               | message
```

Log entries include:
- Validation decisions (DEBUG)
- API request parameters (INFO)
- Raw API responses (DEBUG)
- Errors with full tracebacks (ERROR)

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Invalid side/type | Validation error printed; exits with code 1 |
| Missing LIMIT price | Validation error |
| API error (e.g. -1121 invalid symbol) | `BinanceAPIError` printed; logged; exits 1 |
| Network timeout | Exception message printed; logged; exits 1 |
| Missing credentials | Clear message with fix instructions; exits 1 |

---

## Assumptions

- Testnet base URL: `https://testnet.binancefuture.com` (USDT-M Futures)
- Minimum quantity and price precision follow the symbol's exchange rules — if the testnet rejects a quantity/price, adjust to match the filter (e.g., BTCUSDT min qty = 0.001)
- `timeInForce` for LIMIT orders is set to `GTC` (Good-Till-Cancelled)
- No leverage or margin configuration is performed by this bot; the testnet uses default leverage

---

## Dependencies

```
requests>=2.31.0
```

Python standard library only otherwise (`argparse`, `hmac`, `hashlib`, `logging`, etc.).
