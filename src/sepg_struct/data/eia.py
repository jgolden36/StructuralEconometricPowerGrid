"""EIA Forms 860/923/930/715.

- 860/923: generator capacity / fuel / heat-rate / retirement -> generator state.
- 930: hourly load / interchange / net-gen by BA -> residual non-AI load ``D^O``.
- 715: transmission topology & transfer capacities -> arcs ``A`` and ``T̄_{a,t}``.

(CLAUDE.md §3.)
"""

from __future__ import annotations

from pathlib import Path

from sepg_struct.data.base import context_from_config, require_credential, with_retries

FORM_SCHEMAS = {
    860: ["plant_id", "fuel", "nameplate_mw", "heat_rate", "retirement_year", "ba"],
    923: ["plant_id", "month", "net_gen_mwh", "fuel_consumed", "ba"],
    930: ["ba", "hour", "demand_mwh", "net_gen_mwh", "interchange_mwh"],
    715: ["arc_id", "from_zone", "to_zone", "transfer_cap_mw"],
}


def _pull(ctx, credential: str | None, form: int) -> Path:
    raise NotImplementedError(
        f"Live EIA Form {form} pull not wired. Provide EIA_API_KEY and implement "
        f"the v2 client, or use tests/fixtures/eia_{form}.parquet."
    )


def fetch(config: dict) -> Path:
    ctx = context_from_config("eia", config)
    credential = require_credential(ctx.options.get("credentials_env"))
    forms = ctx.options.get("forms", list(FORM_SCHEMAS))
    # Real impl loops over forms and concatenates; scaffold pulls the first.
    return with_retries(lambda: _pull(ctx, credential, forms[0]))
