"""
Main entry point for Polymarket Multi-Strategy Trading Bot
Initializes database, launches all strategies, and starts TUI
"""

import asyncio
import sys
from database import db
from engine import resolution
from strategies import negrisk_arb, high_prob_bond, whale_copy, temporal_arb

async def setup_paper_fund():
    """
    Check if paper fund exists, if not prompt user to create one
    """
    fund = await db.get_paper_fund()
    
    if fund:
        print(f"\n✓ Paper fund loaded: ${fund['current_balance']:.2f}")
        print(f"  Starting fund: ${fund['starting_fund']:.2f}")
        print(f"  All-time P&L: ${fund['total_profit'] - fund['total_loss']:.2f}")
        return True
    
    # First run - setup
    print("\n" + "="*60)
    print("  POLYMARKET MULTI-STRATEGY TRADING BOT — SETUP")
    print("="*60)
    print("\nWelcome! This bot runs in PAPER TRADE mode.")
    print("No real money will be used.\n")
    
    while True:
        try:
            starting_fund = input("Enter your starting fund (USD): $")
            starting_fund = float(starting_fund)
            
            if starting_fund < 10:
                print("❌ Minimum starting fund is $10")
                continue
            
            if starting_fund > 1000000:
                print("❌ Maximum starting fund is $1,000,000")
                continue
            
            break
        except ValueError:
            print("❌ Please enter a valid number")
    
    # Create paper fund
    await db.create_paper_fund(starting_fund)
    print(f"\n✓ Paper fund created: ${starting_fund:.2f}")
    print("\nStarting bot...\n")
    return True

async def main():
    """
    Main entry point
    """
    print("\n🚀 Polymarket Multi-Strategy Trading Bot")
    print("="*60)
    
    # Initialize database
    print("Initializing database...")
    await db.init_database()
    print("✓ Database initialized")
    
    # Setup paper fund
    if not await setup_paper_fund():
        print("Setup failed")
        return
    
    # Launch all background tasks
    tasks = []
    
    # Resolution engine (Phase 0.5)
    print("✓ Launching resolution engine...")
    tasks.append(asyncio.create_task(resolution.check_and_resolve_trades()))
    
    # Strategy 1: NegRisk Arbitrage
    print("✓ Launching NegRisk arbitrage scanner...")
    tasks.append(asyncio.create_task(negrisk_arb.scan_negrisk_arbitrage()))
    
    # Strategy 2: High-Probability Bonds
    print("✓ Launching high-probability bond scanner...")
    tasks.append(asyncio.create_task(high_prob_bond.scan_high_prob_bonds()))
    
    # Strategy 3: Whale Copy Trading
    print("✓ Launching whale discovery...")
    tasks.append(asyncio.create_task(whale_copy.discover_whales_loop()))
    print("✓ Launching whale monitoring...")
    tasks.append(asyncio.create_task(whale_copy.monitor_whales_loop()))
    
    # Strategy 4: Temporal Arbitrage
    # DISABLED - Requires external BTC price feeds (CoinGecko has rate limits)
    # print("✓ Launching temporal arbitrage scanner...")
    # tasks.append(asyncio.create_task(temporal_arb.scan_temporal_arbitrage()))
    
    print("\n" + "="*60)
    print("✓ All strategies running!")
    print("="*60)
    print("\nStarting TUI Dashboard...")
    await asyncio.sleep(2)  # Give user time to see success messages
    
    # Launch TUI
    from tui.app import PolymarketTUI
    tui_app = PolymarketTUI()
    await tui_app.run_async()
    
    # Verify cleanup (tasks are cancelled when TUI exits)
    print("\n\nShutting down...")
    for task in tasks:
        task.cancel()
    print("✓ Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
