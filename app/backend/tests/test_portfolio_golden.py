"""Golden-master guard: the paper book must not move when we refactor.

The M5 window is running live against a deployed Lambda. Any change to
``PaperPortfolio`` that shifts a single float would silently invalidate the
window's evidence, so the accounting is pinned to a fixture captured before the
executor refactor (see ``scripts/gen_portfolio_golden.py``).

Comparisons are exact — ``==`` on floats, deliberately. These replays are
deterministic and run the same arithmetic in the same order, so the results are
reproducible to the last bit. A "tiny" difference here means the refactor
changed the operation order, which is exactly what must not happen.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.backend.paper_trading.portfolio import PaperPortfolio
from app.backend.tests import golden_scenarios as scenarios

FIXTURE = Path(__file__).parent / "fixtures" / "portfolio_golden.json"
GOLDEN = json.loads(FIXTURE.read_text())["cases"]


def _replay(case: str):
    port = PaperPortfolio(**GOLDEN[case]["params"])
    actions = [port.reconcile(t, p, ts) for t, p, ts in scenarios.steps_for(case)]
    return port, actions


@pytest.mark.parametrize("case", sorted(GOLDEN))
def test_portfolio_matches_golden_master(case: str):
    if case in scenarios.HISTORY_CASES and not scenarios.history_available():
        pytest.skip(f"{scenarios.BTC_1D} absent (data/ml is git-ignored)")

    expected = GOLDEN[case]["result"]
    port, actions = _replay(case)

    assert actions == expected["actions"], f"{case}: action stream diverged"

    final = expected["final"]
    assert port.realized == final["realized"], f"{case}: realized diverged"
    assert port.side == final["side"]
    assert port.entry_fill == final["entry_fill"]
    assert port.entry_equity == final["entry_equity"]
    assert port.equity_before_entry == final["equity_before_entry"]
    assert port.entry_time == final["entry_time"]
    assert port.last_price == final["last_price"]
    assert port.equity() == final["equity"], f"{case}: equity diverged"
    assert port.total_return() == final["total_return"]
    assert port.trades == final["trades"], f"{case}: trade log diverged"


def test_data_free_coverage_is_strong_enough_for_ci():
    """CI has no data/ml, so the synthetic replay must carry the guard alone."""
    replay = GOLDEN["synthetic_long_replay"]["result"]
    assert len(replay["actions"]) >= 1000, "synthetic replay is too short to bite"

    trades = replay["final"]["trades"]
    assert len(trades) >= 20, f"only {len(trades)} closed trades exercised"
    assert any(t["side"] == 1 for t in trades), "no long leg is covered"
    assert any(t["side"] == -1 for t in trades), "no short leg is covered"

    taken = [a for a in replay["actions"] if a]
    assert any(a["from"] == 1 and a["to"] == -1 for a in taken), "no long->short flip"
    assert any(a["from"] == -1 and a["to"] == 1 for a in taken), "no short->long flip"
    assert replay["actions"].count(None) >= 100, "unchanged-target no-op barely covered"


def test_synthetic_replay_is_reproducible():
    """Platform-dependent arithmetic here would make the fixture unusable in CI."""
    first = scenarios.steps_for("synthetic_long_replay")
    second = scenarios.steps_for("synthetic_long_replay")
    assert first == second
    assert all(p > 0 for _, p, _ in first), "a non-positive price would be rejected"


@pytest.mark.skipif(not scenarios.history_available(),
                    reason="data/ml is git-ignored; real history is local-only")
def test_real_history_fixture_still_covers_production_shape():
    long_only = GOLDEN["btc_1d_long_only"]["result"]["final"]
    assert len(long_only["trades"]) == 15, "production replay lost its round trips"

    shorts = GOLDEN["btc_1d_with_shorts"]["result"]["final"]["trades"]
    assert any(t["side"] == -1 for t in shorts), "no short leg is covered"
