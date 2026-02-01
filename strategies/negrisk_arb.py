"""
Strategy 1: NegRisk Rebalancing Arbitrage
Scans NegRisk markets for guaranteed profit opportunities
"""

import asyncio
import uuid
from typing import List, Dict, Any, Optional
import config
from apis import gamma, clob
from engine import paper_trading
from tui.logger import tui_print

async def scan_negrisk_arbitrage():
    """
    Main scanner loop for NegRisk arbitrage
    Runs every NEGRISK_SCAN_INTERVAL seconds
    """
    tui_print("💰 NegRisk arbitrage scanner started")
    
    while True:
        try:
            tui_print("🔍 Scanning NegRisk events for arbitrage...")
            await find_and_execute_arbitrage()
            await asyncio.sleep(config.NEGRISK_SCAN_INTERVAL)
        except Exception as e:
            tui_print(f"Error in NegRisk scanner: {e}")
            await asyncio.sleep(config.NEGRISK_SCAN_INTERVAL)

async def find_and_execute_arbitrage():
    """
    Scan all NegRisk events and execute arbitrage if found
    """
    # Fetch all active NegRisk events
    events = await gamma.fetch_negrisk_events()
    
    for event in events:
        event_id = event.get("id")
        if not event_id:
            continue
        
        # Get all markets for this event
        markets = await gamma.fetch_event_markets(event_id)
        if not markets or len(markets) < 2:
            continue
        
        # Check for arbitrage opportunity
        opportunity = await check_arbitrage_opportunity(event, markets)
        if opportunity:
            await execute_arbitrage(opportunity)

async def check_arbitrage_opportunity(
    event: Dict[str, Any],
    markets: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Check if buying all outcomes costs less than $1.00
    
    Returns opportunity dict if found, None otherwise
    """
    # Get YES prices for all outcomes
    total_cost = 0.0
    outcome_prices = []
    
    for market in markets:
        # Extract token_id safely
        clob_token_ids = market.get("clobTokenIds")
        if not clob_token_ids or not isinstance(clob_token_ids, list) or len(clob_token_ids) == 0:
            continue
        
        token_id = clob_token_ids[0]  # YES token
        if not token_id or not isinstance(token_id, str):
            continue
        
        # Fetch current YES price
        price_data = await clob.fetch_market_price(token_id)
        if not price_data:
            continue
        
        yes_price = float(price_data.get("yes", 0))
        if yes_price <= 0:
            continue
        
        total_cost += yes_price
        outcome_prices.append({
            "market_id": market.get("id"),
            "market_name": market.get("question"),
            "token_id": token_id,
            "yes_price": yes_price
        })
    
    # Check if arbitrage exists
    # Total cost must be < $1.00 - buffer
    threshold = 1.00 - config.NEGRISK_BUFFER
    
    if total_cost < threshold:
        expected_profit = 1.00 - total_cost
        roi = expected_profit / total_cost
        
        return {
            "event_id": event.get("id"),
            "event_name": event.get("title"),
            "outcomes": outcome_prices,
            "total_cost": total_cost,
            "expected_profit": expected_profit,
            "roi": roi
        }
    
    return None

async def execute_arbitrage(opportunity: Dict[str, Any]):
    """
    Execute NegRisk arbitrage by buying all outcomes
    """
    total_cost = opportunity["total_cost"]
    expected_profit = opportunity["expected_profit"]
    outcomes = opportunity["outcomes"]
    
    # Calculate how many sets we can buy
    balance = await paper_trading.get_available_balance()
    max_position = balance * config.NEGRISK_MAX_POSITION_PCT
    
    # Number of sets = min(max_position / total_cost, balance / total_cost)
    sets = min(max_position / total_cost, balance / total_cost)
    sets = int(sets)  # Whole sets only
    
    if sets < 1:
        tui_print(f"Insufficient balance for NegRisk arbitrage: need ${total_cost:.2f}")
        return
    
    # Generate unique arb_id to link all legs
    arb_id = str(uuid.uuid4())
    
    # Execute all legs
    tui_print(f"\n🎯 NegRisk Arbitrage Found!")
    tui_print(f"Event: {opportunity['event_name']}")
    tui_print(f"Total cost per set: ${total_cost:.3f}")
    tui_print(f"Expected profit per set: ${expected_profit:.3f} ({opportunity['roi']*100:.1f}% ROI)")
    tui_print(f"Buying {sets} sets...")
    
    for outcome in outcomes:
        market_id = outcome["market_id"]
        market_name = outcome["market_name"]
        yes_price = outcome["yes_price"]
        position_size = yes_price * sets
        
        await paper_trading.simulate_trade(
            strategy_id="NEGRISK_ARB",
            market_id=market_id,
            market_name=market_name,
            side="YES",
            price=yes_price,
            position_size_usd=position_size,
            is_crypto_15min=False,  # NegRisk is fee-free
            arb_id=arb_id
        )
    
    tui_print(f"✓ NegRisk arbitrage executed: {len(outcomes)} legs, {sets} sets, arb_id={arb_id[:8]}...")
