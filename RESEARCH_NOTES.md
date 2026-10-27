# EvalForge — Research Notes

Status: **partial**. Research was performed with web search and a limited set of
web fetches on 2026-10-18. Official documentation was retrieved for some projects
and not others. Nothing in this file is a performance comparison, adoption
statistic, or verified feature inventory beyond what the cited pages state.

Items marked **[unverified]** were seen only in third-party or search-excerpt
material, or conflict between sources.

## 1. Method and limitations

- Tools: WebSearch (standard mode) and WebFetch against official pages where a
  URL was known.
- Access date for all sources: 2026-10-18.
- Not done: reading each project's full source code, running any of these tools,
  checking current release notes, or confirming pricing or hosted-product terms.
- Promptfoo's license was not confirmed from an official source.

## 2. Projects reviewed

### 2.1 promptfoo

- **Principal use case:** Testing and comparing prompts, models, and LLM
  applications from a CLI, typically in CI.
- **Methodology (official docs fetched):** Deterministic assertions (`equals`,
  `contains`, `regex`, `is-json`, `javascript`, `python`, `latency`, `cost`, and
  others) plus model-graded assertions (`llm-rubric`, `factuality`,
  `context-faithfulness`, and others). Trace-based assertions exist for agent
  workflows.
- **Extension model:** Custom `javascript`, `python`, `ruby` assertions and a
  `webhook` assertion that calls an external endpoint.
- **Reporting / regression:** Pass/fail per assertion; CI gating is the primary
  documented workflow. Comparison across runs is not established from the pages
  reviewed.
- **Limitations noted on the official page:** Negation edge cases, averaging that
  does not rescale scores, custom functions must return finite numbers, derived
  metrics have no circular-dependency protection, and some model-graded checks
  return failure on grader error.
- **Learn from it:** Declarative config for prompts × providers × tests; clear
  distinction between deterministic and model-graded checks; explicit documentation
  of assertion edge cases.
- **EvalForge differentiation (proposed):** Strict per-case status semantics
  (PASS/FAIL/ERROR/SKIPPED/INCONCLUSIVE) and first-class run-to-run comparison with
  compatibility checks, targeting the regression workflow specifically. Python-first
  API and no paid or external dependency in the core.
- **Source:** https://www.promptfoo.dev/docs/configuration/expected-outputs/ (fetched 2026-10-18).
  Secondary: search excerpts describing CI regression use; several third-party
  tutorials (not used as authority).

### 2.2 DeepEval

- **Principal use case:** Unit-test-style evaluation of LLM outputs, pytest-like.
- **License (official README, fetched):** Apache 2.0.
- **Methodology:** Large metric catalogue (RAG, agentic, multi-turn, safety, custom
  G-Eval/DAG). Some metrics are LLM-judged; some use local NLP or statistical
  methods. Metrics produce scores in 0–1 with thresholds.
- **Extension model:** Subclass a base metric class; `evaluate()` API usable outside
  pytest.
- **Reporting / regression:** `deepeval test run` CLI; CI-agnostic; hosted
  dashboards are offered by the vendor (commercial, optional).
- **Learn from it:** pytest-native ergonomics; threshold-per-metric pattern; clear
  split between local and LLM-judged metrics.
- **EvalForge differentiation (proposed):** Model-agnostic core that is fully local,
  deterministic evaluators first, explicit status taxonomy, and comparison between
  stored runs rather than per-test assertions.
- **Source:** https://github.com/confident-ai/deepeval (fetched 2026-10-18).

### 2.3 Ragas

- **Principal use case:** Evaluation of retrieval-augmented generation (RAG)
  pipelines.
- **Methodology (official docs fetched):** Faithfulness is the fraction of claims in
  the response that can be inferred from the retrieved context. The documented
  steps are: identify claims, check each claim against context, divide supported
  claims by total claims. Example from the page: 1 supported of 2 claims = 0.5.
- **Limitations:** The fetched page does not state limitations of the metric. A
  search excerpt notes that faithfulness checks consistency with the provided
  context, not the truth of that context. **[unverified as a Ragas statement;
  reasoning follows from the definition]**
- **Version caveat:** The legacy API is documented as deprecated in v0.4 and
  removed in v1.0; the page recommends the collections-based API.
- **Learn from it:** Decomposition-based scoring makes the metric inspectable.
  Per-claim verdicts are a useful pattern for EvalForge's explanations.
- **EvalForge differentiation:** EvalForge is not a RAG-specific metric library in
  the MVP. Groundedness-style metrics belong in the model-based evaluator phase,
  with the limitations in `EVALUATION_METHODOLOGY.md`.
- **Source:** https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/faithfulness/ (fetched 2026-10-18).

### 2.4 Inspect AI (UK AI Security Institute, formerly AISI)

- **Principal use case:** Framework for running evaluations of LLMs and agents.
- **Core concepts (official docs fetched):** A Task combines a Dataset (samples with
  `input` and `target`), a Solver (produces the answer; can be a full agent), and a
  Scorer (grades outputs and aggregates metrics).
- **Sandboxing (official docs fetched):** Runs untrusted model-generated code in
  isolated environments (Docker, Kubernetes, Modal, Proxmox, Vagrant; extensible).
  The fetched page does not state limits of the sandboxing model.
- **License:** The fetched page does not name a license. A search excerpt says MIT
  **[unverified; check the repository LICENSE before citing]**.
- **Attribution claim:** A third-party page says AISI uses Inspect internally. Not
  confirmed against an official source. Do not repeat it in EvalForge documentation
  without verification.
- **Learn from it:** Clean separation of dataset, solver, and scorer; sandboxing as
  a first-class concept.
- **EvalForge differentiation (proposed):** Narrower scope focused on regression
  comparison of application outputs rather than general agent evaluation; no
  sandbox in MVP because EvalForge does not execute model-generated code (see
  `THREAT_MODEL.md`).
- **Source:** https://inspect.aisi.org.uk/ (fetched 2026-10-18).

### 2.5 OpenAI Evals

- **Principal use case:** Framework and registry for evaluating LLMs and
  LLM-based systems.
- **License (official README, fetched):** MIT. Contributed evals are released under
  the same license.
- **Status (official README, fetched):** Public repository. The README notes that
  evals can also be configured in the OpenAI Dashboard. Custom-code evals are not
  currently accepted; model-graded YAML evals are accepted.
- **Methodology / extension:** Basic and model-graded evals defined with JSON data
  and YAML parameters; the Completion Function Protocol is documented for prompt
  chains and tool-using systems.
- **Learn from it:** A shared registry of reusable datasets is valuable. Keeping
  the framework simple helps adoption.
- **EvalForge differentiation (proposed):** Local-first and not tied to a hosted
  vendor; regression comparison as a first-class operation; a registry is deferred
  until there is a governance and review model.
- **Source:** https://github.com/openai/evals (fetched 2026-10-18).

## 3. Cross-project observations

| Topic | Observation | Implication for EvalForge |
|---|---|---|
| Deterministic checks | Every reviewed tool offers exact/regex/JSON-style checks. | MVP evaluator set is standard, not novel. Differentiate on semantics and comparison. |
| Model-graded checks | Common and powerful, but non-deterministic and costly. | Optional, post-MVP, with documented limits. |
| Status semantics | Assertion-pass/fail is the usual model; infrastructure errors are not consistently separated in the pages reviewed. | Five explicit statuses with defined aggregation. |
| Regression | Documented mainly as CI gating of pass/fail. | Stored runs, compatibility checks, and typed findings. |
| Extension | Custom code is supported widely, often executed directly. | Custom Python evaluators are trusted code; datasets are never executed. |
| Licensing | Apache 2.0 (DeepEval) and MIT (OpenAI Evals) are permissive. | Apache-2.0 is consistent with the project target. |

## 4. Open research gaps

- Promptfoo license and current release status: not verified from an official source.
- Inspect AI license: conflicting or unverified.
- No hands-on evaluation of any tool was performed.
- No user research on the target audience has been performed.
- Pricing, hosted-product features, and adoption figures were intentionally not
  collected.
- Recommended next step: check each repository's LICENSE and recent release notes,
  and record results here with access dates.
