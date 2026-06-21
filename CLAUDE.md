# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

This repo backs the **structural** paper **"A Structural Econometric Model of
AI Demand, Generator Investment, and Power Quality"**
(`StructuralModelAIForPowerGrid (4).tex`). It builds a dynamic
procurement-and-entry game around a **timing wedge** and estimates it in three
stages, then runs policy counterfactuals by re-solving the equilibrium.

The reduced-form companion **"Certificates without Electrons?"**
(`Energy_CAS1 (1) (3).tex`) **already has its own code suite** — the staggered
difference-in-differences (DiD), IV/2SLS, power-quality, and robustness
estimators described in that paper are built and live upstream. **This suite
does not re-implement them.** It *consumes* them: the structural Stage 1 is a
stacked DiD on ancillary-services prices that reuses the existing DiD machinery
and validation suite, and the structural model takes the reduced-form
DiD-implied demand shift as a moment to match. Where this document references a
"reduced-form" estimator, treat it as an existing dependency to import, not new
code to write.

This document specifies the **structural code suite**: (1) acquire the
structural data, (2) build the network/block/demand objects, (3) estimate the
three structural stages and solve the equilibrium, and (4) validate and run
counterfactuals. Treat it as the contract for how the codebase is organized;
keep it in sync as code lands.

---

## 1. What the suite must do

The pipeline runs end-to-end as four stages. Each stage is independently
runnable and caches its outputs so downstream stages do not re-fetch or
re-estimate.

1. **Get data** — pull each raw source into `data/raw/` with a manifest.
2. **Build** — construct the network graph, load blocks, demand-side objects,
   treatment exposure, and the marginal-carbon-intensity panel in
   `data/processed/`.
3. **Estimate (develop + train)** — run the three-stage estimator (short-run
   ancillary DiD → experimental calibration → long-run moment inequalities) and
   solve the equilibrium; write parameters/confidence sets to
   `outputs/estimates/`.
4. **Test** — pre-trends/placebo (reused from the reduced-form suite), the
   twin↔observation cross-check, over-identification/moment-match diagnostics,
   equilibrium convergence checks; then counterfactuals to `outputs/`.

The deliverables are **structural parameters, partial-identification confidence
sets, and counterfactual equilibria** — not a predictive ML model. "Train" =
estimate/calibrate; "test" = validate identifying assumptions and equilibrium
solution. The digital-twin/GPU experiments are a **calibration input** (the
`Λ` map), not the main estimator.

---

## 2. Repository layout (target)

```
.
├── CLAUDE.md                      # this file
├── StructuralModelAIForPowerGrid (4).tex   # structural paper (source of truth)
├── Energy_CAS1 (1) (3).tex        # reduced-form paper (existing suite; reference only)
├── README.md
├── pyproject.toml                 # deps + console-script entry points
├── config/
│   ├── sources.yaml               # API endpoints, paths, credentials refs
│   ├── network.yaml               # echelons, zones, arcs, transfer caps
│   ├── blocks.yaml                # load-block definition + weights ω_b
│   └── structural.yaml            # estimation specs: moments, grids, priors, tol
├── src/sepg_struct/               # package: structural suite
│   ├── data/                      # Stage 1: acquisition (one module per source)
│   ├── build/                     # Stage 2: network, blocks, demand, exposure, MCI
│   ├── estimation/                # Stage 3: 3-stage estimator + equilibrium solver
│   │   ├── stage1_shortrun.py
│   │   ├── stage2_calibration.py
│   │   ├── stage3_longrun.py
│   │   └── equilibrium.py
│   ├── validation/                # Stage 4a: cross-checks & diagnostics
│   ├── counterfactual/            # Stage 4b: policy scenario engine
│   └── utils/                     # geo, time, io, logging, caching
├── data/{raw,interim,processed}/  # gitignored; rebuilt from manifests
├── outputs/{estimates,figures,tables,counterfactuals}/
├── notebooks/                     # exploratory only; nothing imports from here
└── tests/                         # pytest: unit + small end-to-end fixtures
```

Conventions:
- Pure functions in `build/` and `estimation/`; side effects (downloads, file
  writes) live behind thin `data/` and `utils/io` wrappers so they are mockable.
- The reduced-form DiD package is a dependency, imported (e.g.
  `from sepg.estimation import stacked_did, pretrends, placebo`); never vendored.
- Secrets (S&P Capital IQ, Aterio, Whisker Labs keys) come from env vars
  referenced in `config/sources.yaml`; never hard-code or commit them.

---

## 3. Stage 1 — Data acquisition (`src/sepg_struct/data/`)

One module per source. Each exposes `fetch(config) -> path` and writes to
`data/raw/<source>/` plus a row in `data/raw/manifest.csv`
(`source, file, vintage, rows, sha256, fetched_at`). Sources and the model
object each informs come from §"Data" of the structural paper.

| Module | Source | Pulls | Structural object informed |
|---|---|---|---|
| `aterio.py` | **Aterio** registry (+ S&P 451/DC Bytes, interconnection-queue filings for cross-validation) | DC location, operator, MW capacity, build status, announced expansions; AI-use & on-site-generation flags | Hyperscaler capacity stock `K_{f,z,t}^σ`; zone exposure shares |
| `spglobal.py` | **S&P Capital IQ Pro** (+ SEC filings, LevelTen PPA index) | PPA timing/counterparty/tenor/contracted-capacity/buyer-type/form (physical vs virtual); FID/COD financing events; REC prices; gas prices | Contracting margin vs entry margin; financing-rate `r_l(σ²)`; PPA bargaining `ζ_f`; `p^REC` |
| `epoch.py` | **Epoch** + corporate announcements | Release dates, training-compute estimates, release windows, train/infer workload mix | Treatment timing; model quality `q_{f,t}`; train/infer allocation |
| `eia.py` | **EIA** Forms 860/923/930/715 | Generator capacity/fuel/heat-rate/retirement (860/923); hourly load/interchange/net-gen by BA (930); transmission topology & transfer capacities (715) | Generator state; residual non-AI load `D^O_{z,t}`; arcs `A` & `T̄_{a,t}` |
| `epa_camd.py` | **EPA CAMD** (+ ISO unit-level dispatch where available) | Day-ahead generation, fuel use, emissions | Dispatch; marginal carbon intensity `MCI_{z,b,t}` |
| `iso.py` | **ISOs** (PJM Data Miner, ERCOT MIS, CAISO OASIS, MISO, NYISO, ISO-NE, SPP) | Nodal/zonal LMPs; capacity-auction clears (PJM BRA, ISO-NE FCA, NYISO ICAP) + ELCC derating; **ancillary-services clearing prices & quantities by product `j` and zone**; supply-curve slopes | Exogenous `p^ene`, `p^cap`; **aux-services price `p^aux` (DiD outcome) & supply elasticity `ε^s`** |
| `recs.py` | **S&P Global Platts**, M-RETS, PJM-GATS, state compliance reports | REC issuance/retirement records, compliance prices | REC market clearing; granularity standard `h` |
| `whisker.py` | **Whisker Labs** | THD / voltage-sag at utility-month | Aggregate validation of the `Λ` map (predicted vs observed THD) |
| `twin.py` | **CEWIT/AERTC** digital twin + micro data center | Trial-level `(X^exp, θ^tech, ζ, η)`: power/voltage/current/frequency/harmonics/reactive power under varied technical params | `Λ` calibration; `g_j` signature→aux-demand map |

Notes:
- **Model release date is the treatment anchor** for the Stage-1 DiD (timing
  plausibly unrelated to any single zone's aux-services market).
- Geographic/topology assets (ISO zone boundaries, FERC 715 arcs) are digitized
  — store as GeoJSON in `data/raw/geo/` and version the digitization script;
  where Form 715 is coarser than the zone definitions, allocate `T̄` in
  proportion to constituent-zone load.
- Several sources are proprietary (Aterio, S&P, Whisker, twin) — gate behind
  credentials and ship synthetic fixtures in `tests/fixtures/` for CI.

---

## 4. Stage 2 — Build the structural objects (`src/sepg_struct/build/`)

Turn raw sources into the primitives the estimator and equilibrium solver
consume. Harmonize spatial (facility → zone → echelon → BA) and temporal
(hour → load block → annual period) units.

- `network.py` — build the directed graph `G = (Z, A)` from `config/network.yaml`:
  echelons `E` (canonical `E=3`: upstream/transit/downstream), zones `Z_e`,
  forward inter-echelon arcs (`e(j)=e(i)+1`), optional intra-echelon arcs, and
  transfer capacities `T̄_{a,t}`. Emit adjacency + capacity tensors.
- `blocks.py` — partition each annual period into load blocks `B` with weights
  `ω_b` (e.g. peak/off-peak × season × renewable-availability tercile, `B=8`),
  per `config/blocks.yaml`. Each block carries representative load, renewable
  availability, and aux-services requirement.
- `demand.py` — assemble the demand side:
  - Gross IT load `D^M = ρ_train·K_train + ρ_infer·K_infer` (Eq. `eq:gross_load`).
  - Net grid draw `G^M` with PPA/colo/storage/backup offsets and the storage
    energy-balance + ramp constraints (Eqs. `eq:grid_draw`, `eq:storage_balance`).
  - Residual non-AI load `D^O` = EIA Form-930 load − estimated DC load.
  - Timing wedge per block `w_{f,z,b,t}(h) = G^M − R^{M,G}` (granularity `h`).
- `exposure.py` — shift-share treatment exposure `D^k_{z,t,m}` at zone-month:
  firm-`f` model-release event (shift) × zone-`z` exposure share (Aterio DC mix ×
  Epoch-inferred train/infer allocation). Feeds the Stage-1 DiD (Eq. `eq:aux_did`).
- `carbon.py` — marginal carbon intensity `MCI_{z,b,t}` from CAMD + dispatch
  reconstruction, for the emissions accounting (Eq. `eq:emissions`).
- `validate_build.py` — schema/range checks; reconcile Aterio capacity against
  S&P/queue filings; verify aux-services panel completeness by product `j`.

Output: tidy parquet/zarr tensors in `data/processed/` keyed by
`(firm, zone, block, period)` and `(zone, period, event)`.

---

## 5. Stage 3 — Estimation / "develop, train" (`src/sepg_struct/estimation/`)

Three-stage estimation mirroring §"Estimation Strategy", exploiting the model's
separation between the long-run game, the short-run clearing, and the
experimental calibration.

### 5.1 Stage 1 — Short-run estimation (`stage1_shortrun.py`)

- **Ancillary-services stacked DiD** (Eq. `eq:aux_did`): estimate `β^j_k` for
  each product `j` using model releases as the staggered shock. **Reuse the
  reduced-form suite's stacked-DiD estimator** with zone-by-event `γ_{z,m}` and
  time-by-event `δ_{t,m}` FE, controls `X` (weather, fuel prices, residual
  non-AI load, ISO×month-of-sample), and unit-clustered SEs.
- **Price→demand mapping** (Eq. `eq:aux_demand_from_price`): convert the price
  coefficient to an implied demand shift
  `ΔD^aux = β^j_k · ε^s · Q̄^aux` using the ISO-published supply-curve slope
  `ε^s` at the pre-shock clearing point (general case nets `ε^d`). This
  `ΔD^aux` is the **moment** Stage 2 must reproduce in aggregate.
- LMPs, capacity prices, and REC prices are **imported as data**, not estimated.

### 5.2 Stage 2 — Experimental calibration (`stage2_calibration.py`)

- Estimate the **`Λ` map** (Eq. `eq:zeta_map`) by **partially-linear regression**
  of each load-shape signature component `ζ` on technical parameters `θ^tech`,
  controlling **nonparametrically** for the experimental design state `X^exp`.
- Compose `Λ̂` with the engineering map `g_j` to get per-MW aux-services demand;
  aggregate to the within-facility partial `Δ^aux_j(ζ, K)`.
- **Cross-validate**: aggregate twin-implied `Δ^aux` against the Stage-1
  DiD-implied `ΔD^aux`. This is the integration diagnostic — the twin is
  *tested*, not assumed correct.

### 5.3 Stage 3 — Long-run estimation (`stage3_longrun.py`)

- **Moment inequalities** (Holmes/Pakes-style, Eq. `eq:moment_ineq`): observed
  firm portfolios dominate small unilateral deviations in expected discounted
  profit. Construct four deviation classes — **location swaps** (zone
  attractiveness), **procurement swaps** (`Γ`, `r_l`, mode costs), **capacity
  swaps** (contest `α_f`, `η`), **storage swaps** (the three storage channels).
  Deviations must be feasible under headroom/clean-pool given observed rival
  capacity.
- **Generator free-entry** moments (Eq. `eq:gen_free_entry`): match observed
  entry by fuel/zone/contract-structure to model-predicted entry; identifies
  `I^build` and `r_l(σ²)`.
- **PPA bargaining**: identify `ζ_f` from observed PPA prices vs model-implied
  outside options (Eq. `eq:ppa_bargain`).
- **Contest/reputation**: `(η, α_f, θ_f)` from joint distribution of Epoch
  model quality, compute build-out, and investment flows; `γ_f` from
  procurement-mode × sustainability-commitment correlations.
- **Inference**: partial-identification confidence sets (Andrews–Soares /
  Andrews–style); uniqueness is not assumed.

### 5.4 Equilibrium solver (`equilibrium.py`)

The Markov-perfect equilibrium of the long-run game — the object the
counterfactuals re-solve. Components:

- Hyperscaler Bellman (Eq. `eq:hyper_bellman`) over actions
  `(ΔK, σ, ΔS, B)`; payoff = investor contest reward `v_{f,t}` (Eq. `eq:contest`)
  − total cost (Eq. `eq:hyper_cost`) − outage cost − reputational emissions
  penalty `Γ(γ_f, E_{f,t})`.
- Generator Bellman (Eq. `eq:gen_bellman`) with energy/aux/capacity/REC revenue
  and the financing-rate entry hierarchy `entry_Colo ≥ entry_PPA ≥ entry_merch`.
- Short-run market clearing per block: energy, capacity, REC, and the
  behavioral **ancillary-services** market (the rest imported as cost curves).
- Resource constraints clear via shadow prices: interconnection headroom
  `λ^H_{z,t}` (Eq. `eq:headroom`) and clean-MW pool `λ^Z_{z,t}` (Eq. `eq:cleanpool`).
- **Combinatorial location pruning** (Arkolakis-style) using the conditional
  separability in `(C_{f,t}, E_{f,t})` (Eq. `eq:separability`), nested as the
  **inner loop of the price-clearing fixed point**: prune given
  `(λ^H, λ^Z)`, re-clear constraints, iterate to convergence. Verify the
  single-crossing condition in `C` numerically at the estimated parameters.

Each stage writes a standard `EstimationResult` (parameters/confidence set,
moments, spec hash, data vintages) to `outputs/estimates/`. Keep specs
declarative in `config/structural.yaml` (moment set, action grids, tolerances,
inference settings).

---

## 6. Stage 4a — Validation & diagnostics (`src/sepg_struct/validation/`)

These gate the headline results — run them before trusting any estimate.

- `pretrends.py`, `placebo.py` — **reuse the reduced-form suite** for the
  Stage-1 aux-services DiD: joint F-test on pre-period leads, randomized
  treatment-timing/assignment placebos, and the Callaway–Sant'Anna and
  Borusyak–Jaravel–Spiess alternative estimators as robustness checks.
- `cross_check.py` — the twin↔observation `Δ^aux` reconciliation (Stage-1 vs
  Stage-2) and the aggregate Whisker-Labs THD validation of the `Λ` map. If the
  twin-only path cannot reproduce the aggregates, the DiD number is binding and
  technical-decomposition counterfactuals are flagged provisional.
- `moment_checks.py` — over-identification / moment-match diagnostics for the
  Stage-3 inequalities; report which moments bind and the slackness profile.
- `equilibrium_checks.py` — fixed-point convergence, single-crossing
  verification, existence/uniqueness diagnostics, and sensitivity of the
  confidence set to action-grid resolution.

---

## 7. Stage 4b — Counterfactuals (`src/sepg_struct/counterfactual/`)

Each scenario re-solves the Markov-perfect equilibrium with a modified
constraint set, holding structural parameters at their estimated values, and
compares portfolios/prices/emissions/aux-demand/reliability to baseline.
**Report both the partial-equilibrium effect (entry fixed) and the
general-equilibrium effect (entry responds)** — the gap is itself informative.

- `relocation.py` — redistribute inference/training across zones (alter
  admissible `Z_f`); trade aux-services relief at downstream zones against
  transmission utilization.
- `technical.py` — fleet-wide technical changes (INT8 quantization, distilled
  models, power-factor correction, cross-firm batch scheduling): perturb
  `θ^tech`, map through `Λ̂` to a new `ζ`, re-aggregate to a zone demand shift,
  re-solve. **Uniquely enabled by the experimental platform.**
- `supply_policy.py` — transmission expansion (`↑T̄_a`) and build-rate subsidy
  (`↓I^build`).
- `byog.py` — bring-your-own-generation: restrict `σ ∈ {PPA, Colo}` at
  constrained zones; quantify entry response via the financing channel.
- `rec_policy.py` — REC-market elimination (`φ=0`), national REC market
  (`S^qual = Σ_z' S`), and **24/7 CFE** (granularity `h=1`, hourly matching →
  shift toward colocation-plus-storage).
- `aux_market.py` — aux-services market redesign (fast-frequency-response
  product, incremental vs proportional cost attribution, DR product).
- `composite.py` — multi-lever scenarios ("high-clean", "high-efficiency") to
  reveal policy complementarities/substitutions.

Outputs: tables/figures to `outputs/counterfactuals/` with the scenario config
and the estimates vintage they consumed recorded alongside.

---

## 8. Running it

Console scripts (defined in `pyproject.toml`) wrap each stage; a `Makefile`/CLI
chains them:

```bash
sepg-struct data fetch --source all              # Stage 1 → data/raw/ + manifest
sepg-struct build --network config/network.yaml  # Stage 2 → data/processed/
sepg-struct estimate --stage 1                    # short-run aux DiD → ΔD^aux
sepg-struct estimate --stage 2                    # twin calibration → Λ̂, g_j
sepg-struct estimate --stage 3                    # moment-inequality params + CS
sepg-struct solve --equilibrium baseline          # MPE at estimated params
sepg-struct validate --all                        # Stage 4a diagnostics
sepg-struct counterfactual --scenario 24x7,byog,relocation
sepg-struct report                                # regenerate outputs/tables + figures
```

`sepg-struct run` executes the whole chain. Estimation and counterfactual
commands are pinned to an estimates vintage so results are reproducible.

---

## 9. Stack & conventions

- **Python 3.11+**. Econometrics/inference: `statsmodels`, `linearmodels`,
  partial-ID moment-inequality code (custom or `pyDID`-adjacent); reuse the
  reduced-form package for stacked DiD / CS / BJS. Numerics: `numpy`/`scipy`,
  `jax` or `numba` for the equilibrium fixed point. Data: `pandas`/`polars`,
  `pyarrow`, `xarray`/`zarr` for the `(f,z,b,t)` tensors. Geo: `geopandas`,
  `shapely`, `networkx` for the arc graph. Config: `pydantic` + YAML.
- **Determinism**: set and record seeds for placebo resampling, moment-inequality
  subsampling, and any stochastic equilibrium initialization.
- **Equilibrium discipline**: log fixed-point residuals and iteration counts;
  fail loud if the price-clearing loop does not converge within tolerance.
- **Testing**: `pytest`. Unit-test the network build, block aggregation, the
  price→demand mapping, and the equilibrium solver on tiny synthetic economies
  with known fixed points; one end-to-end smoke test on fixtures must run in CI
  without any proprietary credentials.
- **Reproducibility**: every figure/table writes a sidecar JSON with the spec
  hash, estimates vintage, data vintages, and git SHA. Don't hand-edit `outputs/`.
- **Don't commit** `data/raw`, `data/processed`, secrets, or large binaries.

---

## 10. Mapping paper ↔ code (quick reference)

| Paper object | Where it lives |
|---|---|
| Network `G=(Z,A)`, echelons, arcs `T̄` (Eqs. `eq:lr_state`, headroom/cleanpool) | `build/network.py` |
| Load blocks `B`, weights `ω_b` | `build/blocks.py` |
| Gross/net load, storage balance, timing wedge (Eqs. `eq:gross_load`–`eq:storage_balance`) | `build/demand.py` |
| Shift-share exposure `D^k_{z,t,m}` | `build/exposure.py` |
| Aux-services DiD (Eq. `eq:aux_did`) + price→demand (Eq. `eq:aux_demand_from_price`) | `estimation/stage1_shortrun.py` (DiD reused from reduced-form suite) |
| `Λ` map / `g_j` calibration (Eq. `eq:zeta_map`) | `estimation/stage2_calibration.py` |
| Moment inequalities, free-entry, PPA bargaining (Eqs. `eq:moment_ineq`, `eq:gen_free_entry`, `eq:ppa_bargain`) | `estimation/stage3_longrun.py` |
| Hyperscaler/generator Bellman, shadow prices, location pruning (Eqs. `eq:hyper_bellman`, `eq:gen_bellman`, `eq:separability`) | `estimation/equilibrium.py` |
| Pre-trends / placebo / CS / BJS | `validation/*` (imported from reduced-form suite) |
| Twin↔obs `Δ^aux` cross-check, THD validation | `validation/cross_check.py` |
| 9 counterfactuals + composites (§"Counterfactual Analysis") | `counterfactual/*` |
| Data sources (§"Data") | `data/*.py` |

When the paper and code disagree, the **`.tex` file is the source of truth** for
specifications, moments, and identifying assumptions — update the code (and this
map) to match, and flag the discrepancy.
