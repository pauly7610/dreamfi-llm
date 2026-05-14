"""Quality gates for source-intelligence packets."""
from __future__ import annotations

import re

from dreamfi.source_intelligence.models import InsightQuality, SourcePacket

_METRIC_HINT_RE = re.compile(
    r"(\d|%|rate|ratio|count|volume|trend|delta|lift|drop|latency|conversion|funnel|cohort)",
    re.IGNORECASE,
)
_REDACTED_PROFILES = {"aggregate", "masked", "redacted", "summary"}
_SENSITIVE_CLASSES = {"pii", "restricted", "secret"}


def _has_metric_or_observed_change(packet: SourcePacket) -> bool:
    haystack = " ".join(
        value
        for value in (packet.metric, packet.finding, packet.evidence)
        if value is not None
    )
    return bool(_METRIC_HINT_RE.search(haystack))


def _passes_redaction_policy(packet: SourcePacket) -> bool:
    if packet.sensitivity.strip().lower() not in _SENSITIVE_CLASSES:
        return True
    return packet.redaction_profile.strip().lower() in _REDACTED_PROFILES


def score_source_packet(packet: SourcePacket) -> InsightQuality:
    """Score whether a packet is useful evidence rather than connector posture."""
    checks = {
        "has_clear_finding": bool(packet.finding.strip()),
        "has_evidence": bool(packet.evidence.strip()),
        "has_metric_or_observed_change": _has_metric_or_observed_change(packet),
        "has_decision_relevance": bool(packet.decision_relevance.strip()),
        "has_owner_or_topic": bool(packet.owner.strip() or packet.topic_ids),
        "has_freshness_timestamp": packet.updated_at is not None,
        "declares_gap_when_not_fresh": packet.source_status == "connected" or bool(packet.gap),
        "passes_redaction_policy": _passes_redaction_policy(packet),
    }
    blockers = tuple(name for name, passed in checks.items() if not passed)
    score = round(sum(1 for passed in checks.values() if passed) / len(checks), 3)
    return InsightQuality(score=score, checks=checks, blockers=blockers)
