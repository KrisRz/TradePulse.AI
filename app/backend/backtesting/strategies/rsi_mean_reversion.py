"""RSI mean-reversion — a counter-trend strategy.

Buy oversold, sell overbought, and exit back toward the mean:

* enter LONG  when RSI drops below ``oversold``  (e.g. 30);
* exit the long once RSI recovers to ``exit_level`` (e.g. 50);
* enter SHORT when RSI rises above ``overbought`` (e.g. 70);
* exit the short once RSI falls back to ``exit_level``.

The position is held across bars (a small state machine), so the signal is not
a pure function of the current bar's RSI — but it still only ever uses data up
to the current bar, so there is no look-ahead. Expected to shine in sideways
markets and to bleed in strong trends — the complement of EMA crossover.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..indicators import rsi
from ..strategy import Strategy


class RsiMeanReversion(Strategy):
    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        exit_level: float = 50.0,
        allow_short: bool = True,
    ) -> None:
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.exit_level = exit_level
        self.allow_short = allow_short
        self.warmup = period + 1
        self.name = f"RSI-MR({oversold:.0f}/{overbought:.0f})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        r = rsi(df["close"], self.period).to_numpy()
        n = len(r)
        target = np.zeros(n, dtype=float)
        pos = 0
        for i in range(n):
            val = r[i]
            if np.isnan(val):
                target[i] = 0
                continue
            if pos == 0:
                if val < self.oversold:
                    pos = 1
                elif val > self.overbought and self.allow_short:
                    pos = -1
            elif pos == 1:
                if val >= self.exit_level:
                    pos = 0
            elif pos == -1:
                if val <= self.exit_level:
                    pos = 0
            target[i] = pos
        return pd.Series(target, index=df.index, dtype=float)
