"""
WebSocket client for Polymarket
Handles real-time orderbook updates for arbitrage detection
"""

import websockets
import json
import asyncio
from typing import Callable, Optional
import config
from tui.logger import tui_print

class PolymarketWebSocket:
    """WebSocket connection manager for Polymarket CLOB"""
    
    def __init__(self):
        self.ws = None
        self.subscriptions = {}
        self.running = False
    
    async def connect(self):
        """Establish WebSocket connection"""
        try:
            self.ws = await websockets.connect(config.WEBSOCKET_URL)
            self.running = True
            tui_print("WebSocket connected")
        except Exception as e:
            tui_print(f"WebSocket connection error: {e}")
            self.running = False
    
    async def subscribe_market(self, market_id: str, callback: Callable):
        """
        Subscribe to orderbook updates for a market
        callback: async function to handle updates
        """
        if not self.ws:
            await self.connect()
        
        subscribe_msg = {
            "type": "subscribe",
            "market": market_id,
            "channel": "orderbook"
        }
        
        try:
            await self.ws.send(json.dumps(subscribe_msg))
            self.subscriptions[market_id] = callback
            tui_print(f"Subscribed to market {market_id}")
        except Exception as e:
            tui_print(f"Error subscribing to {market_id}: {e}")
    
    async def unsubscribe_market(self, market_id: str):
        """Unsubscribe from a market"""
        if not self.ws:
            return
        
        unsubscribe_msg = {
            "type": "unsubscribe",
            "market": market_id
        }
        
        try:
            await self.ws.send(json.dumps(unsubscribe_msg))
            if market_id in self.subscriptions:
                del self.subscriptions[market_id]
            tui_print(f"Unsubscribed from market {market_id}")
        except Exception as e:
            tui_print(f"Error unsubscribing from {market_id}: {e}")
    
    async def listen(self):
        """
        Listen for WebSocket messages and route to callbacks
        This should run in a background task
        """
        while self.running:
            try:
                if not self.ws:
                    await self.connect()
                    await asyncio.sleep(5)
                    continue
                
                message = await self.ws.recv()
                data = json.loads(message)
                
                # Route message to appropriate callback
                market_id = data.get("market")
                if market_id and market_id in self.subscriptions:
                    callback = self.subscriptions[market_id]
                    await callback(data)
                
            except websockets.exceptions.ConnectionClosed:
                tui_print("WebSocket connection closed, reconnecting...")
                self.running = False
                await asyncio.sleep(5)
                await self.connect()
            except Exception as e:
                tui_print(f"WebSocket error: {e}")
                await asyncio.sleep(1)
    
    async def close(self):
        """Close WebSocket connection"""
        self.running = False
        if self.ws:
            await self.ws.close()
            tui_print("WebSocket closed")

# Global WebSocket instance
ws_client = PolymarketWebSocket()
