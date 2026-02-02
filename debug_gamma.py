import asyncio
from apis import gamma
from tui.logger import tui_print
import config

# Mock tui_print to plain print for script execution
def tui_print(msg):
    print(msg)

async def test_gamma():
    print("--- Testing Crypto Markets Fetch ---")
    markets = await gamma.fetch_active_crypto_markets()
    if markets:
        m = markets[0]
        print(f"Sample Market ID: {m.get('id')}")
        print(f"Sample Question: {m.get('question')}")
        
        # Test fetching by ID
        print("\n--- Testing Fetch by Market ID ---")
        details = await gamma.fetch_market_details(m.get('id'))
        if details:
            print(f"Found details for {m.get('id')}")
            print(f"Question: {details.get('question')}")
        else:
            print("Failed to fetch by ID")
            
        # Test Condition ID logic (if we can find one)
        # Usually conditionId is in the market tokens
        # We will try to fake one or check if 'conditionId' is in the market object
        cond_id = m.get("conditionId")
        if cond_id:
            print(f"\n--- Testing Fetch by Condition ID ({cond_id}) via Data API ---")
            
            # Try using the /trades endpoint with 'market' param as per docs
            # https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets
            try:
                # Note: config.DATA_API_BASE is likely https://data-api.polymarket.com
                # We need to construct the URL manually or verify DATA_API_BASE first
                url = f"{config.DATA_API_BASE}/trades"
                params = {"market": cond_id, "limit": 1}
                print(f"Requesting: {url} with params {params}")
                
                async with gamma.httpx.AsyncClient(verify=False, http2=False) as client:
                    resp = await client.get(url, params=params, timeout=5.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            trade = data[0]
                            title = trade.get('title')
                            print(f"  -> Got Trade! Title: {title}")
                            if "bitcoin" in title.lower() or "btc" in title.lower():
                                print("  *** SUCCESS! match found via Data API ***")
                            else:
                                print("  (Mismatch in title logic, but API call worked)")
                        else:
                            print("  -> Success (200) but empty list (no recent trades?)")
                    else:
                         print(f"  -> HTTP {resp.status_code}: {resp.text}")

            except Exception as e:
                print(f"  -> Error: {e}")

    else:
        print("No active crypto markets found to test with.")

if __name__ == "__main__":
    asyncio.run(test_gamma())
