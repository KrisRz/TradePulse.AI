"""Freeze the paper portfolio's current behaviour into a golden-master fixture.

The M5 paper window is running against a deployed Lambda whose book must not
move. Before refactoring ``PaperPortfolio`` we record exactly what it produces
today; ``test_portfolio_golden.py`` then asserts the refactored code reproduces
those numbers bit-for-bit. Any divergence — even in the last float digit — is a
failed refactor, not an acceptable rounding difference.

Scenarios live in ``app/backend/tests/golden_scenarios.py`` so the generator and
the test can never disagree about what was replayed.

Regenerate ONLY when a behaviour change is intended and understood:

    python scripts/gen_portfolio_golden.py

Run it with ``data/ml/historical/`` present — that git-ignored data supplies the
real-history cases, which are skipped by the test wherever it is absent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.backend.paper_trading.portfolio import PaperPortfolio          # noqa: E402
from app.backend.tests import golden_scenarios as scenarios             # noqa: E402

FIXTURE = ROOT / "app" / "backend" / "tests" / "fixtures" / "portfolio_golden.json"


def _snapshot(port: PaperPortfolio) -> dict:
    """Every piece of portfolio state, at full float precision."""
    return {
        "realized": port.realized,
        "side": port.side,
        "entry_fill": port.entry_fill,
        "entry_equity": port.entry_equity,
        "equity_before_entry": port.equity_before_entry,
        "entry_time": port.entry_time,
        "last_price": port.last_price,
        "equity": port.equity(),
        "total_return": port.total_return(),
        "trades": port.trades,
    }


def _replay(case: str) -> dict:
    params = scenarios.params_for(case)
    port = PaperPortfolio(**params)
    actions = [port.reconcile(t, p, ts) for t, p, ts in scenarios.steps_for(case)]
    return {"params": params, "result": {"actions": actions, "final": _snapshot(port)}}


def build() -> dict:
    cases = {name: _replay(name) for name in scenarios.SYNTHETIC_CASES}

    if scenarios.history_available():
        for name in scenarios.HISTORY_CASES:
            cases[name] = _replay(name)
    else:
        print(f"WARNING: {scenarios.BTC_1D} missing — real-history cases NOT "
              "regenerated; existing ones are preserved", file=sys.stderr)
        if FIXTURE.is_file():
            old = json.loads(FIXTURE.read_text())["cases"]
            for name in scenarios.HISTORY_CASES:
                if name in old:
                    cases[name] = old[name]

    return {
        "_comment": "Golden master of PaperPortfolio behaviour — see "
                    "scripts/gen_portfolio_golden.py. Do not hand-edit.",
        "cases": cases,
    }


def main() -> None:
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    data = build()
    FIXTURE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"wrote {FIXTURE.relative_to(ROOT)}")
    for name, case in data["cases"].items():
        final = case["result"]["final"]
        print(f"  {name:26s} trades={len(final['trades']):3d} "
              f"equity={final['equity']:,.6f}")


if __name__ == "__main__":
    main()
