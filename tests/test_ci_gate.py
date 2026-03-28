"""Tests for the CI/CD quality gate."""

import json
import pytest

from llmguardrail.ci_gate import run_gate


class TestCIGate:
    def test_passing_gate(self, tmp_path):
        config = {
            "pipeline_name": "test",
            "checks": ["rag"],
            "threshold": 0.3,
            "rag_queries": [
                ["What is GDP?", [["GDP is 6%", 0.9]], "GDP is 6%"],
            ],
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config))
        result = run_gate(str(config_path))
        assert result == 0  # PASS

    def test_failing_gate(self, tmp_path):
        config = {
            "pipeline_name": "test",
            "checks": ["rag"],
            "threshold": 0.99,
            "rag_queries": [
                ["What is X?", [["Totally irrelevant", 0.1]], "I don't know"],
            ],
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config))
        result = run_gate(str(config_path))
        assert result == 1  # FAIL

    def test_gate_with_db(self, tmp_path):
        config = {
            "pipeline_name": "tracked",
            "checks": ["rag"],
            "threshold": 0.3,
            "rag_queries": [
                ["What is GDP?", [["GDP is 6%", 0.9]], "GDP is 6%"],
            ],
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config))
        db_path = str(tmp_path / "gate.db")
        result = run_gate(str(config_path), db_path=db_path)
        assert result == 0

    def test_threshold_override(self, tmp_path):
        config = {
            "pipeline_name": "test",
            "checks": ["rag"],
            "threshold": 0.01,  # Would pass
            "rag_queries": [
                ["What is X?", [["Totally irrelevant", 0.1]], "I don't know"],
            ],
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config))
        # Override with high threshold
        result = run_gate(str(config_path), threshold=0.99)
        assert result == 1  # FAIL due to override
