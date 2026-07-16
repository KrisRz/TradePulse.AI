"""
L5 v2.0 feature builder — TRAINING PARITY with retrain_layer5_enhanced.py.

The deployed layer_5_confidence model (XGBRegressor, 15 features) was trained
on features computed from 1m candles by
`scripts/ml/retrain_layer5_enhanced.py::calculate_technical_indicators`.
The generic runtime snapshot uses DIFFERENT units for several of them
(24h ticker volume instead of per-bar volume, absolute USD price change
instead of percent, different volatility/trend formulas), which pushed
z-scores thousands of sigmas off the training distribution and made L5
output garbage. This module mirrors the trainer's formulas exactly.

Every formula here must stay in lockstep with the trainer. If you retrain
with different feature engineering, update BOTH or version the metadata.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Trainer parity constants (retrain_layer5_enhanced.py)
RSI_WINDOW = 14
ATR_WINDOW = 14
BB_WINDOW = 20
TREND_WINDOW = 20
VOLUME_WINDOW = 20
BARS_24H = 1440  # 1m bars in 24h
# minimum bars for the short-window features (macd needs 26 + warmup)
MIN_BARS = 60

L5_FEATURE_ORDER = [
    "close", "volume", "rsi", "macd", "bb_position", "volatility",
    "trend_strength", "volume_ratio", "price_change_24h",
    "session_asian", "session_european", "session_us", "session_overlap",
    "hour_of_day", "volatility_regime",
]


def _candles_to_frame(candles: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for c in candles:
        rows.append({
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
            "volume": float(c["volume"]),
        })
    return pd.DataFrame(rows)


def compute_l5_features_from_candles(
    candles: List[Dict[str, Any]],
    now: Optional[datetime] = None,
    price_change_24h_pct: Optional[float] = None,
) -> np.ndarray:
    """Build the (1, 15) L5 feature vector from chronological 1m candles.

    Args:
        candles: closed 1m candles, oldest first, dicts with
            open/high/low/close/volume.
        now: timestamp for session features (default: utcnow).
        price_change_24h_pct: fallback 24h change in PERCENT (e.g. from the
            Binance ticker) used when fewer than 1440+1 bars are available.

    Raises:
        ValueError: if there are not enough bars for the short-window
            features — callers must treat that as "no L5 signal", never
            substitute a differently-shaped vector.
    """
    if not candles or len(candles) < MIN_BARS:
        raise ValueError(f"L5 features need >= {MIN_BARS} 1m bars, got {len(candles) if candles else 0}")

    df = _candles_to_frame(candles)
    close = df["close"]

    # 1. RSI (14, simple rolling mean — trainer parity, NOT Wilder)
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=RSI_WINDOW).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_WINDOW).mean()
    rs = gain / loss
    rsi = float((100 - (100 / (1 + rs))).iloc[-1])
    if not np.isfinite(rsi):
        rsi = 100.0 if float(gain.iloc[-1]) > 0 else 50.0

    # 2. MACD (12, 26) — RAW price units, trainer parity
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd = float((ema_12 - ema_26).iloc[-1])

    # 3. Bollinger position (20, 2), clipped to [0, 1]
    sma_20 = close.rolling(window=BB_WINDOW).mean()
    std_20 = close.rolling(window=BB_WINDOW).std()
    bb_upper = sma_20 + std_20 * 2
    bb_lower = sma_20 - std_20 * 2
    denom = float((bb_upper - bb_lower).iloc[-1])
    if denom > 0:
        bb_position = float(np.clip((close.iloc[-1] - bb_lower.iloc[-1]) / denom, 0.0, 1.0))
    else:
        bb_position = 0.5

    # 4. Volatility = ATR(14) / close
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - close.shift()).abs()
    low_close = (df["low"] - close.shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr_series = true_range.rolling(window=ATR_WINDOW).mean()
    volatility_series = atr_series / close
    volatility = float(volatility_series.iloc[-1])

    # 5. Trend strength: 20-bar linear regression slope / last price
    tail = close.iloc[-TREND_WINDOW:]
    x = np.arange(len(tail))
    slope = float(np.polyfit(x, tail.to_numpy(), 1)[0])
    trend_strength = slope / float(tail.iloc[-1]) if float(tail.iloc[-1]) != 0 else 0.0

    # 6. Volume ratio: current bar vs 20-bar average (per-bar volume!)
    avg_volume = float(df["volume"].rolling(window=VOLUME_WINDOW).mean().iloc[-1])
    volume = float(df["volume"].iloc[-1])
    volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0

    # 7. Price change 24h in PERCENT (1440 bars back; ticker fallback)
    if len(close) > BARS_24H:
        ref = float(close.iloc[-(BARS_24H + 1)])
        price_change_24h = (float(close.iloc[-1]) - ref) / ref * 100 if ref > 0 else 0.0
    elif price_change_24h_pct is not None:
        price_change_24h = float(price_change_24h_pct)
    else:
        price_change_24h = 0.0
        logger.warning("L5: <24h of bars and no ticker fallback — price_change_24h=0")

    # 8. Session context
    ts = now or datetime.now(timezone.utc)
    hour_utc = ts.hour
    session_asian = 1 if 0 <= hour_utc < 8 else 0
    session_european = 1 if 7 <= hour_utc < 15 else 0
    session_us = 1 if 13 <= hour_utc < 21 else 0
    session_overlap = 1 if (session_asian + session_european + session_us) > 1 else 0

    # 9. Volatility regime vs 24h rolling mean (use what we have, min 100 bars)
    vol_window = min(BARS_24H, max(100, len(volatility_series.dropna())))
    vol_mean = float(volatility_series.rolling(window=vol_window).mean().iloc[-1])
    if not np.isfinite(vol_mean) or vol_mean <= 0:
        vol_mean = float(volatility_series.dropna().mean())
    volatility_regime = 1
    if np.isfinite(vol_mean) and vol_mean > 0:
        if volatility < vol_mean * 0.7:
            volatility_regime = 0
        elif volatility > vol_mean * 1.3:
            volatility_regime = 2

    vec = np.array([[
        float(close.iloc[-1]),
        volume,
        rsi,
        macd,
        bb_position,
        volatility,
        trend_strength,
        volume_ratio,
        price_change_24h,
        float(session_asian),
        float(session_european),
        float(session_us),
        float(session_overlap),
        float(hour_utc),
        float(volatility_regime),
    ]], dtype=np.float32)

    if not np.all(np.isfinite(vec)):
        bad = [L5_FEATURE_ORDER[i] for i in np.where(~np.isfinite(vec[0]))[0]]
        raise ValueError(f"L5 features non-finite: {bad}")
    return vec
