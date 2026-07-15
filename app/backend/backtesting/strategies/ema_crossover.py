"""EMA crossover — a trend-following strategy.

Long while the fast EMA is above the slow EMA, short (if enabled) while it is
below. Optionally require a minimum separation between the EMAs so we don't
flip on every tiny wiggle in a flat market. This is the classic baseline for
capturing trends and is expected to do well in trending regimes and poorly in
choppy/sideways ones — the complement of the mean-reversion strategy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..indicators import ema
from ..strategy import Strategy


class EmaCrossover(Strategy):
    def __init__(
        self,
        fast: int = 20,
        slow: int = 50,
        min_separation: float = 0.0,   # e.g. 0.001 = require 0.1% gap
        allow_short: bool = True,
    ) -> None:
        if fast >= slow:
            raise ValueError("fast period must be shorter than slow period")
        self.fast = fast
        self.slow = slow
        self.min_separation = min_separation
        self.allow_short = allow_short
        self.warmup = slow
        self.name = f"EMA{fast}/{slow}"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        ema_fast = ema(close, self.fast)
        ema_slow = ema(close, self.slow)
        gap = (ema_fast - ema_slow) / ema_slow

        target = np.where(
            gap > self.min_separation, 1,
            np.where(gap < -self.min_separation, -1 if self.allow_short else 0, 0),
        )
        return pd.Series(target, index=df.index, dtype=float)
