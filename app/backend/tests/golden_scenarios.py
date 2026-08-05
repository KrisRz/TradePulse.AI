"""Replay scenarios for the portfolio golden master — one definition, two users.

Both ``scripts/gen_portfolio_golden.py`` (which records the fixture) and
``test_portfolio_golden.py`` (which checks against it) import from here. If the
step sequences lived in both places they would eventually drift, and a drifted
generator silently re-blesses whatever the code now does — exactly the failure
a golden master exists to prevent.

Two families of scenario:

* **synthetic** — pure integer arithmetic, no data files, no ``pandas``. These
  run everywhere including CI, and are bit-reproducible across platforms
  because nothing here touches a transcendental function or a float that was
  not derived from an exact integer.
* **history** — real BTC daily bars driven by the production strategy. The
  strongest check, but ``data/ml/`` is deliberately git-ignored, so these are
  skipped wherever the CSVs are absent.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BTC_1D = ROOT / "data" / "ml" / "historical" / "BTCUSDT_1d.csv"

DEFAULT_PARAMS = {"fee_rate": 0.001, "slippage": 0.0002, "initial_capital": 10_000.0}

Step = tuple[int, float, str]


def _lcg(seed: int, n: int) -> list[int]:
    """Classic LCG — integer-only, so every derived price is an exact float."""
    out, x = [], seed
    for _ in range(n):
        x = (1103515245 * x + 12345) % 2_147_483_648
        out.append(x)
    return out


def _long_replay(n: int = 1500) -> list[Step]:
    """A long deterministic replay with frequent, uneven position changes.

    Prices are a bounded function of the generator state rather than a random
    walk, so they can never drift to zero and every value is exactly
    representable. Targets change only occasionally, which produces genuine
    holds, flips and no-ops instead of alternating every bar.
    """
    steps: list[Step] = []
    target = 0
    for i, x in enumerate(_lcg(seed=20260805, n=n)):
        price = float(20_000 + (x % 8_000))
        if x % 13 == 0:
            target = (x // 13) % 3 - 1      # -1 / 0 / +1
        steps.append((target, price, f"t{i}"))
    return steps


SYNTHETIC_CASES: dict[str, dict] = {
    "synthetic_long_replay": {
        "params": DEFAULT_PARAMS,
        "steps": _long_replay(),
    },
    "direct_side_flips": {
        "params": DEFAULT_PARAMS,
        "steps": [(1, 100.0, "t0"), (-1, 120.0, "t1"),
                  (1, 90.0, "t2"), (0, 95.0, "t3")],
    },
    "repeated_targets_no_op": {
        "params": DEFAULT_PARAMS,
        "steps": [(1, 100.0, "t0"), (1, 101.0, "t1"), (1, 99.0, "t2"),
                  (0, 102.0, "t3"), (0, 103.0, "t4")],
    },
    "short_only": {
        "params": DEFAULT_PARAMS,
        "steps": [(-1, 100.0, "t0"), (-1, 90.0, "t1"), (0, 80.0, "t2")],
    },
    "zero_costs": {
        "params": {"fee_rate": 0.0, "slippage": 0.0, "initial_capital": 10_000.0},
        "steps": [(1, 100.0, "t0"), (-1, 120.0, "t1"),
                  (1, 90.0, "t2"), (0, 95.0, "t3")],
    },
    "high_costs": {
        "params": {"fee_rate": 0.005, "slippage": 0.003, "initial_capital": 1_000.0},
        "steps": [(1, 100.0, "t0"), (-1, 120.0, "t1"),
                  (1, 90.0, "t2"), (0, 95.0, "t3")],
    },
}

# name -> allow_short; driven by EMA20/100, the deployed configuration.
HISTORY_CASES: dict[str, bool] = {
    "btc_1d_long_only": False,
    "btc_1d_with_shorts": True,
}


def history_available() -> bool:
    return BTC_1D.is_file()


def history_steps(allow_short: bool) -> list[Step]:
    """Production-shaped replay: EMA20/100 targets over real BTC daily history."""
    from ..backtesting.data import load_csv
    from ..backtesting.strategies import EmaCrossover

    df = load_csv(str(BTC_1D))
    targets = EmaCrossover(fast=20, slow=100,
                           allow_short=allow_short).target_positions(df)
    return [(int(targets.iloc[i]), float(df["close"].iloc[i]), str(df.index[i]))
            for i in range(len(df))]


def steps_for(case: str) -> list[Step]:
    if case in SYNTHETIC_CASES:
        return SYNTHETIC_CASES[case]["steps"]
    return history_steps(allow_short=HISTORY_CASES[case])


def params_for(case: str) -> dict:
    if case in SYNTHETIC_CASES:
        return SYNTHETIC_CASES[case]["params"]
    return DEFAULT_PARAMS
