#!/usr/bin/env python3
"""
Train short-horizon LSTM models for BTCUSDT (1m and 5m).

Notes
- Uses real Binance klines (public REST) via our Binance client.
- Sequence features are log-returns only for speed/robustness.
- Saves models to app/backend/models/enterprise/lstm_{interval}.h5 (compile=False).
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Local imports
from app.backend.services.binance_hybrid_client import get_hybrid_client


@dataclass
class TrainConfig:
    symbol: str = "BTCUSDT"
    intervals: Tuple[str, ...] = ("1m", "5m")
    lookback_bars: int = 200
    predict_horizon: int = 5
    days: int = 365
    val_split: float = 0.15
    epochs: int = 50
    batch_size: int = 256
    output_dir: Path = Path("app/backend/models/enterprise")
    parquet_dir: Path = Path("data/ml/historical/processed")


async def fetch_klines_range(symbol: str, interval: str, start: datetime, end: datetime) -> List[Dict[str, Any]]:
    client = await get_binance_client()
    all_rows: List[Dict[str, Any]] = []
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)

    async with client:
        cursor = start_ms
        while cursor < end_ms:
            batch = await client.get_klines(symbol, interval, limit=1000, start_time=cursor, end_time=end_ms)
            if not batch:
                break
            all_rows.extend(batch)
            last_close = batch[-1]["close_time"]
            cursor = last_close + 1

    return all_rows


def to_numpy(candles: List[Dict[str, Any]]) -> np.ndarray:
    return np.array([c["close"] for c in candles], dtype=np.float32)


def build_seq_dataset(closes: np.ndarray, lookback: int, horizon: int) -> Tuple[np.ndarray, np.ndarray]:
    rets = np.diff(np.log(closes), prepend=closes[0]).astype(np.float32)
    X_list: List[np.ndarray] = []
    y_list: List[int] = []

    for i in range(lookback, len(closes) - horizon):
        window = rets[i - lookback : i].reshape(lookback, 1)
        future_ret = float(np.log(closes[i + horizon] / closes[i]))
        X_list.append(window)
        y_list.append(1 if future_ret > 0 else 0)

    if not X_list:
        return np.zeros((0, lookback, 1), dtype=np.float32), np.zeros((0,), dtype=np.int32)

    X = np.stack(X_list)
    y = np.array(y_list, dtype=np.int32)
    return X, y


def build_model(input_timesteps: int, input_features: int):
    import tensorflow as tf  # local import for startup speed

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(input_timesteps, input_features)),
        tf.keras.layers.LSTM(64, return_sequences=True),
        tf.keras.layers.Dropout(0.1),
        tf.keras.layers.LSTM(32),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="binary_crossentropy", metrics=["accuracy"])
    return model


async def train_interval(cfg: TrainConfig, interval: str) -> Optional[Path]:
    print(f"[train] interval={interval} fetching klines …")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=cfg.days)
    candles = await fetch_klines_range(cfg.symbol, interval, start, end)
    if len(candles) < cfg.lookback_bars + cfg.predict_horizon + 1000:
        print(f"[train] insufficient candles: {len(candles)}")
        return None

    closes = to_numpy(candles)
    X, y = build_seq_dataset(closes, cfg.lookback_bars, cfg.predict_horizon)
    if X.shape[0] < 2000:
        print(f"[train] insufficient samples after sequence build: {X.shape}")
        return None

    # Train/val split
    split = int(X.shape[0] * (1 - cfg.val_split))
    X_tr, y_tr = X[:split], y[:split]
    X_val, y_val = X[split:], y[split:]

    model = build_model(X.shape[1], X.shape[2])
    import tensorflow as tf
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=6, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3),
    ]
    print(f"[train] fitting {interval}: X_tr={X_tr.shape} X_val={X_val.shape}")
    model.fit(
        X_tr,
        y_tr,
        validation_data=(X_val, y_val),
        epochs=cfg.epochs,
        batch_size=cfg.batch_size,
        callbacks=callbacks,
        verbose=1,
    )

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = cfg.output_dir / f"lstm_{interval}.h5"
    model.save(out_path, include_optimizer=False)

    meta = {
        "interval": interval,
        "symbol": cfg.symbol,
        "lookback": cfg.lookback_bars,
        "horizon": cfg.predict_horizon,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    (cfg.output_dir / f"lstm_{interval}_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[train] saved {out_path}")
    return out_path


async def run(cfg: TrainConfig) -> None:
    for interval in cfg.intervals:
        try:
            await train_interval(cfg, interval)
        except Exception as e:
            print(f"[train] {interval} failed: {e}")


def parse_args() -> TrainConfig:
    p = argparse.ArgumentParser()
    p.add_argument("--intervals", nargs="+", default=["1m", "5m"], help="Intervals to train, e.g., 1m 5m")
    p.add_argument("--days", type=int, default=365, help="Days of history to fetch")
    p.add_argument("--lookback", type=int, default=200, help="Sequence length")
    p.add_argument("--horizon", type=int, default=5, help="Prediction horizon (bars)")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch-size", type=int, default=256)
    args = p.parse_args()
    return TrainConfig(
        intervals=tuple(args.intervals),
        days=args.days,
        lookback_bars=args.lookback,
        predict_horizon=args.horizon,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    cfg = parse_args()
    asyncio.run(run(cfg))


