"""
Configuration file for Polymarket Multi-Strategy Trading Bot
All thresholds, intervals, and API endpoints
"""

# ============================================================================
# API ENDPOINTS
# ============================================================================

# Polymarket APIs (all free, no key required)
GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"
DATA_API_BASE = "https://data-api.polymarket.com"
WEBSOCKET_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/"

# Exchange APIs for BTC price (all free, no key required)
BINANCE_API_BASE = "https://api.binance.com"
COINBASE_API_BASE = "https://api.coinbase.com"

# ============================================================================
# STRATEGY 1: NEGRISK REBALANCING ARBITRAGE
# ============================================================================

# How often to scan for NegRisk arbitrage opportunities (seconds)
NEGRISK_SCAN_INTERVAL = 30

# Buffer to account for slippage and execution time
# Only fire if total cost < $1.00 - NEGRISK_BUFFER
NEGRISK_BUFFER = 0.02  # $0.02

# Maximum % of balance to use on a single arbitrage opportunity
NEGRISK_MAX_POSITION_PCT = 0.10  # 10%

# ============================================================================
# STRATEGY 2: HIGH-PROBABILITY BONDS
# ============================================================================

# How often to scan for high-probability contracts (seconds)
BOND_SCAN_INTERVAL = 15

# Minimum price to consider a "bond" trade
BOND_MIN_PRICE = 0.95  # 95 cents

# Position sizing for bond trades
BOND_DEFAULT_POSITION_PCT = 0.02  # 2% of balance
BOND_MAX_POSITION_PCT = 0.05      # Never exceed 5%

# Minimum liquidity required (USD) to execute bond trade
BOND_MIN_LIQUIDITY = 10.0

# ============================================================================
# STRATEGY 3: WHALE COPY TRADING
# ============================================================================

# How often to refresh leaderboard for new whales (seconds)
WHALE_DISCOVERY_INTERVAL = 1800  # 30 minutes

# How often to poll whale activity (seconds)
WHALE_MONITOR_INTERVAL = 12  # 12 seconds

# Whale vetting criteria
WHALE_MIN_PROFIT = 50.0        # $50 profit in last 7 days (realistic for weekly leaderboard)
WHALE_MIN_TRADES = 3           # At least 3 trades (estimated from volume)
WHALE_MIN_WIN_RATE = 0.50      # 50% win rate (we default to 60% so this will pass)

# Signal detection
WHALE_SIGNAL_MIN_WHALES = 2    # Require at least 2 whales to converge (removes noise)
WHALE_SIGNAL_WINDOW = 300      # 5 minutes (seconds)
WHALE_SIGNAL_MAX_PRICE_MOVE = 0.10  # Max 10% price movement since first whale

# Risk Management
RISK_MANAGEMENT_MODE = "KELLY" # "FIXED" or "KELLY"
KELLY_FRACTION = 0.5           # Half-Kelly for safety
DEFAULT_WIN_RATE = 0.60        # Estimated win rate for whales

# Position sizing by confidence level (realistic for fees + slippage)
WHALE_POSITION_STRONG = 0.05   # 5% for 3+ whales ($5.00) - high confidence
WHALE_POSITION_HIGH = 0.03     # 3% for 2 whales ($3.00) - good confirmation  
WHALE_POSITION_MEDIUM = 0.02   # 2% for 1 whale ($2.00) - minimum viable after fees

# Maximum price movement allowed between signal and execution
WHALE_MAX_SLIPPAGE = 0.05      # 5%

# Indicator filter thresholds
WHALE_RSI_OVERBOUGHT = 80
WHALE_RSI_OVERSOLD = 20
WHALE_LOW_VOLUME_THRESHOLD = 0.50  # 50% of average
WHALE_HIGH_VOLATILITY_MULTIPLIER = 1.5  # 1.5x average ATR

# ============================================================================
# STRATEGY 4: TEMPORAL ARBITRAGE
# ============================================================================

# How often to check for temporal arbitrage (seconds)
TEMPORAL_SCAN_INTERVAL = 1

# Minimum BTC price movement to consider (%)
TEMPORAL_MIN_MOVE_PCT = 0.02   # 2%

# Minimum mispricing to fire (%)
TEMPORAL_MIN_MISPRICING_PCT = 0.10  # 10%

# Maximum time remaining in window (seconds)
TEMPORAL_MAX_TIME_REMAINING = 600  # 10 minutes

# Position sizing
TEMPORAL_DEFAULT_POSITION_PCT = 0.01  # 1%
TEMPORAL_MAX_POSITION_PCT = 0.03      # 3%

# ============================================================================
# PAPER TRADING ENGINE
# ============================================================================

# Resolution engine check interval (seconds)
RESOLUTION_CHECK_INTERVAL = 5

# Paper fund validation
PAPER_FUND_MIN = 10.0          # Minimum $10
PAPER_FUND_MAX = 1000000.0     # Maximum $1M
DAILY_VOLUME_CAP_PCT = 0.50    # Max daily volume as % of total account value

# ============================================================================
# FEE CALCULATION (Polymarket's official formula)
# ============================================================================

# Fee only applies to 15-minute crypto markets
# Formula: fee = C × feeRate × (p × (1-p))^exponent
FEE_RATE = 0.25
FEE_EXPONENT = 2

# NegRisk markets are fee-free
NEGRISK_FEE_FREE = True

# ============================================================================
# TECHNICAL INDICATORS (for whale copy trading)
# ============================================================================

RSI_PERIOD = 14
EMA_SHORT_PERIOD = 9
EMA_LONG_PERIOD = 21
ATR_PERIOD = 14
VOLUME_LOOKBACK_PERIOD = 20

# BTC candle interval for indicators
BTC_CANDLE_INTERVAL = "1h"
BTC_CANDLE_LIMIT = 20

# ============================================================================
# TUI DASHBOARD
# ============================================================================

# Dashboard refresh rate (seconds)
DASHBOARD_REFRESH_INTERVAL = 1

# Activity feed max items
ACTIVITY_FEED_MAX_ITEMS = 100

# ============================================================================
# DATABASE
# ============================================================================

DATABASE_PATH = "polymarket_bot.db"
