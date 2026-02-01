"""
CLOB API client for Polymarket
Handles live prices and orderbook data
"""

import httpx
import asyncio
from typing import Dict, Any, Optional, List
import config
from tui.logger import tui_print

async def fetch_market_price(token_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch current YES/NO prices for a market token
    Returns dict with 'yes' and 'no' prices
    """
    # Validate token_id is a string
    if not token_id or not isinstance(token_id, str):
        tui_print(f"Invalid token_id: {token_id} (type: {type(token_id)})")
        return None
    
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            response = await client.get(
                f"{config.CLOB_API_BASE}/price",
                params={"token_id": token_id},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            tui_print(f"Error fetching price for {token_id} (HTTP {e.response.status_code}): {e.response.text[:200]}")
            return None
        except ValueError as e:
            tui_print(f"Error parsing price response for {token_id} (invalid JSON): {e}")
            return None
        except Exception as e:
            tui_print(f"Error fetching price for {token_id}: {e}")
            return None

async def fetch_orderbook(token_id: str, side: str = "BUY") -> Optional[Dict[str, Any]]:
    """
    Fetch orderbook for a specific token
    side: "BUY" or "SELL"
    Returns orderbook with bids/asks
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            response = await client.get(
                f"{config.CLOB_API_BASE}/book",
                params={"token_id": token_id, "side": side},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            tui_print(f"Error fetching orderbook for {token_id}: {e}")
            return None

async def check_liquidity(token_id: str, min_liquidity: float = 10.0) -> bool:
    """
    Check if there's sufficient liquidity at current price
    Returns True if orderbook has >= min_liquidity USD available
    """
    orderbook = await fetch_orderbook(token_id, "BUY")
    if not orderbook:
        return False
    
    # Sum up available liquidity from orderbook
    bids = orderbook.get("bids", [])
    total_liquidity = sum(float(bid.get("size", 0)) * float(bid.get("price", 0)) for bid in bids)
    
    return total_liquidity >= min_liquidity

async def fetch_multiple_prices(token_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetch prices for multiple tokens in parallel
    Returns dict mapping token_id to price data
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        tasks = []
        for token_id in token_ids:
            tasks.append(fetch_market_price(token_id))
        
        results = await asyncio.gather(*tasks)
        return {token_id: result for token_id, result in zip(token_ids, results) if result}
