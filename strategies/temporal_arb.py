"""
Strategy 4: Temporal Arbitrage
Exploits Polymarket pricing lag vs real BTC price movement
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import config
from apis import gamma, clob, price_feeds
from engine import paper_trading
from tui.logger import tui_print

async def scan_temporal_arbitrage():
    """
    Main scanner loop for temporal arbitrage
    Runs every TEMPORAL_SCAN_INTERVAL second
    """
    tui_print("⚡ Temporal arbitrage scanner started")
    
    while True:
        try:
            tui_print("🔍 Scanning for temporal arbitrage opportunities...")
            await find_and_execute_temporal_arb()
            await asyncio.sleep(config.TEMPORAL_SCAN_INTERVAL)
        except Exception as e:
            tui_print(f"Error in temporal arb scanner: {e}")
            await asyncio.sleep(config.TEMPORAL_SCAN_INTERVAL)

async def find_and_execute_temporal_arb():
    """
    Check for temporal arbitrage opportunities
    """
    # Fetch current BTC price from both exchanges
    btc_prices = await price_feeds.fetch_btc_price_both()
    binance_price = btc_prices.get("binance")
    coinbase_price = btc_prices.get("coinbase")
    
    if not binance_price or not coinbase_price:
        return
    
    # Use average for confirmation
    btc_price = (binance_price + coinbase_price) / 2
    
    # Fetch active 15-min BTC markets
    markets = await gamma.fetch_active_crypto_markets()
    
    for market in markets:
        # Check if this is a 15-minute BTC Up/Down market
        market_name = market.get("question", "")
        if "15" not in market_name.lower() or "btc" not in market_name.lower():
            continue
        
        if "up" not in market_name.lower() and "down" not in market_name.lower():
            continue
        
        # Check for opportunity
        opportunity = await check_temporal_opportunity(market, btc_price)
        if opportunity:
            await execute_temporal_arb(opportunity)

async def check_temporal_opportunity(
    market: Dict[str, Any],
    current_btc_price: float
) -> Optional[Dict[str, Any]]:
    """
    Check if there's a temporal arbitrage opportunity
    """
    market_id = market.get("id")
    market_name = market.get("question")
    
    # Parse market to get start time, end time, and starting BTC price
    # (simplified - in production, parse from market metadata)
    # For now, we'll use placeholder values
    
    # Get market end time
    end_time_str = market.get("endDate")
    if not end_time_str:
        return None
    
    end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
    time_remaining = (end_time - datetime.utcnow()).total_seconds()
    
    # Only consider if < 10 minutes remaining
    if time_remaining > config.TEMPORAL_MAX_TIME_REMAINING:
        return None
    
    # Get starting BTC price from market metadata
    # (simplified - need to parse from market description)
    starting_btc_price = 105000  # Placeholder
    
    # Calculate BTC movement
    btc_move_pct = (current_btc_price - starting_btc_price) / starting_btc_price
    
    # Check if BTC has moved significantly
    if abs(btc_move_pct) < config.TEMPORAL_MIN_MOVE_PCT:
        return None
    
    # Determine which side should win
    if btc_move_pct > 0:
        expected_winner = "YES"  # BTC is Up
    else:
        expected_winner = "NO"   # BTC is Down
    
    # Fetch current market prices
    clob_token_ids = market.get("clobTokenIds", [])
    if not clob_token_ids or not isinstance(clob_token_ids, list) or len(clob_token_ids) < 2:
        return None
    
    yes_token_id = clob_token_ids[0]
    no_token_id = clob_token_ids[1]
    
    # Validate token IDs
    if not yes_token_id or not isinstance(yes_token_id, str):
        return None
    
    price_data = await clob.fetch_market_price(yes_token_id)
    if not price_data:
        return None
    
    yes_price = float(price_data.get("yes", 0))
    no_price = float(price_data.get("no", 0))
    
    # Check for mispricing
    if expected_winner == "YES":
        # YES should be priced high, but if it's still low → opportunity
        if yes_price < 0.70:  # Threshold
            mispricing_pct = (0.90 - yes_price) / yes_price
            if mispricing_pct >= config.TEMPORAL_MIN_MISPRICING_PCT:
                return {
                    "market_id": market_id,
                    "market_name": market_name,
                    "side": "YES",
                    "price": yes_price,
                    "btc_move_pct": btc_move_pct,
                    "time_remaining": time_remaining,
                    "mispricing_pct": mispricing_pct
                }
    else:
        # NO should be priced high
        if no_price < 0.70:
            mispricing_pct = (0.90 - no_price) / no_price
            if mispricing_pct >= config.TEMPORAL_MIN_MISPRICING_PCT:
                return {
                    "market_id": market_id,
                    "market_name": market_name,
                    "side": "NO",
                    "price": no_price,
                    "btc_move_pct": btc_move_pct,
                    "time_remaining": time_remaining,
                    "mispricing_pct": mispricing_pct
                }
    
    return None

async def execute_temporal_arb(opportunity: Dict[str, Any]):
    """
    Execute temporal arbitrage trade
    """
    market_id = opportunity["market_id"]
    market_name = opportunity["market_name"]
    side = opportunity["side"]
    price = opportunity["price"]
    btc_move_pct = opportunity["btc_move_pct"]
    time_remaining = opportunity["time_remaining"]
    mispricing_pct = opportunity["mispricing_pct"]
    
    # Calculate position size
    position_size = await paper_trading.calculate_position_size("TEMPORAL_ARB")
    
    # Execute trade
    tui_print(f"\n⚡ Temporal Arbitrage Found!")
    tui_print(f"Market: {market_name}")
    tui_print(f"BTC moved: {btc_move_pct*100:+.2f}%")
    tui_print(f"Side: {side} @ ${price:.3f}")
    tui_print(f"Mispricing: {mispricing_pct*100:.1f}%")
    tui_print(f"Time remaining: {time_remaining/60:.1f} minutes")
    
    await paper_trading.simulate_trade(
        strategy_id="TEMPORAL_ARB",
        market_id=market_id,
        market_name=market_name,
        side=side,
        price=price,
        position_size_usd=position_size,
        is_crypto_15min=True
    )
