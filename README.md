# Structural Econometric Model of AI Demand, Generator Investment, and Power Quality

Structural code suite backing the paper *A Structural Econometric Model of AI
Demand, Generator Investment, and Power Quality*
(`StructuralModelAIForPowerGrid (4).tex`). It builds a dynamic
procurement-and-entry game around a **timing wedge** and estimates it in three
stages, then runs policy counterfactuals by re-solving the Markov-perfect
equilibrium.

The reduced-form companion *Certificates without Electrons?*
(`Energy_CAS1 (1) (3).tex`) has its **own** code suite (staggered DiD, IV/2SLS,
power-quality, robustness). This suite **consumes** it — it does not
re-implement it. See `CLAUDE.md` for the full contract.

## Pipeline (four stages)

| Stage | Package | What it does |
|---|---|---|
| 1. Get data | `sepg_struct.data` | Pull each raw source into `data/raw/` with a manifest. |
| 2. Build | `sepg_struct.build` | Network graph, load blocks, demand objects, exposure, marginal carbon intensity. |
| 3. Estimate | `sepg_struct.estimation` | Three-stage estimator (short-run aux DiD → twin calibration → long-run moment inequalities) + equilibrium solver. |
| 4a. Validate | `sepg_struct.validation` | Pre-trends/placebo (reused), twin↔obs cross-check, moment-match, equilibrium convergence. |
| 4b. Counterfactual | `sepg_struct.counterfactual` | Re-solve the MPE under each policy lever; report partial- and general-equilibrium effects. |

## Install

```bash
pip install -e ".[dev]"          # core + test tooling
pip install -e ".[dev,fast]"     # add numba/jax for the equilibrium fixed point
```

## Run

```bash
sepg-struct data fetch --source all              # Stage 1 → data/raw/ + manifest
sepg-struct build --network config/network.yaml  # Stage 2 → data/processed/
sepg-struct estimate --stage 1                    # short-run aux DiD → ΔD^aux
sepg-struct estimate --stage 2                    # twin calibration → Λ̂, g_j
sepg-struct estimate --stage 3                    # moment-inequality params + CS
sepg-struct solve --equilibrium baseline          # MPE at estimated params
sepg-struct validate --all                        # Stage 4a diagnostics
sepg-struct counterfactual --scenario 24x7,byog,relocation
sepg-struct report                                # regenerate tables + figures
sepg-struct run                                   # whole chain
```

## Configuration

Declarative YAML under `config/` (validated by `pydantic`):

- `sources.yaml` — API endpoints, paths, credential **env-var names** (never secrets).
- `network.yaml` — echelons, zones, arcs, transfer caps `T̄`.
- `blocks.yaml` — load-block definition + weights `ω_b` (must sum to 1).
- `structural.yaml` — estimation specs: moments, grids, priors, tolerances, inference.

## Status

Scaffolding with the pure, testable cores implemented: network build, block
aggregation, the demand equations (gross load / grid draw / storage balance),
the Stage-1 price→demand mapping, and the equilibrium fixed-point loop (with
residual logging and fail-loud non-convergence). Source fetchers, the moment-
inequality inference critical values, and the location-pruning inner loop are
marked as focused `NotImplementedError` TODOs with their contracts fixed. The
reduced-form DiD / pre-trends / placebo are imported from the companion `sepg`
package, never vendored.

## Tests

```bash
pytest            # unit + CI smoke (no proprietary credentials required)
```

When the paper and code disagree, the `.tex` file is the source of truth — see
`CLAUDE.md` §10 for the paper↔code map.
