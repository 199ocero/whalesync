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
                params={"negRisk": "true", "active": "true"},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            tui_print(f"Error fetching NegRisk events: {e}")
            return []

async def fetch_market_details(market_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch detailed information about a specific market
    Includes resolution status and winning outcome
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            response = await client.get(
                f"{config.GAMMA_API_BASE}/markets/{market_id}",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            tui_print(f"Error fetching market {market_id}: {e}")
            return None

async def fetch_active_crypto_markets() -> List[Dict[str, Any]]:
    """
    Fetch active crypto markets (for bond trading and temporal arbitrage)
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            response = await client.get(
                f"{config.GAMMA_API_BASE}/markets",
                params={"active": "true", "tag": "crypto"},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            tui_print(f"Error fetching crypto markets: {e}")
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
