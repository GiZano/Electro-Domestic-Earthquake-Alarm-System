"""Dataset I/O for the SIL validation set.

Shared layout (documented in research/README.md):
    <dataset_dir>/
        events/
            <event_id>.csv      # t,ax,ay,az  (100 Hz, G units)
        ground_truth.json        # [{event_id, p_arrival_s}]
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from metrics import GroundTruth

GROUND_TRUTH_FILE = "ground_truth.json"
EVENTS_DIR = "events"


def resolve_within_root(path: Path, root: Path | None = None) -> Path:
    """Resolve a user-supplied output path and refuse escapes outside *root*.

    Guards the CLI scripts against path-injection (Sonar S8707): a path such as
    ``../../etc/something`` constructed from a command-line argument must not be
    allowed to write outside the intended working directory.
    """
    base = (root or Path.cwd()).resolve()
    target = Path(path).expanduser().resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise ValueError(f"Refusing to write outside {base}: {target}") from None
    return target


@dataclass
class Accelerogram:
    """One recorded accelerogram."""

    event_id: str
    times: list[float] = field(default_factory=list)
    axes: list[tuple[float, float, float]] = field(default_factory=list)


def load_validation_set(dataset_dir: Path) -> tuple[list[Accelerogram], list[GroundTruth]]:
    """Load all accelerograms and ground truth from a validation dataset dir."""
    dataset_dir = Path(dataset_dir)
    events_dir = dataset_dir / EVENTS_DIR
    gt_path = dataset_dir / GROUND_TRUTH_FILE

    if not events_dir.is_dir():
        raise FileNotFoundError(f"No {EVENTS_DIR}/ directory in {dataset_dir}")
    if not gt_path.is_file():
        raise FileNotFoundError(f"Missing {GROUND_TRUTH_FILE} in {dataset_dir}")

    with gt_path.open() as f:
        raw_gt = json.load(f)
    ground_truth = [GroundTruth(event_id=g["event_id"], p_arrival_s=float(g["p_arrival_s"])) for g in raw_gt]

    samples: list[Accelerogram] = []
    for csv_path in sorted(events_dir.glob("*.csv")):
        times, axes = read_accelerogram(csv_path)
        samples.append(Accelerogram(event_id=csv_path.stem, times=times, axes=axes))

    return samples, ground_truth


def read_accelerogram(path: Path) -> tuple[list[float], list[tuple[float, float, float]]]:
    """Read a t,ax,ay,az CSV (skipping '#' comments)."""
    times: list[float] = []
    axes: list[tuple[float, float, float]] = []
    with path.open() as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            t, ax, ay, az = (float(v) for v in row[:4])
            times.append(t)
            axes.append((ax, ay, az))
    return times, axes
