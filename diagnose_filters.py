import asyncio
from apis import data
from tui.logger import tui_print
import config

# Mock tui_print
def tui_print(msg):
    print(msg)

async def diagnose():
    print("🔍 -- STARTING DIAGNOSTIC --")
    
    # 1. Fetch Leaderboard
    print("\n1. Fetching CRYPTO Leaderboard...")
    leaderboard = await data.fetch_leaderboard(time_period="WEEK", category="CRYPTO")
    if not leaderboard:
        print("❌ Failed to fetch leaderboard!")
        return
        
    top_whale = leaderboard[0]
    wallet = top_whale.get("proxyWallet")
    print(f"✓ Top Whale: {wallet} (PnL: {top_whale.get('pnl')})")
    
    # 2. Fetch Trades
    print(f"\n2. Fetching last 5 trades for {wallet}...")
    trades = await data.fetch_wallet_trades(wallet, limit=5)
    if not trades:
        print("❌ No trades found for this whale.")
        return
        
    print(f"✓ Found {len(trades)} trades.")
    
    # 3. Test Filter Logic
    print("\n3. Testing Filters on Trades...")
    for i, trade in enumerate(trades):
        market_id = trade.get("conditionId")
        print(f"\n-- Trade {i+1}: Market {market_id} --")
        
        if not market_id:
            print("  ❌ Missing conditionId")
            continue
            
        print("  > Fetching market details via data.fetch_market_from_trades...")
        try:
            market_details = await data.fetch_market_from_trades(market_id)
            if not market_details:
                print("  ❌ data.fetch_market_from_trades returned None")
                continue
                
            question = market_details.get("question", "")
            title = market_details.get("title", "")
            final_question = question or title
            
            print(f"  > Market Question: '{final_question}'")
            
            # Run the EXACT check from whale_copy.py
            is_crypto = any(x in final_question.lower() for x in ["btc", "eth", "bitcoin", "ethereum"])
            
            if is_crypto:
                print("  ✅ PASS: Market is Crypto")
            else:
                print("  ⛔ FAIL: Market is NOT Crypto (Filter rejected it)")
                
        except Exception as e:
            print(f"  ❌ Exception during lookup: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose())
