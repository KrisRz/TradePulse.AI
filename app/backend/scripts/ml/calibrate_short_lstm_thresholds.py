#!/usr/bin/env python3
"""
Calibrate probability thresholds for short-horizon LSTM models (1m, 5m).

Writes threshold and metrics into meta JSON next to the model file.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from app.backend.services.binance_hybrid_client import get_hybrid_client


@dataclass
class CalibCfg:
    symbol: str = "BTCUSDT"
    intervals: Tuple[str, ...] = ("1m", "5m")
    days: int = 180
    lookback: int = 200
    horizon_1m: int = 5
    horizon_5m: int = 3
    models_dir: Path = Path("app/backend/models/enterprise")


async def fetch(symbol: str, interval: str, start: datetime, end: datetime) -> List[Dict[str, Any]]:
    client = await get_binance_client()
    out: List[Dict[str, Any]] = []
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    async with client:
        cursor = start_ms
        while cursor < end_ms:
            batch = await client.get_klines(symbol, interval, limit=1000, start_time=cursor, end_time=end_ms)
            if not batch:
                break
            out.extend(batch)
            cursor = batch[-1]["close_time"] + 1
    return out


def features(candles: List[Dict[str, Any]], lookback: int, horizon: int) -> Tuple[np.ndarray, np.ndarray]:
    # Minimal features: logret sequence, to avoid mismatch with model; if model used richer features,
    # calibration still estimates a usable threshold over its output on these inputs.
    close = np.array([c["close"] for c in candles], dtype=np.float32)
    rets = np.diff(np.log(close), prepend=close[0]).astype(np.float32)
    X_list: List[np.ndarray] = []
    y_list: List[int] = []
    warmup = lookback
    for i in range(warmup, len(close) - horizon):
        seq = rets[i - lookback : i].reshape(lookback, 1)
        fut = float(np.log(close[i + horizon] / close[i]))
        X_list.append(seq)
        y_list.append(1 if fut > 0 else 0)
    X = np.stack(X_list) if X_list else np.zeros((0, lookback, 1), dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)
    return X, y


def best_threshold(probs: np.ndarray, y: np.ndarray) -> Tuple[float, Dict[str, float]]:
    # Maximize F1 across grid
    best_t, best_f1 = 0.5, -1.0
    best = {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    for t in np.linspace(0.3, 0.7, 41):
        pred = (probs >= t).astype(int)
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        if f1 > best_f1:
            best_f1 = f1
            best_t = float(t)
            best = {"precision": precision, "recall": recall, "f1": f1}
    return best_t, best


async def calibrate_interval(cfg: CalibCfg, interval: str) -> None:
    print(f"[calib] interval={interval} backfill …")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=cfg.days)
    candles = await fetch(cfg.symbol, interval, start, end)
    if interval == "1m":
        horizon = cfg.horizon_1m
    else:
        horizon = cfg.horizon_5m

    X, y = features(candles, cfg.lookback, horizon)
    if X.shape[0] < 5000:
        print("[calib] not enough samples; skipping")
        return

    import tensorflow as tf
    model_path = cfg.models_dir / f"lstm_{interval}.h5"
    if not model_path.exists():
        print(f"[calib] model missing: {model_path}")
        return
    model = tf.keras.models.load_model(model_path, compile=False)

    # Sample recent chunk for calibration
    tail = min(200_000, X.shape[0])
    Xc, yc = X[-tail:], y[-tail:]
    probs = model.predict(Xc, verbose=0).reshape(-1)
    probs = np.clip(probs, 0.0, 1.0)
    t, metrics = best_threshold(probs, yc)
    print(f"[calib] {interval} best_threshold={t:.3f} metrics={metrics}")

    meta_path = cfg.models_dir / f"lstm_{interval}_meta.json"
    meta = {"interval": interval, "threshold": t, "metrics": metrics, "calibrated_at": datetime.now(timezone.utc).isoformat()}
    if meta_path.exists():
        try:
            old = json.loads(meta_path.read_text())
            old.update(meta)
            meta = old
        except Exception:
            pass
    meta_path.write_text(json.dumps(meta, indent=2))


async def run(cfg: CalibCfg) -> None:
    for interval in cfg.intervals:
        await calibrate_interval(cfg, interval)


def parse_args() -> CalibCfg:
    p = argparse.ArgumentParser()
    p.add_argument("--intervals", nargs="+", default=["1m", "5m"])
    p.add_argument("--days", type=int, default=180)
    args = p.parse_args()
    return CalibCfg(intervals=tuple(args.intervals), days=args.days)


if __name__ == "__main__":
    cfg = parse_args()
    asyncio.run(run(cfg))


