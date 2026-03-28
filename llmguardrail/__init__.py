"""llmguardrail — Unified AI Reliability Platform.

One install. 12 diagnostic engines. Continuous monitoring, fault diagnosis,
and compliance for LLM pipelines.

    pip install llm-sentry

Quick start:

    import llmguardrail as lg

    # Diagnose a RAG pipeline
    from llmguardrail.rag import RAGDiagnoser, RAGQuery, Chunk
    diagnoser = RAGDiagnoser("my_pipeline")
    diagnosis = diagnoser.diagnose_query(RAGQuery(
        query="What is GDP?",
        retrieved_chunks=[Chunk("GDP is 6%", score=0.9)],
        generated_answer="GDP is 6%",
    ))

    # Monitor agent behavior
    from llmguardrail.agents import PatrolMonitor
    monitor = PatrolMonitor(task_description="answer questions")

    # Check chain-of-thought coherence
    from llmguardrail.coherence import check, parse_steps

    # Run a full pipeline scan
    report = lg.scan(checks=["rag", "coherence", "agents", "chains"])
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = [
    # Top-level API
    "scan",
    "ScanReport",
    "CheckResult",
    "HealthStatus",
    # Submodules (lazy)
    "rag",
    "chains",
    "agents",
    "coherence",
    "prompts",
    "models",
    "contracts",
    "drift",
    "context",
]

import json
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable


# ─── Health Status ──────────────────────────────────────────────────────────


class HealthStatus(str, Enum):
    """Overall health of an AI pipeline."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    UNKNOWN = "unknown"

    @classmethod
    def from_score(cls, score: float) -> "HealthStatus":
        if score >= 0.7:
            return cls.HEALTHY
        elif score >= 0.4:
            return cls.DEGRADED
        else:
            return cls.FAILING


# ─── Check Result ───────────────────────────────────────────────────────────


@dataclass
class CheckResult:
    """Result from a single diagnostic check."""
    check_name: str
    score: float = 0.0
    status: HealthStatus = HealthStatus.UNKNOWN
    details: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "check_name": self.check_name,
            "score": round(self.score, 4),
            "status": self.status.value,
            "details": self.details,
            "recommendations": self.recommendations,
        }
        if self.error:
            d["error"] = self.error
        return d


# ─── Scan Report ────────────────────────────────────────────────────────────


@dataclass
class ScanReport:
    """Unified report from a full pipeline scan."""
    pipeline_name: str = "default"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    checks: list[CheckResult] = field(default_factory=list)
    overall_score: float = 0.0
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    recommendations: list[str] = field(default_factory=list)

    def _compute(self):
        """Compute overall score and status from individual checks."""
        scored = [c for c in self.checks if c.error is None]
        if not scored:
            self.overall_score = 0.0
            self.overall_status = HealthStatus.UNKNOWN
            return
        self.overall_score = sum(c.score for c in scored) / len(scored)
        self.overall_status = HealthStatus.from_score(self.overall_score)
        # Collect all recommendations
        self.recommendations = []
        for c in self.checks:
            self.recommendations.extend(c.recommendations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_name": self.pipeline_name,
            "timestamp": self.timestamp,
            "overall_score": round(self.overall_score, 4),
            "overall_status": self.overall_status.value,
            "checks": [c.to_dict() for c in self.checks],
            "recommendations": self.recommendations,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def summary(self) -> str:
        lines = [
            f"Pipeline: {self.pipeline_name}",
            f"Health: {self.overall_status.value.upper()} ({self.overall_score:.0%})",
            f"Checks: {len(self.checks)} run",
        ]
        for c in self.checks:
            icon = "+" if c.status == HealthStatus.HEALTHY else "-" if c.status == HealthStatus.FAILING else "~"
            lines.append(f"  [{icon}] {c.check_name}: {c.status.value} ({c.score:.0%})")
        if self.recommendations:
            lines.append(f"Recommendations: {len(self.recommendations)}")
            for r in self.recommendations[:5]:
                lines.append(f"  - {r}")
            if len(self.recommendations) > 5:
                lines.append(f"  ... and {len(self.recommendations) - 5} more")
        return "\n".join(lines)


# ─── Scan Store ─────────────────────────────────────────────────────────────


class ScanStore:
    """SQLite store for scan history. Zero infrastructure."""

    def __init__(self, db_path: str | Path = "llmguardrail_scans.db"):
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                overall_score REAL,
                overall_status TEXT,
                report_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        self._conn.commit()

    def save(self, report: ScanReport) -> int:
        cur = self._conn.execute(
            "INSERT INTO scans (pipeline_name, timestamp, overall_score, overall_status, report_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (report.pipeline_name, report.timestamp, report.overall_score,
             report.overall_status.value, report.to_json()),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_history(self, pipeline_name: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if pipeline_name:
            rows = self._conn.execute(
                "SELECT id, pipeline_name, timestamp, overall_score, overall_status "
                "FROM scans WHERE pipeline_name = ? ORDER BY id DESC LIMIT ?",
                (pipeline_name, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, pipeline_name, timestamp, overall_score, overall_status "
                "FROM scans ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"id": r[0], "pipeline": r[1], "timestamp": r[2], "score": r[3], "status": r[4]}
            for r in rows
        ]

    def get_scan(self, scan_id: int) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT report_json FROM scans WHERE id = ?", (scan_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def trend(self, pipeline_name: str, last_n: int = 10) -> list[float]:
        """Get score trend for a pipeline (oldest first)."""
        rows = self._conn.execute(
            "SELECT overall_score FROM scans WHERE pipeline_name = ? "
            "ORDER BY id DESC LIMIT ?",
            (pipeline_name, last_n),
        ).fetchall()
        return [r[0] for r in reversed(rows)]

    def close(self):
        self._conn.close()


# ─── Unified Scan ───────────────────────────────────────────────────────────


# Registry of available check runners
_CHECK_REGISTRY: dict[str, Callable[..., CheckResult]] = {}


def register_check(name: str, runner: Callable[..., CheckResult]):
    """Register a diagnostic check by name."""
    _CHECK_REGISTRY[name] = runner


def available_checks() -> list[str]:
    """List all registered check names."""
    _ensure_builtin_checks()
    return sorted(_CHECK_REGISTRY.keys())


_BUILTINS_LOADED = False


def _ensure_builtin_checks():
    """Lazily register all built-in checks on first use."""
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    _BUILTINS_LOADED = True

    # RAG check
    def _rag_check(**kwargs) -> CheckResult:
        try:
            from rag_pathology import RAGDiagnoser, RAGQuery, Chunk
            queries = kwargs.get("rag_queries", [])
            pipeline_name = kwargs.get("pipeline_name", "default")
            if not queries:
                return CheckResult(
                    check_name="rag",
                    error="No rag_queries provided. Pass list of (query, chunks, answer) tuples.",
                )
            diagnoser = RAGDiagnoser(pipeline_name)
            for q, chunks, answer in queries:
                diagnoser.diagnose_query(RAGQuery(
                    query=q,
                    retrieved_chunks=[Chunk(c, score=s) for c, s in chunks],
                    generated_answer=answer,
                ))
            pd = diagnoser.pipeline_diagnosis()
            return CheckResult(
                check_name="rag",
                score=pd.overall_health,
                status=HealthStatus.from_score(pd.overall_health),
                details={
                    "total_queries": pd.total_queries,
                    "soil_distribution": pd.soil_distribution,
                },
                recommendations=pd.recommendations,
            )
        except ImportError:
            return CheckResult(check_name="rag", error="rag-pathology not installed")
        except Exception as e:
            return CheckResult(check_name="rag", error=str(e))
    register_check("rag", _rag_check)

    # Coherence check
    def _coherence_check(**kwargs) -> CheckResult:
        try:
            from cot_coherence import check as cot_check, parse_steps
            traces = kwargs.get("coherence_traces", [])
            if not traces:
                return CheckResult(
                    check_name="coherence",
                    error="No coherence_traces provided. Pass list of (steps_text, conclusion) tuples.",
                )
            scores = []
            violations = 0
            for steps_text, conclusion in traces:
                steps = parse_steps(steps_text)
                report = cot_check(steps=steps, conclusion=conclusion)
                scores.append(report.overall_score if hasattr(report, "overall_score") else
                              (1.0 if report.status.value == "coherent" else 0.0))
                violations += len(report.violations) if hasattr(report, "violations") else 0
            avg = sum(scores) / len(scores) if scores else 0.0
            recs = []
            if violations > 0:
                recs.append(f"{violations} coherence violations detected across {len(traces)} traces")
            return CheckResult(
                check_name="coherence",
                score=avg,
                status=HealthStatus.from_score(avg),
                details={"traces_checked": len(traces), "total_violations": violations},
                recommendations=recs,
            )
        except ImportError:
            return CheckResult(check_name="coherence", error="cot-coherence not installed")
        except Exception as e:
            return CheckResult(check_name="coherence", error=str(e))
    register_check("coherence", _coherence_check)

    # Chain/pipeline check
    def _chain_check(**kwargs) -> CheckResult:
        try:
            from chain_probe import Pipeline
            pipeline_obj = kwargs.get("chain_pipeline")
            chain_input = kwargs.get("chain_input")
            if not pipeline_obj:
                return CheckResult(
                    check_name="chains",
                    error="No chain_pipeline provided. Pass a chain_probe.Pipeline instance.",
                )
            result = pipeline_obj.cascade(initial_input=chain_input)
            score = 1.0 if result.pipeline_verdict.value == "healthy" else (
                0.5 if result.pipeline_verdict.value == "degraded" else 0.0)
            recs = []
            if result.root_cause_step:
                recs.append(f"Root cause failure at step: {result.root_cause_step}")
            return CheckResult(
                check_name="chains",
                score=score,
                status=HealthStatus.from_score(score),
                details={
                    "verdict": result.pipeline_verdict.value,
                    "root_cause": result.root_cause_step,
                    "total_steps": len(result.step_records),
                },
                recommendations=recs,
            )
        except ImportError:
            return CheckResult(check_name="chains", error="chain-probe not installed")
        except Exception as e:
            return CheckResult(check_name="chains", error=str(e))
    register_check("chains", _chain_check)

    # Agent patrol check
    def _agent_check(**kwargs) -> CheckResult:
        try:
            from agent_patrol import PatrolMonitor
            task = kwargs.get("agent_task", "")
            actions = kwargs.get("agent_actions", [])
            if not actions:
                return CheckResult(
                    check_name="agents",
                    error="No agent_actions provided. Pass list of (action, result) tuples.",
                )
            monitor = PatrolMonitor(task_description=task)
            pathologies_found = []
            for action, result in actions:
                report = monitor.observe(action=action, result=result)
                if report and report.pathology:
                    pathologies_found.append(report.pathology.value)
            score = 1.0 - (len(pathologies_found) / len(actions)) if actions else 1.0
            score = max(0.0, min(1.0, score))
            recs = []
            if pathologies_found:
                from collections import Counter
                counts = Counter(pathologies_found)
                for p, n in counts.most_common():
                    recs.append(f"Agent pathology '{p}' detected {n} time(s)")
            return CheckResult(
                check_name="agents",
                score=score,
                status=HealthStatus.from_score(score),
                details={"actions_checked": len(actions), "pathologies": pathologies_found},
                recommendations=recs,
            )
        except ImportError:
            return CheckResult(check_name="agents", error="agent-patrol not installed")
        except Exception as e:
            return CheckResult(check_name="agents", error=str(e))
    register_check("agents", _agent_check)

    # Drift check
    def _drift_check(**kwargs) -> CheckResult:
        try:
            from spec_drift import DriftMonitor
            monitor = kwargs.get("drift_monitor")
            observations = kwargs.get("drift_observations", [])
            if not monitor:
                return CheckResult(
                    check_name="drift",
                    error="No drift_monitor provided. Pass a spec_drift.DriftMonitor instance.",
                )
            alerts = []
            for obs in observations:
                result = monitor.observe(obs)
                if hasattr(result, "alerts") and result.alerts:
                    alerts.extend(result.alerts)
            score = 1.0 - (len(alerts) / max(len(observations), 1))
            score = max(0.0, min(1.0, score))
            return CheckResult(
                check_name="drift",
                score=score,
                status=HealthStatus.from_score(score),
                details={"observations": len(observations), "alerts": len(alerts)},
                recommendations=[f"{len(alerts)} drift alerts detected"] if alerts else [],
            )
        except ImportError:
            return CheckResult(check_name="drift", error="spec-drift not installed")
        except Exception as e:
            return CheckResult(check_name="drift", error=str(e))
    register_check("drift", _drift_check)

    # Contract check
    def _contract_check(**kwargs) -> CheckResult:
        try:
            import llm_contract  # noqa: F401
            return CheckResult(
                check_name="contracts",
                score=1.0,
                status=HealthStatus.HEALTHY,
                details={"note": "llm-contract available; use @contract decorator on LLM functions"},
            )
        except ImportError:
            return CheckResult(check_name="contracts", error="llm-contract not installed")
    register_check("contracts", _contract_check)

    # Prompt brittleness check
    def _prompt_check(**kwargs) -> CheckResult:
        try:
            import prompt_shield  # noqa: F401
            return CheckResult(
                check_name="prompts",
                score=1.0,
                status=HealthStatus.HEALTHY,
                details={"note": "prompt-brittleness available; use BrittlenessRunner for testing"},
            )
        except ImportError:
            return CheckResult(check_name="prompts", error="prompt-brittleness not installed")
    register_check("prompts", _prompt_check)

    # Model parity check
    def _model_check(**kwargs) -> CheckResult:
        try:
            import model_parity  # noqa: F401
            return CheckResult(
                check_name="models",
                score=1.0,
                status=HealthStatus.HEALTHY,
                details={"note": "model-parity available; use ParityRunner for model comparison"},
            )
        except ImportError:
            return CheckResult(check_name="models", error="model-parity not installed")
    register_check("models", _model_check)


def scan(
    pipeline_name: str = "default",
    checks: list[str] | None = None,
    **kwargs,
) -> ScanReport:
    """Run a unified diagnostic scan across multiple engines.

    Args:
        pipeline_name: Name of the pipeline being scanned.
        checks: List of check names to run. None = run all available.
        **kwargs: Check-specific arguments (rag_queries, coherence_traces, etc.)

    Returns:
        ScanReport with results from all checks.
    """
    _ensure_builtin_checks()
    report = ScanReport(pipeline_name=pipeline_name)

    targets = checks or list(_CHECK_REGISTRY.keys())
    for name in targets:
        runner = _CHECK_REGISTRY.get(name)
        if runner is None:
            report.checks.append(CheckResult(
                check_name=name, error=f"Unknown check: {name}"
            ))
            continue
        result = runner(**kwargs, pipeline_name=pipeline_name)
        report.checks.append(result)

    report._compute()
    return report


# ─── Convenience re-exports (lazy) ─────────────────────────────────────────
# Users can do: from llmguardrail import rag, chains, agents, etc.
# These are lazy-loaded to avoid import cost when not used.


class _LazyModule:
    """Lazy module loader to avoid importing all 12 packages at startup."""

    _MAPPING = {
        "rag": "rag_pathology",
        "chains": "chain_probe",
        "agents": "agent_patrol",
        "coherence": "cot_coherence",
        "prompts": "prompt_shield",
        "models": "model_parity",
        "contracts": "llm_contract",
        "drift": "spec_drift",
        "context": "context_lens",
        "mutation": "llm_mutation",
        "injection": "prompt_lock",
        "sentinel": "drift_guard",
    }

    def __init__(self, alias: str, real_module: str):
        self._alias = alias
        self._real_module = real_module
        self._mod = None

    def _load(self):
        if self._mod is None:
            import importlib
            self._mod = importlib.import_module(self._real_module)
        return self._mod

    def __getattr__(self, name: str):
        return getattr(self._load(), name)

    def __repr__(self):
        return f"<llmguardrail.{self._alias} -> {self._real_module}>"


def __getattr__(name: str):
    """Module-level lazy loading for submodule aliases."""
    if name in _LazyModule._MAPPING:
        mod = _LazyModule(name, _LazyModule._MAPPING[name])
        globals()[name] = mod
        return mod
    raise AttributeError(f"module 'llmguardrail' has no attribute {name!r}")


# ─── CLI ────────────────────────────────────────────────────────────────────


def _cli_main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(
        prog="llmguardrail",
        description="LLM Guardrail — Unified AI Reliability Platform",
    )
    parser.add_argument("--version", action="version", version=f"llmguardrail {__version__}")

    sub = parser.add_subparsers(dest="command")

    # Status command
    sub.add_parser("status", help="Show which diagnostic engines are installed")

    # History command
    hist = sub.add_parser("history", help="Show scan history")
    hist.add_argument("--pipeline", default=None, help="Filter by pipeline name")
    hist.add_argument("--db", default="llmguardrail_scans.db", help="Database path")

    args = parser.parse_args()

    if args.command == "status":
        _ensure_builtin_checks()
        engines = [
            ("rag-pathology", "rag_pathology", "RAG pipeline diagnosis (Four Soils)"),
            ("chain-probe", "chain_probe", "Pipeline CASCADE fault analysis"),
            ("agent-patrol", "agent_patrol", "Agent behavior pathology detection"),
            ("cot-coherence", "cot_coherence", "Chain-of-thought coherence verification"),
            ("prompt-brittleness", "prompt_shield", "Prompt robustness testing"),
            ("inject-lock", "prompt_lock", "Prompt injection detection"),
            ("llm-mutation", "llm_mutation", "Prompt mutation testing"),
            ("model-parity", "model_parity", "Model swap parity verification"),
            ("spec-drift", "spec_drift", "Output schema drift monitoring"),
            ("drift-sentinel", "drift_guard", "PR intent drift detection"),
            ("llm-contract", "llm_contract", "LLM output contract enforcement"),
            ("context-recall", "context_lens", "Context window recall auditing"),
        ]
        print(f"LLM Guardrail v{__version__}")
        print(f"{'Engine':<22} {'Status':<12} Description")
        print("-" * 75)
        for name, module, desc in engines:
            try:
                __import__(module)
                status = "INSTALLED"
            except ImportError:
                status = "MISSING"
            icon = "+" if status == "INSTALLED" else "-"
            print(f"  [{icon}] {name:<18} {status:<12} {desc}")

    elif args.command == "history":
        store = ScanStore(args.db)
        history = store.get_history(args.pipeline)
        if not history:
            print("No scan history found.")
        else:
            print(f"{'ID':<6} {'Pipeline':<20} {'Score':<8} {'Status':<12} Timestamp")
            print("-" * 70)
            for h in history:
                print(f"{h['id']:<6} {h['pipeline']:<20} {h['score']:<8.2f} {h['status']:<12} {h['timestamp']}")
        store.close()

    else:
        parser.print_help()
