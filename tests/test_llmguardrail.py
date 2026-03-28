"""Tests for llmguardrail — Unified AI Reliability Platform."""

import json
import pytest

from llmguardrail import (
    CheckResult, HealthStatus, ScanReport, ScanStore,
    __version__, available_checks, register_check, scan,
)


# ─── HealthStatus Tests ────────────────────────────────────────────────────


class TestHealthStatus:
    def test_healthy(self):
        assert HealthStatus.from_score(0.85) == HealthStatus.HEALTHY

    def test_degraded(self):
        assert HealthStatus.from_score(0.55) == HealthStatus.DEGRADED

    def test_failing(self):
        assert HealthStatus.from_score(0.2) == HealthStatus.FAILING

    def test_boundary_healthy(self):
        assert HealthStatus.from_score(0.7) == HealthStatus.HEALTHY

    def test_boundary_degraded(self):
        assert HealthStatus.from_score(0.4) == HealthStatus.DEGRADED

    def test_boundary_failing(self):
        assert HealthStatus.from_score(0.39) == HealthStatus.FAILING


# ─── CheckResult Tests ─────────────────────────────────────────────────────


class TestCheckResult:
    def test_basic(self):
        r = CheckResult(check_name="test", score=0.8, status=HealthStatus.HEALTHY)
        assert r.check_name == "test"
        assert r.score == 0.8

    def test_to_dict(self):
        r = CheckResult(
            check_name="rag",
            score=0.75,
            status=HealthStatus.HEALTHY,
            details={"queries": 10},
            recommendations=["add more docs"],
        )
        d = r.to_dict()
        assert d["check_name"] == "rag"
        assert d["score"] == 0.75
        assert d["status"] == "healthy"
        assert d["details"]["queries"] == 10
        assert "error" not in d

    def test_to_dict_with_error(self):
        r = CheckResult(check_name="broken", error="not installed")
        d = r.to_dict()
        assert d["error"] == "not installed"

    def test_defaults(self):
        r = CheckResult(check_name="x")
        assert r.score == 0.0
        assert r.status == HealthStatus.UNKNOWN
        assert r.details == {}
        assert r.recommendations == []
        assert r.error is None


# ─── ScanReport Tests ──────────────────────────────────────────────────────


class TestScanReport:
    def test_empty_report(self):
        r = ScanReport(pipeline_name="test")
        r._compute()
        assert r.overall_status == HealthStatus.UNKNOWN
        assert r.overall_score == 0.0

    def test_single_check(self):
        r = ScanReport(pipeline_name="test")
        r.checks.append(CheckResult(check_name="a", score=0.8, status=HealthStatus.HEALTHY))
        r._compute()
        assert r.overall_score == 0.8
        assert r.overall_status == HealthStatus.HEALTHY

    def test_multiple_checks(self):
        r = ScanReport(pipeline_name="test")
        r.checks.append(CheckResult(check_name="a", score=0.9, status=HealthStatus.HEALTHY))
        r.checks.append(CheckResult(check_name="b", score=0.5, status=HealthStatus.DEGRADED))
        r._compute()
        assert r.overall_score == pytest.approx(0.7)
        assert r.overall_status == HealthStatus.HEALTHY

    def test_errored_checks_excluded_from_score(self):
        r = ScanReport(pipeline_name="test")
        r.checks.append(CheckResult(check_name="a", score=0.8, status=HealthStatus.HEALTHY))
        r.checks.append(CheckResult(check_name="broken", error="not installed"))
        r._compute()
        assert r.overall_score == 0.8  # Only scored check counts

    def test_recommendations_aggregated(self):
        r = ScanReport(pipeline_name="test")
        r.checks.append(CheckResult(
            check_name="a", score=0.5, status=HealthStatus.DEGRADED,
            recommendations=["fix retrieval"],
        ))
        r.checks.append(CheckResult(
            check_name="b", score=0.6, status=HealthStatus.DEGRADED,
            recommendations=["improve grounding"],
        ))
        r._compute()
        assert len(r.recommendations) == 2
        assert "fix retrieval" in r.recommendations
        assert "improve grounding" in r.recommendations

    def test_to_dict(self):
        r = ScanReport(pipeline_name="my_pipe")
        r.checks.append(CheckResult(check_name="a", score=0.8, status=HealthStatus.HEALTHY))
        r._compute()
        d = r.to_dict()
        assert d["pipeline_name"] == "my_pipe"
        assert len(d["checks"]) == 1
        assert d["overall_status"] == "healthy"

    def test_to_json(self):
        r = ScanReport(pipeline_name="test")
        r._compute()
        j = json.loads(r.to_json())
        assert j["pipeline_name"] == "test"

    def test_summary(self):
        r = ScanReport(pipeline_name="prod_rag")
        r.checks.append(CheckResult(
            check_name="rag", score=0.8, status=HealthStatus.HEALTHY,
        ))
        r.checks.append(CheckResult(
            check_name="chains", score=0.3, status=HealthStatus.FAILING,
            recommendations=["Fix root cause"],
        ))
        r._compute()
        s = r.summary()
        assert "prod_rag" in s
        assert "DEGRADED" in s or "HEALTHY" in s
        assert "rag" in s
        assert "chains" in s


# ─── ScanStore Tests ────────────────────────────────────────────────────────


class TestScanStore:
    def test_save_and_retrieve(self, tmp_path):
        db = tmp_path / "test.db"
        store = ScanStore(db)
        report = ScanReport(pipeline_name="test_pipe", overall_score=0.85,
                            overall_status=HealthStatus.HEALTHY)
        scan_id = store.save(report)
        assert scan_id >= 1
        history = store.get_history("test_pipe")
        assert len(history) == 1
        assert history[0]["score"] == 0.85
        store.close()

    def test_get_scan(self, tmp_path):
        db = tmp_path / "test.db"
        store = ScanStore(db)
        report = ScanReport(pipeline_name="detail", overall_score=0.5,
                            overall_status=HealthStatus.DEGRADED)
        scan_id = store.save(report)
        details = store.get_scan(scan_id)
        assert details["pipeline_name"] == "detail"
        store.close()

    def test_get_nonexistent(self, tmp_path):
        db = tmp_path / "test.db"
        store = ScanStore(db)
        assert store.get_scan(999) is None
        store.close()

    def test_history_all_pipelines(self, tmp_path):
        db = tmp_path / "test.db"
        store = ScanStore(db)
        store.save(ScanReport(pipeline_name="a", overall_score=0.9,
                              overall_status=HealthStatus.HEALTHY))
        store.save(ScanReport(pipeline_name="b", overall_score=0.5,
                              overall_status=HealthStatus.DEGRADED))
        history = store.get_history()
        assert len(history) == 2
        store.close()

    def test_trend(self, tmp_path):
        db = tmp_path / "test.db"
        store = ScanStore(db)
        for score in [0.5, 0.6, 0.7, 0.8]:
            store.save(ScanReport(pipeline_name="p", overall_score=score,
                                  overall_status=HealthStatus.from_score(score)))
        trend = store.trend("p")
        assert trend == [0.5, 0.6, 0.7, 0.8]
        store.close()


# ─── Register and Scan Tests ───────────────────────────────────────────────


class TestRegistration:
    def test_register_custom_check(self):
        def my_check(**kwargs) -> CheckResult:
            return CheckResult(check_name="custom", score=0.99, status=HealthStatus.HEALTHY)
        register_check("custom_test", my_check)
        checks = available_checks()
        assert "custom_test" in checks

    def test_scan_unknown_check(self):
        report = scan(pipeline_name="test", checks=["nonexistent_xyz_check"])
        assert len(report.checks) == 1
        assert report.checks[0].error is not None
        assert "Unknown check" in report.checks[0].error


class TestScan:
    def test_scan_with_rag(self):
        """Test RAG check with actual rag-pathology."""
        report = scan(
            pipeline_name="test_rag",
            checks=["rag"],
            rag_queries=[
                (
                    "What is Ghana GDP growth rate",
                    [("Ghana GDP growth rate is 6.0 percent in 2025", 0.95)],
                    "Ghana GDP growth rate is 6.0 percent",
                ),
                (
                    "What is the exchange rate",
                    [("Recipe for bread making", 0.1)],
                    "I cannot determine the exchange rate",
                ),
            ],
        )
        assert len(report.checks) == 1
        rag_check = report.checks[0]
        assert rag_check.check_name == "rag"
        if rag_check.error is None:
            assert 0.0 <= rag_check.score <= 1.0
            assert rag_check.details["total_queries"] == 2

    def test_scan_with_agents(self):
        """Test agent check with actual agent-patrol."""
        report = scan(
            pipeline_name="test_agents",
            checks=["agents"],
            agent_task="answer user questions",
            agent_actions=[
                ("search database", "found 3 results"),
                ("format response", "formatted answer"),
                ("send response", "response sent"),
            ],
        )
        assert len(report.checks) == 1
        agent_check = report.checks[0]
        assert agent_check.check_name == "agents"
        if agent_check.error is None:
            assert agent_check.score > 0.0

    def test_scan_with_coherence(self):
        """Test coherence check with actual cot-coherence."""
        report = scan(
            pipeline_name="test_cot",
            checks=["coherence"],
            coherence_traces=[
                ("1. GDP grew by 6%\n2. This means the economy expanded\n3. Therefore growth is positive",
                 "Ghana's economy is growing"),
            ],
        )
        assert len(report.checks) == 1
        coh_check = report.checks[0]
        assert coh_check.check_name == "coherence"

    def test_scan_multiple_checks(self):
        """Test running multiple checks at once."""
        report = scan(
            pipeline_name="multi_test",
            checks=["rag", "agents", "coherence"],
            rag_queries=[
                ("What is GDP", [("GDP is 6%", 0.9)], "GDP is 6%"),
            ],
            agent_task="test",
            agent_actions=[("action", "result")],
            coherence_traces=[("1. A\n2. B", "C")],
        )
        assert len(report.checks) == 3
        assert report.pipeline_name == "multi_test"

    def test_scan_empty_rag_queries(self):
        """Error when no queries provided."""
        report = scan(pipeline_name="test", checks=["rag"])
        assert report.checks[0].error is not None

    def test_scan_computes_overall(self):
        """Overall score and status computed after scan."""
        def good_check(**kwargs):
            return CheckResult(check_name="good", score=0.9, status=HealthStatus.HEALTHY)
        register_check("_test_good", good_check)
        report = scan(pipeline_name="test", checks=["_test_good"])
        assert report.overall_score == 0.9
        assert report.overall_status == HealthStatus.HEALTHY


# ─── Integration Tests ──────────────────────────────────────────────────────


class TestIntegration:
    def test_full_scan_and_store(self, tmp_path):
        """Full scan → store → retrieve cycle."""
        report = scan(
            pipeline_name="integration_test",
            checks=["rag"],
            rag_queries=[
                ("What is GDP", [("GDP is 6%", 0.9)], "GDP is 6%"),
            ],
        )
        db = tmp_path / "integration.db"
        store = ScanStore(db)
        scan_id = store.save(report)
        retrieved = store.get_scan(scan_id)
        assert retrieved["pipeline_name"] == "integration_test"
        store.close()

    def test_scan_summary_output(self):
        """Summary is human-readable."""
        report = scan(
            pipeline_name="summary_test",
            checks=["rag"],
            rag_queries=[
                ("What is GDP", [("GDP is 6%", 0.9)], "GDP is 6%"),
            ],
        )
        s = report.summary()
        assert "summary_test" in s
        assert "rag" in s


# ─── Lazy Import Tests ──────────────────────────────────────────────────────


class TestLazyImports:
    def test_rag_module(self):
        import llmguardrail
        try:
            rag = llmguardrail.rag
            assert rag is not None
        except ImportError:
            pass  # OK if rag-pathology not installed

    def test_agents_module(self):
        import llmguardrail
        try:
            agents = llmguardrail.agents
            assert agents is not None
        except ImportError:
            pass

    def test_unknown_attribute_raises(self):
        import llmguardrail
        with pytest.raises(AttributeError):
            _ = llmguardrail.nonexistent_thing


# ─── Version ────────────────────────────────────────────────────────────────


def test_version():
    assert __version__ == "0.1.0"
