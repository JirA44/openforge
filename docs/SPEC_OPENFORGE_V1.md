# OpenForge V1 — Cahier des charges

Version : 1.0-draft · Date : 2026-08-22 · Statut : approuvé (dialogue)

## 1. Structure officielle retenue

| Rang | Projet | Objet |
|---|---|---|
| 0 | **OpenForge Core** | Infrastructure universelle : artefacts versionnés, provenance, hashes, tests automatiques, certification, API, scores de confiance |
| 1 | **MOS Hub / StrategyHub** | Première application : stratégies de trading reproductibles et certifiées |
| 2 | DataForge | Datasets versionnés, qualité, anomalies, biais |
| 3 | ModelForge | Modèles et agents IA, benchmarks reproductibles |
| 4 | KnowledgeForge + ProofForge | Affirmations sourcées, débats, preuves formelles |
| 5 | DecisionForge + CompanyForge | Décisions vs réalité, entreprises, valorisations |
| 6 | ExperimentForge + SimulationForge + RobotForge | Sciences, simulations, systèmes physiques |

Toutes les Forges partagent le noyau OpenForge : identités, versionnement,
provenance, signatures, exécution reproductible, certifications,
réputation, classement, API commune.

## 2. Architecture V1

```
┌─────────────────────────────────────────────────────┐
│                   Écrans (Web UI)                    │
│   leaderboard · fiche stratégie · comparaison        │
│   soumission · surveillance live                     │
└──────────────────────┬──────────────────────────────┘
                       │ REST
┌──────────────────────▼──────────────────────────────┐
│                  API FastAPI                         │
│  /validate /hash (existant)                          │
│  /moshub/backtest /moshub/sheets /moshub/compare     │
│  /moshub/certify /moshub/leaderboard                 │
│  /auth /artifacts                                    │
└───────┬──────────────────┬──────────────────┬────────┘
        │                  │                  │
┌───────▼──────┐  ┌────────▼────────┐  ┌──────▼─────────┐
│ Artifact     │  │ Certification   │  │ Repro Runner   │
│ Store        │  │ Engine          │  │ (sandbox)      │
│ (git + JSONL │  │ machine à états │  │ backtests      │
│ immuable)    │  │ + seuils        │  │ déterministes  │
└──────────────┘  └─────────────────┘  └────────────────┘
```

Principes non négociables :
1. **Append-only** : aucun résultat ni statut n'est réécritable ; corrections = nouvelle version.
2. **Décisions calculées** : la certification découle des preuves enregistrées, jamais écrite par un agent ou un humain directement.
3. **Reproductibilité** : même manifeste + même dataset hashé ⇒ mêmes métriques bit-à-bit.
4. **Pas de secret dans les artefacts** ; les clés vivent dans l'environnement du runner.

### 2.1 Base de données

SQLite au démarrage (fichier `openforge.db`), migration PostgreSQL prévue V2.

```sql
-- Artefacts (contenu immuable)
CREATE TABLE artifacts (
  manifest_hash TEXT PRIMARY KEY,       -- sha256 canonique du manifeste
  artifact_type TEXT NOT NULL,           -- strategy|dataset|knowledge|proof|decision
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  license TEXT NOT NULL,
  manifest_json TEXT NOT NULL,           -- manifeste complet sérialisé
  parent_hash TEXT,                      -- fork / version précédente
  created_at TEXT NOT NULL
);

-- Datasets rattachés (provenance exacte)
CREATE TABLE dataset_bindings (
  manifest_hash TEXT NOT NULL,           -- stratégie
  dataset_hash TEXT NOT NULL,            -- artefact dataset
  PRIMARY KEY (manifest_hash, dataset_hash)
);

-- Exécutions reproductibles (résultats append-only)
CREATE TABLE runs (
  run_id TEXT PRIMARY KEY,               -- sha256(manifest_hash + data_hash + engine_version)
  manifest_hash TEXT NOT NULL,
  dataset_hash TEXT NOT NULL,
  engine_version TEXT NOT NULL,
  metrics_json TEXT NOT NULL,            -- PF brut/net, CAGR, Sharpe, Sortino, Calmar, DD, trades…
  folds_json TEXT NOT NULL,
  sheet_signature TEXT NOT NULL,         -- HMAC du résultat
  runtime_s REAL,
  computed_at TEXT NOT NULL
);

-- Machine à états de certification
CREATE TABLE certifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  manifest_hash TEXT NOT NULL,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  checks_json TEXT NOT NULL,             -- détail PASS/FAIL/NOT_EVALUATED par check
  blocking_reasons_json TEXT NOT NULL,
  computed_at TEXT NOT NULL
);
```

### 2.2 Statuts officiels MOS Hub V1

```
DRAFT → RESEARCH → BACKTESTING → BACKTEST_VALIDATED → OOS_VALIDATED
      → PAPER_VALIDATED → SHADOW_VALIDATED → CERTIFIED → READY_FOR_LIVE
      → LIVE → SUSPENDED → DECERTIFIED
```

Transitions latérales autorisées : tout statut → SUSPENDED ;
SUSPENDED → DECERTIFIED (dérive confirmée) ou retour au stade correspondant
(recertification). Toute autre transition est rejetée.

Mapping avec l'implémentation existante (`strategy_engine`) :
`OOS_VALIDATED→paper`, `PAPER_TRADING→PAPER_VALIDATED`,
`SHADOW_TRADING→SHADOW_VALIDATED`, `CERTIFIED→CERTIFIED`.

### 2.3 Moteur de certification

Seuils bloquants (tous obligatoires, aucun contournable) :

| Check | Seuil |
|---|---|
| rr_nominal | ≥ 3.0 |
| pf_net OOS agrégé | ≥ 1.5 |
| pf_net walk-forward | ≥ 1.5 |
| expectancy nette | > 0 (après TOUS les coûts : frais, spread, slippage, funding) |
| drawdown max | ≤ limite déclarée dans le manifeste |
| taille d'échantillon | scalping ≥500 / intraday ≥250 / swing ≥100 trades |
| monte-carlo p-value | < 0.05 |
| paper | PASS (PF ≥ 1.5 sur fenêtre forward, ≥ 15 trades) |
| shadow | PASS (coûts adversariaux majorés) |
| erreurs critiques | 0 (données manquantes, lookahead, NaN) |
| reproductibilité | re-run donne métriques identiques |

Chaque check produit `PASS | FAIL | NOT_EVALUATED`. Un seul FAIL ou
NOT_EVALUATED bloque READY_FOR_LIVE. La décision est recalculée à chaque
nouvelle preuve et journalisée dans `certifications`.

**Décertification automatique** : en LIVE, si l'une des conditions suivantes
est observée sur la fenêtre glissante — drawdown > limite × 1.5, PF net
glissant < 1.0 sur N trades déclarés, kill-switch déclenché — alors transition
automatique vers SUSPENDED puis DECERTIFIED après revue.

### 2.4 API V1

```
POST /moshub/artifacts            # enregistre un manifeste signé
GET  /moshub/artifacts/{hash}
POST /moshub/backtest             # {manifest} -> run_id + sheet (reproductible)
GET  /moshub/runs/{run_id}
POST /moshub/compare              # {a, b} -> diff métrique par métrique
GET  /moshub/sheets               # liste pour leaderboard
POST /moshub/evidence             # ajoute une preuve (oos/paper/shadow/stress)
GET  /moshub/certify/{hash}       # recalcule et journalise la décision
GET  /moshub/leaderboard          # trié par score de confiance
```

Score de confiance (leaderboard) : moyenne pondérée des checks PASS,
pénalité par FAIL, bonus de réplication indépendante (formule précise en V1.1).

### 2.5 Écrans V1

1. **Leaderboard** — stratégies triées par confiance ; colonnes : statut,
   PF net OOS, DD, trades, robustness, badge CERTIFIED/READY_FOR_LIVE.
2. **Fiche stratégie** — manifeste, hashes, datasets rattachés, courbe
   d'équité, folds, historique de certification complet.
3. **Comparaison** — deux hashes côte à côte, delta par métrique, gagnant.
4. **Soumission** — upload manifeste + lien dataset ; validation instantanée.
5. **Surveillance live** — pour stratégies LIVE : PnL temps réel, distance
   aux kill-switches, alertes.

## 3. Implémentation existante (au 22/08/2026)

| Brique | État | Emplacement |
|---|---|---|
| Validation manifeste + hash canonique | ✅ | `backend/app/main.py` |
| Backtest manifeste-driven + fiche signée | ✅ | `backend/app/moshub.py` |
| Comparaison de deux fiches | ✅ | `backend/app/moshub.py` |
| Machine à états + validateur sans faux PASS | ✅ (Python, ml_trading) | à porter côté API |
| Walk-forward + coûts + RR gate + MC | ✅ (ml_trading) | dépendance optionnelle du runner |
| Paper/shadow trackers | ✅ | ml_trading `strategy_engine/forward.py` |
| Leaderboard HTML console | 🟡 | `run_dashboard.py` → à porter en écran web |
| Auth utilisateurs | ⬜ V1.1 | — |
| Décertification automatique | ⬜ V1.1 | — |

## 4. Jalons

- **V1.0** (ce document) : API moshub complète + DB SQLite + écran leaderboard.
- **V1.1** : auth, décertification auto, score de confiance finalisé.
- **V2** : PostgreSQL, multi-utilisateurs, réplications indépendantes, ouverture des autres Forges (DataForge en premier).
