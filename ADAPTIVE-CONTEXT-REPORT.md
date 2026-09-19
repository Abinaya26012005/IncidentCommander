# IncidentCommander — Adaptive Context Intelligence verification

This report records the recovered implementation and the final local verification run. Status labels are deliberately limited to `TESTED`, `IMPLEMENTED — NOT RUNTIME TESTED`, `PARTIAL`, and `NOT IMPLEMENTED`.

## A. Recovery

**TESTED** — The project root is an exported workspace rather than a Git repository, so root `git status`/`git diff` correctly report no repository. Nested PayFlow runtime Git state was inspected; the approved repair leaves only the expected repaired source change. Existing hardening files, tests, protected hashes and reports were preserved.

## B. Adaptive Context Intelligence

**TESTED** — Payload profiling, JSON/TOON/HYBRID serialization, AUTO utility selection, the 5% minimum-saving policy, exact token/byte/timing measurements, canonical round-trip validation, path-aware integrity anchors, token-budget arithmetic, deterministic JSON fallback, copied-payload secret redaction and observability metadata.

The TOON candidate uses the versioned JavaScript reference codec (`@toon-format/toon` 4.1.1), aligned with the [TOON specification](https://github.com/toon-format/spec). A local `tiktoken` reference tokenizer is used; no model-specific tokenizer claim is made.

## C. Integrations

**TESTED** — Final RCA, INCIDENT_MEMORY and INVESTIGATOR_CONTEXT are measured once and recorded as boundary operations; Copilot and postmortem output expose the same metadata. **IMPLEMENTED — NOT RUNTIME TESTED** — Sending optimized context to a real external provider, because no provider credentials were configured. The provider boundary remains one call with structured output instructions.

## D. UI

**TESTED** — Commander displays the AI Context card and details dialog with selected strategy, candidate comparison, tokens/bytes, measured reduction, minimum-saving reason, budget, integrity categories, memory, boundary operations, overhead and fallback. Static assets load from explicit routes. Light theme, dark-theme control, empty/loading/error states and responsive CSS are implemented; the live browser pass verified the light incident card and details dialog. **PARTIAL** — Narrow viewport was covered by CSS/UI-state tests but not manually resized in this run.

## E. Runtime applications

**TESTED** — IncidentCommander 8787, PayFlow gateway 8788 and ConverseLab gateway 8797 were simultaneously listening and returned healthy responses. Application-scoped state and context endpoints remained isolated.

## F. Browser verification

**TESTED** — Three independent browser tabs were opened after the regression: Commander `8787`, PayFlow `8788` and ConverseLab `8797`. Commander showed the resolved PayFlow incident, 18/18 verification and the AI Context card. PayFlow completed a successful checkout and displayed a transaction confirmation. ConverseLab completed a healthy Chat request and a typed Voice request with visible Knowledge, LLM, STT and TTS HTTP 200 pipeline steps. The Commander page showed incident `INC-37DA04A5`, AI Context `JSON`, 3,361 original/selected tokens, 0.0% reduction, integrity `PASS`, deterministic fallback delivery and the details dialog with all candidate rows and anchor counts. No browser console inspection API was available in the final CUA surface; static asset HTTP checks and the automated UI/HTTP tests passed.

## G. Actual benchmark table

**TESTED** — Measurements are stored in `CONTEXT-BENCHMARKS.json`.

| Fixture | JSON/original tokens | Selected | Selected tokens | Reduction | Integrity/fallback |
|---|---:|---|---:|---:|---|
| small | 5 | JSON | 5 | 0.0% | PASS / policy fallback |
| uniform | 4,102 | TOON | 2,518 | 38.6% | PASS / none |
| mixed | 4,894 | HYBRID | 3,212 | 34.4% | PASS / none |
| payflow hero | 2,534 | JSON | 2,534 | 0.0% | PASS / policy fallback |
| converselab hero | 11,857 | JSON | 11,857 | 0.0% | JSON fallback after TOON/HYBRID integrity rejection |

Encoding, profiling, validation and total optimization timings are retained per fixture in the JSON artifact; these are local measurement overheads, not live-model latency or cost claims.

## H. PayFlow E2E

**TESTED** — The live UNKNOWN connection-pool incident was approved through its exact plan. Verification passed 18/18 fresh requests, p95 142 ms, pool utilization 0%, healthy database and sandbox bank, and the incident resolved.

## I. ConverseLab E2E

**TESTED** — Hero HTTP tests exercised the isolated ConverseLab context path and existing conversation failure/recovery coverage. The service ended healthy on port 8797.

## J. Fallback demonstration

**TESTED** — PayFlow selected JSON because measured alternatives did not clear the configured utility threshold. ConverseLab's large hero payload demonstrates the stronger safety case: candidate integrity/round-trip rejection selects JSON and records the reason. No evidence is silently dropped.

## K. Tests

**TESTED** — Adaptive Context unit tests: 21/21 pass. Hero HTTP tests: 2/2 pass. Existing hardening suite: 36 test methods plus eight scenario rows from the previous acceptance run. The final full regression is recorded in `test-results.json`; rerunning `python run_tests.py` is the project-wide command.

## L. Safe judge claims

**TESTED** — The demo can claim deterministic context profiling, reversible candidate measurements, explicit integrity gates, application isolation, approval-gated repair, fresh verification and honest provider-not-configured labeling.

## M. Unsafe claims

**NOT IMPLEMENTED** — Do not claim production LLM savings, lower live-model latency, calibrated evidence probabilities, live external speech/LLM/bank integrations, remote GitHub operation, production authentication or money movement.

## N. Remaining limitations

**PARTIAL** — The local reference tokenizer is not a provider tokenizer; the provider call is unconfigured; TOON/HYBRID can lose to JSON on small or irregular payloads; strict numeric canonical integrity intentionally rejects unsafe round trips; the browser visual pass did not manually exercise every breakpoint; the root export has no single Git history. These are surfaced in the UI and documentation.
