"""Drive the host-compiled detection binary (same C++ source as the firmware).

The orchestrator is the *sole* Python↔C++ bridge: it invokes `detect_cli` via
subprocess, feeds it the accelerograms over stdin and collects the trigger
points. The detection decision itself is 100% owned by the C++ core.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CLI = Path(__file__).resolve().parents[1] / "firmware" / "tools" / "detect_cli"


@dataclass
class TriggerPoint:
    """A single trigger emitted by the detector."""

    time_s: float  # seconds, relative to the start of the accelerogram
    ratio: float  # STA/LTA at trigger time


@dataclass
class DetectionResult:
    """Detector output for one accelerogram."""

    event_id: str
    triggers: list[TriggerPoint] = field(default_factory=list)


class DetectionError(RuntimeError):
    """Raised when the C++ binary fails to run."""


def build_cli(cli_path: Path | None = None) -> Path:
    """Compile the host CLI if the binary is missing. Returns the binary path."""
    cli_path = cli_path or DEFAULT_CLI
    if cli_path.is_file():
        return cli_path

    src_dir = Path(__file__).resolve().parents[1] / "firmware"
    cli_src = src_dir / "tools" / "detect_cli.cpp"
    if not cli_src.is_file():
        raise DetectionError(f"Missing source: {cli_src}")

    gcc = shutil.which("g++")
    if gcc is None:
        raise DetectionError("g++ not found: install a C++ toolchain to run SIL validation")

    cmd = [gcc, "-std=c++11", "-I", str(src_dir / "src"), str(cli_src), "-lm", "-o", str(cli_path)]
    subprocess.run(cmd, check=True, capture_output=True)
    return cli_path


def run_detector(
    cli_path: Path,
    times: list[float],
    axes: list[tuple[float, float, float]],
    trigger_ratio: float = 1.8,
    noise_floor: float = 0.04,
    hpf_alpha: float = 0.9,
) -> list[TriggerPoint]:
    """Feed one accelerogram to the C++ core and return the trigger points.

    Args:
        cli_path: path to the compiled detect_cli binary.
        times: sample timestamps in seconds (100 Hz).
        axes: (ax, ay, az) samples in G.
        trigger_ratio/noise_floor/hpf_alpha: detector parameters.
    """
    if len(times) != len(axes):
        raise ValueError("times and axes must have the same length")

    lines = ["# t,ax,ay,az"]
    for t, (ax, ay, az) in zip(times, axes):
        lines.append(f"{t:.6f},{ax:.6f},{ay:.6f},{az:.6f}")
    stdin_data = "\n".join(lines)

    cmd = [str(cli_path), str(trigger_ratio), str(noise_floor), str(hpf_alpha)]
    proc = subprocess.run(
        cmd, input=stdin_data, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise DetectionError(f"detect_cli exited {proc.returncode}: {proc.stderr}")

    triggers: list[TriggerPoint] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) != 2:
            continue
        try:
            triggers.append(TriggerPoint(time_s=float(parts[0]), ratio=float(parts[1])))
        except ValueError:
            continue
    return triggers
