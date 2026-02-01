"""
Strategy 2: High-Probability Bonds ("Tail Trading")
Scans for contracts trading at 0.95+ and buys them for steady small wins
"""

import asyncio
from typing import List, Dict, Any, Optional
import config
from apis import gamma, clob
from engine import paper_trading
from tui.logger import tui_print

async def scan_high_prob_bonds():
    """
    Main scanner loop for high-probability bonds
    Runs every BOND_SCAN_INTERVAL seconds
    """
    tui_print("🎯 High-probability bond scanner started")
    
    while True:
        try:
            tui_print("🔍 Scanning for high-probability bonds...")
            await find_and_execute_bonds()
            await asyncio.sleep(config.BOND_SCAN_INTERVAL)
        except Exception as e:
            tui_print(f"Error in bond scanner: {e}")
            await asyncio.sleep(config.BOND_SCAN_INTERVAL)

async def find_and_execute_bonds():
    """
    Scan active crypto markets for high-probability contracts
    """
    # Fetch active crypto markets
    markets = await gamma.fetch_active_crypto_markets()
    
    for market in markets:
        # Check both YES and NO sides
        await check_and_execute_bond(market, "YES")
        await check_and_execute_bond(market, "NO")

async def check_and_execute_bond(market: Dict[str, Any], side: str):
    """
    Check if a specific side qualifies as a bond trade and execute if so
    """
    market_id = market.get("id")
    market_name = market.get("question")
    
    # Get token ID for the side we're checking
    clob_token_ids = market.get("clobTokenIds", [])
    if not clob_token_ids or not isinstance(clob_token_ids, list) or len(clob_token_ids) < 2:
        return
    
    token_id = clob_token_ids[0] if side == "YES" else clob_token_ids[1]
    
    # Validate token_id
    if not token_id or not isinstance(token_id, str):
        return
    
    # Fetch current price
    price_data = await clob.fetch_market_price(token_id)
    if not price_data:
        return
    
    price = float(price_data.get(side.lower(), 0))
    
    # Check if price >= bond minimum
    if price < config.BOND_MIN_PRICE:
        return
    
    # Check liquidity
    has_liquidity = await clob.check_liquidity(token_id, config.BOND_MIN_LIQUIDITY)
    if not has_liquidity:
        return
    
    # Determine if this is a 15-minute crypto market (affects fees)
    is_crypto_15min = "15" in market_name.lower() or "15m" in market_name.lower()
    
    # Calculate fee
    shares_test = 100  # Test with 100 shares
    fee_per_share = paper_trading.calculate_fee(shares_test, price, is_crypto_15min) / shares_test
    
    # Calculate profit after fee
    profit_per_share = 1.00 - price - fee_per_share
    
    # Only execute if profit is positive
    if profit_per_share <= 0:
        return
    
    # Calculate position size
    position_size = await paper_trading.calculate_position_size("HIGH_PROB_BOND")
    
    # Cap at max position
    max_position = await paper_trading.get_available_balance() * config.BOND_MAX_POSITION_PCT
    position_size = min(position_size, max_position)
    
    # Execute trade
    tui_print(f"\n💰 High-Prob Bond Found!")
    tui_print(f"Market: {market_name}")
    tui_print(f"Side: {side} @ ${price:.3f}")
    tui_print(f"Expected profit: ${profit_per_share:.4f} per share")
    
    await paper_trading.simulate_trade(
        strategy_id="HIGH_PROB_BOND",
        market_id=market_id,
        market_name=market_name,
        side=side,
        price=price,
        position_size_usd=position_size,
        is_crypto_15min=is_crypto_15min
    )
