import numpy as np
import pytest

from sepg_struct.build import demand


def test_gross_load_partitions_capacity():
    d = demand.gross_it_load(
        rho_train=np.array([1.0]), k_train=np.array([100.0]),
        rho_infer=np.array([0.5]), k_infer=np.array([40.0]),
    )
    assert d[0] == pytest.approx(120.0)


def test_net_grid_draw_floored_and_offset():
    g = demand.net_grid_draw(
        d_m=np.array([100.0, 10.0]),
        q_contract=np.array([30.0, 0.0]),
        q_colo=np.array([20.0, 0.0]),
        q_stor_out=np.array([10.0, 0.0]),
        q_stor_in=np.array([0.0, 0.0]),
        b_run=np.array([5.0, 0.0]),
        # second cell: large offsets -> floored at 0
    )
    assert g[0] == pytest.approx(35.0)
    assert g[1] == pytest.approx(10.0)


def test_storage_balance_and_ramp_guard():
    stock = np.array([50.0])
    cap = np.array([100.0])
    nxt = demand.storage_step(stock, q_in=np.array([10.0]), q_out=np.array([0.0]),
                              eta_s=0.9, capacity=cap, c_rate=0.5)
    assert nxt[0] == pytest.approx(59.0)  # 50 + 0.9*10

    with pytest.raises(ValueError, match="ramp"):
        demand.storage_step(stock, q_in=np.array([60.0]), q_out=np.array([0.0]),
                            eta_s=0.9, capacity=cap, c_rate=0.5)  # 60 > 0.5*100
