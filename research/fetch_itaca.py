"""Download accelerograms + ground truth from the ITACA strong-motion portal.

Graceful-degradation fetcher used as the single entry point for real-world
validation data for the SIL pipeline (ROADMAP R1). The script emits a *fixed*
dataset layout (documented in research/README.md) so downstream modules
(metrics.py, calibrate.py, the C++ core) never know whether they process a real
earthquake or a locally generated mock -- that is the I/O contract.

Resolution strategy:
  1. If the ``ITACA_TOKEN`` environment variable is set (e.g. from a .env
     file), fetch the real accelerogram from the ITACA/ESM ``eventdata``
     web-service and parse the returned DYNA 1.2 ASCII archive.
  2. Otherwise, gracefully degrade to a *realistic synthetic* accelerogram
     (white background noise + high-frequency P impulse + larger S arrival),
     whose exact P-arrival is known and written to ground_truth.json.

Output:
    <out_dir>/
        events/<event_id>.csv   # t,ax,ay,az  (100 Hz, G)
        ground_truth.json        # [{event_id, p_arrival_s}]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
from pathlib import Path

SAMPLING_HZ = 100

# The gravity constant is the *standard* one used in geophysics, NOT the 9.81
# approximation from the ADXL345 datasheet. ITACA/ESM DYNA 1.2 files carry
# accelerations in Gal (cm/s^2); 1 G = 980.665 Gal exactly. Keeping this
# constant lets the C++ NOISE_FLOOR react to the same physical scale both
# locally and on the real MEMS node.
G_TO_MS2 = 9.80665
GAL_PER_G = 1e2 / G_TO_MS2  # = 980.665 Gal per G
GRAVITY = G_TO_MS2  # m/s^2, vertical baseline for the synthetic mock


class ItacaDataError(RuntimeError):
    """Raised when the ITACA portal does not return usable data."""


class ItacaFetcher:
    """Downloads real ITACA data when a token is available.

    Uses the ITACA strong-motion web-services:
        eventdata WS : /itaca40ws/eventdata/1/query
        auth         : a signed-message token from
                       /itaca40ws/generate-signed-message/1/

    The exact HTTP auth handshake changes across portal revisions and is
    therefore isolated here so the rest of the pipeline never changes.
    """

    def __init__(self, base_url: str = "https://itaca.mi.ingv.it", token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token if token is not None else os.environ.get("ITACA_TOKEN")

    @property
    def available(self) -> bool:
        """Whether a real download is possible (a token is configured)."""
        return bool(self.token)

    def list_events(self, min_magnitude: float = 4.0) -> list[dict]:
        """Return [{event_id, p_arrival_s}] for catalog events above magnitude.

        Queries the ITACA *flatfile* web-service (publicly accessible, no token
        required) for candidate events and their P-arrival metadata. The
        flatfile currently does NOT expose phase arrivals, so this is a hook
        for the future schema mapping.
        """
        raise NotImplementedError(
            "Real ITACA event catalogue not bound to the live flatfile schema; "
            "use the synthetic fallback (no ITACA_TOKEN)."
        )

    def download(self, event: dict, out_dir: Path) -> None:
        """Download one real event's accelerogram and write the CSV (G units).

        Adapt `_build_request` / `_parse_dyna` to the live portal format.
        """
        raise NotImplementedError(
            "Real ITACA waveform parsing is token-gated and not implemented; "
            "use the synthetic fallback (no ITACA_TOKEN)."
        )


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
    out_dir = Path(out_dir)
    events_dir = out_dir / "events"
    events_dir.mkdir(parents=True, exist_ok=True)

    gen = RealisticSynthetic()
    ground_truth: list[dict] = []
    for i in range(n_events):
        event_id = f"synth_{i:03d}"
        times, axes, p_arrival = gen.synthesize(event_id, seed=seed + i, pga_ms2=1.0 + 0.6 * i)
        write_accelerogram_csv(events_dir / f"{event_id}.csv", times, axes)
        ground_truth.append({"event_id": event_id, "p_arrival_s": p_arrival})

    with (out_dir / "ground_truth.json").open("w") as f:
        json.dump(ground_truth, f, indent=2)


def resolve_mode(fetcher: ItacaFetcher | None = None) -> str:
    """Return ``real`` or ``synthetic`` depending on the available token."""
    fetcher = fetcher or ItacaFetcher()
    return "real" if fetcher.available else "synthetic"


def download_catalog(
    out_dir: Path,
    min_magnitude: float = 4.0,
    n_events: int = 5,
    seed: int = 42,
    fetcher: ItacaFetcher | None = None,
) -> tuple[list[Path], list[dict], str]:
    """Download the catalog. Returns (written_paths, ground_truth, mode).

    The output contract (layout + units) is identical in both modes.
    """
    mode = resolve_mode(fetcher)
    if mode == "real":
        # TODO: implement the real ITACA path once a token is available and the
        # DYNA 1.2 parser is bound. Until then the real path refuses to run
        # instead of emitting a mock under a misleading name.
        raise NotImplementedError(
            "ITACA real download is not implemented yet. "
            "Run without ITACA_TOKEN to use the synthetic fallback."
        )

    build_synthetic_dataset(Path(out_dir), n_events=n_events, seed=seed)
    written = sorted((Path(out_dir) / "events").glob("*.csv"))
    with (Path(out_dir) / "ground_truth.json").open() as f:
        ground_truth = json.load(f)
    return written, ground_truth, mode


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_dir", type=Path, help="output validation dataset dir")
    parser.add_argument("--min-magnitude", type=float, default=4.0)
    parser.add_argument("--n-events", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    try:
        written, ground_truth, mode = download_catalog(
            args.out_dir, args.min_magnitude, n_events=args.n_events, seed=args.seed
        )
    except NotImplementedError as exc:
        print(f"ITACA download not yet integrated ({exc}).", file=sys.stderr)
        return 1

    print(f"[{mode}] Wrote {len(written)} accelerograms to {args.out_dir / 'events'}")
    print(f"[{mode}] Ground truth: {len(ground_truth)} events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
