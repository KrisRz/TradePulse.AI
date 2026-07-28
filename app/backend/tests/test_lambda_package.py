"""Tests for the paper-bot Lambda package build.

The zip these rules describe is what trades. An unpinned dependency means the
next `terraform apply` can ship a version nobody validated, so the build must be
reproducible by construction — checked here rather than discovered in production.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
REQS = ROOT / "app" / "backend" / "requirements-lambda.txt"
BUILD_SCRIPT = ROOT / "scripts" / "build_lambda_package.sh"

# Everything the bot imports at runtime that is not provided by the AWS managed
# pandas layer (numpy/pandas) or the Lambda runtime itself (boto3/botocore).
REQUIRED_PACKAGES = {"requests", "urllib3"}

# Shipping these in the zip shadows the layer/runtime copies and breaks imports.
FORBIDDEN_PACKAGES = {"numpy", "pandas", "boto3", "botocore"}


def _requirement_lines() -> list[str]:
    return [
        line.strip()
        for line in REQS.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _pinned() -> dict[str, str]:
    pins = {}
    for line in _requirement_lines():
        spec = line.split("#", 1)[0].strip()
        name, _, version = spec.partition("==")
        pins[name.strip().lower()] = version.strip()
    return pins


def test_requirements_file_exists() -> None:
    assert REQS.is_file(), f"missing {REQS}"


@pytest.mark.parametrize("line", _requirement_lines())
def test_every_dependency_is_exactly_pinned(line: str) -> None:
    spec = line.split("#", 1)[0].strip()
    assert "==" in spec, f"{spec!r} is not pinned with '=='"
    name, _, version = spec.partition("==")
    assert name.strip(), f"{spec!r} has no package name"
    # A bare version, not a range or wildcard — `1.2.*` still floats.
    assert re.fullmatch(r"[0-9][0-9A-Za-z.\-+!]*", version.strip()), (
        f"{spec!r} does not pin one concrete version"
    )


def test_runtime_imports_are_covered() -> None:
    missing = REQUIRED_PACKAGES - set(_pinned())
    assert not missing, f"bot imports these but the zip would not carry them: {missing}"


def test_layer_provided_packages_are_not_shipped() -> None:
    shipped = FORBIDDEN_PACKAGES & set(_pinned())
    assert not shipped, (
        f"{shipped} come from the AWS pandas layer / Lambda runtime; "
        "shipping them in the zip shadows and breaks them"
    )


def test_urllib3_stays_below_2_1_for_botocore() -> None:
    """The runtime's botocore imports urllib3 from /var/task when present."""
    major, minor = (int(p) for p in _pinned()["urllib3"].split(".")[:2])
    assert (major, minor) < (2, 1), "botocore on py3.10+ requires urllib3 < 2.1"


def test_build_script_installs_from_the_pinned_file() -> None:
    script = BUILD_SCRIPT.read_text()
    assert "requirements-lambda.txt" in script, "build script ignores the pinned file"
    # An unpinned `pip install <name>` next to it would silently win.
    loose = re.search(r"pip[\"']?\s+install\s+(?!-r\b)[A-Za-z]", script)
    assert loose is None, f"build script has an unpinned install: {loose.group(0)!r}"


def test_build_script_strips_layer_provided_packages() -> None:
    script = BUILD_SCRIPT.read_text()
    for pkg in ("numpy", "pandas"):
        assert re.search(rf"rm\b.*{pkg}", script), (
            f"build script must delete bundled {pkg} — the layer provides it"
        )
