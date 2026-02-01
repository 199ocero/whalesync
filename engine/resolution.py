"""
Resolution Engine (Phase 0.5)
Continuously checks open trades and settles them when markets resolve
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
import config
from database import db
from apis import gamma
from tui.logger import tui_print

async def check_and_resolve_trades():
    """
    Main resolution loop
    Runs every RESOLUTION_CHECK_INTERVAL seconds
    Checks all open trades and resolves them if market is resolved
    """
    while True:
        try:
            # Get all open trades
            open_trades = await db.get_open_trades()
            
            for trade in open_trades:
                await process_trade_resolution(trade)
            
            # Wait before next check
            await asyncio.sleep(config.RESOLUTION_CHECK_INTERVAL)
            
        except Exception as e:
            tui_print(f"Error in resolution engine: {e}")
            await asyncio.sleep(config.RESOLUTION_CHECK_INTERVAL)

async def process_trade_resolution(trade: Dict[str, Any]):
    """
    Check if a trade's market has resolved and settle it
    """
    market_id = trade["market_id"]
    trade_id = trade["id"]
    strategy_id = trade["strategy_id"]
    side = trade["side"]
    shares = trade["shares"]
    cost = trade["cost"]
    fee = trade["fee"]
    arb_id = trade.get("arb_id")
    
    # Fetch market details from Gamma API
    market = await gamma.fetch_market_details(market_id)
    if not market:
        return
    
    # Check if resolved
    is_resolved = market.get("resolved", False)
    if not is_resolved:
        return
    
    # Get winning outcome
    winning_outcome = market.get("winningOutcome")  # "YES" or "NO"
    
    # Calculate payout
    if strategy_id == "NEGRISK_ARB" and arb_id:
        # Special case: NegRisk arbitrage
        # We bought all outcomes, so exactly one wins
        # Need to check if THIS leg won
        payout = await calculate_negrisk_payout(trade, winning_outcome, arb_id)
    else:
        # Normal trade
        if side == winning_outcome:
            # WIN: Each share pays $1.00
            payout = shares * 1.00
        else:
            # LOSS: Shares are worthless
            payout = 0.0
    
    # Calculate profit or loss
    profit_or_loss = payout - cost - fee
    
    # Determine if win or loss
    is_win = profit_or_loss > 0
    is_loss = profit_or_loss < 0
    
    # Update trade record
    outcome = "WIN" if is_win else "LOSS"
    await db.resolve_trade(
        trade_id=trade_id,
        outcome=outcome,
        payout=payout,
        profit_or_loss=profit_or_loss
    )
    
    # Update paper fund balance
    fund = await db.get_paper_fund()
    current_balance = fund["current_balance"]
    new_balance = current_balance + payout
    
    await db.update_paper_fund_balance(
        new_balance=new_balance,
        profit=profit_or_loss if is_win else 0,
        loss=abs(profit_or_loss) if is_loss else 0,
        fee=fee,
        is_win=is_win,
        is_loss=is_loss
    )
    
    # Update daily P&L
    await db.update_daily_pnl(strategy_id, profit_or_loss)
    
    # Log resolution
    symbol = "✓" if is_win else "✗"
    color = "green" if is_win else "red"
    tui_print(f"{symbol} Trade resolved: {trade['market_name']} | {side} | {outcome} | P&L: ${profit_or_loss:.2f}")

async def calculate_negrisk_payout(
    trade: Dict[str, Any],
    winning_outcome: str,
    arb_id: str
) -> float:
    """
    Calculate payout for a NegRisk arbitrage leg
    
    NegRisk arbitrage: we bought ALL outcomes, so one MUST win
    Total payout across all legs = $1.00 per set
    This leg pays $1.00 if it won, $0 if it lost
    """
    side = trade["side"]
    shares = trade["shares"]
    
    if side == winning_outcome:
        # This leg won
        return shares * 1.00
    else:
        # This leg lost
        return 0.0
