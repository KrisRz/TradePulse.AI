"""
API contract test (M3/B9): every /api/... path the frontend calls must
exist in the backend route table. This is the CI tripwire for the class
of bug where a component fetches a path the backend never registered
(real-trading vs real_trading, /api/communication vs
/api/admin/communications, ...).

Method: regex-scan frontend sources for '/api/...' string literals in
fetch/apiClient calls, normalize template interpolations to wildcards,
and match against the FastAPI route table (path params → wildcards).
"""

import re
from pathlib import Path

import pytest

FRONTEND_SRC = Path(__file__).resolve().parents[3] / "app" / "frontend" / "src"

# Paths that intentionally have no backend route (documented decisions).
ALLOWLIST = {
    "/api/ai/confidence",  # ❓D3: component mocked pending a real endpoint
}

API_LITERAL = re.compile(r"""["'`](/api/[A-Za-z0-9_\-/${}.]*)["'`]""")


def _frontend_api_paths():
    paths = set()
    if not FRONTEND_SRC.exists():
        return paths
    for ext in ("*.ts", "*.tsx", "*.astro", "*.js", "*.jsx"):
        for f in FRONTEND_SRC.rglob(ext):
            try:
                text = f.read_text(errors="ignore")
            except OSError:
                continue
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith(("//", "*", "/*")):
                    continue  # comments / commented-out calls don't 404
                for m in API_LITERAL.finditer(line):
                    raw = m.group(1).split("?")[0].rstrip("/")
                    if not raw or raw == "/api":
                        continue
                    # template interpolation → wildcard segment(s)
                    norm = re.sub(r"\$\{[^}]*\}", "*", raw)
                    paths.add((norm, str(f.relative_to(FRONTEND_SRC))))
    return paths


@pytest.fixture(scope="module")
def backend_route_regexes():
    import app.backend.main as m

    regexes = []
    for route in m.app.routes:
        path = getattr(route, "path", None)
        if not path:
            continue
        pattern = re.sub(r"\{[^}]*\}", "[^/]+", path.rstrip("/") or "/")
        regexes.append(re.compile(f"^{pattern}$"))
    return regexes


def test_every_frontend_api_path_has_a_backend_route(backend_route_regexes):
    missing = []
    for norm, source_file in sorted(_frontend_api_paths()):
        if norm in ALLOWLIST:
            continue
        # substitute wildcard segments with a concrete token, then match
        # against every backend route pattern (whose params also match it)
        test_path = norm.replace("*", "x")
        matched = any(rx.match(test_path) for rx in backend_route_regexes)
        if not matched:
            missing.append(f"{norm}  (from {source_file})")
    assert not missing, (
        "Frontend calls these API paths but the backend has no matching route:\n  "
        + "\n  ".join(missing)
    )
