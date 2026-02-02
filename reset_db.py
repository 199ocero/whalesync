import asyncio
import aiosqlite
import config

async def reset_db():
    print("⚠️  Resetting database...")
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # 1. Clear paper trades
        await db.execute("DELETE FROM paper_trades")
        print("✓ Cleared paper_trades table")
        
        # 2. Reset paper fund to $100
        await db.execute("""
            UPDATE paper_fund 
            SET current_balance = 100.0,
                starting_fund = 100.0,
                total_profit = 0,
                total_loss = 0,
                total_fees_paid = 0,
                total_trades = 0,
                winning_trades = 0,
                losing_trades = 0
            WHERE id = 1
        """)
        print("✓ Reset paper_fund to $100.00")
        
        # 3. Clear daily P&L
        await db.execute("DELETE FROM daily_pnl")
        print("✓ Cleared daily_pnl table")
        
        # 4. Clear signals (optional, but good for clean slate)
        await db.execute("DELETE FROM signals")
        print("✓ Cleared signals table")
        
        await db.commit()
    print("✅ Database reset complete!")

if __name__ == "__main__":
    confirm = input("Are you sure you want to reset the DB to $100? (y/n): ")
    if confirm.lower() == 'y':
        asyncio.run(reset_db())
    else:
        print("Cancelled.")
