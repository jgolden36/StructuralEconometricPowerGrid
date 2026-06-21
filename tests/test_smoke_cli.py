"""End-to-end CI smoke test: runs without any proprietary credentials.

Exercises the parts of the chain that don't require live data — config parse,
network/block build via the CLI — so CI proves the package imports and wires
together (CLAUDE.md §9).
"""

from sepg_struct.cli import main


def test_build_command_runs(capsys):
    rc = main(["build", "--network", "config/network.yaml", "--blocks", "config/blocks.yaml"])
    assert rc == 0


def test_version_flag():
    import pytest

    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_run_chain_smoke(monkeypatch):
    # Stub data fetch so the smoke run needs no network/credentials.
    import sepg_struct.cli as cli

    monkeypatch.setattr(cli, "cmd_data", lambda args: 0)
    rc = cli.cmd_run(type("NS", (), {"vintage": "test"})())
    assert rc == 0
