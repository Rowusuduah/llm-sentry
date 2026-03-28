# llmguardrail

**One install. 12 diagnostic engines. Your AI pipeline's immune system.**

Stop guessing why your LLM app is broken. `llmguardrail` runs 12 specialized diagnostic engines across your entire AI stack — RAG pipelines, agent loops, chain-of-thought reasoning, prompt stability, model swaps, and output drift — in a single scan.

```bash
pip install llm-sentry
```

## The Problem

You have an LLM in production. It breaks. You don't know why.

- Is it retrieval? Generation? Both?
- Is your agent stuck in a loop?
- Did your last prompt change break something?
- Is your chain-of-thought reasoning actually coherent?
- Did swapping models change behavior?

You're left stitching together 5+ tools, each with different APIs, different install processes, different report formats.

**llmguardrail** gives you one API, one report, one answer.

## Quick Start

```python
import llmguardrail as lg

# Run a full diagnostic scan
report = lg.scan(
    pipeline_name="my_rag_app",
    checks=["rag", "coherence", "agents"],
    rag_queries=[
        ("What is the return policy?",
         [("Returns accepted within 30 days", 0.95)],
         "Our return policy allows returns within 30 days."),
    ],
    coherence_traces=[
        ("1. User asked about returns\n2. Policy doc found\n3. Answer generated",
         "Returns are allowed within 30 days"),
    ],
    agent_task="answer customer questions",
    agent_actions=[
        ("search_docs", "found 3 results"),
        ("generate_answer", "answer produced"),
    ],
)

print(report.summary())
# Pipeline: my_rag_app
# Health: HEALTHY (85%)
# Checks: 3 run
#   [+] rag: healthy (90%)
#   [+] coherence: healthy (88%)
#   [+] agents: healthy (100%)
```

## 12 Diagnostic Engines

| Engine | What it catches | Package |
|--------|----------------|---------|
| **RAG Pathology** | Retrieval miss, poor grounding, context noise (Four Soils) | `rag-pathology` |
| **Chain Probe** | CASCADE fault analysis — finds root cause in multi-step pipelines | `chain-probe` |
| **Agent Patrol** | Futile cycles, oscillation, stall, drift, abandonment in agents | `agent-patrol` |
| **CoT Coherence** | Reasoning gaps, contradictions, unsupported conclusions | `cot-coherence` |
| **Prompt Brittleness** | Prompts that break under paraphrase stress | `prompt-brittleness` |
| **Inject Lock** | Prompt injection vulnerability detection | `inject-lock` |
| **LLM Mutation** | Mutation testing for prompt robustness | `llm-mutation` |
| **Model Parity** | Behavioral drift when swapping models | `model-parity` |
| **Spec Drift** | Output schema violations in production | `spec-drift` |
| **Drift Sentinel** | PR intent vs. actual code drift | `drift-sentinel` |
| **LLM Contract** | Runtime output contract enforcement | `llm-contract` |
| **Context Recall** | Context window position bias auditing | `context-recall` |

Every engine is zero-dependency. No OpenAI key required. No LLM calls to evaluate LLMs.

## Use Individual Engines

```python
# RAG diagnosis
from llmguardrail.rag import RAGDiagnoser, RAGQuery, Chunk

diagnoser = RAGDiagnoser("my_pipeline")
diagnosis = diagnoser.diagnose_query(RAGQuery(
    query="What is GDP?",
    retrieved_chunks=[Chunk("GDP is 6%", score=0.9)],
    generated_answer="GDP is 6%",
))
print(diagnosis.soil_type)  # SoilType.GOOD

# Agent monitoring
from llmguardrail.agents import PatrolMonitor

monitor = PatrolMonitor(task_description="answer questions")
report = monitor.observe(action="searching", result="no results")

# Chain fault analysis
from llmguardrail.chains import Pipeline

pipeline = Pipeline("my_chain")
# ... add steps with @pipeline.probe ...
result = pipeline.cascade(initial_input="data")
print(result.root_cause_step)
```

## Scan History & Trends

```python
from llmguardrail import ScanStore, scan

report = scan(pipeline_name="prod", checks=["rag", "coherence"])

store = ScanStore("guardrail.db")
store.save(report)

# Track health over time
trend = store.trend("prod", last_n=10)
print(trend)  # [0.72, 0.75, 0.78, 0.81, ...]

# Full history
history = store.get_history("prod")
```

## CLI

```bash
# Check which engines are installed
llmguardrail status

# View scan history
llmguardrail history --pipeline my_app
```

## Custom Checks

```python
from llmguardrail import register_check, CheckResult, HealthStatus, scan

def my_custom_check(**kwargs) -> CheckResult:
    # Your custom diagnostic logic
    score = run_my_diagnostics()
    return CheckResult(
        check_name="my_check",
        score=score,
        status=HealthStatus.from_score(score),
        recommendations=["Fix X"] if score < 0.7 else [],
    )

register_check("my_check", my_custom_check)
report = scan(checks=["rag", "my_check"])
```

## Why not RAGAS / DeepEval / TruLens?

| | llmguardrail | RAGAS | DeepEval | TruLens |
|---|---|---|---|---|
| Needs OpenAI key | No | Yes | Yes | Yes |
| Diagnoses failure type | Yes | No (just scores) | No | No |
| Agent monitoring | Yes | No | No | No |
| Chain fault analysis | Yes | No | No | No |
| Prompt robustness | Yes | No | Partial | No |
| Zero dependencies | Yes | No | No | No |
| Works offline | Yes | No | No | No |

## License

MIT
