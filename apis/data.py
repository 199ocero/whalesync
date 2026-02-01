"""
Data API client for Polymarket
Handles leaderboard and whale activity tracking
"""

import httpx
from typing import List, Dict, Any, Optional
import config
from tui.logger import tui_print

async def fetch_leaderboard(
    time_period: str = "7d",
    limit: int = 100,
    sort_by: str = "profit"
) -> List[Dict[str, Any]]:
    """
    Fetch leaderboard data
    time_period: "1d", "7d", "30d", "all"
    sort_by: "profit", "volume", "trades"
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            response = await client.get(
                f"{config.DATA_API_BASE}/leaderboard",
                params={
                    "timePeriod": time_period,
                    "limit": limit,
                    "sortBy": sort_by
                },
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            tui_print(f"Error fetching leaderboard: {e}")
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
    """
    async with httpx.AsyncClient(verify=False, http2=False) as client:
        try:
            response = await client.get(
                f"{config.DATA_API_BASE}/trades",
                params={"wallet": wallet_address, "limit": limit},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            tui_print(f"Error fetching trades for {wallet_address}: {e}")
            return []
