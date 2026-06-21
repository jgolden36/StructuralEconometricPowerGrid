import pytest

from sepg_struct.estimation.stage1_shortrun import price_to_demand_shift


def test_price_to_demand_baseline_inelastic():
    # ΔD = β · ε^s · Q̄
    dd = price_to_demand_shift(beta_j=0.10, supply_elasticity=2.0, cleared_quantity_mw=500.0)
    assert dd == pytest.approx(100.0)


def test_price_to_demand_general_case_nets_demand_slope():
    # ΔD = β · (ε^s − ε^d) · Q̄, with ε^d ≤ 0 the gap widens
    dd = price_to_demand_shift(
        beta_j=0.10, supply_elasticity=2.0, cleared_quantity_mw=500.0,
        demand_elasticity=-1.0,
    )
    assert dd == pytest.approx(150.0)
