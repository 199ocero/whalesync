# Polymarket Multi-Strategy Trading Bot

A Python-based paper trading bot that runs 4 concurrent strategies on Polymarket, prioritized by proven profitability.

## Features

- **100% Paper Trading** — No real money, no wallet connection required
- **4 Concurrent Strategies:**
  1. **NegRisk Rebalancing Arbitrage** — Guaranteed profit when sum of all outcomes < $1.00
  2. **High-Probability Bonds** — Buy contracts ≥ 0.95 for steady small wins
  3. **Whale Copy Trading** — Track top traders with RSI/EMA/volume/ATR filters
  4. **Temporal Arbitrage** — Exploit pricing lag vs BTC price movements
- **Automatic Resolution** — Checks markets every 5 seconds and settles trades
- **Per-Strategy P&L Tracking** — See which strategy actually makes money

## Installation

### Requirements

- Python 3.11+
- Virtual environment (venv)

### Setup

```bash
cd polymarket_bot

# Activate virtual environment
source venv/bin/activate  # On Mac/Linux
# or
venv\Scripts\activate  # On Windows

# Dependencies are already installed
```

## Usage

### Run the Bot

```bash
python main.py
```

On first run, you'll be prompted to enter a starting fund ($10 - $1,000,000). This is your virtual paper trading balance.

### What Happens

The bot will:
1. Initialize SQLite database
2. Launch resolution engine (checks trades every 5 seconds)
3. Launch all 4 strategy scanners
4. Monitor for opportunities and execute paper trades
5. Display activity in the terminal

### Stopping the Bot

Press `Ctrl+C` to stop all strategies and exit.

## Configuration

Edit `config.py` to adjust:
- Scan intervals for each strategy
- Position sizing rules
- Thresholds (arbitrage buffer, bond minimum price, etc.)
- Technical indicator settings

## Database

All data is stored in `polymarket_bot.db` (SQLite):
- Paper fund balance and P&L
- All paper trades (open and resolved)
- Tracked whales
- Daily P&L by strategy

## API Costs

**$0** — All APIs are free:
- Polymarket Gamma API (market data, resolution)
- Polymarket CLOB API (prices, orderbooks)
- Polymarket Data API (leaderboard, whale activity)
- Binance API (BTC prices)
- Coinbase API (BTC prices backup)

## Deployment

### Local Mac (24/7)

```bash
# Disable sleep mode first
# System Settings → Battery → Prevent sleeping when power adapter is connected

# Run in tmux
brew install tmux
tmux new -s poly_bot
python main.py

# Detach: Ctrl+B then d
# Reattach: tmux attach -t poly_bot
```

### Hetzner VPS (Production)

1. Choose Amsterdam location (lowest latency to Polymarket)
2. CX11 or CX21 plan (~€5/month)
3. Ubuntu 22.04
4. Install Python 3.11+
5. Upload project files
6. Run `python main.py` in tmux/screen

## Strategy Details

### 1. NegRisk Arbitrage (Highest Priority)

- Scans every 30 seconds
- Detects when sum of all outcome prices < $1.00
- Buys one share of EVERY outcome (guaranteed $1.00 payout)
- Risk-free profit = $1.00 - total cost
- No fees (NegRisk markets are fee-free)

### 2. High-Probability Bonds

- Scans every 15 seconds
- Finds contracts trading at ≥ 0.95
- Validates liquidity and profit after fees
- Position size: 2% of balance (max 5%)
- Expected: 95% win rate, small profit per trade

### 3. Whale Copy Trading

- Discovers whales every 30 minutes from leaderboard
- Monitors whale activity every 12 seconds
- Fires when 2+ whales buy same side within 5 minutes
- Applies RSI/EMA/volume/ATR filters before execution
- Position size: 0.5-2% based on confidence and indicators

### 4. Temporal Arbitrage (Stretch Goal)

- Scans every 1 second
- Compares BTC price movement vs Polymarket pricing
- Detects lag windows (< 10 min remaining)
- Position size: 1% of balance (max 3%)
- May not fire often on Hetzner (requires speed)

## Testing

After 2+ weeks of paper trading, check which strategies are profitable:
- View `polymarket_bot.db` with SQLite browser
- Check `daily_pnl` table for per-strategy P&L
- Analyze win rates and average profit per trade

## License

MIT

## Disclaimer

This is paper trading software for educational purposes. No real money is involved. Past performance does not guarantee future results.
