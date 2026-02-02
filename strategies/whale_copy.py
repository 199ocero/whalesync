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
from apis import gamma
from tui.logger import tui_print

# ============================================================================
# PHASE 3A: WHALE DISCOVERY & MONITORING
# ============================================================================

# Global set to track markets currently being processed to prevent race conditions
PROCESSING_MARKETS = set()

# Global dict to store market metadata (asset, resolution_time)
MARKET_METADATA = {}

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
        # Fetch leaderboard with correct parameters
        leaderboard = await data.fetch_leaderboard(time_period="DAY", limit=15, order_by="PNL", category="CRYPTO")
        
        if not leaderboard:
            tui_print("⚠️  No leaderboard data available")
            return
        
        tui_print(f"📊 Found {len(leaderboard)} traders on leaderboard")
        
        new_whales_count = 0
        for entry in leaderboard:
            # API returns 'proxyWallet' not 'wallet_address'
            wallet = entry.get("proxyWallet")
            if not wallet:
                tui_print(f"⚠️  Entry missing proxyWallet: {list(entry.keys())[:5]}")
                continue
            
            # Check if already tracking
            try:
                existing_whales = await db.get_active_whales()
                if any(w["wallet_address"] == wallet for w in existing_whales):
                    continue
                
                # Convert API response to our format
                # API provides: proxyWallet, pnl, vol, rank, userName
                # We need to estimate trades from volume (rough estimate: 1 trade per $100 volume)
                estimated_trades = max(int(entry.get("vol", 0) / 100), 1)
                
                whale_data = {
                    "wallet_address": wallet,
                    "profit_7d": entry.get("pnl", 0),  # API uses 'pnl' not 'profit_7d'
                    "total_trades": estimated_trades,  # Estimated from volume
                    "win_rate": 0.6,  # API doesn't provide win rate, use default
                    "last_trade_at": datetime.utcnow().isoformat()
                }
                
                # Vet whale
                if await vet_whale(whale_data):
                    await db.upsert_whale(
                        wallet_address=wallet,
                        profit_7d=whale_data["profit_7d"],
                        total_trades=whale_data["total_trades"],
                        win_rate=whale_data["win_rate"],
                        last_trade_at=whale_data["last_trade_at"]
                    )
                    new_whales_count += 1
                    tui_print(f"✓ New whale discovered: {wallet[:10]}... | Profit: ${whale_data['profit_7d']:.0f}")
            except Exception as e:
                tui_print(f"⚠️  Error processing whale {wallet[:10]}...: {e}")
                import traceback
                tui_print(f"Traceback: {traceback.format_exc()[:200]}")
                continue
        
        if new_whales_count == 0:
            tui_print("ℹ️  No new whales found (all already tracked)")
        else:
            tui_print(f"✓ Discovered {new_whales_count} new whales")
    except Exception as e:
        import traceback
        tui_print(f"❌ Error in discover_and_vet_whales: {e}")
        tui_print(f"Traceback: {traceback.format_exc()}")

async def vet_whale(whale_data: Dict[str, Any]) -> bool:
    """Check if whale meets vetting criteria"""
    profit_7d = whale_data.get("profit_7d", 0)
    total_trades = whale_data.get("total_trades", 0)
    win_rate = whale_data.get("win_rate", 0)
    
    meets_criteria = (
        profit_7d >= config.WHALE_MIN_PROFIT and
        total_trades >= config.WHALE_MIN_TRADES and
        win_rate >= config.WHALE_MIN_WIN_RATE
    )
    
    if not meets_criteria:
        tui_print(f"  ⊘ Whale failed vetting: profit=${profit_7d:.0f} (need ${config.WHALE_MIN_PROFIT}), trades={total_trades} (need {config.WHALE_MIN_TRADES})")
    
    return meets_criteria

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
    
    if not whales:
        tui_print("ℹ️  No whales to monitor yet")
        return
    
    # Only log monitoring message occasionally to reduce spam
    # tui_print(f"👀 Monitoring {len(whales)} whales for activity...")
    
    trades_found = 0
    for whale in whales:
        wallet = whale["wallet_address"]
        trades = await data.fetch_wallet_trades(wallet, limit=5)
        
        if trades:
            trades_found += len(trades)
            tui_print(f"  📊 Found {len(trades)} recent trades for {wallet[:10]}...")
        
        for trade in trades:
            # Check if we've already logged this trade
            # (simplified - in production, check against database)
            await process_whale_trade(whale, trade)
    
    if trades_found > 0:
        tui_print(f"✓ Processed {trades_found} whale trades")

async def process_whale_trade(whale: Dict[str, Any], trade: Dict[str, Any]):
    """
    Process a whale trade and check for signals
    
    Polymarket API trade format:
    {
        "proxyWallet": "0x...",
        "side": "BUY" or "SELL",
        "asset": "token_id",  # Long number, not useful
        "conditionId": "market_id",
        "outcome": "Up" / "Down" / "Yes" / "No" / etc,
        "outcomeIndex": 0 or 1,
        "size": "shares",
        "price": "price",
        "timestamp": "unix_timestamp",
        "transactionHash": "0x..."
    }
    """
    wallet = whale["wallet_address"]
    
    # Map Polymarket API fields to our format
    market_id = trade.get("conditionId")  # Polymarket uses conditionId for market
    outcome = trade.get("outcome", "")  # "Up", "Down", "Yes", "No", etc
    outcome_index = trade.get("outcomeIndex", 0)  # 0 or 1
    price = float(trade.get("price", 0))
    shares = float(trade.get("size", 0))
    
    # Normalize outcome to YES/NO
    # outcomeIndex 0 is typically YES/Up, 1 is NO/Down
    if outcome_index == 0:
        side = "YES"
    else:
        side = "NO"
    
    # Validate required fields
    if not market_id:
        tui_print(f"  ⚠️  Skipping incomplete trade data: conditionId={market_id}")
        tui_print(f"      Trade keys available: {list(trade.keys())[:10]}")
        return
    
    # Check if market is a 15-minute crypto market
    # Fetch full market details to verify
    try:
        # Use Gamma API to fetch market info (includes endDate field)
        market_details = await gamma.fetch_market_details(market_id)
        
        if not market_details:
            tui_print(f"  ⚠️  Could not fetch details for {market_id}, skipping")
            return
            
        # Check description/question for BTC/ETH and 15m context
        question = market_details.get("question", "").lower()
        
        # EXTRACT ASSET
        detected_asset = "Crypto"
        for asset in ["btc", "eth", "sol", "doge", "avax", "link", "uni", "matic", "bitcoin", "ethereum", "solana", "cardano", "ripple", "xrp"]:
            if asset in question:
                detected_asset = asset.upper()
                if detected_asset == "BITCOIN": detected_asset = "BTC"
                if detected_asset == "ETHEREUM": detected_asset = "ETH"
                if detected_asset == "SOLANA": detected_asset = "SOL"
                if detected_asset == "RIPPLE": detected_asset = "XRP"
                break
                
        if not any(x in question for x in ["btc", "eth", "sol", "doge", "avax", "link", "uni", "matic", "bitcoin", "ethereum", "solana", "cardano", "ripple", "xrp"]):
            # Not a major crypto market
            tui_print(f"  ℹ️  Skipping non-crypto market ({market_id[:10]}...): '{question}'")
            return
            
        # CALCULATE TIME TO RESOLUTION
        time_msg = ""
        resolution_time_iso = None  # Initialize here to ensure it's in scope
        end_date_str = market_details.get("endDate") or market_details.get("resolutionTime")
        if end_date_str:
            # Store the original ISO timestamp for database
            resolution_time_iso = end_date_str
            
            try:
                # ISO format usually "2024-02-02T12:00:00Z"
                end_date_clean = end_date_str
                if end_date_str.endswith("Z"):
                    end_date_clean = end_date_str[:-1]
                end_dt = datetime.fromisoformat(end_date_clean)
                now = datetime.utcnow()
                delta = end_dt - now
                
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                if delta.days < 0:
                   time_msg = " (Ended)"
                else:
                   time_msg = f" | ⏳ Ends: {hours}h {minutes}m"
            except Exception:
                pass
            
        processed_msg = f"  ✓ Verified {detected_asset} market{time_msg}"
        # tui_print(processed_msg) # Optional debug log
        
    except Exception as e:
        tui_print(f"Error validating market type: {e}")
        return
    

    try:
        was_logged = await db.log_whale_trade(wallet, market_id, side, price, shares)
        
        if not was_logged:
            # Duplicate trade - skip
            return
        
        # Use detected_asset and time_msg from above if available
        asset_info = locals().get('detected_asset', 'Crypto')
        time_info = locals().get('time_msg', '')
        
        tui_print(f"  ✓ Logged whale: {wallet[:6]}.. | {asset_info} | {side} @ ${price:.2f}{time_info}")
        
        # Store market metadata for later use (resolution_time_iso is now properly in scope)
        MARKET_METADATA[market_id] = {
            'asset': asset_info,
            'resolution_time': resolution_time_iso
        }
        
        # Check for multi-whale signal
        await check_for_signal(market_id, side, price)
    except Exception as e:
        tui_print(f"  ❌ Error logging whale trade: {e}")
        import traceback
        tui_print(f"      {traceback.format_exc()[:200]}")

# ============================================================================
# PHASE 3B: SIGNAL DETECTION
# ============================================================================

async def check_for_signal(market_id: str, side: str, price: float):
    """
    Check if multiple whales are buying the same side
    Only creates signal when 2+ whales converge
    """
    # Concurrency Guard: Don't process if already processing this market
    if market_id in PROCESSING_MARKETS:
        return
        
    PROCESSING_MARKETS.add(market_id)
    
    try:
        # Get recent whale trades for this market (last 5 minutes)
        cutoff_time = datetime.utcnow() - timedelta(seconds=config.WHALE_SIGNAL_WINDOW)
        
        # Query database for whale trades on this market since cutoff
        trades = await db.get_whale_trades_for_market(market_id, cutoff_time)
        
        if not trades:
            return  # No trades yet
        
        # Count unique whales on each side
        whales_yes = set()
        whales_no = set()
        
        for trade in trades:
            if trade['side'] == 'YES':
                whales_yes.add(trade['wallet_address'])
            else:
                whales_no.add(trade['wallet_address'])
        
        whale_count = len(whales_yes) if side == 'YES' else len(whales_no)
        
        # Only create signal if we have enough whales
        if whale_count < config.WHALE_SIGNAL_MIN_WHALES:
            return  # Not enough convergence
        
        # Check position limits BEFORE creating signal
        open_trades = await db.get_open_trades()
        whale_copy_trades = [t for t in open_trades if t['strategy_id'] == 'whale_copy']
        
        if len(whale_copy_trades) >= 5:  # Max 5 open whale copy positions
            tui_print(f"⚠️  Max whale copy positions reached (5/5), skipping signal")
            return
        
        # Check if we already have a position on this market
        for trade in whale_copy_trades:
            if trade['market_id'] == market_id:
                tui_print(f"  ℹ️  Already have position on this market, skipping")
                return
        
        # Determine confidence level based on whale count
        if whale_count >= 3:
            confidence = "STRONG"   # 3+ whales agree (rare, very high confidence)
        elif whale_count >= 2:
            confidence = "HIGH"     # 2 whales agree (good confirmation)
        elif whale_count >= 1:
            confidence = "MEDIUM"   # 1 whale (smart money following)
        else:
            return  # No whales (shouldn't happen)
        
        # Create signal
        signal_id = await db.create_signal(
            market_id=market_id,
            side=side,
            whale_count=whale_count,
            confidence=confidence,
            price_at_signal=price
        )
        
        tui_print(f"🐋 Whale signal: {whale_count} whales on {side} | {confidence} confidence")
        
        # Execute trade with indicator filter
        await execute_whale_copy_trade(market_id, side, confidence, price)
        
    except Exception as e:
        tui_print(f"❌ Error in check_for_signal: {type(e).__name__}: {e}")
        import traceback
        tui_print(f"   {traceback.format_exc()[:300]}")
    finally:
        # Release lock
        if market_id in PROCESSING_MARKETS:
            PROCESSING_MARKETS.remove(market_id)

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
    # Get market metadata
    metadata = MARKET_METADATA.get(market_id, {})
    asset = metadata.get('asset', 'Crypto')
    resolution_time = metadata.get('resolution_time')
    
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
        market_name=f"Whale Copy - {asset}",
        side=side,
        price=current_price,
        position_size_usd=final_position,
        is_crypto_15min=True,
        asset=asset,
        resolution_time=resolution_time
    )
