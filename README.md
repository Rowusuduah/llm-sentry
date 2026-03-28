# llm-sentry

**One install. 12 diagnostic engines. Your AI pipeline's immune system.**

Stop guessing why your LLM app is broken. `llm-sentry` runs 12 specialized diagnostic engines across your entire AI stack — RAG pipelines, agent loops, chain-of-thought reasoning, prompt stability, model migrations, and output drift — in a single scan.

```bash
pip install llm-sentry
```

```python
import llmguardrail as lg

report = lg.scan(
    pipeline_name="my_app",
    checks=["rag", "coherence", "agents", "prompts"],
    ...
)
print(report.summary())
```

---

## The 12 Diagnostic Engines

| # | Engine | What It Detects | Module |
|---|--------|----------------|--------|
| 1 | **RAG Pathology** | Retrieval failures by type and location (Four Soils classification) | `rag_pathology` |
| 2 | **Agent Patrol** | Agent loops, stalls, oscillation, drift, and abandonment | `agent_patrol` |
| 3 | **Chain Probe** | Root-cause step in multi-step pipeline failures (CASCADE analysis) | `chain_probe` |
| 4 | **Context Lens** | Lost-in-the-middle — LLM failing to retrieve from context positions | `context_lens` |
| 5 | **LLM Mutation** | Gaps in prompt test coverage via semantic mutation testing | `llm_mutation` |
| 6 | **Prompt Shield** | Brittle prompts that break under paraphrase stress testing | `prompt_shield` |
| 7 | **LLM Contract** | Behavioral contract violations on LLM function calls | `llm_contract` |
| 8 | **Drift Guard** | PR intent drift — code changes that don't match stated purpose | `drift_guard` |
| 9 | **Spec Drift** | Semantic specification drift even when structural validation passes | `spec_drift` |
| 10 | **Prompt Lock** | Prompt regression detection with judge calibration and CI gate | `prompt_lock` |
| 11 | **Model Parity** | Behavioral divergence when swapping LLM providers (7 dimensions) | `model_parity` |
| 12 | **CoT Coherence** | Silent incoherence in chain-of-thought reasoning between steps | `cot_coherence` |

---

## Why One Platform?

Most teams discover LLM failures in production, then stitch together 5+ tools with different APIs, install processes, and report formats.

**llm-sentry** gives you:
- **One install** — `pip install llm-sentry`
- **One API** — `lg.scan()` with check selection
- **One report** — unified diagnostics across all failure modes
- **One CI gate** — `llm-sentry ci` blocks merges on regressions

---

## Use Cases

- **RAG apps**: retrieval quality + generation faithfulness + context window coverage
- **Agent systems**: loop detection + drift monitoring + abandonment alerts
- **Prompt engineering**: brittleness testing + regression gating + mutation coverage
- **Model migrations**: behavioral parity certification across 7 dimensions
- **Production monitoring**: continuous semantic drift detection + contract enforcement

---

## Requirements

- Python 3.10+
- Zero required dependencies (LLM-powered checks optional)

## License

MIT
