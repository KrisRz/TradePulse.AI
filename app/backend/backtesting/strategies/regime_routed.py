"""Regime-routed strategy.

Runs the right tool for the current market: a trend-follower while the market
trends, a mean-reverter while it ranges, and flat during volatility spikes.
This is the core hypothesis of Phase 1b — that routing beats running either
strategy everywhere.

Each sub-strategy computes its own target over the full series (so its
indicators have full history and there is no look-ahead); the router then
selects, per bar, the target of whichever sub-strategy owns the current regime.
When a bar's regime has no assigned strategy (e.g. VOLATILE), the target is 0.
"""

from __future__ import annotations

import pandas as pd

from .. import regime as regime_mod
from ..strategy import Strategy
from .ema_crossover import EmaCrossover
from .rsi_mean_reversion import RsiMeanReversion


class RegimeRouted(Strategy):
    def __init__(
        self,
        trend_strategy: Strategy | None = None,
        range_strategy: Strategy | None = None,
        adx_threshold: float = 25.0,
        vol_mult: float = 1.8,
        trade_volatile: bool = False,
    ) -> None:
        self.trend_strategy = trend_strategy or EmaCrossover(fast=20, slow=50)
        self.range_strategy = range_strategy or RsiMeanReversion(period=14, oversold=30, overbought=70)
        self.adx_threshold = adx_threshold
        self.vol_mult = vol_mult
        self.trade_volatile = trade_volatile
        self.warmup = max(self.trend_strategy.warmup, self.range_strategy.warmup, 100)
        self.name = f"Regime[{self.trend_strategy.name}|{self.range_strategy.name}]"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        regime = regime_mod.classify(
            df, adx_threshold=self.adx_threshold, vol_mult=self.vol_mult
        )
        trend_sig = self.trend_strategy.generate_signals(df).reindex(df.index).fillna(0.0)
        range_sig = self.range_strategy.generate_signals(df).reindex(df.index).fillna(0.0)

        target = pd.Series(0.0, index=df.index)
        target = target.mask(regime == regime_mod.TREND, trend_sig)
        target = target.mask(regime == regime_mod.RANGE, range_sig)
        if self.trade_volatile:
            # In volatile regime, default to the trend strategy (momentum burst).
            target = target.mask(regime == regime_mod.VOLATILE, trend_sig)
        return target
