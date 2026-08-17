# QuakeGuard — SIL Research (ROADMAP R1)

Software-in-the-Loop cross-validation of the STA/LTA detection core against the
INGV/ITACA strong-motion dataset. The detection runs on **the exact same C++
code** as the ESP32 firmware (`firmware/src/DetectionCore.h`), guaranteeing
numerical equivalence for the IEEE paper.

```
┌─ synthetic.py ─── generate a realistic synthetic dataset (no network) for CI / smoke tests
│                        (canonical fallback provider; same layout as the future ESM path)
│
├─ calibrate_io.py ── load events/ + ground_truth.json
│
├─ orchestrator.py ── compile & run the host C++ CLI (firmware/tools/detect_cli.cpp)
│                         sole Python↔C++ bridge (subprocess)
│
├─ metrics.py ────── Sensitivity/Recall, False-Alarm Rate, latency, ROC
│
├─ calibrate.py ──── sweep TRIGGER_RATIO x NOISE_FLOOR, maximize F1
│
└─ plot_roc.py ───── ROC curve figure for the paper
```

## Graceful degradation (I/O contract)

`synthetic.py` emits a **fixed** dataset layout. Downstream modules
(`metrics.py`, `calibrate.py`, the C++ core) never know whether they process a
real earthquake or a locally generated mock — that is the point. Resolution:

- **Real path (ESM, to be implemented).** The planned ESM (European
  Strong-Motion) downloader queries the **public FDSN web-service** using
  **ObsPy** (`obspy.fdsn`), downloads the parametric flatfiles and accelerograms,
  and converts them into the shared layout. No registration token is required,
  so the real path can work headlessly in CI/CD. This replaces the previous
  ITACA DYNA-1.2 parser (custom code, token-gated portal).
- **Synthetic fallback (default).** When no network/ESM is available,
  `synthetic.py` generates *realistic* accelerometer-like mocks: white background
  noise, a high-frequency P impulse, a larger/lower-frequency S arrival, and a
  1 G gravity offset (matching the firmware's `sensors_event_t`). The exact
  P-arrival is written to `ground_truth.json` as the reference.

```
┌────────────────────────────────────────────────────────────────────────┐
│  synthetic.py                                                           │
│    (fallback) ───────▶ realistic synthetic generator ──── P known       │
│                                                                         │
│  ESM downloader (future, ObsPy public FDSN) ───▶ t,ax,ay,az  (m/s²)    │
└──────────────────────────────▶ (identical layout below) ────────────────┘
```

## Dataset layout

The dataset is **not** committed to git (see `research/README.md` re: license
and weight). Generate it with:

```bash
# realistic local / CI mock (no network required)
python research/synthetic.py research/data_synth
# real ESM (public FDSN API, no token) — to be implemented (R1 closure)
# python research/fetch_esm.py research/data
```

Layout produced by every path (units **m/s^2**, the same as the firmware
`Adafruit sensors_event_t`; gravity baseline ~9.8 on Z):

```
<dataset>/
    events/<event_id>.csv      # t,ax,ay,az  (100 Hz, m/s^2; '#' = comment)
    ground_truth.json          # [{"event_id": ..., "p_arrival_s": ...}]
```

## Run the full pipeline

```bash
# 1. build the host CLI (or let orchestrator.py compile it)
g++ -std=c++11 -I firmware/src firmware/tools/detect_cli.cpp -lm -o firmware/tools/detect_cli

# 2. calibrate against the dataset
python research/calibrate.py research/data --out research/out/calibration.json

# 3. print the ROC figure
python research/plot_roc.py research/out/calibration.json --roc-out research/out/roc.png
```

## Unit conversion (Gal → m/s²)

ESM/ITACA flatfiles carry accelerations in **Gal** (cm/s²). The parser converts
to the same m/s² scale the firmware/C++ core expects:

```
Acceleration (m/s²) = Acceleration (Gal) / 100
1 G = 980.665 Gal = 9.8 m/s²
```

## Licensing & the real Zenodo dataset

- **ESM = CC-BY-4.0 (parametric flatfiles).** ESM distributes its parametric
  flatfiles (magnitude, station coordinates, PGA, distances) under **CC-BY-4.0**.
  The **derived calibration dataset** (parsed events + ground truth in the shared
  layout) is therefore **re-distributable**: it can be published as an open
  validation artifact on Zenodo with its own DOI. Cite ESM in `CITATION.cff`.
- **ITACA = CC-BY-NC-ND-4.0.** ITACA forbids redistribution and modification of
  its data. The derived, converted accelerograms must *not* be redistributed as a
  modified dataset. The elegant resolution:
  * fetch the raw data on-the-fly on the user's machine (the code, not the data,
    is distributed);
  * process it locally; publish only the **aggregate results** (ROC, F1,
    false-alarm rates, optimal calibration parameters) — these are research
    outputs, not derivatives of the seismic data;
  * cite ITACA formally (CC-BY attribution) in the paper and in `CITATION.cff`.
- **License re-verification gate.** Before publishing ANY derived artifact,
  re-check the current ITACA/ESM license terms (they can change) and update
  `CITATION.cff` accordingly at release time.
- **QuakeGuard MEMS Dataset (yours).** The Zenodo dataset with its own DOI is
  the accelerogram recorded by your physical ESP32-C3 nodes (Tier A) — your own
  IP, licensed freely (e.g. MIT / CC-BY 4.0). ITACA/ESM serve only as reference
  ground truth for validating the detection algorithm (R1), never as a
  publishable output. See `CITATION.cff` for the ESM/ITACA citations once published.

## DOI workflow (QuakeGuard MEMS Dataset)

1. Collect the real MEMS accelerograms from your nodes into the documented
   layout.
2. Zip: `cd research && zip -r quakeguard_mems_v1.3.0.zip data/`
3. Upload to **Zenodo** → metadata (title, authors + ORCID, license, keywords)
   → **Publish**.
4. Append the returned DOI (type `doi`) to `CITATION.cff`.
5. Do **not** commit the raw data (gitignored); the README documents re-download.

> The DOI is assigned **once**; fix data only by publishing a new Zenodo version.