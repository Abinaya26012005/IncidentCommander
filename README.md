# IncidentCommander · PayFlow · ConverseLab

An application-agnostic incident-response prototype with two independent monitored applications. The shared control plane detects failures, gathers evidence, proposes restricted repairs, requests approval and verifies recovery with new requests.

## Run locally

Requires Python 3.10+, Git, and Node.js. Install the optional context measurement dependencies with `pip install -r requirements-context.txt` and the JavaScript TOON codec with `npm install`. Tested here with Python 3.14 on Windows.

```powershell
python run.py
```

Windows: double-click `start.cmd`. Keep the launcher running. Ctrl+C stops its three child processes.

| App/service | Default port |
|---|---|
| IncidentCommander | 8787 |
| PayFlow gateway / checkout | 8788 |
| PayFlow payment / bank / orders | 8789 / 8790 / 8791 |
| ConverseLab gateway / UI | 8797 |
| Conversation / STT / Knowledge / LLM / TTS | 8798 / 8799 / 8800 / 8801 / 8802 |

`IC_BASE_PORT` changes Commander's port; PayFlow uses the next four ports. ConverseLab defaults to base + 10 through base + 15; `CL_BASE_PORT` overrides its first port. `IC_DATA_DIR` optionally changes the runtime directory. Do not start a second launcher on occupied ports. The launcher creates the internal patch-apply token.

## Start your presentation here

1. Open Commander: http://127.0.0.1:8787
2. Show Applications: PayFlow and ConverseLab share the same control plane.
3. Open PayFlow: http://127.0.0.1:8788 — show a healthy demo checkout.
4. Open ConverseLab: http://127.0.0.1:8797 — show healthy chat and simulated voice.
5. Follow DEMO-SCRIPT.md for the manual source-edit PayFlow challenge and the TTS failure/recovery story.

## Read the handoff

- **BUTTON-GUIDE.md** — plain-language explanation of the screens and controls.
- **DEMO-SCRIPT.md** — two hero journeys and expected outcomes.
- **DEMO-GUIDE.md** — judge-facing story and 30-second Adaptive Context explanation.
- **RUN-DEMO.md** — exact startup, smoke-test, hero-flow and troubleshooting runbook.
- **DEMO-CHECKLIST.md** — pre-demo, hero, context and regression checklists.
- **ARCHITECTURE.md** — complete implementation architecture and Mermaid diagrams.
- **WEBSITES.md** — the three websites, ports, routes, dependencies and behavior.
- **JUDGE-QA.md** — technically accurate answers to common judge questions.
- **ONBOARDING.md** — application contract and how to connect a third app.
- **MULTIAPP-REPORT.md** — current 20-part implementation/verification report and limits.
- **ADAPTIVE-CONTEXT-REPORT.md** — Adaptive Context Intelligence implementation, benchmark, UI and runtime verification report.
- **CONTEXT-BENCHMARKS.json** — measured JSON/TOON/HYBRID candidates and timings.
- **test-results.json** — latest automated results, also shown in Validation suite.
- **MULTIAPP-ACCEPTANCE.json** / **MULTIAPP-PAYFLOW-ACCEPTANCE.json** — captured live acceptance evidence.

Older UPGRADE-REPORT, VERIFIED-DEMO-REPORT, manual-acceptance.json and PAYFLOW-TECHNICAL-NOTES describe the earlier PayFlow upgrade. They are historical, not the current multi-app acceptance report.

## Architecture

`commander.py` registers adapters and routes app-scoped requests. `response_engine.py` provides one shared lifecycle implementation. `investigator.py` correlates normalized evidence; `ai_reasoning.py` requests a bounded structured RCA/patch from the configured provider as the primary proposal, with explicit deterministic fallback. Backend scoring and patch validation remain authoritative. `application.py` defines the application boundary and shared plan policy. `patch_safety.py` and `source_provider.py` are reused by both monitored applications.

Adaptive Context Intelligence profiles the bounded evidence payload, measures reversible JSON, TOON and HYBRID serializations, validates full round trips plus path-aware anchors, and selects AUTO only when the measured utility clears the configured minimum saving threshold. It records tokenizer, bytes, tokens, timings, integrity, budget and fallback metadata in the incident timeline and `/api/context-optimization/*` endpoints. The browser's AI Context card and details dialog render those same backend measurements. Context is prepared once for INCIDENT_MEMORY, INVESTIGATOR_CONTEXT and the final RCA boundary; it is not sent to a live model unless credentials are configured. The TOON candidate uses the versioned `@toon-format/toon` reference codec; JSON remains the safe fallback when integrity or utility checks fail.

PayFlow retains its actual SQLite pool, HTTP checkout path, manual source watcher and 11 controlled failure classes. ConverseLab runs separately with six HTTP listeners and four reliable failure scenarios. Both adapters collect ten evidence categories and supply distinct recovery strategies. Application and incident IDs scope evidence, history, approvals and copilot context.

One process per monitored app hosts its HTTP services; this is not a container-per-service deployment. The browser uses plain HTML/CSS/JavaScript and displays backend-reported stage outcomes.

## Verify

```powershell
python run_tests.py
```

The latest full run is recorded in `test-results.json`; it includes the existing multi-application suite plus the Adaptive Context unit, UI-state and hero HTTP tests. Tests use isolated ports and temporary Git/SQLite data. They cover both applications, all four ConverseLab scenarios, the existing PayFlow cases, simultaneous incidents, application isolation, approval/hash restrictions, source edits, actual fresh verification requests, context integrity/budget/fallback behavior and shared UI-state behavior. The optional AI adapter is mocked in tests.

## What is real and what is simulated

**TESTED:** real localhost HTTP requests, delays and failure codes; bounded logs/metrics/traces; correlation IDs; independent health probes; actual local Git/config/source diffs; approval-gated patches; fresh recovery checks; completed incident persistence.

**SIMULATED:** external bank, ConverseLab STT/LLM/TTS, seeded support documents and clearly labeled example incident memory. Voice accepts typed text and simulates delivery; it does not generate or play audio. Retrieval uses keywords. No money moves.

**IMPLEMENTED BUT NOT TESTED live:** OpenAI structured RCA and patch proposals. Set both OPENAI_API_KEY and OPENAI_MODEL in the launching environment to configure the provider. No credentials were available for this acceptance run. The UI explicitly says LIVE AI — NOT CONFIGURED and DETERMINISTIC FALLBACK. Provider responses are mocked in contract tests; this does not prove a real external-model recovery. Evidence Strength is a heuristic, not a calibrated probability.

**NOT IMPLEMENTED:** remote GitHub provider, production authentication/authorization, live speech providers, microphone/audio playback, full third-party observability integrations, and a separate fifth LLM-outage demo. Provider interfaces and generic adapters are extension points, not claims of completed integrations.

## Operating boundaries

Use this as a local trusted demo. No production endpoints or credentials are needed. Source repair is deliberately restricted to the known PayFlow function/config and ConverseLab config schema. Unsupported changes can require engineer review. Reset overwrites local demo edits, while completed reports remain. Rollback can restore the original fault. Recent ConverseLab requests and current incident state are in memory; completed Commander reports persist. A restart does not resume an in-progress approval.

A single successful presentation cannot establish production reliability. The tests prove these two local integrations and the declared repair capabilities.

## Final hardening

The same backend report supplies the UI and Markdown download. Recovery comparisons use the saved incident evidence window and fresh verification requests/probes; missing observations are labeled. Failed verification stays OPEN, with Reinvestigate and local Escalate actions. Escalate records a local note only; it sends no notification. The latest acceptance evidence is in the sibling HARDENING-REPORT.md.
