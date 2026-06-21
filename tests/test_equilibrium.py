import numpy as np
import pytest

from sepg_struct.build.network import build_network
from sepg_struct.estimation.equilibrium import (
    EquilibriumConfig,
    ShadowPrices,
    solve_equilibrium,
)
from sepg_struct.utils.config import load_network


def _network():
    return build_network(load_network("config/network.yaml"))


def test_solver_finds_known_fixed_point():
    """Tiny synthetic economy: contraction map p' = 0.5 p + c has fixed point 2c."""
    net = _network()
    n = net.n_zones
    c = np.linspace(10, 20, n)

    def clear_markets(prices, shadow):
        new_prices = 0.5 * prices + c
        slack_zero = np.zeros(n)  # constraints non-binding -> shadow prices stay 0
        return new_prices, slack_zero, slack_zero, {"dummy": True}

    cfg = EquilibriumConfig(max_iter=500, tol=1e-9, damping=1.0)
    res = solve_equilibrium(net, cfg, clear_markets=clear_markets, init_prices=np.zeros(n))

    assert res.converged
    np.testing.assert_allclose(res.prices, 2 * c, atol=1e-6)
    np.testing.assert_allclose(res.shadow_prices.headroom, 0.0, atol=1e-9)


def test_solver_fails_loud_on_nonconvergence():
    net = _network()
    n = net.n_zones

    def diverge(prices, shadow):
        # expansive map -> never converges
        return prices + 1.0, np.zeros(n), np.zeros(n), {}

    cfg = EquilibriumConfig(max_iter=5, tol=1e-9, damping=1.0)
    with pytest.raises(RuntimeError, match="did NOT converge"):
        solve_equilibrium(net, cfg, clear_markets=diverge, init_prices=np.zeros(n))


def test_shadow_price_roundtrip():
    sp = ShadowPrices(headroom=np.array([1.0, 2.0]), cleanpool=np.array([3.0, 4.0]))
    back = ShadowPrices.from_stack(sp.stack(), n_zones=2)
    np.testing.assert_array_equal(back.cleanpool, sp.cleanpool)
