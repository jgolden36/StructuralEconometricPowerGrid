"""Console entry point ``sepg-struct`` chaining the four pipeline stages.

Mirrors CLAUDE.md §8::

    sepg-struct data fetch --source all
    sepg-struct build --network config/network.yaml
    sepg-struct estimate --stage 1|2|3
    sepg-struct solve --equilibrium baseline
    sepg-struct validate --all
    sepg-struct counterfactual --scenario 24x7,byog,relocation
    sepg-struct report
    sepg-struct run               # whole chain

Estimation and counterfactual commands are pinned to an estimates vintage so
results are reproducible.
"""

from __future__ import annotations

import argparse
import sys

from sepg_struct import __version__
from sepg_struct.utils.logging import get_logger

log = get_logger("sepg_struct.cli")


# --------------------------------------------------------------------------- #
# Command handlers (thin: orchestration only; logic lives in the packages).
# --------------------------------------------------------------------------- #


def cmd_data(args: argparse.Namespace) -> int:
    from sepg_struct.data import fetch_all, fetch_source
    from sepg_struct.utils.config import load_sources

    cfg = load_sources(args.config).model_dump()
    if args.source in (None, "all"):
        paths = fetch_all(cfg)
    else:
        paths = {args.source: fetch_source(args.source, cfg)}
    for name, path in paths.items():
        log.info("fetched %s -> %s", name, path)
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    from sepg_struct.build.blocks import build_blocks
    from sepg_struct.build.network import build_network
    from sepg_struct.utils.config import load_blocks, load_network

    net = build_network(load_network(args.network))
    blocks = build_blocks(load_blocks(args.blocks))
    log.info("built network: %d zones, %d arcs", net.n_zones, net.graph.number_of_edges())
    log.info("built blocks: %d (Σω=%.3f)", blocks.n_blocks, float(blocks.omega.sum()))
    return 0


def cmd_estimate(args: argparse.Namespace) -> int:
    log.info("estimate stage %s (vintage=%s)", args.stage, args.vintage)
    log.warning(
        "Stage %s estimation needs processed inputs from `build` and the "
        "reduced-form DiD dependency; wire data loading then call "
        "sepg_struct.estimation.stage%s_*.estimate().", args.stage, args.stage,
    )
    return 0


def cmd_solve(args: argparse.Namespace) -> int:
    log.info("solve equilibrium: %s", args.equilibrium)
    log.warning(
        "Provide a `clear_markets` callback (short-run clearing + Bellman best "
        "responses) and call estimation.equilibrium.solve_equilibrium()."
    )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    log.info("validate (all=%s)", args.all)
    log.warning(
        "Run validation/{pretrends,placebo,cross_check,moment_checks,"
        "equilibrium_checks} against the estimates vintage."
    )
    return 0


def cmd_counterfactual(args: argparse.Namespace) -> int:
    scenarios = (args.scenario or "").split(",") if args.scenario else []
    log.info("counterfactual scenarios: %s (vintage=%s)", scenarios, args.vintage)
    log.warning("Build each Scenario, then counterfactual.base.run_scenario(...).")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    log.info("regenerate outputs/tables + figures (with reproducibility sidecars)")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Execute the whole chain end-to-end."""
    for fn, ns in (
        (cmd_data, argparse.Namespace(config="config/sources.yaml", source="all")),
        (cmd_build, argparse.Namespace(network="config/network.yaml", blocks="config/blocks.yaml")),
        (cmd_estimate, argparse.Namespace(stage="1", vintage=args.vintage)),
        (cmd_estimate, argparse.Namespace(stage="2", vintage=args.vintage)),
        (cmd_estimate, argparse.Namespace(stage="3", vintage=args.vintage)),
        (cmd_solve, argparse.Namespace(equilibrium="baseline")),
        (cmd_validate, argparse.Namespace(all=True)),
        (cmd_report, argparse.Namespace()),
    ):
        rc = fn(ns)
        if rc != 0:
            return rc
    return 0


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sepg-struct", description=__doc__)
    p.add_argument("--version", action="version", version=f"sepg-struct {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("data", help="Stage 1: acquire raw sources")
    d.add_argument("action", choices=["fetch"])
    d.add_argument("--source", default="all")
    d.add_argument("--config", default="config/sources.yaml")
    d.set_defaults(func=cmd_data)

    b = sub.add_parser("build", help="Stage 2: build structural objects")
    b.add_argument("--network", default="config/network.yaml")
    b.add_argument("--blocks", default="config/blocks.yaml")
    b.set_defaults(func=cmd_build)

    e = sub.add_parser("estimate", help="Stage 3: estimate a stage")
    e.add_argument("--stage", required=True, choices=["1", "2", "3"])
    e.add_argument("--vintage", default="dev")
    e.set_defaults(func=cmd_estimate)

    s = sub.add_parser("solve", help="Solve the Markov-perfect equilibrium")
    s.add_argument("--equilibrium", default="baseline")
    s.set_defaults(func=cmd_solve)

    v = sub.add_parser("validate", help="Stage 4a: diagnostics")
    v.add_argument("--all", action="store_true")
    v.set_defaults(func=cmd_validate)

    c = sub.add_parser("counterfactual", help="Stage 4b: policy scenarios")
    c.add_argument("--scenario", help="comma-separated scenario names")
    c.add_argument("--vintage", default="dev")
    c.set_defaults(func=cmd_counterfactual)

    r = sub.add_parser("report", help="Regenerate tables/figures")
    r.set_defaults(func=cmd_report)

    run = sub.add_parser("run", help="Execute the whole pipeline")
    run.add_argument("--vintage", default="dev")
    run.set_defaults(func=cmd_run)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
