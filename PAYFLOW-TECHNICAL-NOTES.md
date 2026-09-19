> Historical PayFlow implementation notes. For current multi-application behavior, read README.md and MULTIAPP-REPORT.md.

# IncidentCommander AI + PayFlow

A local incident-response lab with real HTTP failures, observed evidence, reviewed patches, and fresh recovery transactions. This upgrade preserves the existing Python architecture and completed incident history.

## Start

Requires Python 3.10+ and Git on PATH. Tests also use Node.js for the shared UI state module. No pip or npm packages are required.

```powershell
python run.py
```

Windows: double-click `start.cmd`. Keep the launcher open; Ctrl+C stops both applications.

- IncidentCommander: http://127.0.0.1:8787
- PayFlow: http://127.0.0.1:8788
- Set `IC_BASE_PORT` before launch to use another base port and the next four ports.

## The strongest demo: the judge changes the code

1. Make a successful PayFlow test payment.
2. Open `runtime/payflow-repo/payment_logic.py` in an editor. Remove the `try`/`finally` wrapper and `pool.release(connection)`; dedent the three statements inside `try` by four spaces. See DEMO-SCRIPT.md for exact before/after code.
3. Save. The local watcher detects the uncommitted change and reloads the restricted payment function. No scenario selection is needed.
4. In Demo lab, start background traffic. After failures appear, stop traffic. Retry PayFlow to show the customer failure.
5. Commander begins with `failure_type: UNKNOWN`. Inspect logs, traces, independent database/provider health, and E-004's working-tree diff.
6. Review the proposed patch, pre-apply checks, risk, file hashes, and rollback plan. Until approval, the broken source stays unchanged.
7. Approve the sandbox fix. Commander applies the exact validated edit, reloads, and sends 18 new checkout requests in two batches.
8. Show recovery checks, retry PayFlow, and open the postmortem. Runbooks and actual completed incidents provide retrieval context.

The live acceptance record is in `manual-acceptance.json`, summarized in `UPGRADE-REPORT.md`. This manual run did not call a scenario or reset endpoint.

## Eleven observed failure classes

| Demo lab case | Real sandbox mechanism | Diagnosis separates |
|---|---|---|
| Connection leak | Missing cleanup exhausts SQLite pool | Healthy DB versus saturated application pool |
| Bank outage | Local bank returns HTTP 503 | Provider failure versus database failure |
| Bad timeout | Timeout budget below bank response time | Healthy provider versus short request budget |
| Slow bank | Bank delays response by 1.6 seconds | Provider latency versus local processing |
| Database unavailable | DB facade rejects access | Availability versus connection capacity |
| Null error | Payment source dereferences None | Source exception versus dependency outage |
| Order failure | Order endpoint returns 500 | Order creation versus payment processing |
| Bank endpoint | Configured path returns 404 | Healthy provider versus wrong path |
| Small pool | One connection under concurrent traffic | Contention versus leaked connections |
| Gateway routing | Gateway target path returns 404 | Routing versus payment service health |
| Processing delay | Payment code waits 700 ms | Local latency versus dependency latency |

Every case has an actual HTTP lifecycle integration test. Scenario identifiers are control-plane inputs only; the investigator receives observations, not the selected scenario. Database outages are controlled facade failures, not an external database server being stopped. Bank recovery resets a local simulator; it is not a claim to repair an external provider.

## Local edit boundary

The watcher reads only `payment_logic.py` and `config.json` inside `runtime/payflow-repo`. It records hashes, file timestamps, working diff, status, recent commits, and reload errors. Changes are debounced; reload waits for active requests. Existing source is preserved at startup. Small supported manual changes really affect runtime. Unsupported Python constructs fail validation and surface as reload failure; this is deliberately not arbitrary Python execution.

The payment function retains `process(pool, charge, save)`. Supported constructs include assignments, calls to these capabilities, basic conditions, exceptions, and try/finally. Imports, loops, filesystem operations, shell access, indirect calls, and nested functions are rejected. Configuration uses nine typed, bounded keys and local endpoint paths.

## Patch and approval boundary

`PatchExecutor` accepts structured edits with `path`, `original_hash`, and full `content`. It rejects other fields and all files outside the two-file boundary, including `.env` and Commander itself. Python patches pass AST/syntax validation and success/provider-error cleanup tests in a fixed isolated Python subprocess before being offered. Configuration patches pass schema and bounds checks; fresh end-to-end verification follows application.

Approval is bound to a plan, Git revision, and source hashes. The backend uses a private per-launch control token; the model gets no shell or approval capability. Atomic file replacement, exact originals, proposed content, and results are retained in `runtime/patch-audit`. Rollback is a separate human action and refuses to overwrite newer edits. It restores the previous content, which may intentionally restore the fault.

## Optional real LLM

Without credentials, the product says **Offline evidence engine**. Supported cases use evidence rules and restricted repair generation. Copilot uses guided incident-grounded answers. An unfamiliar exception escalates with insufficient evidence instead of a fabricated repair.

Configure locally before launching:

```powershell
$env:OPENAI_API_KEY = '<your key>'
$env:OPENAI_MODEL = '<a Responses API model available to your account>'
python run.py
```

The Responses adapter sends bounded sandbox evidence (maximum 60,000 serialized characters), including the two allowlisted source/config files, with `store: false`. Keep these demo files free of secrets. It validates structured hypotheses, evidence citations, contradictions, and optional edits. Unknown-code patches still pass the same independent safety checks and human approval. Confidence is calculated in Python and is not a calibrated probability. API failure is visible and does not authorize an AI patch.

**IMPLEMENTED BUT NOT TESTED against a live provider:** no credentials were configured during acceptance. The adapter has a mocked transport contract test; do not present that test as a real model run. The manual acceptance used the offline evidence engine. Model-specific compatibility and unknown LLM-generated repair must be checked after configuring your provider.

## Interface

Both apps support complete dark/light tokens, a header toggle, and per-origin localStorage preference. Copilot starts closed, opens as a floating panel, expands, restores, minimizes, closes, and exits expanded mode with Escape. Closing/reopening preserves the current conversation; a page refresh starts a new conversation. Desktop and 390px mobile controls were checked in both themes. PayFlow shows order confirmation and recent process-local transactions, including verification traffic.

## Tests and reproducibility

```powershell
python run_tests.py
```

The suite uses ports 8897–8901 and temporary SQLite/Git data, leaving presentation ports and history untouched. It contains 20 test methods, with eight additional scenario breakdowns displayed as 28 result cards. Cards distinguish real HTTP integration, patch unit tests, UI state tests, and the mocked AI adapter. `test-results.json` records actual outcomes and durations. Refresh the browser to load a new report.

Original three lifecycle tests remain. Added coverage includes all eight new lifecycles, manual-edit UNKNOWN flow, insufficient evidence, no mutation before approval, rejection/staleness, forbidden patches, exact rollback, and UI state/theme contracts. Manual browser acceptance also checked customer failure/recovery and copilot controls.

## Architecture and limits

- Two Python processes: Commander and PayFlow. Four loopback HTTP services share the PayFlow process: gateway, order, payment, and bank simulator.
- Real SQLite transactions; bounded concurrent connection pool. Trace durations and metrics come from real local requests.
- Ten evidence categories: metrics, logs, traces, Git/local source, deployment/reload, dependencies, database, configuration, runbooks, and incident history.
- Active state and recent transaction display are process-local. Completed reports persist in `runtime/incidents.json`; SQLite payment records persist separately.
- Recovery checks 18 payments, zero failures, p95 below 500 ms, pool below 80%, and independent database/bank health, with a two-second inter-batch observation interval. This is sandbox verification, not production SLO certification.
- Restricted AST and bounded subprocess validation are not an OS security boundary for hostile code. Use only trusted local demo participants.
- No public hosting, multi-user authentication, cloud Git connector, external bank integration, production telemetry pipeline, or optional cache scenario is implemented.
- Reset restores the known healthy baseline and clears the active incident; completed history remains. Back up judge changes before reset.

## Project map

| File | Role |
|---|---|
| run.py / start.cmd | Launch both applications |
| payflow.py | Four HTTP services, SQLite pool, watcher/reload, telemetry |
| commander.py | Detection, evidence, lifecycle, approval, verification |
| investigator.py | Evidence-only diagnosis, 11 runbooks, optional structured LLM |
| source_provider.py | Bounded local source/Git observations |
| patch_safety.py / patch_probe.py | Restricted validation, apply, audit, rollback |
| common.py | Loopback HTTP/static helpers |
| web/ux.js / web/theme.css | Shared copilot state and theme tokens |
| web/app.js / web/index.html / web/style.css | Commander interface |
| web/payflow.html / web/payflow.js | Customer checkout and history |
| tests/ / run_tests.py | Integration, safety, UI, and adapter checks |

See DEMO-SCRIPT.md for presentation steps and UPGRADE-REPORT.md for exact tested/unverified scope.
