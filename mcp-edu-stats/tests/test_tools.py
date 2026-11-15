"""Registri alat, audit, replay, CLI, dan (bila paket mcp ada) pendaftaran server."""
import inspect
import json

import numpy as np
import pandas as pd
import pytest

from edu_stats import cli, tools


@pytest.fixture(autouse=True)
def audit_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("EDU_STATS_AUDIT_DIR", str(tmp_path / "audit"))


@pytest.fixture
def csv(tmp_path):
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"nilai": rng.normal(75, 8, 40).round(1), "kelas": ["A", "B"] * 20,
                       "pre": rng.normal(60, 8, 40).round(1)})
    p = tmp_path / "d.csv"
    df.to_csv(p, index=False)
    return p


def test_run_tool_is_json_safe_and_audited(csv):
    out = tools.run_tool("ttest_independent", {"file": str(csv), "dv": "nilai", "group": "kelas"})
    json.dumps(out, allow_nan=False)  # tidak boleh ada NaN/inf/numpy
    assert out["audit"]["audit_id"] and out["audit"]["data_sha256"]
    log = tools.audit_log(5)["entries"]
    assert log[-1]["audit_id"] == out["audit"]["audit_id"]
    assert log[-1]["params"]["dv"] == "nilai"


def test_replay_identical_then_detects_data_change(csv):
    out = tools.run_tool("anova_oneway", {"file": str(csv), "dv": "nilai", "group": "kelas"})
    rep = tools.replay(out["audit"]["audit_id"])
    assert rep["identical"] and rep["data_unchanged"]
    df = pd.read_csv(csv)
    df.loc[0, "nilai"] += 10
    df.to_csv(csv, index=False)
    rep2 = tools.replay(out["audit"]["audit_id"])
    assert not rep2["identical"] and not rep2["data_unchanged"]
    assert "berubah" in rep2["keputusan"]


def test_errors_are_returned_not_raised(csv):
    assert "error" in tools.run_tool("ttest_independent", {"file": str(csv), "dv": "tidak_ada", "group": "kelas"})
    e = tools.run_tool("ttest_independent", {"file": str(csv), "dv": "nilai", "group": "kelas", "salah": 1})
    assert "tidak dikenal" in e["error"]
    assert "wajib" in tools.run_tool("ttest_independent", {"dv": "nilai"})["error"]
    assert "wajib" in tools.run_tool("ttest_independent", {"file": str(csv), "dv": "nilai"})["error"]
    assert "tidak dikenal" in tools.run_tool("uji_ajaib", {})["error"]
    assert "error" in tools.run_tool("ttest_independent", {"file": "tidak/ada.csv", "dv": "a", "group": "b"})


def test_r_table_tool():
    out = tools.run_tool("r_table", {"n": 30})
    assert out["result"]["r_table"] == pytest.approx(0.361, abs=5e-4)


def test_public_signatures():
    fns = tools.public_functions()
    assert set(fns) == set(tools.list_tools())
    sig = inspect.signature(fns["ancova"])
    assert list(sig.parameters)[:4] == ["file", "dv", "group", "covariates"]
    assert "ds" not in sig.parameters and "sheet" in sig.parameters
    for name, fn in fns.items():
        assert fn.__doc__, name


def test_public_wrapper_runs(csv):
    out = tools.public_functions()["ancova"](file=str(csv), dv="nilai", group="kelas", covariates=["pre"])
    assert "audit" in out and out["result"]["adjusted_means"]


def test_cli_run_and_replay(csv, capsys):
    code = cli.main(["run", "mann_whitney", f"file={csv}", "dv=nilai", "group=kelas", 'groups=["A","B"]'])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["result"]["U"] >= 0
    code = cli.main(["replay", out["audit"]["audit_id"]])
    rep = json.loads(capsys.readouterr().out)
    assert code == 0 and rep["identical"]
    assert cli.main(["run", "mann_whitney", f"file={csv}", "dv=nilai"]) == 1
    capsys.readouterr()
    assert cli.main(["list"]) == 0 and "ancova" in capsys.readouterr().out


def test_mcp_server_registers_all_tools():
    pytest.importorskip("mcp")
    import asyncio

    from edu_stats import server

    srv = server.build_server()
    listed = asyncio.run(srv.list_tools())
    names = {t.name for t in listed}
    assert names == set(tools.list_tools())
    ancova = next(t for t in listed if t.name == "ancova")
    # mcp 1.x: Tool.inputSchema; mcp 2.x: Tool.input_schema
    schema = getattr(ancova, "input_schema", None) or getattr(ancova, "inputSchema")
    assert set(schema["required"]) >= {"file", "dv", "group", "covariates"}
