"""
Price feeds API client
Fetches BTC prices from Binance and Coinbase for temporal arbitrage and indicators
"""

import httpx
from typing import Optional, Dict, Any, List
import config
from tui.logger import tui_print
import time

# Simple cache to prevent rate limiting
_btc_price_cache = {"price": None, "timestamp": 0}
_CACHE_DURATION = 30  # seconds

# ============================================================================
# BINANCE API (Primary)
# ============================================================================

async def fetch_binance_btc_price() -> Optional[float]:
    """
    Fetch current BTC/USD price from CoinGecko (replacing Binance due to ISP blocking)
    Returns price as float or None if error
    Uses 30-second cache to prevent rate limiting
    """
    global _btc_price_cache
    
    # Check cache
    current_time = time.time()
    if _btc_price_cache["price"] and (current_time - _btc_price_cache["timestamp"]) < _CACHE_DURATION:
        return _btc_price_cache["price"]
    
    async with httpx.AsyncClient(verify=False, http2=False, follow_redirects=True) as client:
        try:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd"},
                timeout=10.0,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            response.raise_for_status()
            data = response.json()
            price = float(data.get("bitcoin", {}).get("usd", 0))
            
            # Update cache
            _btc_price_cache["price"] = price
            _btc_price_cache["timestamp"] = current_time
            
            return price
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                tui_print(f"⚠️  CoinGecko rate limit hit - using cached price if available")
                return _btc_price_cache.get("price")
            tui_print(f"Error fetching CoinGecko BTC price (HTTP {e.response.status_code}): {e.response.text[:200]}")
            return _btc_price_cache.get("price")  # Return cached price on error
        except ValueError as e:
            tui_print(f"Error parsing CoinGecko BTC price response (invalid JSON): {e}")
            return _btc_price_cache.get("price")
        except Exception as e:
            tui_print(f"Error fetching CoinGecko BTC price: {e}")
            return _btc_price_cache.get("price")

async def fetch_binance_btc_candles(
    interval: str = "1h",
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Fetch BTC/USDT candlestick data from Binance
    interval: "1m", "5m", "15m", "1h", "4h", "1d"
    limit: number of candles to fetch
    Returns list of candles with OHLCV data
    
    NOTE: DISABLED - Binance API is blocked by ISP (PLDT Smart)
    """
    return []

# ============================================================================
# COINBASE API (Backup)
# ============================================================================

async def fetch_coinbase_btc_price() -> Optional[float]:
    """
    Fetch current BTC/USD price from Blockchain.info (replacing Coinbase due to ISP blocking)
    Returns price as float or None if error
    """
    async with httpx.AsyncClient(verify=False, http2=False, follow_redirects=True) as client:
        try:
            response = await client.get(
                "https://blockchain.info/ticker",
                timeout=10.0,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            response.raise_for_status()
            data = response.json()
            return float(data.get("USD", {}).get("last", 0))
        except httpx.HTTPStatusError as e:
            tui_print(f"Error fetching Blockchain.info BTC price (HTTP {e.response.status_code}): {e.response.text[:200]}")
            return None
        except ValueError as e:
            tui_print(f"Error parsing Blockchain.info BTC price response (invalid JSON): {e}")
            return None
        except Exception as e:
            tui_print(f"Error fetching Blockchain.info BTC price: {e}")
            return None

# ============================================================================
# UNIFIED PRICE FETCHER
# ============================================================================

async def fetch_btc_price() -> Optional[float]:
    """
    Fetch BTC price with fallback
    Tries Binance first, falls back to Coinbase if Binance fails
    """
    price = await fetch_binance_btc_price()
    if price:
        return price
    
    # Fallback to Coinbase
    price = await fetch_coinbase_btc_price()
    return price

async def fetch_btc_price_both() -> Dict[str, Optional[float]]:
    """
    Fetch BTC price from both sources for confirmation
    Returns dict with 'binance' and 'coinbase' keys
    NOTE: Using CoinGecko and Blockchain.info instead of Binance/Coinbase (ISP blocking)
    """
    coingecko_price = await fetch_binance_btc_price()  # Actually CoinGecko now
    blockchain_price = await fetch_coinbase_btc_price()  # Actually Blockchain.info now
    
    return {
        "binance": coingecko_price,
        "coinbase": blockchain_price
    }
