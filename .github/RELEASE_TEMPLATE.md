# QuakeGuard [vX.Y.Z] - [Codename/Title]

**Release Date:** YYYY-MM-DD  
**Type:** [Major / Minor / Patch / Security Fix]  
**Codename:** [Codename]

---

## 🎯 Highlights

<!-- Inserisci i 3-4 cambiamenti più importanti e di maggior impatto architettonico -->
- **[Feature 1]**: Breve descrizione dell'impatto.
- **[Feature 2]**: Breve descrizione dell'impatto.
- **[Quality/Security]**: Es. SonarCloud Quality Gate Rating A.

---

## 🔧 Changes by Component

<!-- Rimuovi le tabelle dei componenti che non hanno subito modifiche in questa release -->

### Firmware (ESP32-C3)
| Change | Description |
|--------|-------------|
| **[Componente/File]** | Descrizione tecnica della modifica. |

### Backend (FastAPI + Redis + TimescaleDB)
| Area | Changes |
|------|---------|
| **[Area/Modulo]** | Descrizione tecnica della modifica. |

### Mobile (React Native + Expo)
| Area | Changes |
|------|---------|
| **[Screen/Logic]** | Descrizione tecnica della modifica. |

### Documentation & Infrastructure
| File/Area | Changes |
|-----------|---------|
| **[File.md]** | Aggiornamenti alle istruzioni o alla CI/CD. |

---

## 🔒 Security

<!-- Dettaglia le modifiche relative alla sicurezza (Zero-Trust, crittografia, hardening). Rimuovi la sezione se non ci sono aggiornamenti di sicurezza. -->
- **[Vulnerability/Hardening]**: Spiegazione di come il sistema è stato blindato.

---

## 🧪 Testing Summary

| Suite | Status |
|-------|--------|
| Backend (pytest) | <!-- Es: 118 passed --> ✅ |
| Mobile (jest / ESLint) | <!-- Es: 23 passed, 0 errors --> ✅ |
| Firmware (PlatformIO / Native) | <!-- Es: Build SUCCESS, 3/3 passed --> ✅ |
| Static Analysis (CodeQL/Sonar) | <!-- Es: Clean --> ✅ |

---

## 🚀 Deployment & Artifacts

**Auto-triggers post-merge:**
- GitHub Container Registry push (backend Docker image)
- GitHub Pages deploy (docs/web)
- Zenodo archive (via `CITATION.cff`)

**Versioned Artifacts:**
- `CHANGELOG.md`
- `CITATION.cff`
- `README.md` & `ROADMAP.md`

---

## 🔗 Related

- PR: #[Numero PR]
- SonarCloud: https://sonarcloud.io/summary/new_code?id=GiZano_QuakeGuard
- Roadmap: `ROADMAP.md`

<!-- La sezione "What's Changed" e il link al full changelog verranno iniettati in automatico da GitHub al momento della pubblicazione -->