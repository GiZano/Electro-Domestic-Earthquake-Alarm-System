"""Generate a synthetic validation dataset for local smoke tests / CI.

Canonical provider of the realistic synthetic fallback for the SIL pipeline
(R1). Produces the same layout as the real ESM path (to be implemented via
ObsPy, public FDSN API — see research/README.md):
    <out_dir>/
        events/<event_id>.csv
        ground_truth.json

Used to exercise the full SIL pipeline without downloading a real dataset.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path

from calibrate_io import resolve_within_root

SAMPLING_HZ = 100

# Standard geophysics gravity constant (1 G = 9.80665 m/s^2). The synthetic
# node "sits" under this baseline, matching the firmware `sensors_event_t`.
GRAVITY = 9.80665  # m/s^2, vertical baseline for the synthetic mock


class RealisticSynthetic:
    """Realistic accelerometer-like mock: noise + high-frequency P + larger S.

    The waveform mimics what a MEMS node resting under gravity records. Because
    the detector's feature is the *magnitude* norm(x,y,z) over a ~9.8 m/s^2
    gravity baseline, only the VERTICAL (Z) component changes that norm in
    first order; horizontal shaking perturbs it to second order and stays below
    the noise floor. The synthetic therefore puts both the P and S energy on
    the vertical axis (as a vertical-component accelerogram does), while the
    measured axes still carry a realistic 9.8 m/s^2 gravity offset:

      - continuous white background noise (well below NOISE_FLOOR);
      - a short, high-frequency P impulse arriving at ``p_arrival_s``;
      - a stronger, lower-frequency S arrival ~1.8 s later;
      - a constant GRAVITY vertical offset (the node "sits" under gravity).

    Units: m/s^2, matching the Adafruit `sensors_event_t` API the firmware
    feeds into the core and the 9.8 m/s^2 gravity baseline of the C++ detector.
    """

    def __init__(self, fs: int = SAMPLING_HZ) -> None:
        self.fs = fs

    def synthesize(
        self,
        event_id: str,
        seed: int = 0,
        pga_ms2: float = 2.0,
        p_arrival_s: float = 7.0,
    ) -> tuple[list[float], list[tuple[float, float, float]], float]:
        """Return (times, axes_in_m/s2, exact_p_arrival_s)."""
        del event_id
        rng = random.Random(seed)
        fs = self.fs

        s_offset_s = 1.8  # S follows P by ~1.8 s (near-source delay)
        s_arrival_s = p_arrival_s + s_offset_s
        duration_s = p_arrival_s + 15.0
        n = int(duration_s * fs)
        times = [i / fs for i in range(n)]

        noise_sigma = 0.02  # ~0.02 m/s^2 background gaussian noise (<= 2e-3 G)
        axes: list[tuple[float, float, float]] = []

        for i in range(n):
            t = times[i]
            ax = rng.gauss(0.0, noise_sigma)
            ay = rng.gauss(0.0, noise_sigma)
            raw_z = rng.gauss(0.0, noise_sigma)

            # P-wave impulse: short high-frequency burst on the vertical axis
            dt_p = t - p_arrival_s
            if 0.0 <= dt_p < 0.5:
                f_p = 10.0
                az_p = 0.30 * pga_ms2 * math.sin(2 * math.pi * f_p * dt_p) * math.exp(-25.0 * dt_p)
                raw_z += az_p
                ax += 0.15 * az_p
                ay += 0.15 * az_p

            # S-wave arrival: larger, lower-frequency energy on the vertical axis
            dt_s = t - s_arrival_s
            if 0.0 <= dt_s < 5.0:
                f_s = 2.5
                as_ = pga_ms2 * math.sin(2 * math.pi * f_s * dt_s) * math.exp(-1.2 * dt_s)
                raw_z += as_

            # Horizontal projection is kept near-zero: with a gravity baseline the
            # magnitude is dominated by the vertical, so horizontal-only motion is
            # invisible to norm3 (as on the real node).
            axes.append((ax, ay, raw_z + GRAVITY))

        return times, axes, p_arrival_s


def write_accelerogram_csv(
    path: Path, times: list[float], axes: list[tuple[float, float, float]]
) -> None:
    """Write an accelerogram in the shared t,ax,ay,az CSV format (G units)."""
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["# t,ax,ay,az"])  # header (ignored by parser)
        for t, (ax, ay, az) in zip(times, axes):
            writer.writerow([f"{t:.6f}", f"{ax:.6f}", f"{ay:.6f}", f"{az:.6f}"])


def build_synthetic_dataset(out_dir: Path, n_events: int = 5, seed: int = 42) -> None:
    """Generate a realistic synthetic validation dataset (fallback mode)."""
    safe_dir = resolve_within_root(out_dir)
    events_dir = safe_dir / "events"
    events_dir.mkdir(parents=True, exist_ok=True)

    gen = RealisticSynthetic()
    ground_truth: list[dict] = []
    for i in range(n_events):
        event_id = f"synth_{i:03d}"
        times, axes, p_arrival = gen.synthesize(event_id, seed=seed + i, pga_ms2=1.0 + 0.6 * i)
        write_accelerogram_csv(events_dir / f"{event_id}.csv", times, axes)
        ground_truth.append({"event_id": event_id, "p_arrival_s": p_arrival})

    with (safe_dir / "ground_truth.json").open("w") as f:
        json.dump(ground_truth, f, indent=2)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_dir", type=Path, help="output dataset dir")
    parser.add_argument("--n-events", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    build_synthetic_dataset(args.out_dir, n_events=args.n_events, seed=args.seed)
    print(f"Synthetic dataset written to {args.out_dir}")


if __name__ == "__main__":
    main()
