"""Tests MOS Hub : backtest manifeste, fiche signée, comparaison, reproductibilité."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "backend"
spec = importlib.util.spec_from_file_location("moshub", BACKEND / "app" / "moshub.py")
moshub = importlib.util.module_from_spec(spec)
sys.modules["moshub"] = moshub
spec.loader.exec_module(moshub)


MANIFEST = {
    "schema_version": "1.0.0",
    "artifact_type": "strategy",
    "name": "momentum-pullback-g3",
    "version": "1.0.0",
    "license": "MIT",
    "family": "momentum_pullback",
    "params": {"trend_lookback": 150.0, "pullback_scale": 2.0},
}


def _evaluator(manifest):
    seed = int(moshub.canonical_hash(manifest)[:8], 16)
    pf = 1.0 + (seed % 100) / 100
    return {
        "aggregate": {
            "net_profit_factor": round(pf, 3),
            "gross_profit_factor": round(pf * 1.2, 3),
            "compounded_return_pct": round((pf - 1) * 100, 2),
            "closed_trades": 100 + seed % 50,
            "positive_fold_ratio": 0.6,
        },
        "folds": [],
    }


class TestBacktest:
    def test_sheet_is_deterministic_and_signed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(moshub, "DataDir", tmp_path)
        sheet_a = moshub.run_backtest(MANIFEST, evaluator=_evaluator)
        sheet_b = moshub.run_backtest(MANIFEST, evaluator=_evaluator)
        assert sheet_a["results"] == sheet_b["results"]
        assert sheet_a["sheet_signature"]
        # la signature couvre les résultats : modifier un métrique change la signature
        tampered = dict(sheet_a)
        tampered["results"] = {"aggregate": {"net_profit_factor": 99}}
        assert moshub.sign_sheet(tampered) != sheet_a["sheet_signature"]

    def test_invalid_manifest_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(moshub, "DataDir", tmp_path)
        with pytest.raises(ValueError, match="champs manquants"):
            moshub.run_backtest({"artifact_type": "strategy"}, evaluator=_evaluator)

    def test_non_strategy_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(moshub, "DataDir", tmp_path)
        bad = {**MANIFEST, "artifact_type": "dataset"}
        with pytest.raises(ValueError, match="strategy"):
            moshub.run_backtest(bad, evaluator=_evaluator)

    def test_load_roundtrip_and_404(self, tmp_path, monkeypatch):
        monkeypatch.setattr(moshub, "DataDir", tmp_path)
        moshub.run_backtest(MANIFEST, evaluator=_evaluator)
        loaded = moshub.load_sheet(MANIFEST)
        assert loaded["manifest_name"] == MANIFEST["name"]
        with pytest.raises(FileNotFoundError):
            moshub.load_sheet("deadbeef" * 8)


class TestCompare:
    def test_compare_two_manifests(self, tmp_path, monkeypatch):
        monkeypatch.setattr(moshub, "DataDir", tmp_path)
        sheet_a = moshub.run_backtest(MANIFEST, evaluator=_evaluator)
        other = {**MANIFEST, "name": "mean-reversion-g1", "params": {"window": 60.0}}
        sheet_b = moshub.run_backtest(other, evaluator=_evaluator)
        result = moshub.compare(sheet_a["manifest_hash"], sheet_b["manifest_hash"])
        assert set(result["diff"].keys()) == set(moshub.METRIC_KEYS)
        assert result["winner_by_net_pf"] in (sheet_a["manifest_hash"][:16], sheet_b["manifest_hash"][:16])
        # le gagnant a bien le PF net max
        pf_a = sheet_a["results"]["aggregate"]["net_profit_factor"]
        pf_b = sheet_b["results"]["aggregate"]["net_profit_factor"]
        expected = sheet_a["manifest_hash"][:16] if pf_a >= pf_b else sheet_b["manifest_hash"][:16]
        assert result["winner_by_net_pf"] == expected
