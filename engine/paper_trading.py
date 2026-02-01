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
    arb_id: Optional[str] = None
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
    
    Returns:
        Trade ID if successful, None if insufficient balance
    """
    # Get current balance
    fund = await db.get_paper_fund()
    if not fund:
        tui_print("Error: Paper fund not initialized")
        return None
    
    current_balance = fund["current_balance"]
    
    # Check sufficient balance
    if position_size_usd > current_balance:
        tui_print(f"Insufficient balance: need ${position_size_usd:.2f}, have ${current_balance:.2f}")
        return None
    
    # Calculate shares and fee
    shares = position_size_usd / price
    fee = calculate_fee(shares, price, is_crypto_15min)
    total_cost = position_size_usd + fee
    
    # Double-check total cost doesn't exceed balance
    if total_cost > current_balance:
        # Adjust shares to fit within balance
        available_for_shares = current_balance - fee
        shares = available_for_shares / price
        position_size_usd = shares * price
        total_cost = position_size_usd + fee
    
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
        arb_id=arb_id
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
        # Position size based on confidence level
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
