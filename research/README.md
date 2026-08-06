# QuakeGuard — SIL Research (ROADMAP R1)

Software-in-the-Loop cross-validation of the STA/LTA detection core against the
INGV/ITACA strong-motion dataset. The detection runs on **the exact same C++
code** as the ESP32 firmware (`firmware/src/DetectionCore.h`), guaranteeing
numerical equivalence for the IEEE paper.

```
┌─ fetch_itaca.py ─── download accelerograms + P-arrival ground truth
│                        (graceful degradation: real ITACA if ITACA_TOKEN,
│                         realistic synthetic fallback otherwise)
│
├─ synthetic.py ─────── generate a synthetic dataset (no network) for CI / smoke tests
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

`fetch_itaca.py` emits a **fixed** dataset layout. Downstream modules
(`metrics.py`, `calibrate.py`, the C++ core) never know whether they process a
real earthquake or a locally generated mock — that is the point. Resolution:

- **Real path (ITACA).** Set `ITACA_TOKEN` (e.g. in a `.env`). The script then
  calls the ITACA/ESM `eventdata` web-service (`/itaca40ws/eventdata/1/query`)
  and parses the returned DYNA 1.2 ASCII archive into the shared layout.
  *Note:* the ITACA registration/token portal is currently unavailable, so the
  real download path is implemented as an explicitly-failing stub rather than a
  silent mock.
- **Synthetic fallback (default).** When no token is configured the script
  generates *realistic* accelerometer-like mocks: white background noise, a
  high-frequency P impulse, a larger/lower-frequency S arrival, and a 1 G
  gravity offset (matching the firmware's `sensors_event_t`). The exact
  P-arrival is written to `ground_truth.json` as the reference.

```
┌────────────────────────────────────────────────────────────────────────┐
│  fetch_itaca.py                                                         │
│    ITACA_TOKEN set? ──yes──▶ eventdata WS → DYNA 1.2 → t,ax,ay,az (m/s²)│
│           │no                                                          │
│           └──────────▶ realistic synthetic generator ──── P known       │
└──────────────────────────────▶ (identical layout below) ────────────────┘
```

## Dataset layout

The dataset is **not** committed to git (see `research/README.md` re: license
and weight). Generate it with:

```bash
# real INGV/ITACA (needs ITACA_TOKEN in the environment)
python research/fetch_itaca.py research/data
# or, for a realistic local / CI mock:
python research/fetch_itaca.py research/data          # same command, no token
python research/synthetic.py  research/data_synth
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

ITACA/ESM DYNA 1.2 files carry accelerations in **Gal** (cm/s²). The real
parser converts to the same m/s² scale the firmware/C++ core expects:

```
Acceleration (m/s²) = Acceleration (Gal) / 100
1 G = 980.665 Gal = 9.8 m/s²
```

## Licensing & the real Zenodo dataset

- **ITACA = CC-BY-NC-ND 4.0.** The derived, converted accelerograms must *not*
  be redistributed as a modified dataset. The elegant resolution:
  * fetch the raw ITACA data on-the-fly on the user's machine (the code, not
    the data, is distributed);
  * process it locally; publish only the **aggregate results** (ROC, F1,
    false-alarm rates, optimal calibration parameters) — these are research
    outputs, not derivatives of the seismic data;
  * cite ITACA formally (CC-BY attribution) in the paper and in `CITATION.cff`.
- **QuakeGuard MEMS Dataset (yours).** The Zenodo dataset with its own DOI is
  the accelerogram recorded by your physical ESP32-C3 nodes (Tier A) — your own
  IP, licensed freely (e.g. MIT / CC-BY 4.0). ITACA serves only as reference
  ground truth for validating the detection algorithm (R1), never as a
  publishable output. See `CITATION.cff` for the ITACA citation once published.

## DOI workflow (QuakeGuard MEMS Dataset)

1. Collect the real MEMS accelerograms from your nodes into the documented
   layout.
2. Zip: `cd research && zip -r quakeguard_mems_v1.3.0.zip data/`
3. Upload to **Zenodo** → metadata (title, authors + ORCID, license, keywords)
   → **Publish**.
4. Append the returned DOI (type `doi`) to `CITATION.cff`.
5. Do **not** commit the raw data (gitignored); the README documents re-download.

> The DOI is assigned **once**; fix data only by publishing a new Zenodo version.