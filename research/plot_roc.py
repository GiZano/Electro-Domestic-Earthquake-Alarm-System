"""Generate paper artifacts from a calibration run: ROC plot + metrics JSON.

matplotlib is optional; plotting is skipped cleanly if it is not installed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from calibrate_io import resolve_within_root


def plot_roc(calibration: dict, out_path: Path) -> bool:
    """Render the ROC curve. Returns False if matplotlib is unavailable."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    roc = calibration["roc"]
    xs = [r["fpr"] for r in roc]
    ys = [r["tpr"] for r in roc]

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot(xs, ys, marker="o", label="SIL detector")
    ax.plot([0, 1], [0, 1], "--", color="gray", label="random")
    ax.set_xlabel("False-Alarm Rate")
    ax.set_ylabel("Sensitivity (TPR)")
    ax.set_title("QuakeGuard R1: STA/LTA Algorithm Cross-Validation (SIL)")
    ax.legend(loc="lower right")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    return True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("calibration_json", type=Path)
    parser.add_argument("--roc-out", type=Path, default=Path("roc_curve.png"))
    args = parser.parse_args(argv)

    calibration = json.loads(args.calibration_json.read_text())
    out_path = resolve_within_root(args.roc_out)
    wrote = plot_roc(calibration, out_path)
    print(f"ROC plot written to {out_path}" if wrote else "matplotlib not installed; plot skipped")


if __name__ == "__main__":
    main()
