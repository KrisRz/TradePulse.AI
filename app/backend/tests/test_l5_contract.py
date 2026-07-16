"""
Contract tests for the L5 confidence pipeline (M0/A3).

Guards two invariants that broke production:
1. Model, training scaler and runtime vector builder agree on 15 features.
2. Runtime features are computed in TRAINING units (per-bar 1m volume,
   percent 24h change, ATR/close volatility) — the old snapshot path fed
   24h ticker volume and absolute USD change, putting inputs thousands of
   sigmas outside the training distribution.
"""

import json
import pickle
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

MODELS_DIR = Path(__file__).resolve().parents[1] / "models" / "enterprise"


def _synthetic_1m_candles(n=1500, price0=110000.0, seed=7):
    """Realistic-ish BTCUSDT 1m candles: ~0.02% noise, ~10 BTC volume/bar."""
    rng = np.random.default_rng(seed)
    closes = price0 * np.cumprod(1 + rng.normal(0, 0.0002, n))
    candles = []
    prev_close = price0
    for close in closes:
        high = max(prev_close, close) * (1 + abs(rng.normal(0, 0.0001)))
        low = min(prev_close, close) * (1 - abs(rng.normal(0, 0.0001)))
        candles.append({
            "open": prev_close,
            "high": high,
            "low": low,
            "close": float(close),
            "volume": float(abs(rng.normal(10, 6)) + 0.5),
        })
        prev_close = float(close)
    return candles


def _load_scaler():
    scaler_path = MODELS_DIR / "layer_5_confidence_scaler.pkl"
    if not scaler_path.exists():
        pytest.skip("L5 scaler not present")
    with open(scaler_path, "rb") as f:
        return pickle.load(f)


def test_parity_builder_returns_15_features():
    from app.backend.ml.l5_features import compute_l5_features_from_candles

    vec = compute_l5_features_from_candles(_synthetic_1m_candles())
    assert vec.shape == (1, 15)
    assert np.all(np.isfinite(vec))


def test_parity_builder_rejects_insufficient_bars():
    from app.backend.ml.l5_features import compute_l5_features_from_candles

    with pytest.raises(ValueError):
        compute_l5_features_from_candles(_synthetic_1m_candles(n=30))


def test_scaler_matches_metadata():
    metadata_path = MODELS_DIR / "layer_5_confidence_metadata.json"
    if not metadata_path.exists():
        pytest.skip("L5 metadata not present")
    scaler = _load_scaler()
    metadata = json.loads(metadata_path.read_text())
    assert metadata["n_features"] == 15
    assert scaler.n_features_in_ == metadata["n_features"]


def test_parity_features_land_inside_training_distribution():
    """The decisive test: scaled features must be within a few sigmas of the
    training distribution (the old snapshot path produced |z| in the
    thousands for volume/price_change_24h)."""
    from app.backend.ml.l5_features import L5_FEATURE_ORDER, compute_l5_features_from_candles

    scaler = _load_scaler()
    vec = compute_l5_features_from_candles(
        _synthetic_1m_candles(),
        now=datetime(2026, 7, 15, 14, 30, tzinfo=timezone.utc),
    )
    z = scaler.transform(vec)[0]
    offenders = {
        name: round(float(val), 2)
        for name, val in zip(L5_FEATURE_ORDER, z)
        if abs(val) > 25
    }
    assert not offenders, f"features far outside training distribution: {offenders}"


def test_l5_model_predicts_in_confidence_range():
    model_path = MODELS_DIR / "layer_5_confidence.pkl"
    if not model_path.exists():
        pytest.skip("L5 model not present")
    pytest.importorskip("xgboost")
    scaler = _load_scaler()

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    from app.backend.ml.l5_features import compute_l5_features_from_candles

    vec = compute_l5_features_from_candles(_synthetic_1m_candles())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pred = float(model.predict(scaler.transform(vec))[0])
    assert np.isfinite(pred)
    assert -1.0 <= pred <= 2.0


def test_legacy_6_feature_path_is_gone():
    import app.backend.ml.infer as infer

    assert not hasattr(infer, "predict_l5_rf_safe")
    assert not hasattr(infer, "build_l5_rf_vector")
