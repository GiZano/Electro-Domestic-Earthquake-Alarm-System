"""QuakeGuard SIL research package.

Software-in-the-Loop cross-validation of the STA/LTA detection core
(R1 of the ROADMAP #Research node).

Pipeline:
    fetch_itaca.py   -> download INGV/ITACA accelerograms + ground truth
    orchestrator.py  -> run the host-compiled detect_cli (same C++ as firmware)
    metrics.py       -> Sensitivity/Recall, False-Alarm Rate, latency, ROC
    calibrate.py     -> sweep TRIGGER_RATIO x NOISE_FLOOR against ground truth
"""

__version__ = "0.1.0"
