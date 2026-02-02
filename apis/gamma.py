"""
Gamma API client for Polymarket
Handles market discovery, NegRisk events, and resolution status
"""

import httpx
from typing import List, Dict, Any, Optional
import config
from tui.logger import tui_print

async def fetch_negrisk_events() -> List[Dict[str, Any]]:
    """
    Fetch all active NegRisk events from Gamma API
    Returns list of events with their market conditions
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            response = await client.get(
                f"{config.GAMMA_API_BASE}/events",
                params={"negRisk": "true", "closed": "false"},
                timeout=10.0
            )
            response.raise_for_status()
            events = response.json()
            tui_print(f"✓ Fetched {len(events) if isinstance(events, list) else 0} NegRisk events")
            return events if isinstance(events, list) else []
        except httpx.HTTPStatusError as e:
            tui_print(f"❌ HTTP {e.response.status_code} fetching NegRisk events")
            tui_print(f"   Response: {e.response.text[:200]}")
            return []
        except Exception as e:
            tui_print(f"❌ Error fetching NegRisk events: {type(e).__name__}: {e}")
            return []

async def fetch_market_details(market_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch detailed information about a specific market
    Includes resolution status and winning outcome
    Supports both Market ID and Condition ID (0x...)
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            # Check if this is a Condition ID (starts with 0x)
            if market_id.startswith("0x"):
                # Use query parameter for Condition ID
                response = await client.get(
                    f"{config.GAMMA_API_BASE}/markets",
                    params={"conditionId": market_id},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                # API returns a list for search queries, take the first result
                return data[0] if isinstance(data, list) and len(data) > 0 else None
            else:
                # Use path parameter for Market ID
                response = await client.get(
                    f"{config.GAMMA_API_BASE}/markets/{market_id}",
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                tui_print(f"⚠️  Market not found: {market_id}")
                return None
            tui_print(f"❌ HTTP {e.response.status_code} fetching market {market_id}")
            return None
        except Exception as e:
            tui_print(f"Error fetching market {market_id}: {e}")
            return None

async def fetch_active_crypto_markets() -> List[Dict[str, Any]]:
    """
    Fetch active crypto markets (for bond trading and temporal arbitrage)
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            # Correct parameters: closed=false for active markets
            # Note: filtering by crypto tag may need to be done client-side
            response = await client.get(
                f"{config.GAMMA_API_BASE}/markets",
                params={
                    "closed": "false",
                    "limit": 100
                },
                timeout=10.0
            )
            response.raise_for_status()
            
            markets = response.json()
            
            # Filter for crypto markets client-side if needed
            # (check if market question/title contains crypto terms)
            crypto_markets = []
            for market in markets:
                question = market.get("question", "").lower()
                if any(term in question for term in ["btc", "bitcoin", "eth", "ethereum", "crypto", "xrp"]):
                    crypto_markets.append(market)
            
            tui_print(f"✓ Fetched {len(crypto_markets)} crypto markets (from {len(markets)} total)")
            return crypto_markets
            
        except httpx.HTTPStatusError as e:
            tui_print(f"❌ HTTP {e.response.status_code} fetching crypto markets")
            tui_print(f"   Response: {e.response.text[:200]}")
            return []
        except Exception as e:
            tui_print(f"❌ Error fetching crypto markets: {type(e).__name__}: {e}")
            return []

async def fetch_event_markets(event_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all markets for a specific event (used for NegRisk arbitrage)
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            response = await client.get(
                f"{config.GAMMA_API_BASE}/events/{event_id}",
                timeout=10.0
            )
            response.raise_for_status()
            event_data = response.json()
            return event_data.get("markets", [])
        except Exception as e:
            tui_print(f"Error fetching event {event_id} markets: {e}")
            return []
