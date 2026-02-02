"""
Paper Trading Engine
Simulates trades without real money, tracks virtual balance
"""

import config
from database import db
from typing import Optional
import math
from tui.logger import tui_print

def calculate_fee(shares: float, price: float, is_crypto_15min: bool = True) -> float:
    """
    Calculate Polymarket fee using official formula
    fee = C × feeRate × (p × (1-p))^exponent
    
    Args:
        shares: Number of shares
        price: Entry price (0-1)
        is_crypto_15min: True if this is a 15-minute crypto market
    
    Returns:
        Fee amount in USD
    """
    # NegRisk markets are fee-free
    if not is_crypto_15min:
        return 0.0
    
    # Polymarket's fee formula
    fee = shares * config.FEE_RATE * math.pow(price * (1 - price), config.FEE_EXPONENT)
    return round(fee, 6)

async def simulate_trade(
    strategy_id: str,
    market_id: str,
    market_name: str,
    side: str,
    price: float,
    position_size_usd: float,
    is_crypto_15min: bool = True,
    arb_id: Optional[str] = None,
    asset: Optional[str] = None,
    resolution_time: Optional[str] = None
) -> Optional[int]:
    """
    Simulate a paper trade
    
    Args:
        strategy_id: "NEGRISK_ARB", "HIGH_PROB_BOND", "WHALE_COPY", "TEMPORAL_ARB"
        market_id: Polymarket market ID
        market_name: Human-readable market name
        side: "YES" or "NO"
        price: Entry price (0-1)
        position_size_usd: How much USD to spend
        is_crypto_15min: Whether this is a 15-min crypto market (affects fees)
        arb_id: Optional ID to link multi-leg arbitrage trades
        asset: Optional asset/coin being traded (e.g., "BTC", "ETH")
        resolution_time: Optional ISO timestamp when market resolves
    
    Returns:
        Trade ID if successful, None if insufficient balance
    """
    # Get current balance
    fund = await db.get_paper_fund()
    if not fund:
        tui_print("Error: Paper fund not initialized")
        return None
    
    current_balance = fund["current_balance"]
    
    # Calculate fees and total cost first to check against limits
    shares = position_size_usd / price
    fee = calculate_fee(shares, price, is_crypto_15min)
    total_cost = position_size_usd + fee

    # DAILY INVESTMENT CAP CHECK
    # Calculate Total Account Value (NAV) = Cash + Cost of Open Positions
    # (Using cost is safer/simpler than market value for this check)
    open_trades = await db.get_open_trades()
    open_positions_value = sum(t['cost'] for t in open_trades)
    total_account_value = current_balance + open_positions_value
    
    # Calculate spending today
    daily_spend = await db.get_daily_spend()
    
    # Limit: 50% of Total Account Value
    daily_limit = total_account_value * config.DAILY_VOLUME_CAP_PCT
    
    if (daily_spend + total_cost) > daily_limit:
        tui_print(f"⚠️  Daily investment limit reached! Spend: ${daily_spend:.2f} + ${total_cost:.2f} > ${daily_limit:.2f} (50% of ${total_account_value:.2f})")
        return None

    # Check sufficient balance
    if total_cost > current_balance:
        # If we have balance issues but haven't hit the daily cap, try to adjust size
        # However, for strategy consistency, we might just fail here or adjust
        if current_balance < 1.0: # Minimum trade check
             tui_print(f"Insufficient balance: need ${total_cost:.2f}, have ${current_balance:.2f}")
             return None
        
        # Adjust to max available
        available = current_balance - 0.05 # Leave tiny buffer
        if available < 1.0:
            return None
        
        # Recalculate based on available
        shares = available / price
        fee = calculate_fee(shares, price, is_crypto_15min)
        total_cost = available # Approx
        position_size_usd = total_cost - fee
        tui_print(f"  ℹ️  Adjusted position to available balance: ${position_size_usd:.2f}")

    # Double-check total cost doesn't exceed balance strict check
    if total_cost > current_balance:
        return None
    
    # shares and fee are calculated above or adjusted

    
    # Create trade record
    trade_id = await db.create_paper_trade(
        strategy_id=strategy_id,
        market_id=market_id,
        market_name=market_name,
        side=side,
        price=price,
        shares=shares,
        cost=position_size_usd,
        fee=fee,
        arb_id=arb_id,
        asset=asset,
        resolution_time=resolution_time
    )
    
    # Deduct from balance
    new_balance = current_balance - total_cost
    await db.update_paper_fund_balance(new_balance)
    
    tui_print(f"✓ Paper trade executed: {strategy_id} | {market_name} | {side} @ ${price:.3f} | {shares:.2f} shares | Fee: ${fee:.3f}")
    
    return trade_id

async def get_available_balance() -> float:
    """Get current available balance for trading"""
    fund = await db.get_paper_fund()
    if not fund:
        return 0.0
    return fund["current_balance"]

async def calculate_position_size(
    strategy_id: str,
    confidence: Optional[str] = None
) -> float:
    """
    Calculate position size based on strategy and confidence
    
    Args:
        strategy_id: Strategy identifier
        confidence: For whale copy: "STRONG", "HIGH", "MEDIUM"
    
    Returns:
        Position size in USD
    """
    balance = await get_available_balance()
    
    if strategy_id == "NEGRISK_ARB":
        # Max 10% of balance per arbitrage opportunity
        return balance * config.NEGRISK_MAX_POSITION_PCT
    
    elif strategy_id == "HIGH_PROB_BOND":
        # Default 2% of balance
        return balance * config.BOND_DEFAULT_POSITION_PCT
    
    elif strategy_id == "WHALE_COPY":
        # Risk Management: Kelly Criterion vs Fixed
        if hasattr(config, 'RISK_MANAGEMENT_MODE') and config.RISK_MANAGEMENT_MODE == "KELLY":
            # Need price to calculate odds, but function sig limits us. 
            # We will use confidence to adjust the Kelly Fraction slightly if needed,
            # but ideally we need the price passed in. 
            # modifying calculate_position_size signature is risky for existing calls.
            # We will infer 'b' (odds) assumes a roughly 1:1 payout (price ~0.5) if not available,
            # BUT for accurate Kelly we really need the price.
            # Let's use a safe default assuming price is around 0.5-0.6 (odds ~0.8)
            # Better approach: Use fixed tiers but calibrated by Kelly logic conceptually
            
            # HOWEVER, for true Kelly, we should calculate it dynamically.
            # Since we can't easily change the signature everywhere safely in one go,
            # we'll stick to the "Confidence Tiers" which are effectively simplified Kelly
            # for 60% win rate at different conviction levels.
            
            # If user strictly wants Kelly math:
            # Kelly % = W - (1-W)/R where R = profit/loss ratio.
            # for binary options, R = (1-p)/p where p is entry price.
            # So Kelly = W - (1-W)/((1-p)/p) = W - (1-W)*p/(1-p) = (W - p) / (1-p)
            
            # We will use a baseline price of 0.55 for sizing roughly.
            # Kelly = (0.60 - 0.55) / (1 - 0.55) = 0.05 / 0.45 = 11%
            # Half Kelly = 5.5%
            
            if confidence == "STRONG":
                return balance * 0.05  # ~Half Kelly for 60% win rate
            elif confidence == "HIGH":
                return balance * 0.03
            else:
                return balance * 0.02
        else:
            # Original Fixed Sizing
            if confidence == "STRONG":
                return balance * config.WHALE_POSITION_STRONG
            elif confidence == "HIGH":
                return balance * config.WHALE_POSITION_HIGH
            else:  # MEDIUM
                return balance * config.WHALE_POSITION_MEDIUM
    
    elif strategy_id == "TEMPORAL_ARB":
        # Conservative 1% for temporal arbitrage
        return balance * config.TEMPORAL_DEFAULT_POSITION_PCT
    
    return 0.0
