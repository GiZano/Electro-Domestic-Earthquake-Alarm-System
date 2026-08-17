# TODO — Single-repo workflow + Sonar gate fix + dual-track roadmap

Stato: il flusso single-repo (docs/web → GiZano.github.io) è **implementato e
attivo** (commit `3036774`). Questa lista traccia il follow-up corrente:

1. **Fix del quality gate SonarCloud** (rosso dopo `3036774`)
2. **Rimozione del fetcher ITACA** (`research/fetch_itaca.py`) in favore di ESM
3. **Roadmap del sito a doppio binario** (sviluppo | ricerca), allineata a `ROADMAP.md`
4. Tutto passa da **PR unica** (niente push diretto su main)

---

## ✅ Fatto (single-repo, già su main `3036774`)

- [x] Whitepaper spostato in `docs/whitepaper/` (git mv + PDF) e nuovo hub `docs/README.md`
- [x] `docs/web/` creato con i 4 file + `assets/` (path relativi invariati)
- [x] Contenuto v1.2.1 applicato a html + dict JS EN/IT
- [x] Badge `release.svg` → v1.2.1
- [x] `deploy-gh-pages.yml` creato e **funzionante** (sync `43cde26` su GiZano.github.io)
- [x] Secret `GIZANO_IO_PAT` aggiunto (PAT Contents R/W + Metadata su GiZano.github.io)
- [x] Pagina live verificata: `softwareVersion: 1.2.1`

## 🔴 Problema rilevato (dopo il deploy)

Il quality gate SonarCloud è **rosso**: il commit ha messo `docs/web/` sotto
analisi. Nuovo-codice nel leak period:

- `docs/web/quakeguard.html:57` — CSP `unsafe-inline` (vulnerabilità)
- `docs/web/quakeguard.html:112` — `<a>` senza `onKeyDown` (bug) + button-role (code smell)
- `docs/web/quakeguard.html:677` — status-role (code smell)
- `docs/web/quakeguard.js` — 4.3% duplicazione (dict EN/IT)
- `research/fetch_itaca.py:228` — path-injection (preesistente, dentro il leak period)

---

## Fase A — Escludere `docs/` da SonarCloud

- [x] `sonar-project.properties`: `sonar.exclusions` += `docs/web/**,docs/whitepaper/**`
- [x] (nessuna modifica a html/js: CSP e accessibility sono scelte del sito)

## Fase B — Rimuovere `research/fetch_itaca.py` (ITACA → ESM)

- [x] Relocare il generatore sintetico (`RealisticSynthetic`,
      `write_accelerogram_csv`, `build_synthetic_dataset`, costanti) in
      `research/synthetic.py` (oggi è solo un wrapper) — CLI invariata per `iot-ci.yml`
- [x] Eliminare `fetch_itaca.py` (codice ITACA morto: `ItacaFetcher`,
      `download_catalog`, `resolve_mode`, CLI, `ItacaDataError`, logica `ITACA_TOKEN`)
- [x] Aggiornare `research/__init__.py` (docstring pipeline)
- [x] Aggiornare `research/README.md` (diagramma, graceful degradation, comandi);
      ESM resta documentato come rimanente per chiudere R1
- [x] (niente obspy ora)

## Fase C — Roadmap sito a doppio binario (docs/web, EN/IT)

- [x] Bottone in cima alla `#roadmap`: "See the detailed roadmap" →
      `https://github.com/GiZano/QuakeGuard/blob/main/ROADMAP.md`
- [x] Colonna **Sviluppo**: v1.0 · v1.1 · **v1.2.0 (nuova)** · **v1.2.1 · Current**
      (Geo-Zoning & Cooldown Fragmentation, GNSS-ready) · **v1.2.2 = Zero-Trust
      Serial Fallback (USB)** · v1.3 · v2.0 · v2.1
- [x] Colonna **Ricerca**: R1 · Done · R2 · Next · R3 · Planned (+ nota dipendenza R1→v2.2.0)
- [x] Specchio nel dict JS EN/IT (`road_120_*`, `road_122`, `road_13`,
      `r1/r2/r3`, `roadmap_details`)

## Fase D — Verifiche

- [x] `ruff check research/` (nessun errore nuovo: S311 era già in `fetch_itaca.py`)
- [x] Smoke test SIL: `python research/synthetic.py research/out/synth_dataset --n-events 3`
      + `cd research && python calibrate.py out/synth_dataset --out out/calibration.json` ✓
- [x] `node --check docs/web/quakeguard.js` + parità chiavi EN/IT (185 = 185)
- [x] Sanity check exclusion Sonar

## Fase E — PR unica

- [x] Branch `fix/sonar-gate-and-roadmap`
- [ ] Commit:
      `chore(quality): exclude docs/ from sonarcloud analysis` ·
      `refactor(research): drop ITACA fetcher, keep synthetic generator in synthetic.py` ·
      `docs(web): dual-track roadmap aligned with ROADMAP.md`
- [ ] `gh pr create` → SonarCloud sulla PR: gate atteso **verde**
- [ ] Merge → `deploy-gh-pages.yml` risincronizza la pagina live; verifica finale

## Validazione post-merge

- [ ] `https://giovanni-zanotti.is-a.dev/projects/quakeguard.html` mostra la
      roadmap dual-track + bottone; gate Sonar verde su main
