# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

This repo backs the paper **"Certificates without Electrons? Theory and
Evidence on Impacts from AI-Driven Power Demand"** (`Energy_CAS1 (1) (3).tex`)
and its structural companion **"A Structural Econometric Model of AI Demand,
Generator Investment, and Power Quality"** (`StructuralModelAIForPowerGrid
(4).tex`). The papers estimate the causal grid-level effects of AI model
releases (power quality, fossil-fuel demand, wholesale prices, ancillary
services) using staggered difference-in-differences (DiD) and a structural
procurement-and-entry model built around a **timing wedge**.

This document specifies the **code suite** needed to (1) acquire the data,
(2) build the analysis panel, (3) develop/estimate the models, and (4) test,
validate, and run counterfactuals. Treat it as the contract for how the
codebase is organized; keep it in sync as code lands.

---

## 1. What the suite must do

The pipeline runs end-to-end as four stages. Each stage is independently
runnable and caches its outputs so downstream stages do not re-fetch.

1. **Get data** — pull each raw source into `data/raw/` with a manifest.
2. **Build** — clean, harmonize spatial/temporal units, link sources, and
   construct the treatment, producing the analysis panels in `data/processed/`.
3. **Estimate (develop + train)** — fit the reduced-form DiD/IV models and
   the structural model; write coefficients to `outputs/estimates/`.
4. **Test** — parallel-trends, placebo, PSM/IPW, sensitivity, and structural
   over-identification checks; then counterfactuals to `outputs/`.

The "model" here is econometric: the deliverables are **estimated treatment
effects, elasticities, and structural parameters**, not a predictive ML model.
"Train" = estimate/fit; "test" = validate identifying assumptions and run
robustness. Where the paper trains small LLMs to measure GPU energy
(`GPU Experiments`), that is a calibration input, not the main estimator.

---

## 2. Repository layout (target)

```
.
├── CLAUDE.md                      # this file
├── Energy_CAS1 (1) (3).tex        # reduced-form paper (DiD; primary reference)
├── StructuralModelAIForPowerGrid (4).tex   # structural paper
├── README.md
├── pyproject.toml                 # deps + console-script entry points
├── config/
│   ├── sources.yaml               # API endpoints, paths, credentials refs
│   ├── samples.yaml               # sample definitions (conservative → broad)
│   └── models.yaml                # estimation specs, horizons, FE, controls
├── src/sepg/                      # package: Structural Econometric Power Grid
│   ├── data/                      # Stage 1: acquisition (one module per source)
│   ├── build/                     # Stage 2: cleaning, linkage, treatment, panel
│   ├── estimation/                # Stage 3: reduced-form + structural estimators
│   ├── validation/                # Stage 4a: assumption tests & robustness
│   ├── counterfactual/            # Stage 4b: scenario engine
│   └── utils/                     # geo, time, io, logging, caching
├── data/{raw,interim,processed}/  # gitignored; rebuilt from manifests
├── outputs/{estimates,figures,tables,counterfactuals}/
├── notebooks/                     # exploratory only; nothing imports from here
└── tests/                         # pytest: unit + small end-to-end fixtures
```

Conventions:
- Pure functions in `build/` and `estimation/`; side effects (downloads, file
  writes) live behind thin `data/` and `utils/io` wrappers so they are mockable.
- Every dataset carries a `source`, `vintage`, and `geo_resolution` tag.
- Secrets (S&P Capital IQ, Aterio, Whisker Labs keys) come from env vars
  referenced in `config/sources.yaml`; never hard-code or commit them.

---

## 3. Stage 1 — Data acquisition (`src/sepg/data/`)

One module per source. Each exposes `fetch(config) -> path` and writes to
`data/raw/<source>/` plus a row in `data/raw/manifest.csv`
(`source, file, vintage, rows, sha256, fetched_at`). Sources, content, and the
analysis role come straight from the papers' data tables.

| Module | Source | Pulls | Granularity / coverage | Role |
|---|---|---|---|---|
| `aterio.py` | **Aterio** registry | Data-center location, operator, MW capacity, build/expand/retire dates, **AI-use flag**, **on-site-generation flag** | Facility level, ~3,862 centers | Treatment definition; model→company→DC crosswalk; colocation counterfactual |
| `whisker.py` | **Whisker Labs** | **CPQI** (surges/sags/brownouts/interruptions) and **THD** (waveform distortion) | County/utility, monthly (THD hourly), 2022–2025, 72 utilities | DiD outcome variables (power quality) |
| `campd.py` | **EPA CAMPD/CAMD** | Hourly generator demand (MWh), **heat rates** (Btu/kWh), emissions | Unit-hour, ~thousands of generators, 2021–2023 (~22M generator-hours) | Fossil-demand outcome; heat rate IV |
| `spglobal.py` | **S&P Capital IQ Pro** | Natural-gas (Henry Hub) prices; **PPA** timing/counterparty/tenor/form; REC prices; asset/financing events | Daily prices; contract level | Price IV & fuel control; structural contracting margin |
| `meteostat.py` | **Meteostat** | Temperature, dewpoint, precipitation | County/station, hourly | Demand & renewable controls; PSM covariates |
| `iso.py` | **ISOs** (PJM Data Miner, ERCOT, CAISO, MISO, NYISO, ISO-NE, SPP) | Zonal/nodal LMPs, capacity-auction prices, **ancillary-services** clearing prices/quantities, zonal boundary shapefiles | Zonal, hourly; 54 zones (PJM focus: 20 zones) | Price outcomes/controls; ancillary-services DiD (structural) |
| `eia.py` | **EIA** Forms 860/923/930/715 | Retail service-territory shapefiles; generator capacity/fuel/retirement; hourly load & interchange by BA; transmission topology/transfer capacity | Utility / BA / arc level | Treatment boundaries; geo reconciliation; network flow (structural) |
| `epoch.py` | **Epoch** database | Model release dates, training compute (FLOPs), parameter counts | Model level, ~75 models | Treatment timing; scaling & efficiency counterfactuals |
| `releases.py` | Press releases / news / SEC filings | Verified training locations, training windows, API release dates | Model level (subset) | Conservative "verified" sample; staggered treatment anchor |

Notes:
- **Release date is the primary treatment anchor** (training start/location are
  usually unobserved). `releases.py` produces the verified subset (4 models with
  exact training date + location; API dates for >half of foundational models).
- Geographic assets (ISO/EIA shapefiles) are digitized maps — store as GeoJSON
  in `data/raw/geo/` and version the digitization script.
- Be polite to APIs: cache, back off, and respect the manifest so re-runs are
  incremental. Several sources are proprietary — gate them behind credentials
  and ship synthetic fixtures in `tests/fixtures/` for CI.

---

## 4. Stage 2 — Build & linkage (`src/sepg/build/`)

The core data-engineering contribution: "no single clean dataset contains all
variables." Harmonize **spatial** (facility → county → utility territory → ISO
zone → balancing authority) and **temporal** (hour ↔ month) units, then link.

- `geo.py` — crosswalks via point-in-polygon and radius joins:
  - DC → **utility service territory** (EIA) for the power-quality panel.
  - DC → **generators within a 20-mile radius** (CAMPD) for the demand panel.
  - Generator/DC → **ISO zone** (digitized boundaries) and → county.
- `treatment.py` — implements Appendix "Treatment Definition and Data Linkage":
  1. Flag AI data centers using Aterio's AI-use field.
  2. Crosswalk **model → developing company → all AI DCs of that company**.
  3. Build event-time exposure `D_{ut}^k = 1[event-time = k] × Treated_u`
     for horizons `k ∈ [-K, K]` (leads = training window, lags = inference).
  4. Emit treatment variants: binary, **intensity** (count/MW of AI DCs),
     verified-timing subset, and multi-BA-dropped subset (for sensitivity).
- `panel.py` — assemble the stacked/long panels:
  - **Power-quality panel**: utility-month, CPQI/THD + weather + regional load.
  - **Fossil-demand panel**: generator-month (from generator-hour), demand +
    heat rate + gas price + weather + zonal price.
  - **Price panel**: PJM zonal, LMP + demand/supply shifters.
  - **Stacked panel**: per release event `m`, treated + clean not-yet-treated
    controls in window `[r_m−K, r_m+K]`, then stacked (Cengiz/Deshpande style)
    so no already-treated unit is ever a control.
- `samples.py` — materialize `config/samples.yaml`: the conservative verified
  sample (4 models) up through progressively broader sets, each with its caveats.
- `validate_build.py` — schema/range checks reproducing the paper's summary
  stats as guardrails (CPQI mean≈0.52 sd≈0.42; THD mean≈1.81 sd≈6.77; CAMPD
  demand mean≈218 MW sd≈158; wholesale ≈$51/MWh; temp≈17°C). Fail loud on drift.

Output: tidy parquet panels in `data/processed/` keyed by `(unit, time, event)`.

---

## 5. Stage 3 — Estimation / "develop, train" (`src/sepg/estimation/`)

### 5.1 Reduced-form DiD (primary; `Energy_CAS1`)

- `did.py` — canonical two-way FE DiD (Eq. `eq:DiD`) as the teaching/baseline
  spec: `Y_it = α + β(Treat_i × Post_t) + γ_i + δ_t + ε_it`.
- `stacked_did.py` — **stacked DiD with multiple horizons** (Eq. `eq:stacked`),
  the main estimator. Returns dynamic coefficients `{β_k}` with unit-by-event
  and time-by-event FE; SEs clustered at the unit level. Used for:
  - **Power quality**: CPQI and THD specs (`eq:pq_eventstudy`, `eq:thd_eventstudy`).
  - **Fossil demand**: generator-month outcome (`eq:demand_eventstudy`).
- `iv.py` — **2SLS** for the demand model. First stage instruments price with
  generator **heat rate × natural-gas price** (`eq:firststage`); second stage
  puts predicted price `p̂` into the stacked-DiD demand spec. Report first-stage
  strength and the structural price elasticity (paper: ≈0.135, SE 0.013).
- `price_effects.py` — map the demand shift to prices via a **linear supply
  curve** `Q^s = a + b·p` estimated by IV (demand-side instruments:
  weather-driven load, industrial production), yielding
  `%Δp = %ΔQ^d / ε^s` (`eq:price-impact-elasticity`). PJM zonal only.
- Alternative estimators for robustness: **Callaway–Sant'Anna** and
  **Borusyak–Jaravel–Spiess** imputation (wrap `differences`/`did_imputation`).

Each estimator returns a standard `EstimationResult` (coefficients, vcov,
sample id, spec hash) serialized to `outputs/estimates/`. Keep specs declarative
in `config/models.yaml` (outcome, horizons K, FE, controls, sample, cluster).

### 5.2 Structural model (`StructuralModelAIForPowerGrid`)

Three-stage estimation (`structural/`), mirroring §"Estimation Strategy":

- `stage1_shortrun.py` — ancillary-services stacked DiD (`eq:aux_did`); map the
  DiD price coefficient to an implied ancillary-services demand quantity via the
  ISO supply-curve slope. Import LMPs, capacity, and REC prices as data.
- `stage2_calibration.py` — partially-linear regression of load-shape signatures
  `ζ` on technical params `θ^tech` (digital-twin/GPU experiments), controlling
  nonparametrically for design state; produces `Λ̂`. Cross-validate twin-implied
  vs. observation-implied `Δ^aux`.
- `stage3_longrun.py` — **moment-inequality** estimation of the hyperscaler
  problem (Holmes-style): observed portfolios dominate unilateral deviations
  (location / procurement / capacity / storage swaps), plus generator free-entry
  and PPA-bargaining moments. Partial-identification inference (Andrews-style
  confidence sets).
- `equilibrium.py` — the procurement-and-entry game: timing wedge
  `W = E[(ℓ−m)⁺]`, instrument-specific delivery for REC/PPA/BTM, endogenous
  financing `ρ(θ)=ρ0+λ·CV(R_θ)`, and free-entry capacity `K_θ`. This is the
  simulator the counterfactuals call.

---

## 6. Stage 4a — Validation & robustness (`src/sepg/validation/`)

Implements §"Validating Assumptions and Robustness". These gate the headline
results — run them before trusting any estimate.

- `pretrends.py` — joint F-test that pre-release leads `{β_k : k<0}` = 0; plus
  per-lead CIs. Significant pre-trends invalidate causal reading.
- `placebo.py` — randomized **treatment timing** (reshuffle release dates) and
  randomized **treatment assignment** (reshuffle treated units); compare actual
  estimate to the placebo distribution (randomization-inference p-value).
- `psm.py` — **propensity-score matching / IPW** (Appendix `APP:PSM`): logit on
  pre-trend load growth, temp, dewpoint, precip, heat rate, gas price; trim to
  common support `[0.1, 0.9]`; stabilized weights capped at `[0.01, 100]` and
  normalized within group; re-estimate weighted DiD.
- `sensitivity.py` — vary treatment definition: intensity weighting, drop
  multi-BA companies, verified-timing-only, and **radius sweeps** (generator
  match distance). Heterogeneity by model scale / company / release year.
- `structural_checks.py` — over-identification / moment-match diagnostics and
  the Stage-1↔Stage-2 `Δ^aux` cross-validation.

---

## 7. Stage 4b — Counterfactuals (`src/sepg/counterfactual/`)

Driven by `equilibrium.py` parameters + reduced-form coefficients
(§"Counterfactual Analysis"). Each scenario maps to a model prediction
(Table `tab:predictions`).

- `scaling.py` — Epoch parameter/FLOP trends → grid impact; efficiency
  elasticities linking demand to power-quality coefficients (P. amplification).
- `geographic.py` — (a) cloud→**edge** inference: redistribute inference impact
  across non-AI DCs (per-node spike/variance falls); (b) **relocation** of
  training to energy-abundant low-load regions (higher load–availability
  alignment). Appendix sensitivity for comms/efficiency losses.
- `colocation.py` — re-estimate with/without Aterio on-site-generation flag;
  report the **sign reversal** in power-quality effects (P. colocation).
- `policy.py` (structural) — REC-market elimination, national REC market,
  24/7 CFE mandate, bring-your-own-generation, transmission/generation mandates,
  composite scenarios.

Outputs: tables/figures to `outputs/counterfactuals/` with the scenario config
and the estimates vintage they consumed recorded alongside.

---

## 8. Running it

Console scripts (defined in `pyproject.toml`) wrap each stage; a `Makefile`/CLI
chains them:

```bash
sepg data fetch --source all            # Stage 1 → data/raw/ + manifest
sepg build panel --sample conservative  # Stage 2 → data/processed/
sepg estimate --spec power_quality      # Stage 3 (also: fossil_demand, price)
sepg estimate --spec structural --stage 1,2,3
sepg validate --spec power_quality --all # Stage 4a: pretrends+placebo+psm+sens
sepg counterfactual --scenario scaling,geographic,colocation
sepg report                             # regenerate outputs/tables + figures
```

`sepg run --sample conservative` executes the whole chain. Estimation and
counterfactual commands are pinned to a `--sample` and an estimates vintage so
results are reproducible.

---

## 9. Stack & conventions

- **Python 3.11+**. Econometrics: `pyfixest` or `linearmodels` (FE/IV),
  `differences` (Callaway–Sant'Anna), `statsmodels`. Data: `pandas`/`polars`,
  `pyarrow`. Geo: `geopandas`, `shapely`. Config: `pydantic` + YAML.
  (R via `rpy2` is acceptable for `did`/`fixest` if a Python equivalent is
  missing — keep it optional and isolated.)
- **Determinism**: set seeds for placebo/PSM resampling; record them in outputs.
- **Clustering**: default cluster at the unit (utility/generator) level; make it
  configurable per spec.
- **Testing**: `pytest`. Unit-test crosswalks and estimators against tiny
  synthetic fixtures with known answers; one end-to-end smoke test on fixtures
  must run in CI without any proprietary credentials.
- **Reproducibility**: every figure/table writes a sidecar JSON with the spec
  hash, sample id, data vintages, and git SHA. Don't hand-edit `outputs/`.
- **Don't commit** `data/raw`, `data/processed`, secrets, or large binaries.

---

## 10. Mapping paper ↔ code (quick reference)

| Paper object | Where it lives |
|---|---|
| Eq. `eq:DiD` (canonical DiD) | `estimation/did.py` |
| Eq. `eq:stacked`, `eq:pq_eventstudy`, `eq:demand_eventstudy` | `estimation/stacked_did.py` |
| First stage `eq:firststage` / 2SLS | `estimation/iv.py` |
| `%Δp = %ΔQ^d/ε^s` | `estimation/price_effects.py` |
| Timing wedge `W`, REC/PPA/BTM, entry `K_θ` | `estimation/structural/equilibrium.py` |
| 3-stage structural estimation | `estimation/structural/stage{1,2,3}_*.py` |
| Treatment linkage (model→company→DC, 20-mi) | `build/treatment.py`, `build/geo.py` |
| Data sources (Table `tab:DataSources`) | `data/*.py` |
| Pre-trends / placebo / PSM-IPW / sensitivity | `validation/*.py` |
| Scaling / edge / relocation / colocation / policy | `counterfactual/*.py` |

When the papers and code disagree, the **`.tex` files are the source of truth**
for specifications, samples, and identifying assumptions — update the code (and
this map) to match, and flag the discrepancy.
