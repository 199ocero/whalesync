"""
Data API client for Polymarket
Handles leaderboard and whale activity tracking
"""

import httpx
from typing import List, Dict, Any, Optional
import config
from tui.logger import tui_print

async def fetch_leaderboard(
    time_period: str = "WEEK",
    limit: int = 50,
    order_by: str = "PNL",
    category: str = "OVERALL"
) -> List[Dict[str, Any]]:
    """
    Fetch leaderboard data
    time_period: "DAY", "WEEK", "MONTH", "ALL"
    order_by: "PNL" (profit), "VOL" (volume)
    category: "OVERALL", "CRYPTO", "SPORTS", "POLITICS", etc.
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            url = f"{config.DATA_API_BASE}/v1/leaderboard"
            params = {
                "category": category,
                "timePeriod": time_period,
                "orderBy": order_by,
                "limit": min(limit, 50)  # API max is 50
            }
            
            tui_print(f"🔍 Fetching leaderboard: {url} with params {params}")
            
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            
            data = response.json()
            tui_print(f"✓ Leaderboard fetched: {len(data) if isinstance(data, list) else 'unknown'} traders")
            return data if isinstance(data, list) else []
            
        except httpx.HTTPStatusError as e:
            tui_print(f"❌ HTTP error fetching leaderboard: {e.response.status_code}")
            tui_print(f"Response: {e.response.text[:200]}")
            return []
        except Exception as e:
            tui_print(f"❌ Error fetching leaderboard: {type(e).__name__}: {e}")
            import traceback
            tui_print(f"Traceback: {traceback.format_exc()[:300]}")
            return []

async def fetch_wallet_activity(wallet_address: str) -> Optional[Dict[str, Any]]:
    """
    Fetch recent activity for a specific wallet
    Returns trades, positions, and performance metrics
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            response = await client.get(
                f"{config.DATA_API_BASE}/activity",
                params={"wallet": wallet_address},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            tui_print(f"Error fetching activity for {wallet_address}: {e}")
            return None

async def fetch_wallet_positions(wallet_address: str) -> List[Dict[str, Any]]:
    """
    Fetch current open positions for a wallet
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            response = await client.get(
                f"{config.DATA_API_BASE}/positions",
                params={"wallet": wallet_address},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            tui_print(f"Error fetching positions for {wallet_address}: {e}")
            return []

async def fetch_wallet_trades(
    wallet_address: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Fetch recent trades for a wallet
    Endpoint: GET /trades?user=<address>&limit=<limit>
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            # Correct endpoint with user parameter
            url = f"{config.DATA_API_BASE}/trades"
            params = {
                "user": wallet_address,
                "limit": limit
            }
            
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
                tui_print(f"  ✓ Fetched {len(data)} trades for {wallet_address[:10]}...")
                # Show sample trade structure for debugging
                if len(data) > 0:
                    tui_print(f"    Sample trade keys: {list(data[0].keys())[:10]}")
            
            return data if isinstance(data, list) else []
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                tui_print(f"⚠️  No trades found for wallet {wallet_address[:10]}...")
            else:
                tui_print(f"❌ Error fetching trades for {wallet_address[:10]}...: {type(e).__name__}: {e}")
            return []

async def fetch_market_from_trades(condition_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch market metadata (title, slug, etc.) using Condition ID
    by querying the trades endpoint with limit=1
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            # Use query parameter 'market' for Condition ID as per docs
            url = f"{config.DATA_API_BASE}/trades"
            params = {
                "market": condition_id,
                "limit": 1
            }
            
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            
            data = response.json()
            # Return the first trade object which contains market metadata (title, slug, etc)
            if data and isinstance(data, list) and len(data) > 0:
                market_data = data[0]
                # Map 'title' to 'question' to match expected format if needed, or caller handles it
                if "question" not in market_data and "title" in market_data:
                    market_data["question"] = market_data["title"]
                return market_data
            
            return None
            
        except Exception as e:
            tui_print(f"Error fetching market info from trades for {condition_id}: {e}")
            return None

async def fetch_market_prices(token_ids: List[str]) -> Dict[str, float]:
    """
    Fetch current prices for multiple markets from Polymarket Pricing API
    
    Args:
        token_ids: List of token IDs to fetch prices for
    
    Returns:
        Dict mapping token_id to current price (0-1 range)
    
    API Docs: https://docs.polymarket.com/api-reference/pricing/get-multiple-market-prices
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            # Polymarket Pricing API endpoint
            url = "https://clob.polymarket.com/prices"
            
            # Token IDs should be comma-separated
            params = {
                "token_ids": ",".join(token_ids)
            }
            
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            
            data = response.json()
            
            # Response format: {"token_id": "0.XX", ...}
            # Convert string prices to floats
            prices = {}
            for token_id, price_str in data.items():
                try:
                    prices[token_id] = float(price_str)
                except (ValueError, TypeError):
                    tui_print(f"⚠️  Invalid price for token {token_id}: {price_str}")
                    prices[token_id] = 0.0
            
            return prices
            
        except httpx.HTTPStatusError as e:
            tui_print(f"❌ HTTP error fetching Polymarket prices: {e.response.status_code}")
            tui_print(f"Response: {e.response.text[:200]}")
            return {}
        except Exception as e:
            tui_print(f"❌ Error fetching Polymarket prices: {type(e).__name__}: {e}")
            return {}
