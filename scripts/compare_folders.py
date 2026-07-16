#!/usr/bin/env python3
"""Compare old TradePulse folder copies against our canonical folder.

Goal: before deleting ~68GB of old copies, PROVE nothing unique is lost.
For each old folder it reports:
  1. files present in the OLD copy but MISSING from ours (by category),
  2. source files present in BOTH but with DIFFERENT content (possible local edits).

Data/model files are reported separately (they are in git and/or regenerable).
"""

import hashlib
import os
import sys

OURS = "/Applications/TradePuls"
OLD = [
    "/Applications/Applications/Projects/TradePulse.AI",
    "/Applications/Projects/TradePulse.AI",
    "/Applications/Projects/TradePulse.AI.backup",
    "/Applications/Projects/Backup/TradePulse.AI- backup.AI",
    "/Users/krisrz/Backups/TradePulseAI",
]

EXCLUDE_DIRS = {"node_modules", ".venv", "venv", ".git", "__pycache__",
                ".astro", ".terraform", ".pytest_cache", ".mypy_cache", ".idea"}
SOURCE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".astro", ".sh", ".yml",
              ".yaml", ".toml", ".tf", ".css", ".html", ".cfg", ".ini", ".env"}
DATA_EXT = {".csv", ".json", ".parquet", ".pkl", ".h5", ".keras", ".joblib",
            ".db", ".jar", ".zip", ".tar", ".gz", ".png", ".jpg", ".sqlite"}

# Files we INTENTIONALLY removed/changed during Phase 0-2 (expected to differ/miss).
KNOWN_REMOVED = {
    "app/backend/services/adaptive_position_sizer.py",
    "infra/tfplan", "infra/apprunner-update.tfplan", "infra/iam-fix.tfplan",
    "infra/ssm.tf.bak2", "infra/ssm.tf.bak3",
}


def sha1(path, limit=3_000_000):
    try:
        if os.path.getsize(path) > limit:
            return None
        h = hashlib.sha1()
        with open(path, "rb") as fh:
            h.update(fh.read())
        return h.hexdigest()
    except OSError:
        return None


def inventory(root, want_hash=True):
    files = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS]
        for fn in fns:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, root)
            ext = os.path.splitext(fn)[1].lower()
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            h = sha1(full) if (want_hash and ext in SOURCE_EXT) else None
            files[rel] = (size, h, ext)
    return files


def categorize(rel, ext):
    if ext in DATA_EXT:
        return "data/model"
    if ext in SOURCE_EXT:
        return "SOURCE"
    return "other"


print(f"Inventorying OURS: {OURS} ...", flush=True)
ours = inventory(OURS)
print(f"  {len(ours):,} files\n", flush=True)

grand_missing_source = 0
for old in OLD:
    print("=" * 78)
    if not os.path.isdir(old):
        print(f"OLD (missing): {old}")
        continue
    print(f"OLD: {old}", flush=True)
    inv = inventory(old)
    print(f"  files: old={len(inv):,}  ours={len(ours):,}")

    missing = {r: v for r, v in inv.items() if r not in ours}
    diff = {r: v for r, v in inv.items()
            if r in ours and v[1] and ours[r][1] and v[1] != ours[r][1]}

    cats = {"SOURCE": [], "data/model": [], "other": []}
    for r, (sz, h, ext) in missing.items():
        cats[categorize(r, ext)].append(r)

    ms = sorted(x for x in cats["SOURCE"] if x not in KNOWN_REMOVED)
    grand_missing_source += len(ms)
    print(f"\n  [MISSING SOURCE] only in old, not ours (excl. intentionally removed): {len(ms)}")
    for r in ms[:50]:
        print(f"      - {r}")
    if len(ms) > 50:
        print(f"      ... +{len(ms)-50} more")

    dm = cats["data/model"]
    dm_mb = sum(inv[r][0] for r in dm) / 1e6
    print(f"\n  [MISSING data/model] {len(dm)} files, {dm_mb:.0f} MB (in git and/or regenerable)")

    other = [x for x in cats["other"] if x not in KNOWN_REMOVED]
    print(f"  [MISSING other] {len(other)} files")
    for r in other[:15]:
        print(f"      - {r}")

    src_diff = sorted(r for r in diff if r not in KNOWN_REMOVED)
    print(f"\n  [DIFFERENT SOURCE] in both, different content: {len(src_diff)}")
    print("      (expected for files we edited in Phase 0-2; review only unexpected ones)")
    for r in src_diff[:50]:
        print(f"      ~ {r}")
    if len(src_diff) > 50:
        print(f"      ... +{len(src_diff)-50} more")
    print()

print("=" * 78)
print(f"VERDICT: total UNIQUE missing SOURCE files across all old copies "
      f"(excl. intentional removals): {grand_missing_source}")
print("If 0 -> nothing source-level is lost; safe to delete after preserving .env.")
