"""Proof of life that does not live in the account it is watching.

Every alarm this system has is a CloudWatch alarm in the same AWS account, in
the same region, as the bot it watches. That is fine for the failures they were
written for — an exception, a dead schedule, a message in the DLQ — and useless
for the one they cannot see: the account or the region itself going away. Then
nothing throws, nothing is missed, no metric moves. Silence looks exactly like
health, and a bot holding a position would sit there unattended for as long as it
took someone to wonder.

So the liveness signal is inverted and moved outside: after every healthy run the
bot pings a service that expects to hear from it, and **that service** raises the
alarm when it does not. A dead-man switch — it fires on absence, which is the
only way to detect a failure that also disables the detector.

Two deliberate properties:

* **It never raises.** A monitoring call is not allowed to fail a trading run.
  Losing the ping costs a false alert; letting it propagate would turn a
  monitoring outage into a bot outage, which is the wrong way round.
* **A halt pings the failure endpoint, not the healthy one.** The kill switch
  firing is the single most important event this system can produce, and it is
  otherwise invisible outside AWS: the Lambda returns 200, keeps being invoked
  and moves no error metric. Saying so out loud, off-account, costs one request.

Configuration is one SSM parameter per channel (``HEALTHCHECK_PARAM``), read
alongside the credentials. Absent parameter = feature off, logged once — the bot
must run perfectly well for anyone who has not set this up.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

#: Long enough for a slow TLS handshake, short enough that it cannot meaningfully
#: extend a run that is already holding a position.
PING_TIMEOUT = 5.0


def ping(url: Optional[str], failed: bool = False,
         timeout: float = PING_TIMEOUT, session=None) -> bool:
    """Tell the outside world this run happened. Returns whether it got through.

    ``failed=True`` pings the ``/fail`` endpoint instead, which most dead-man
    services (healthchecks.io among them) treat as an immediate alert rather
    than as a heartbeat.

    Never raises. The return value exists so a caller can log or test it, not so
    a caller can react — there is nothing useful to do about a failed ping from
    inside the process whose liveness is in question.
    """
    if not url:
        return False

    target = f"{url.rstrip('/')}/fail" if failed else url
    try:
        (session or requests).get(target, timeout=timeout)
        logger.info("dead-man ping sent (%s)", "FAIL" if failed else "ok")
        return True
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring
        logger.warning("dead-man ping did not get through (%s): %s", target, exc)
        return False
