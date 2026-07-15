"""Strategy interface for the backtesting layer.

A strategy is a pure function of market data: given an OHLCV DataFrame it
returns, for every bar, a *target position* decided at that bar's close:

    +1  -> want to be long
     0  -> want to be flat
    -1  -> want to be short

The engine (see engine.py) executes any change in the target at the NEXT bar's
open, which is what keeps the backtest free of look-ahead bias — a strategy can
only ever act on information available at the close of the current bar.

Risk management (stop-loss / take-profit / max-hold) is intentionally NOT part
of the strategy. It is a separate overlay applied by the engine, mirroring the
entry-engine / exit-engine separation in the live system and letting us measure
each independently.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """Base class for all rule-based strategies."""

    #: Human-readable name used in reports.
    name: str = "strategy"

    #: Bars of history required before signals are valid. The engine ignores
    #: (keeps flat) the first ``warmup`` bars.
    warmup: int = 0

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Return an integer Series in {-1, 0, +1} aligned to ``df.index``.

        The value at bar ``t`` is the position the strategy wants to hold as of
        the close of bar ``t``. Implementations must only use data up to and
        including bar ``t`` (all indicators in ``indicators.py`` already
        satisfy this).
        """
        raise NotImplementedError

    def target_positions(self, df: pd.DataFrame) -> pd.Series:
        """Signals, cleaned up: warmup zeroed, NaNs -> flat, forward-filled."""
        sig = self.generate_signals(df).reindex(df.index)
        sig = sig.fillna(0.0)
        if self.warmup > 0:
            sig.iloc[: self.warmup] = 0.0
        return sig.round().astype(int).clip(-1, 1)

    def describe(self) -> str:
        return self.name
