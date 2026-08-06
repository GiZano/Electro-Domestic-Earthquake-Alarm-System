"""Generate a synthetic validation dataset for local smoke tests / CI.

Thin wrapper over the realistic synthetic generator in fetch_itaca.py, so the
fallback (no-token) path and this generator stay exactly in sync. Produces the
same layout as the ITACA path:
    <out_dir>/
        events/<event_id>.csv
        ground_truth.json

Used to exercise the full SIL pipeline without downloading the INGV dataset.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fetch_itaca import build_synthetic_dataset


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