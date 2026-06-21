import pytest

from sepg_struct.build.network import build_network
from sepg_struct.utils.config import NetworkConfig, load_network


def test_build_network_from_config():
    net = build_network(load_network("config/network.yaml"))
    assert net.n_zones == 6
    assert net.graph.number_of_edges() == 5
    # forward arc carries its transfer cap
    assert net.transfer_cap("Z_INT_A", "Z_DC_E") == 6000


def test_forward_arc_restriction_enforced():
    bad = NetworkConfig.model_validate(
        {
            "echelons": [{"id": 0, "name": "up"}, {"id": 2, "name": "down"}],
            "zones": [
                {"id": "A", "echelon": 0, "iso": "X", "ba": "X"},
                {"id": "B", "echelon": 2, "iso": "X", "ba": "X"},
            ],
            # echelon jump of 2 violates e(dst) = e(src) + 1
            "arcs": [{"src": "A", "dst": "B", "t_bar_mw": 100}],
        }
    )
    with pytest.raises(ValueError, match="forward inter-echelon arc"):
        build_network(bad)
