# Launch Plan for llm-sentry

## Hacker News Post (Show HN)

**Title:** Show HN: LLM Sentry – 12 diagnostic engines for AI pipelines, zero dependencies, no API keys

**Text:**

I built llm-sentry because I was tired of debugging LLM apps by staring at RAGAS scores.

RAGAS tells you your RAG pipeline scores 0.6. Now what? Is it retrieval? Generation? Context assembly? Is your agent stuck in a loop? Did your last prompt change break something? RAGAS won't tell you. Neither will DeepEval, TruLens, or Promptfoo.

llm-sentry runs 12 specialized diagnostic engines across your entire AI stack in a single scan:

- RAG Pathology: Classifies failures into 4 types (retrieval miss, poor grounding, noisy context, healthy) — tells you exactly WHERE your RAG pipeline breaks
- Chain Probe: CASCADE fault analysis for multi-step pipelines — finds the root cause, not just the symptom
- Agent Patrol: Detects 5 agent pathologies (futile cycles, oscillation, stall, drift, abandonment)
- CoT Coherence: Catches reasoning gaps, contradictions, and unsupported conclusions
- Prompt Brittleness: Stress-tests prompts under paraphrase — finds fragile prompts before production does
- Plus 7 more: injection detection, mutation testing, model swap parity, output drift, contracts, context recall

Key differentiators:

1. Zero dependencies. No OpenAI key required. No LLM calls to evaluate LLMs.
2. Works completely offline.
3. One install, one API: `pip install llm-sentry` gives you everything.
4. Diagnosis, not just scores. Every check tells you what's wrong AND what to fix.

```python
import llmguardrail as lg

report = lg.scan(
    pipeline_name="my_app",
    checks=["rag", "coherence", "agents"],
    rag_queries=[("What is the return policy?", [("Returns within 30 days", 0.95)], "Returns within 30 days")],
)
print(report.summary())
# Pipeline: my_app
# Health: HEALTHY (92%)
# Checks: 3 run
```

GitHub: https://github.com/Rowusuduah/llm-sentry
PyPI: https://pypi.org/project/llm-sentry/
License: MIT

I'd love feedback on what checks you wish existed, or what's missing from your current AI debugging workflow.

---

## Reddit r/MachineLearning Post

**Title:** [P] I built a zero-dependency diagnostic toolkit for LLM pipelines — 12 engines, no API keys, works offline

**Body:**

Every LLM eval tool I've tried (RAGAS, DeepEval, TruLens) gives me a score. A score doesn't help when production is broken at 2 AM.

I built llm-sentry — a unified platform with 12 diagnostic engines that tell you WHAT is wrong and WHERE in your pipeline:

**What it catches:**
- RAG failures: Is it retrieval, generation, or noisy context? (Four Soils classification)
- Agent loops: Futile cycles, oscillation, stall, drift, abandonment
- Reasoning breaks: CoT gaps, contradictions, unsupported conclusions
- Prompt fragility: Which prompts break under paraphrase?
- Pipeline faults: Root cause analysis across multi-step chains
- Output drift: Schema violations, behavioral changes after model swaps

**Why it's different:**
- No API keys. No OpenAI calls. Zero external dependencies.
- Works offline. Runs in CI/CD.
- Diagnoses, not just scores. Every check gives you a fix.

```bash
pip install llm-sentry
```

```python
import llmguardrail as lg
report = lg.scan(pipeline_name="prod", checks=["rag", "coherence", "agents"])
print(report.summary())
```

GitHub: https://github.com/Rowusuduah/llm-sentry

Looking for feedback — what diagnostic would you add? What's the hardest part of debugging your LLM apps?

---

## Reddit r/Python Post

**Title:** [Project] llm-sentry: Unified diagnostic platform for LLM pipelines — 12 engines, pure Python, zero deps

**Body:**

I built llm-sentry, a pure-Python toolkit for diagnosing failures in LLM-powered applications.

The problem: You have an LLM app in production. Something breaks. Existing tools (RAGAS, DeepEval) give you a score but don't tell you what's wrong.

llm-sentry gives you 12 diagnostic engines under one API:

| Engine | What it catches |
|--------|----------------|
| RAG Pathology | Retrieval miss vs. grounding failure vs. context noise |
| Chain Probe | Root cause in multi-step pipelines |
| Agent Patrol | 5 agent pathologies (loops, stall, drift, etc.) |
| CoT Coherence | Reasoning gaps and contradictions |
| Prompt Brittleness | Prompts that break under paraphrase |
| + 7 more | Injection, mutation, model parity, drift, contracts, context |

Design decisions:
- Zero dependencies (pure Python, stdlib only)
- No LLM calls needed to evaluate LLMs
- Every engine has a SQLite store built in for history/trends
- Unified `scan()` API runs any combination of checks
- Extensible: register your own custom checks

```bash
pip install llm-sentry
```

Built with hatchling, tested with pytest (37+ tests), MIT licensed.

GitHub: https://github.com/Rowusuduah/llm-sentry
PyPI: https://pypi.org/project/llm-sentry/

---

## Twitter/X Thread

**Tweet 1:**
I just shipped llm-sentry — 12 diagnostic engines for LLM pipelines, zero dependencies, no API keys.

RAGAS gives you a score. llm-sentry tells you what's broken and how to fix it.

pip install llm-sentry

🧵 What's inside:

**Tweet 2:**
1/ RAG Pathology — "Four Soils" classification

Your RAG scores 0.6. But WHY?

- PATH: Retrieval missed entirely → fix embeddings
- ROCKY: Good retrieval, bad generation → fix grounding prompt
- THORNY: Noisy context → add reranking
- GOOD: Working as intended

**Tweet 3:**
2/ Agent Patrol — detects 5 agent pathologies

Your agent is "thinking" for 5 minutes. Is it:
- Futile cycling (same actions over and over)?
- Oscillating between two states?
- Stalled on a subtask?
- Drifted from the original goal?
- Abandoned the task entirely?

Now you know.

**Tweet 4:**
3/ Chain Probe — CASCADE fault analysis

Multi-step pipeline fails at step 5. But the REAL problem was step 2.

Chain Probe traces the cascade: ROOT_CAUSE → INHERITED → INHERITED → INHERITED → symptom.

Fix the root, fix everything.

**Tweet 5:**
The key insight: you don't need GPT-4 to evaluate GPT-4.

Every engine in llm-sentry works with zero LLM calls. Pure algorithmic diagnosis. Works offline. Runs in CI/CD.

GitHub: https://github.com/Rowusuduah/llm-sentry
PyPI: https://pypi.org/project/llm-sentry/

MIT licensed. Feedback welcome.
