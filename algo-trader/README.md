# Algo Trader - TWS API Python Client

A Python client for Interactive Brokers TWS API to fetch account data and manage trades.

## Prerequisites

1. **IB Gateway Docker Container Running**
   - The IB Gateway container should be running and accessible
   - Paper trading port: `4002` (mapped to internal `4004`)
   - Live trading port: `4001` (mapped to internal `4003`)

2. **Python 3.11+**
   - Required by the TWS API

3. **TWS API Python Package**

   ```powershell
   pip install ibapi
   ```

## Project Structure

```
algo-trader/
├── README.md
├── requirements.txt
├── config.py              # Configuration settings
├── account_balance.py     # Fetch account balance/summary
└── examples/
    └── basic_connection.py  # Basic connection test
```

## Quick Start

1. **Install dependencies**:

   ```powershell
   cd algo-trader
   pip install -r requirements.txt
   ```

2. **Run the account balance script**:

   ```powershell
   python account_balance.py
   ```

## Configuration

Edit `config.py` to change connection settings:

- `TWS_HOST`: Default `127.0.0.1`
- `TWS_PORT`: Default `4002` (paper trading)
- `CLIENT_ID`: Default `0`

## Available Scripts

### `account_balance.py`

Fetches and displays:

- Net Liquidation Value
- Total Cash Balance
- Buying Power
- All currency balances
- Current positions

### `examples/basic_connection.py`

Simple connection test to verify IB Gateway connectivity.

## Port Reference

| Mode | Docker Port | Internal Port |
|------|-------------|---------------|
| Live | 4001 | 4003 |
| Paper | 4002 | 4004 |

## Resources

- [TWS API Documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/)
- [Python TWS API Course](https://www.interactivebrokers.com/campus/trading-course/python-tws-api/)
- [Account & Portfolio Data](https://www.interactivebrokers.com/campus/trading-lessons/python-account-portfolio/)
