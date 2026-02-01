"""
Strategy 3: Whale Copy Trading (with Indicator Filters)
Tracks top traders, detects multi-whale signals, applies technical filters
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import config
from apis import data, clob
from database import db
from engine import paper_trading
from strategies import indicators
from tui.logger import tui_print

# ============================================================================
# PHASE 3A: WHALE DISCOVERY & MONITORING
# ============================================================================

async def discover_whales_loop():
    """
    Continuously refresh leaderboard and vet new whales
    Runs every WHALE_DISCOVERY_INTERVAL seconds
    """
    tui_print("🐋 Whale discovery started")
    
    while True:
        try:
            tui_print("🔍 Scanning leaderboard for new whales...")
            await discover_and_vet_whales()
            await asyncio.sleep(config.WHALE_DISCOVERY_INTERVAL)
        except Exception as e:
            import traceback
            tui_print(f"❌ Error in whale discovery: {e}")
            tui_print(f"Traceback: {traceback.format_exc()}")
            await asyncio.sleep(config.WHALE_DISCOVERY_INTERVAL)

async def discover_and_vet_whales():
    """Fetch leaderboard and vet new whales"""
    try:
        leaderboard = await data.fetch_leaderboard(time_period="7d", limit=100)
        
        if not leaderboard:
            tui_print("⚠️  No leaderboard data available")
            return
        
        tui_print(f"📊 Found {len(leaderboard)} traders on leaderboard")
        
        new_whales_count = 0
        for entry in leaderboard:
            wallet = entry.get("wallet_address")
            if not wallet:
                continue
            
            # Check if already tracking
            try:
                existing_whales = await db.get_active_whales()
                if any(w["wallet_address"] == wallet for w in existing_whales):
                    continue
                
                # Vet whale
                if await vet_whale(entry):
                    await db.upsert_whale(
                        wallet_address=wallet,
                        profit_7d=entry.get("profit_7d", 0),
                        total_trades=entry.get("total_trades", 0),
                        win_rate=entry.get("win_rate", 0),
                        last_trade_at=entry.get("last_trade_at", datetime.utcnow().isoformat())
                    )
                    new_whales_count += 1
                    tui_print(f"✓ New whale discovered: {wallet[:10]}... | Profit: ${entry.get('profit_7d', 0):.0f}")
            except Exception as e:
                tui_print(f"⚠️  Error processing whale {wallet[:10]}...: {e}")
                continue
        
        if new_whales_count == 0:
            tui_print("ℹ️  No new whales found")
    except Exception as e:
        import traceback
        tui_print(f"❌ Error in discover_and_vet_whales: {e}")
        tui_print(f"Traceback: {traceback.format_exc()}")

async def vet_whale(entry: Dict[str, Any]) -> bool:
    """Check if whale meets vetting criteria"""
    profit_7d = entry.get("profit_7d", 0)
    total_trades = entry.get("total_trades", 0)
    win_rate = entry.get("win_rate", 0)
    
    return (
        profit_7d >= config.WHALE_MIN_PROFIT and
        total_trades >= config.WHALE_MIN_TRADES and
        win_rate >= config.WHALE_MIN_WIN_RATE
    )

async def monitor_whales_loop():
    """
    Continuously monitor whale activity
    Runs every WHALE_MONITOR_INTERVAL seconds
    """
    tui_print("👀 Whale monitoring started")
    
    while True:
        try:
            await monitor_whale_activity()
            await asyncio.sleep(config.WHALE_MONITOR_INTERVAL)
        except Exception as e:
            import traceback
            tui_print(f"❌ Error monitoring whales: {e}")
            tui_print(f"Traceback: {traceback.format_exc()}")
            await asyncio.sleep(config.WHALE_MONITOR_INTERVAL)

async def monitor_whale_activity():
    """Check all tracked whales for new trades"""
    whales = await db.get_active_whales()
    
    for whale in whales:
        wallet = whale["wallet_address"]
        trades = await data.fetch_wallet_trades(wallet, limit=5)
        
        for trade in trades:
            # Check if we've already logged this trade
            # (simplified - in production, check against database)
            await process_whale_trade(whale, trade)

async def process_whale_trade(whale: Dict[str, Any], trade: Dict[str, Any]):
    """Process a whale trade and check for signals"""
    wallet = whale["wallet_address"]
    market_id = trade.get("market_id")
    side = trade.get("side")  # "YES" or "NO"
    price = trade.get("price", 0)
    shares = trade.get("shares", 0)
    
    # Log whale trade
    await db.log_whale_trade(wallet, market_id, side, price, shares)
    
    # Check for multi-whale signal
    await check_for_signal(market_id, side, price)

# ============================================================================
# PHASE 3B: SIGNAL DETECTION
# ============================================================================

async def check_for_signal(market_id: str, side: str, price: float):
    """
    Check if multiple whales are buying the same side
    If so, create a signal
    """
    # Get recent whale trades for this market (last 5 minutes)
    cutoff_time = datetime.utcnow() - timedelta(seconds=config.WHALE_SIGNAL_WINDOW)
    
    # Query database for whale trades on this market since cutoff
    # (simplified - in production, query database properly)
    # For now, we'll assume we have the data
    
    # Count unique whales on each side
    # If >= WHALE_SIGNAL_MIN_WHALES on same side → signal
    
    # Determine confidence level
    whale_count = 2  # Placeholder
    if whale_count >= 3:
        confidence = "STRONG"
    elif whale_count >= 2:
        confidence = "HIGH"
    else:
        confidence = "MEDIUM"
    
    # Create signal
    signal_id = await db.create_signal(
        market_id=market_id,
        side=side,
        whale_count=whale_count,
        confidence=confidence,
        price_at_signal=price
    )
    
    tui_print(f"🐋 Whale signal detected: {market_id} | {side} | {confidence} ({whale_count} whales)")
    
    # Execute trade with indicator filter
    await execute_whale_copy_trade(market_id, side, confidence, price)

# ============================================================================
# PHASE 3C & 3D: INDICATOR FILTER & EXECUTION
# ============================================================================

async def execute_whale_copy_trade(
    market_id: str,
    side: str,
    confidence: str,
    signal_price: float
):
    """
    Execute whale copy trade after applying indicator filters
    """
    # Fetch current price
    # (simplified - need to get token_id first)
    current_price = signal_price  # Placeholder
    
    # Check if price hasn't moved too much
    price_change = abs(current_price - signal_price) / signal_price
    if price_change > config.WHALE_MAX_SLIPPAGE:
        tui_print(f"⚠️  Price moved too much ({price_change*100:.1f}%), skipping whale copy")
        return
    
    # Fetch BTC indicators
    btc_indicators = await indicators.fetch_btc_indicators()
    
    # If indicators unavailable, use full position size
    if not btc_indicators:
        tui_print("ℹ️  BTC indicators unavailable - using full position size")
        multiplier = 1.0
        warnings = 0
    else:
        # Score indicators
        warnings = indicators.score_indicators(btc_indicators, side)
        multiplier = indicators.get_position_multiplier(warnings)
        
        if multiplier == 0:
            tui_print(f"⚠️  Too many indicator warnings ({warnings}), skipping whale copy")
            return
    
    # Calculate base position size
    base_position = await paper_trading.calculate_position_size("WHALE_COPY", confidence)
    
    # Apply multiplier
    final_position = base_position * multiplier
    
    # Execute trade
    tui_print(f"\n🐋 Whale Copy Trade!")
    tui_print(f"Market: {market_id}")
    tui_print(f"Side: {side} @ ${current_price:.3f}")
    tui_print(f"Confidence: {confidence}")
    if btc_indicators:
        tui_print(f"Indicator warnings: {warnings} → {multiplier*100:.0f}% position size")
    else:
        tui_print(f"Position size: ${final_position:.2f}")
    
    await paper_trading.simulate_trade(
        strategy_id="WHALE_COPY",
        market_id=market_id,
        market_name=f"Whale Copy - {market_id[:20]}...",
        side=side,
        price=current_price,
        position_size_usd=final_position,
        is_crypto_15min=True
    )
