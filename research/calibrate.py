"""Calibration of the STA/LTA trigger parameters against INGV ground truth.

Sweeps TRIGGER_RATIO x NOISE_FLOOR (HPF_ALPHA fixed at 0.9), runs the
detector on every accelerogram, and selects the parameters that maximise the
F1 score (harmonic mean of precision and recall).

Output (JSON):
    {
      "best": {"trigger_ratio": ..., "noise_floor": ..., "hpf_alpha": 0.9,
               "sensitivity": ..., "false_alarm_rate": ...,
               "median_latency_s": ...},
      "sweep": [{ "trigger_ratio":..., "noise_floor":...,
                  "sensitivity":..., "false_alarm_rate":..., "f1":...}, ...],
      "roc": [{ "trigger_ratio":..., "fpr":..., "tpr":...,
                "median_latency_s":...}, ...]
    }
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from calibrate_io import load_validation_set
from metrics import compute_metrics, roc_curve
from orchestrator import build_cli, run_detector

DEFAULT_RATIOS = [1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0]
DEFAULT_FLOORS = [0.02, 0.03, 0.04, 0.05, 0.06, 0.08]
HPF_ALPHA = 0.9


def f1(sensitivity: float, false_alarm_rate: float) -> float:
    """F1 = harmonic mean of precision and recall."""
    precision = 1.0 - false_alarm_rate
    denom = precision + sensitivity
    if denom == 0.0:
        return 0.0
    return 2.0 * (precision * sensitivity) / denom


def calibrate(
    cli_path: Path,
    samples,
    ground_truth,
    ratios: list[float] | None = None,
    floors: list[float] | None = None,
) -> dict:
    """Run the full sweep and return the summary dict (JSON-serialisable)."""
    ratios = ratios or DEFAULT_RATIOS
    floors = floors or DEFAULT_FLOORS

    def evaluate(ratio, floor):
        results = {}
        for s in samples:
            results[s.event_id] = run_detector(
                cli_path,
                s.times,
                s.axes,
                trigger_ratio=ratio,
                noise_floor=floor,
                hpf_alpha=HPF_ALPHA,
            )
        return results

    sweep = []
    for ratio in ratios:
        for floor in floors:
            m = compute_metrics(evaluate(ratio, floor), ground_truth)
            sweep.append(
                {
                    "trigger_ratio": ratio,
                    "noise_floor": floor,
                    "sensitivity": m.sensitivity,
                    "false_alarm_rate": m.false_alarm_rate,
                    "median_latency_s": m.median_latency_s,
                    "f1": f1(m.sensitivity, m.false_alarm_rate),
                }
            )

    best = max(sweep, key=lambda row: row["f1"])
    roc = []
    for ratio in ratios:
        floor = best["noise_floor"]
        m = compute_metrics(evaluate(ratio, floor), ground_truth)
        roc.append(
            {
                "trigger_ratio": ratio,
                "fpr": m.false_alarm_rate,
                "tpr": m.sensitivity,
                "median_latency_s": m.median_latency_s,
            }
        )

    return {"best": best, "sweep": sweep, "roc": roc}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset", type=Path, help="validation dataset dir (CSV + ground truth JSON)"
    )
    parser.add_argument("--out", type=Path, default=Path("calibration.json"))
    parser.add_argument("--cli", type=Path, default=None, help="detect_cli binary")
    args = parser.parse_args(argv)

    samples, ground_truth = load_validation_set(args.dataset)
    cli = build_cli(args.cli)

    summary = calibrate(cli, samples, ground_truth)
    args.out.write_text(json.dumps(summary, indent=2))
    print(f"Calibration written to {args.out}")
    print(
        f"Best: ratio={summary['best']['trigger_ratio']} "
        f"floor={summary['best']['noise_floor']} "
        f"sensitivity={summary['best']['sensitivity']:.3f} "
        f"FAR={summary['best']['false_alarm_rate']:.3f} "
        f"latency={_fmt_latency(summary['best']['median_latency_s'])}"
    )


def _fmt_latency(latency: float | None) -> str:
    """Render a latency, or a clear placeholder when no event was detected."""
    return f"latency={latency:.3f}s" if latency is not None else "latency=n/a (no detections)"


if __name__ == "__main__":
    main()
