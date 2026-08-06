"""AWS Lambda entrypoint for the execution heartbeat.

EventBridge invokes this once a day, after the paper bot's own slot, so the two
never contend for the same DynamoDB item. Configuration comes from the
environment:

    PAPER_STATE_BACKEND=dynamodb
    PAPER_STATE_TABLE=tradepulse_paper_bot     # same table, different key
    SHADOW_NOTIONAL=10                         # quote units per leg
    SHADOW_CREDENTIALS_PATH=/tradepulse/demo   # SSM prefix, see below

Why credentials come from SSM rather than the function's environment
--------------------------------------------------------------------
Lambda environment variables are stored in the function *configuration*, which
means they show up in ``get-function``, in CloudTrail, and in any Terraform state
that manages them. SSM Parameter Store keeps them encrypted, out of tfstate, and
rotatable without touching the deployment. Standard parameters are free, so this
costs nothing — which matters for a bot whose whole infrastructure bill is
$0.60 a month.

The keys are demo-venue keys with fake money behind them. The handling is strict
anyway: the same code path will one day hold keys that are not.
"""

from __future__ import annotations

import json
import logging
import os

from .shadow import build_shadow_runner

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def load_credentials_from_ssm(prefix: str) -> dict:
    """Read ``<prefix>/key`` and ``<prefix>/secret`` as decrypted SecureStrings."""
    import boto3  # provided by the Lambda runtime

    ssm = boto3.client("ssm")
    names = [f"{prefix}/key", f"{prefix}/secret"]
    resp = ssm.get_parameters(Names=names, WithDecryption=True)

    missing = resp.get("InvalidParameters") or []
    if missing:
        raise RuntimeError(f"missing SSM parameters: {missing}")

    values = {p["Name"]: p["Value"] for p in resp["Parameters"]}
    return {
        "BINANCE_DEMO_KEY": values[f"{prefix}/key"],
        "BINANCE_DEMO_SECRET": values[f"{prefix}/secret"],
    }


def handler(event, context):
    symbol = os.environ.get("TRADING_SYMBOL", "BTCUSDT")
    timeframe = os.environ.get("TRADING_TIMEFRAME", "1d")
    notional = float(os.environ.get("SHADOW_NOTIONAL", "10"))
    ssm_prefix = os.environ.get("SHADOW_CREDENTIALS_PATH", "/tradepulse/demo")

    credentials = load_credentials_from_ssm(ssm_prefix)
    runner = build_shadow_runner(symbol=symbol, timeframe=timeframe,
                                 notional=notional, credentials=credentials)
    result = runner.run_once()

    logger.info("shadow heartbeat: %s", json.dumps(result, default=str))

    # A venue error must fail the invocation so the existing alarm + DLQ machinery
    # notices. "already_done" and a clean run are both successes.
    if result.get("status") in ("venue_error", "too_small", "not_flat"):
        raise RuntimeError(f"shadow heartbeat failed: {result.get('error') or result}")
    return result
