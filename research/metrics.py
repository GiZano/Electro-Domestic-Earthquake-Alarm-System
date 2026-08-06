"""SIL detection metrics: Sensitivity/Recall, False-Alarm Rate, latency, ROC.

Definitions (per event/accelerogram):
  - Sensitivity/Recall  = TP / (TP + FN)  over events
  - False-Alarm Rate    = FP / (FP + TP)  over triggers
  - Response latency    = trigger time - P-arrival time (median over TPs)
  - ROC curve           = sweep of TRIGGER_RATIO -> (FPR, TPR)

A trigger is a True Positive (TP) if it falls within a matching window after
the ground-truth P-arrival; otherwise it is a False Positive (FP).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from orchestrator import TriggerPoint

# P-wave arrival tolerance: a trigger is a TP if it fires between P and
# P + WINDOW. Triggers before the event or far after are FPs.
WINDOW_S = 10.0


@dataclass
class GroundTruth:
    """Known arrival times for one event."""

    event_id: str
    p_arrival_s: float  # P-wave arrival, relative to the start of the accelerogram


@dataclass
class EventScore:
    """Per-event outcome."""

    event_id: str
    triggers: list[TriggerPoint]
    p_arrival_s: float
    detected: bool
    latency_s: float | None = None


@dataclass
class MetricsSummary:
    """Aggregate metrics over a validation set."""

    sensitivity: float
    false_alarm_rate: float
    median_latency_s: float | None
    n_events: int
    n_triggers: int
    n_true_positives: int
    n_false_positives: int
    per_event: list[EventScore] = field(default_factory=list)


def score_event(triggers: list[TriggerPoint], truth: GroundTruth) -> EventScore:
    """Classify one event's triggers against its P-arrival."""
    tp = [
        tr
        for tr in triggers
        if tr.time_s >= truth.p_arrival_s and tr.time_s <= truth.p_arrival_s + WINDOW_S
    ]
    detected = len(tp) > 0
    latency = min(tr.time_s - truth.p_arrival_s for tr in tp) if tp else None
    return EventScore(
        event_id=truth.event_id,
        triggers=triggers,
        p_arrival_s=truth.p_arrival_s,
        detected=detected,
        latency_s=latency,
    )


def compute_metrics(
    results: dict[str, list[TriggerPoint]], ground_truth: list[GroundTruth]
) -> MetricsSummary:
    """Compute aggregate sensitivity, FAR and latency over the whole set."""
    truth_by_id = {g.event_id: g for g in ground_truth}
    unknown = [e for e in results if e not in truth_by_id]
    if unknown:
        raise ValueError(f"No ground truth for events: {sorted(unknown)}")

    scores: list[EventScore] = []
    for event_id, triggers in results.items():
        scores.append(score_event(triggers, truth_by_id[event_id]))

    n_events = len(scores)
    n_detected = sum(1 for s in scores if s.detected)
    n_triggers = sum(len(s.triggers) for s in scores)
    n_tp = sum(1 for s in scores if s.detected)
    n_fp = n_triggers - n_tp

    latencies = [s.latency_s for s in scores if s.latency_s is not None]
    median_latency = statistics.median(latencies) if latencies else None

    sensitivity = n_detected / n_events if n_events else 0.0
    false_alarm_rate = n_fp / (n_fp + n_tp) if (n_fp + n_tp) else 0.0

    return MetricsSummary(
        sensitivity=sensitivity,
        false_alarm_rate=false_alarm_rate,
        median_latency_s=median_latency,
        n_events=n_events,
        n_triggers=n_triggers,
        n_true_positives=n_tp,
        n_false_positives=n_fp,
        per_event=scores,
    )


@dataclass
class RocPoint:
    """One operating point of the ROC curve."""

    trigger_ratio: float
    fpr: float
    tpr: float
    median_latency_s: float | None


def roc_curve(
    evaluate: callable,
    ground_truth: list[GroundTruth],
    ratios: list[float],
) -> list[RocPoint]:
    """Trace the ROC curve by sweeping TRIGGER_RATIO.

    Args:
        evaluate: callable(ratio) -> dict[event_id, list[TriggerPoint]].
        ground_truth: ground-truth arrivals.
        ratios: candidate TRIGGER_RATIO values (ascending recommended).
    """
    curve: list[RocPoint] = []
    for ratio in ratios:
        results = evaluate(ratio)
        m = compute_metrics(results, ground_truth)
        curve.append(
            RocPoint(
                trigger_ratio=ratio,
                fpr=m.false_alarm_rate,
                tpr=m.sensitivity,
                median_latency_s=m.median_latency_s,
            )
        )
    return curve
