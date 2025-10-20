#!/usr/bin/env python3
"""
Offline smoke test for EnterpriseTradingEngine signal generation.
Asserts that primary signal path can generate BUY and SELL given mocked inputs.
"""

import sys
import os
from typing import Dict, Any

# Ensure project root on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import module directly to avoid services __init__ side effects
from importlib import import_module
engine_module = import_module("app.backend.services.enterprise_trading_engine")
EnterpriseTradingEngine = getattr(engine_module, "EnterpriseTradingEngine")


def run_case(engine: Any, name: str, confidence: float, timing_score: float,
             reversal_prob: float, filter_score: float, features: Dict[str, float]) -> str:
    action, conf = engine._calculate_primary_signal(
        confidence=confidence,
        timing_score=timing_score,
        reversal_prob=reversal_prob,
        filter_score=filter_score,
        features=features,
        layer_results={}
    )
    print(f"{name}: action={action}, confidence={conf:.3f}")
    return action


def main() -> int:
    engine = EnterpriseTradingEngine()

    # BUY scenario: strong confidence, timing up, reversal strong, filters pass, not overbought
    buy_features = {
        "rsi": 35.0,
        "bb_position": 0.2,
        "macd": 0.002,
        "volume_ratio": 1.1,
    }
    buy_action = run_case(
        engine,
        name="BUY_CASE",
        confidence=0.82,
        timing_score=0.012,
        reversal_prob=0.80,
        filter_score=0.12,
        features=buy_features,
    )

    # SELL scenario: timing down or alternative SELL path (overbought + reversal)
    sell_features = {
        "rsi": 88.0,
        "bb_position": 0.96,
        "macd": -0.003,
        "volume_ratio": 1.3,
    }
    sell_action = run_case(
        engine,
        name="SELL_CASE",
        confidence=0.78,
        timing_score=-0.006,
        reversal_prob=0.85,
        filter_score=0.10,
        features=sell_features,
    )

    # Assertions
    errors = []
    if buy_action != "BUY":
        errors.append(f"Expected BUY, got {buy_action}")
    if sell_action != "SELL":
        errors.append(f"Expected SELL, got {sell_action}")

    if errors:
        print("\n❌ Offline signal test failed:")
        for e in errors:
            print(" - ", e)
        return 1

    print("\n✅ Offline signal test passed: BUY and SELL paths operational")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


