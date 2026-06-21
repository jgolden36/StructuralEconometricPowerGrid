import numpy as np
import pytest

from sepg_struct.build.blocks import build_blocks
from sepg_struct.utils.config import BlocksConfig, load_blocks


def test_block_weights_sum_to_one_and_aggregate():
    blocks = build_blocks(load_blocks("config/blocks.yaml"))
    assert blocks.n_blocks == 8
    np.testing.assert_allclose(blocks.omega.sum(), 1.0, atol=1e-9)
    # Σ_b ω_b · 1 == 1
    assert blocks.weighted_sum(np.ones(blocks.n_blocks)) == pytest.approx(1.0)


def test_bad_weights_rejected():
    cfg = BlocksConfig(
        partition={},
        blocks=[
            {"id": "b1", "time_of_day": "peak", "season": "summer", "renewables": "low",
             "omega": 0.4, "ren_avail": 0.2, "aux_req_mult": 1.0},
            {"id": "b2", "time_of_day": "offpeak", "season": "summer", "renewables": "high",
             "omega": 0.4, "ren_avail": 0.7, "aux_req_mult": 1.0},
        ],
    )
    with pytest.raises(ValueError, match="sum to 1"):
        build_blocks(cfg)
