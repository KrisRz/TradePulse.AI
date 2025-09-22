from typing import Optional

try:
    from prometheus_client import Counter, Histogram, Gauge, Info
except Exception:  # Prometheus optional; engines should degrade gracefully
    Counter = None  # type: ignore
    Histogram = None  # type: ignore
    Gauge = None  # type: ignore

# Metrics registry (module-level singletons)
COOLDOWN_SKIPS: Optional[Counter] = Counter("entry_cooldown_skips_total", "Number of entry analyses skipped due to cooldown") if Counter else None
HISTORICAL_CONTEXT_ERRORS: Optional[Counter] = Counter("historical_context_errors_total", "Number of historical context failures") if Counter else None
ENTRY_CONFIDENCE: Optional[Histogram] = Histogram(
    "entry_confidence",
    "Confidence distribution of entry decisions",
    buckets=[0.1,0.2,0.3,0.35,0.40,0.45,0.48,0.50,0.52,0.54,0.56,0.58,0.60,0.65,0.7,0.8,0.9,1.0]
) if Histogram else None
EFFECTIVE_THRESHOLD: Optional[Gauge] = Gauge("effective_threshold", "Effective confidence threshold used for decisions", ["signal_type"]) if Gauge else None
INDICATOR_MISMATCH: Optional[Counter] = Counter("indicator_snapshot_mismatch_total", "Count of indicator snapshot mismatches", ["module", "field"]) if Counter else None
ENGINE_PHASE: Optional[Gauge] = Gauge("engine_phase", "Engine phase gauge (1=init,2=warmup,3=running)", ["module"]) if Gauge else None
DECISION_THRESHOLD: Optional[Gauge] = Gauge("decision_threshold", "Decision threshold used at stage", ["stage", "profile", "phase"]) if Gauge else None
L5_CONSTANT_PREDICTION: Optional[Counter] = Counter("l5_constant_prediction_total", "Count of constant L5 prediction detections") if Counter else None
HISTORICAL_VALIDATION_ZERO: Optional[Counter] = Counter("historical_validation_zero_total", "Historical validation rate of 0 detected") if Counter else None
CIRCUIT_BREAKER_HALTS: Optional[Counter] = Counter("circuit_breaker_halts_total", "Circuit breaker halts", ["reason"]) if Counter else None
CB_ACTIVE: Optional[Gauge] = Gauge("cb_active", "Circuit breaker active flag", ["symbol"]) if Gauge else None
VOLUME_ZSCORE: Optional[Gauge] = Gauge("volume_zscore", "Volume z-score", ["symbol"]) if Gauge else None
REST_REINITS: Optional[Counter] = Counter("rest_session_reinits_total", "REST session reinitializations", ["reason"]) if Counter else None
ENTRY_CONFIDENCE_STDDEV: Optional[Gauge] = Gauge("entry_confidence_stddev", "Rolling stddev of entry confidence", ["window"]) if Gauge else None
READINESS_GATE: Optional[Gauge] = Gauge("readiness_gate", "Readiness gate (1=ready,0=not)", ["component"]) if Gauge else None
HISTORY_ASOF_EPOCH: Optional[Gauge] = Gauge("history_cache_asof_epoch_seconds", "As-of time of latest closed candle (epoch seconds)") if Gauge else None
SNAPSHOT_AGE: Optional[Gauge] = Gauge("snapshot_age_seconds", "Age of latest market snapshot in seconds") if Gauge else None
SNAPSHOT_ASOF_EPOCH: Optional[Gauge] = Gauge("snapshot_asof_epoch_seconds", "As-of time of latest snapshot (epoch seconds)") if Gauge else None
ENGINE_INFO: Optional[Info] = Info("engine_info", "Engine identity info") if Info else None
L5_VECTOR_SOURCE: Optional[Counter] = Counter("l5_vector_source_total", "L5 vector source count", ["source"]) if Counter else None
SSOT_GUARD_VIOLATIONS: Optional[Counter] = Counter("ssot_guard_violations_total", "SSOT guard violations", ["module", "reason"]) if Counter else None
L5_BUILDER_ERRORS: Optional[Counter] = Counter("l5_builder_errors_total", "L5 vector builder errors", ["reason"]) if Counter else None
DECISION_DUPE_SUPPRESSED: Optional[Counter] = Counter("decision_dupe_suppressed_total", "Suppressed duplicate entries", ["reason"]) if Counter else None
TRADING_DECISIONS: Optional[Counter] = Counter("trading_decisions_total", "Total trading decisions", ["outcome", "action", "signal_type"]) if Counter else None
LAST_DECISION_EPOCH: Optional[Gauge] = Gauge("last_decision_epoch_seconds", "Unix epoch of last decision event") if Gauge else None
ANALYSIS_ONLY_FAILURE: Optional[Counter] = Counter("analysis_only_failure_total", "Analysis-only failures", ["reason"]) if Counter else None
POSITIONS_OPENED: Optional[Counter] = Counter("positions_opened_total", "Positions opened total") if Counter else None
POSITIONS_CLOSED: Optional[Counter] = Counter("positions_closed_total", "Positions closed total") if Counter else None
CONCURRENT_POSITIONS: Optional[Gauge] = Gauge("concurrent_positions", "Current number of open positions") if Gauge else None
ANALYSIS_CYCLES: Optional[Counter] = Counter("analysis_cycles_total", "Analysis loop iterations total") if Counter else None
BRAIN_CYCLES: Optional[Counter] = Counter("brain_cycles_total", "BRAIN trading cycles total") if Counter else None
BRAIN_STATE: Optional[Gauge] = Gauge("brain_state", "BRAIN state (1=init,2=warmup,3=running,4=halt,5=cooldown,6=error)") if Gauge else None
# Extended observability
TRADING_DECISIONS_PLAYBOOK: Optional[Counter] = Counter(
    "trading_decisions_by_playbook_total",
    "Total trading decisions by playbook",
    ["outcome", "action", "signal_type", "playbook"]
) if Counter else None
ENTRY_GUARD_BLOCK: Optional[Counter] = Counter(
    "entry_guard_block_total",
    "Entry decisions blocked by guards",
    ["guard"]
) if Counter else None
VALIDATOR_FAIL: Optional[Counter] = Counter(
    "validator_fail_total",
    "Validator failures with codes",
    ["validator", "code"]
) if Counter else None
DUPE_MICRO_BYPASS: Optional[Counter] = Counter(
    "dupe_micro_bypass_total",
    "Burst escape hatch micro-size entries allowed"
) if Counter else None


def inc_cooldown_skip() -> None:
    if COOLDOWN_SKIPS:
        COOLDOWN_SKIPS.inc()


def inc_historical_context_error() -> None:
    if HISTORICAL_CONTEXT_ERRORS:
        HISTORICAL_CONTEXT_ERRORS.inc()


def observe_entry_confidence(value: float) -> None:
    if ENTRY_CONFIDENCE:
        ENTRY_CONFIDENCE.observe(max(0.0, min(1.0, float(value))))


def set_effective_threshold(value: float, signal_type: str) -> None:
    if EFFECTIVE_THRESHOLD:
        EFFECTIVE_THRESHOLD.labels(signal_type=signal_type).set(float(value))


def inc_indicator_mismatch(module: str, field: str) -> None:
    if INDICATOR_MISMATCH:
        INDICATOR_MISMATCH.labels(module=module, field=field).inc()


def set_engine_phase(module: str, phase_value: int) -> None:
    if ENGINE_PHASE:
        ENGINE_PHASE.labels(module=module).set(float(phase_value))


def set_decision_threshold(stage: str, profile: str, phase: str, value: float) -> None:
    if DECISION_THRESHOLD:
        DECISION_THRESHOLD.labels(stage=stage, profile=profile, phase=phase).set(float(value))


def inc_l5_constant_prediction() -> None:
    if L5_CONSTANT_PREDICTION:
        L5_CONSTANT_PREDICTION.inc()


def inc_historical_validation_zero() -> None:
    if HISTORICAL_VALIDATION_ZERO:
        HISTORICAL_VALIDATION_ZERO.inc()


def inc_cb_halt(reason: str) -> None:
    if CIRCUIT_BREAKER_HALTS:
        CIRCUIT_BREAKER_HALTS.labels(reason=reason).inc()


def set_cb_active(symbol: str, active: bool) -> None:
    if CB_ACTIVE:
        CB_ACTIVE.labels(symbol=symbol).set(1.0 if active else 0.0)


def set_volume_zscore(symbol: str, z: float) -> None:
    if VOLUME_ZSCORE:
        VOLUME_ZSCORE.labels(symbol=symbol).set(float(z))


def inc_rest_reinit(reason: str) -> None:
    if REST_REINITS:
        REST_REINITS.labels(reason=reason).inc()


def set_confidence_stddev(window: str, stddev_value: float) -> None:
    if ENTRY_CONFIDENCE_STDDEV:
        ENTRY_CONFIDENCE_STDDEV.labels(window=window).set(float(stddev_value))


def set_snapshot_age_seconds(age_seconds: float) -> None:
    if SNAPSHOT_AGE:
        SNAPSHOT_AGE.set(float(age_seconds))


def set_snapshot_asof_epoch(seconds: float) -> None:
    if SNAPSHOT_ASOF_EPOCH:
        SNAPSHOT_ASOF_EPOCH.set(float(seconds))


def set_history_asof_epoch(seconds: float) -> None:
    if HISTORY_ASOF_EPOCH:
        HISTORY_ASOF_EPOCH.set(float(seconds))


def set_readiness_gate(component: str, ready: bool) -> None:
    if READINESS_GATE:
        READINESS_GATE.labels(component=component).set(1.0 if ready else 0.0)


def set_engine_info(service: str, profile: str, phase: str, instance: str) -> None:
    if ENGINE_INFO:
        ENGINE_INFO.info({
            "service": service,
            "profile": profile,
            "phase": phase,
            "instance": instance,
        })


def inc_l5_vector_source(source: str) -> None:
    if L5_VECTOR_SOURCE:
        L5_VECTOR_SOURCE.labels(source=source).inc()


def inc_ssot_guard_violation(module: str, reason: str) -> None:
    if SSOT_GUARD_VIOLATIONS:
        SSOT_GUARD_VIOLATIONS.labels(module=module, reason=reason).inc()


def inc_l5_builder_error(reason: str) -> None:
    if L5_BUILDER_ERRORS:
        L5_BUILDER_ERRORS.labels(reason=reason).inc()


def preinit_l5_vector_source_series() -> None:
    if L5_VECTOR_SOURCE:
        for src in ("snapshot", "fallback"):
            L5_VECTOR_SOURCE.labels(source=src).inc(0)


def inc_decision_dupe(reason: str) -> None:
    if DECISION_DUPE_SUPPRESSED:
        DECISION_DUPE_SUPPRESSED.labels(reason=reason).inc()


def preinit_decision_dupe_series() -> None:
    if DECISION_DUPE_SUPPRESSED:
        for r in ("reentry_cooldown", "similar_signal"):
            DECISION_DUPE_SUPPRESSED.labels(reason=r).inc(0)


def inc_decision(outcome: str, action: str, signal_type: str) -> None:
    if TRADING_DECISIONS:
        TRADING_DECISIONS.labels(outcome=outcome, action=action, signal_type=signal_type).inc()


def set_last_decision_epoch(epoch_seconds: float) -> None:
    if LAST_DECISION_EPOCH:
        LAST_DECISION_EPOCH.set(float(epoch_seconds))


def inc_analysis_only_failure(reason: str) -> None:
    if ANALYSIS_ONLY_FAILURE:
        ANALYSIS_ONLY_FAILURE.labels(reason=reason).inc()


def preinit_analysis_only_failure_series() -> None:
    if ANALYSIS_ONLY_FAILURE:
        for r in ("duplicate", "cooldown", "cb_active", "no_signal", "risk_block", "not_ready"):
            ANALYSIS_ONLY_FAILURE.labels(reason=r).inc(0)


def inc_positions_opened() -> None:
    if POSITIONS_OPENED:
        POSITIONS_OPENED.inc()


def inc_positions_closed() -> None:
    if POSITIONS_CLOSED:
        POSITIONS_CLOSED.inc()


def set_concurrent_positions(value: int) -> None:
    if CONCURRENT_POSITIONS:
        CONCURRENT_POSITIONS.set(float(value))


def inc_analysis_cycle() -> None:
    if ANALYSIS_CYCLES:
        ANALYSIS_CYCLES.inc()


def inc_brain_cycle() -> None:
    if BRAIN_CYCLES:
        BRAIN_CYCLES.inc()


def set_brain_state(state_value: int) -> None:
    if BRAIN_STATE:
        BRAIN_STATE.set(float(state_value))


def inc_decision_by_playbook(outcome: str, action: str, signal_type: str, playbook: str) -> None:
    if TRADING_DECISIONS_PLAYBOOK:
        TRADING_DECISIONS_PLAYBOOK.labels(
            outcome=outcome, action=action, signal_type=signal_type, playbook=playbook
        ).inc()


def inc_entry_guard_block(guard: str) -> None:
    if ENTRY_GUARD_BLOCK:
        ENTRY_GUARD_BLOCK.labels(guard=guard).inc()


def inc_validator_fail(validator: str, code: str) -> None:
    if VALIDATOR_FAIL:
        VALIDATOR_FAIL.labels(validator=validator, code=code).inc()


def inc_dupe_micro_bypass() -> None:
    if DUPE_MICRO_BYPASS:
        DUPE_MICRO_BYPASS.inc()
