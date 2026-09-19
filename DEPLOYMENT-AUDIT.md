# Deployment compatibility audit

Audit baseline: main at `48e62a6eab5a8e0bb530ddd3cdd2ab970cb07072`. Working tree was clean before deployment additions. Existing application source is preserved. No destructive Git operation is required.

## Findings

| Area | Existing implementation | Deployment consequence |
| --- | --- | --- |
| Processes | run.py launches PayFlow, ConverseLab and Commander; each hosts threaded internal HTTP services | Keep cooperating processes together; separate optional supervisor handles shutdown and child failure |
| Ports | Commander 8787; PayFlow 8788–8791; ConverseLab 8797–8802; IC_BASE_PORT/CL_BASE_PORT configurable | Internal loopback stays unchanged; only authenticated gateway binds 0.0.0.0:$PORT |
| Browser URLs | Root-relative assets/API fetches; localhost application links and ConverseLab Commander link | Gateway adapts presentation URLs and two JavaScript fetch prefixes; evidence URLs and source diffs remain unchanged |
| Transport | HTTP polling, no WebSockets/SSE | Ordinary bounded HTTP proxy is sufficient |
| Authentication | Local applications have no login; internal patch token generated at startup | Public gateway fails closed, uses environment credentials, HttpOnly/SameSite session and exact Origin checks on writes |
| Filesystem | IC_DATA_DIR contains SQLite WAL payments, runtime Git repositories, config/source edits, patch audit, completed incident JSON | Mount persistent /data; do not mount development runtime or personal Git metadata |
| Restart | Completed incident histories persist; active incidents, metrics, jobs and sessions are in memory | Restart ends the session; next successful login restores healthy sandbox through existing controls; completed reports remain |
| Git evidence | source_provider/adapters inspect generated runtime Git repositories | Install Git; runtime initializes its own demo author and commits, without upstream credentials |
| Remediation | Plan-bound approval; PatchExecutor validates registered paths/config and bounded AST | Preserve executor; never expose /patch/*, telemetry internals or arbitrary execution endpoints |
| Faults | PayFlow leak changes sandbox source; ConverseLab TTS changes runtime config; reload watchers apply changes | Writable runtime supports actual faults and repairs; no mock success added |
| Reset | Per-application engine locks, adapter reset and traffic control | Gateway disables traffic and invokes both existing resets at session start/end; refuses busy operations |
| Concurrency | Global state per application, shared by all browsers | One exclusive 20-minute lease, one replica. Another login receives “Demo currently in use”. Not tenant isolation |
| Context | @toon-format/toon 4.1.1 via Node; tiktoken 0.14.0; JSON evidence; fail-safe router | Install existing pinned manifests, pre-cache tokenizer. Preserve measurements, fallback and PREPARED—NOT SENT |
| Secrets | No cloud credential variable names found during audit | Public supervisor passes a minimal environment to applications; no private provider keys inherited |

Readiness /healthz checks process HTTP readiness, not absence of deliberately injected faults. Sandbox application health is available after login. Historical reports persist across judge sessions; use fictional inputs only. Expired sessions cannot act; reset runs when the next judge logs in, not immediately at lease expiration. Ending a busy session must be retried after the operation finishes.

## Selected Platform

Render Docker web service with one instance and a persistent disk. One HTTPS origin routes `/` to Commander, `/payflow/` to PayFlow and `/converselab/` to ConverseLab. This retains internal loopback communication and filesystem-based evidence without a distributed rewrite. A paid 1 CPU / 2 GB starting configuration provides headroom for Python processes, Node codec and tokenizer; actual resource use must be measured on the host before judging.

Render requires the public listener on its supplied PORT ([web services](https://render.com/docs/web-services)); [persistent disks](https://render.com/docs/disks) require paid service. Disk-backed deployments have downtime and cannot be horizontally scaled. Configuration follows the current [Blueprint specification](https://render.com/docs/blueprint-spec). Railway Docker plus a volume is also viable ([volumes](https://docs.railway.com/volumes)), but offers no reason to split these tightly coupled processes. Static hosting and an ephemeral free service do not meet runtime persistence requirements.

## Verification boundaries

Initial local checks: all three roots and /health endpoints returned HTTP 200. Detailed gateway, browser and regression results are recorded in DEPLOYMENT-VERIFICATION.md after testing. Original reported baseline was 59 tests; it is not a fresh test result.

Docker and deployment CLIs are unavailable on this Windows machine. No cloud deployment has been claimed. Platform login, paid resource provisioning, image build and public HTTPS acceptance remain required. The application is a bounded hackathon sandbox, not a general-purpose production service or multi-tenant security boundary.
