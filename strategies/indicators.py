"""
Technical Indicators for Whale Copy Trading
Calculates RSI, EMA, Volume, and ATR using the ta library
"""

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from typing import Dict, List, Any, Optional
import config
from apis import price_feeds

async def fetch_btc_indicators() -> Optional[Dict[str, Any]]:
    """
    Fetch BTC price data and calculate all indicators
    Returns dict with RSI, EMA crossover, volume, and ATR data
    """
    # Fetch BTC candles from Binance
    candles = await price_feeds.fetch_binance_btc_candles(
        interval=config.BTC_CANDLE_INTERVAL,
        limit=config.BTC_CANDLE_LIMIT + 20  # Extra for indicator calculation
    )
    
    if not candles or len(candles) < config.BTC_CANDLE_LIMIT:
        return None
    
    # Convert to pandas DataFrame
    df = pd.DataFrame(candles)
    
    # Calculate indicators
    rsi = calculate_rsi(df)
    ema_signal = calculate_ema_crossover(df)
    volume_signal = calculate_volume_signal(df)
    atr_signal = calculate_atr_signal(df)
    
    return {
        "rsi": rsi,
        "ema_signal": ema_signal,  # "UP", "DOWN", or "NEUTRAL"
        "volume_signal": volume_signal,  # "LOW", "NORMAL", or "HIGH"
        "atr_signal": atr_signal  # "HIGH_VOLATILITY" or "NORMAL"
    }

def calculate_rsi(df: pd.DataFrame) -> float:
    """Calculate 14-period RSI"""
    rsi_indicator = RSIIndicator(close=df["close"], window=config.RSI_PERIOD)
    rsi_values = rsi_indicator.rsi()
    return rsi_values.iloc[-1]

def calculate_ema_crossover(df: pd.DataFrame) -> str:
    """
    Calculate EMA crossover signal
    Returns "UP" if short EMA > long EMA, "DOWN" otherwise
    """
    ema_short = EMAIndicator(close=df["close"], window=config.EMA_SHORT_PERIOD)
    ema_long = EMAIndicator(close=df["close"], window=config.EMA_LONG_PERIOD)
    
    short_values = ema_short.ema_indicator()
    long_values = ema_long.ema_indicator()
    
    if short_values.iloc[-1] > long_values.iloc[-1]:
        return "UP"
    else:
        return "DOWN"

def calculate_volume_signal(df: pd.DataFrame) -> str:
    """
    Check if current volume is low compared to average
    Returns "LOW", "NORMAL", or "HIGH"
    """
    volumes = df["volume"]
    avg_volume = volumes.rolling(window=config.VOLUME_LOOKBACK_PERIOD).mean().iloc[-1]
    current_volume = volumes.iloc[-1]
    
    if current_volume < avg_volume * config.WHALE_LOW_VOLUME_THRESHOLD:
        return "LOW"
    elif current_volume > avg_volume * 1.5:
        return "HIGH"
    else:
        return "NORMAL"

def calculate_atr_signal(df: pd.DataFrame) -> str:
    """
    Check if volatility is high using ATR
    Returns "HIGH_VOLATILITY" or "NORMAL"
    """
    atr_indicator = AverageTrueRange(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=config.ATR_PERIOD
    )
    atr_values = atr_indicator.average_true_range()
    
    current_atr = atr_values.iloc[-1]
    avg_atr = atr_values.rolling(window=config.ATR_PERIOD).mean().iloc[-1]
    
    if current_atr > avg_atr * config.WHALE_HIGH_VOLATILITY_MULTIPLIER:
        return "HIGH_VOLATILITY"
    else:
        return "NORMAL"

def score_indicators(
    indicators: Dict[str, Any],
    whale_signal_side: str  # "YES" or "NO" (which side whales are buying)
) -> int:
    """
    Score the indicators to determine position sizing
    Returns number of warnings (0-4)
    Each warning = -1 point
    
    0 warnings  → FULL SIZE
    1 warning   → HALF SIZE
    2 warnings  → QUARTER SIZE
    3+ warnings → SKIP
    """
    warnings = 0
    
    rsi = indicators["rsi"]
    ema_signal = indicators["ema_signal"]
    volume_signal = indicators["volume_signal"]
    atr_signal = indicators["atr_signal"]
    
    # Warning 1: RSI overbought/oversold AND whale disagrees
    if whale_signal_side == "YES":
        # Whales buying YES (bullish)
        if rsi > config.WHALE_RSI_OVERBOUGHT:
            warnings += 1  # Already overbought, risky to buy more
    else:
        # Whales buying NO (bearish)
        if rsi < config.WHALE_RSI_OVERSOLD:
            warnings += 1  # Already oversold, risky to sell more
    
    # Warning 2: EMA trend disagrees with whale signal
    if whale_signal_side == "YES" and ema_signal == "DOWN":
        warnings += 1  # Whales bullish but trend is down
    elif whale_signal_side == "NO" and ema_signal == "UP":
        warnings += 1  # Whales bearish but trend is up
    
    # Warning 3: Low volume
    if volume_signal == "LOW":
        warnings += 1
    
    # Warning 4: High volatility
    if atr_signal == "HIGH_VOLATILITY":
        warnings += 1
    
    return warnings

def get_position_multiplier(warnings: int) -> float:
    """
    Convert warnings to position size multiplier
    0 warnings  → 1.0 (FULL)
    1 warning   → 0.5 (HALF)
    2 warnings  → 0.25 (QUARTER)
    3+ warnings → 0.0 (SKIP)
    """
    if warnings == 0:
        return 1.0
    elif warnings == 1:
        return 0.5
    elif warnings == 2:
        return 0.25
    else:
        return 0.0  # SKIP
