# Connect another application

IncidentCommander uses one response-engine implementation for all registered applications. Each application has an isolated engine instance and supplies an adapter; it does not supply a second RCA engine.

## Shared flow

```text
Application HTTP telemetry + independent probes + bounded source/Git observations
    → ApplicationAdapter.collect
    → normalize_evidence(application_id, incident_id)
    → shared investigator.diagnose / optional structured AI enrichment
    → shared build_plan and capability policy
    → explicit approval for exact application, plan, revision and hashes
    → adapter.apply → restricted PatchExecutor
    → adapter.verify → shared incident report and scoped memory
```

`ResponseEngine` owns detection, investigation, lifecycle, approval, verification dispatch, copilot context and report persistence. Adapters own service descriptions, evidence acquisition, permitted repair translations and application-specific recovery probes. The application and fault injector do not call the investigator or provide a fault label to it.

## Adapter contract

1. Create a class derived from `application.ApplicationAdapter` with a `MonitoredApplication` descriptor. Declare a unique ID, name/type, service graph, evidence providers, capabilities, remediation capabilities and UI metadata.
2. Implement `telemetry()`, `collect(incident, telemetry, history)`, `propose(rca, telemetry)`, `probe(origin)` and `verify(incident, emit)`. Supply `get_health()` and dependency probes as appropriate, plus metric and topology presentation methods. Return measured observations, not diagnoses from your fault injector.
3. Provide the telemetry shape used by the engine: timestamp, metrics with error_rate/p95, bounded events with timestamp/latency/ok, logs, deployment, local_source and config. Preserve request correlation IDs. Adapt another service's native output at this boundary.
4. Emit evidence records with ID, application_id, incident_id, source_type, source_name, service, timestamp, summary, metadata, raw_reference and relevance. Evidence IDs such as E-001 are incident-local: retain both scope IDs when storing or joining them.
5. Declare only the safe repair actions your adapter supports. `propose` translates an evidence-derived action/component into bounded edits. The shared policy refuses undeclared actions. Validation must enforce paths, schema/code restrictions and functional behavior before the plan reaches approval.
6. Implement a restricted application-side patch endpoint. Reuse `PatchExecutor` with an explicit file allowlist and validator. Apply checks the launch token, expected Git revision and original file hashes. Never add arbitrary shell execution as a remediation.
7. Verification must send NEW requests, validate the actual product output, probe dependencies and return checks, unique trace IDs, fresh_requests, passed and application_id. Service health alone is insufficient.
8. Register the adapter in `commander.py`'s `adapters` list. Start the independent application with the launcher or your own process manager. The UI selector and cards derive from the registry. Provide its `ui` fields: request, plural, http_services and optional scenarios.
9. Add real HTTP tests for healthy behavior, failure localization, negative evidence, repair/verification and simultaneous incidents. Prove that its plan cannot be approved in another application's context.

## Current implementations

| Concern | PayFlow | ConverseLab |
|---|---|---|
| Independent process | `payflow.py` | `converselab/server.py` |
| HTTP services | 4 plus SQLite | 6 |
| Adapter | `payflow_adapter.py` | `converselab_adapter.py` |
| Editable files | payment_logic.py, config.json | config.json |
| Recovery probes | 18 payments, pool, database, bank | 5 voice + 3 chat, complete valid output, latency, 4 dependencies |
| History file | runtime/incidents.json | runtime/converselab-incidents.json |

The renamed application/dependency test demonstrates that generic dependency diagnosis does not depend on ConverseLab's name or selected fault scenario. It does not prove arbitrary third-party applications work without adapter development. Novel failure types may need additional shared observation rules or reviewed AI proposals.

## Scope limits

This is a local prototype, not a production tenant/security boundary. There is no remote authentication, distributed storage, Kubernetes or external observability collector. Services within each demo application use separate HTTP listeners in one process. Completed Commander reports persist; ConverseLab recent requests are bounded in-memory records. Active engine state is not resumed after restart.

`LocalGitProvider` is an alias of the tested local source/Git provider. A remote `GitHubProvider` is NOT IMPLEMENTED. Optional structured OpenAI analysis exists but was tested with a mock, not a live provider. ConverseLab STT/LLM/TTS are explicitly simulated; external-provider interfaces are extension points, not installed live integrations.
