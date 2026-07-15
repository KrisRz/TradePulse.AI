#!/usr/bin/env python3
"""
Pro short-horizon LSTM training for BTCUSDT at 1m and 5m.

Features
- Real Binance historical klines via internal client
- Rich technical features inside sequences
- Time-series walk-forward CV (3 folds)
- Optuna hyperparameter search
- Progress bars (verbose=1) and logging suitable for overnight runs

Outputs
- app/backend/models/enterprise/lstm_{interval}.h5 (compile=False)
- app/backend/models/enterprise/lstm_{interval}_meta.json
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
import optuna

from app.backend.services.binance_hybrid_client import get_hybrid_client


@dataclass
class ProCfg:
    symbol: str = "BTCUSDT"
    intervals: Tuple[str, ...] = ("1m", "5m")
    days: int = 365
    lookback: int = 200
    horizon_1m: int = 5
    horizon_5m: int = 3
    folds: int = 3
    trials: int = 30
    out_dir: Path = Path("app/backend/models/enterprise")


def ema(arr: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    out = np.empty_like(arr)
    out[:] = np.nan
    if len(arr) == 0:
        return out
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
    return out


def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    if len(close) < period + 1:
        return np.full_like(close, 50.0)
    deltas = np.diff(close, prepend=close[0])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.convolve(gains, np.ones(period), 'full')[: len(gains)] / period
    avg_loss = np.convolve(losses, np.ones(period), 'full')[: len(losses)] / period
    avg_loss = np.where(avg_loss == 0, 1e-9, avg_loss)
    rs = avg_gain / avg_loss
    rsi_vals = 100 - (100 / (1 + rs))
    return rsi_vals.astype(np.float32)


def macd_line(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd = ema_fast - ema_slow
    sig = ema(macd, signal)
    hist = macd - sig
    return macd.astype(np.float32), sig.astype(np.float32), hist.astype(np.float32)


def bollinger_position(close: np.ndarray, period: int = 20) -> Tuple[np.ndarray, np.ndarray]:
    if len(close) < period:
        return np.full_like(close, 0.5), np.full_like(close, 0.0)
    roll = np.lib.stride_tricks.sliding_window_view(close, period)
    sma = np.concatenate([np.full(period - 1, np.nan), roll.mean(axis=1)])
    std = np.concatenate([np.full(period - 1, np.nan), roll.std(axis=1)])
    upper = sma + 2 * std
    lower = sma - 2 * std
    width = (upper - lower) / np.where(sma == 0, 1e-9, sma)
    pos = (close - lower) / np.where(upper == lower, 1e-9, (upper - lower))
    pos = np.clip(pos, 0, 1)
    pos = np.nan_to_num(pos, nan=0.5)
    return pos.astype(np.float32), np.nan_to_num(width).astype(np.float32)


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])
    # Wilder's smoothing
    alpha = 1.0 / period
    out = np.empty_like(tr)
    out[0] = tr[0]
    for i in range(1, len(tr)):
        out[i] = out[i - 1] + alpha * (tr[i] - out[i - 1])
    return out.astype(np.float32)


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


def build_feature_tensor(candles: List[Dict[str, Any]], stride: int, lookback: int, horizon: int) -> Tuple[np.ndarray, np.ndarray]:
    close = np.array([c["close"] for c in candles], dtype=np.float32)
    high = np.array([c["high"] for c in candles], dtype=np.float32)
    low = np.array([c["low"] for c in candles], dtype=np.float32)
    volume = np.array([c["volume"] for c in candles], dtype=np.float32)

    logret = np.diff(np.log(close), prepend=close[0]).astype(np.float32)
    ema9 = ema(close, 9).astype(np.float32)
    ema21 = ema(close, 21).astype(np.float32)
    macd, macd_sig, macd_hist = macd_line(close)
    rsi14 = rsi(close, 14)
    bb_pos, bb_width = bollinger_position(close, 20)
    atr14 = atr(high, low, close, 14)
    vol_sma20 = np.convolve(volume, np.ones(20), 'full')[: len(volume)] / 20.0
    vol_ratio = (volume / np.where(vol_sma20 == 0, 1e-9, vol_sma20)).astype(np.float32)

    feats = np.stack([
        logret,
        (ema9 - close) / np.where(close == 0, 1e-9, close),
        (ema21 - close) / np.where(close == 0, 1e-9, close),
        macd,
        macd_sig,
        macd_hist,
        rsi14 / 100.0,
        bb_pos,
        bb_width,
        atr14 / np.where(close == 0, 1e-9, close),
        vol_ratio,
    ], axis=1)  # shape (T, F)
    # Sanitize any remaining NaNs/Infs
    feats = np.nan_to_num(feats, nan=0.0, posinf=0.0, neginf=0.0)

    X_list: List[np.ndarray] = []
    y_list: List[int] = []
    warmup = 50  # ensure indicators are matured
    for i in range(max(lookback, warmup), len(close) - horizon, stride):
        window = feats[i - lookback : i]
        future_ret = float(np.log(close[i + horizon] / close[i]))
        X_list.append(window)
        y_list.append(1 if future_ret > 0 else 0)

    X = np.stack(X_list).astype(np.float32)
    y = np.array(y_list, dtype=np.int32)
    return X, y


def time_series_folds(n: int, folds: int) -> List[Tuple[slice, slice]]:
    # Sequential folds: progressively expanding train window, fixed-size val window
    idx = np.arange(n)
    fold_sizes = n // (folds + 1)
    splits: List[Tuple[slice, slice]] = []
    for k in range(1, folds + 1):
        val_start = fold_sizes * k
        val_end = fold_sizes * (k + 1)
        splits.append((slice(0, val_start), slice(val_start, val_end)))
    return splits


def build_model(trial: optuna.Trial, timesteps: int, features: int):
    import tensorflow as tf
    units1 = trial.suggest_int("units1", 32, 128, step=16)
    units2 = trial.suggest_int("units2", 16, 64, step=16)
    dropout = trial.suggest_float("dropout", 0.0, 0.3)
    lr = trial.suggest_float("lr", 1e-4, 3e-3, log=True)

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(timesteps, features)),
        tf.keras.layers.LSTM(units1, return_sequences=True),
        tf.keras.layers.Dropout(dropout),
        tf.keras.layers.LSTM(units2),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer=tf.keras.optimizers.Adam(lr), loss="binary_crossentropy", metrics=["accuracy", tf.keras.metrics.AUC(name="auc")])
    return model


def objective_factory(X: np.ndarray, y: np.ndarray, folds: int):
    import tensorflow as tf

    splits = time_series_folds(X.shape[0], folds)

    def obj(trial: optuna.Trial) -> float:
        # choose stride for augmentation-like effect
        batch_size = trial.suggest_categorical("batch", [256, 512])
        epochs = trial.suggest_int("epochs", 25, 60)
        model = build_model(trial, X.shape[1], X.shape[2])
        val_aucs: List[float] = []
        for train_slice, val_slice in splits:
            X_tr, y_tr = X[train_slice], y[train_slice]
            X_val, y_val = X[val_slice], y[val_slice]
            callbacks = [
                tf.keras.callbacks.EarlyStopping(monitor="val_auc", mode="max", patience=6, restore_best_weights=True),
                tf.keras.callbacks.ReduceLROnPlateau(monitor="val_auc", mode="max", factor=0.5, patience=3),
            ]
            hist = model.fit(X_tr, y_tr, validation_data=(X_val, y_val), epochs=epochs, batch_size=batch_size, verbose=1, callbacks=callbacks)
            best_auc = float(max(hist.history.get("val_auc", [0.0])))
            val_aucs.append(best_auc)
        avg_auc = float(np.mean(val_aucs))
        trial.set_user_attr("fold_aucs", val_aucs)
        return avg_auc

    return obj


async def train_interval(cfg: ProCfg, interval: str) -> Optional[Path]:
    print(f"[pro] interval={interval} backfill …")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=cfg.days)
    candles = await fetch(cfg.symbol, interval, start, end)
    if interval == "1m":
        horizon = cfg.horizon_1m
        stride = 5
    else:
        horizon = cfg.horizon_5m
        stride = 2
    X, y = build_feature_tensor(candles, stride=stride, lookback=cfg.lookback, horizon=horizon)
    print(f"[pro] dataset {interval}: X={X.shape}, y={y.shape}")
    if X.shape[0] < 5000:
        print("[pro] not enough samples for pro training")
        return None

    study = optuna.create_study(direction="maximize")
    study.optimize(objective_factory(X, y, cfg.folds), n_trials=cfg.trials, show_progress_bar=True)
    print(f"[pro] best auc={study.best_value:.4f} params={study.best_trial.params}")

    # Train best model on full data with early stopping vs a final holdout
    import tensorflow as tf
    params = study.best_trial.params
    trial = optuna.trial.FixedTrial(params)
    model = build_model(trial, X.shape[1], X.shape[2])
    split = int(X.shape[0] * 0.9)
    X_tr, y_tr = X[:split], y[:split]
    X_val, y_val = X[split:], y[split:]
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_auc", mode="max", patience=8, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_auc", mode="max", factor=0.5, patience=4),
    ]
    epochs = int(params.get("epochs", 50))
    batch = int(params.get("batch", 256))
    model.fit(X_tr, y_tr, validation_data=(X_val, y_val), epochs=epochs, batch_size=batch, verbose=1, callbacks=callbacks)

    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    out = cfg.out_dir / f"lstm_{interval}.h5"
    model.save(out, include_optimizer=False)
    meta = {
        "interval": interval,
        "symbol": cfg.symbol,
        "lookback": cfg.lookback,
        "horizon": horizon,
        "best_params": params,
        "best_auc": study.best_value,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "features": [
            "logret", "ema9_delta", "ema21_delta", "macd", "macd_sig", "macd_hist",
            "rsi14_norm", "%B", "bb_width", "atr14_norm", "vol_ratio",
        ],
        "folds": cfg.folds,
        "trials": cfg.trials,
        "stride": stride,
    }
    (cfg.out_dir / f"lstm_{interval}_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[pro] saved {out}")
    return out


async def run(cfg: ProCfg) -> None:
    for interval in cfg.intervals:
        await train_interval(cfg, interval)


def parse_args() -> ProCfg:
    p = argparse.ArgumentParser()
    p.add_argument("--intervals", nargs="+", default=["1m", "5m"])
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--lookback", type=int, default=200)
    p.add_argument("--trials", type=int, default=30)
    p.add_argument("--folds", type=int, default=3)
    args = p.parse_args()
    return ProCfg(
        intervals=tuple(args.intervals),
        days=args.days,
        lookback=args.lookback,
        trials=args.trials,
        folds=args.folds,
    )


if __name__ == "__main__":
    cfg = parse_args()
    asyncio.run(run(cfg))


