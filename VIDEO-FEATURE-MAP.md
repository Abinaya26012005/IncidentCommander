# Video feature map

| Feature | Implementation | Website/page | UI evidence | Timestamp |
|---|---|---|---|---|
| Two monitored apps | `PayFlowAdapter`, `ConverseLabAdapter` | Commander → Applications | PayFlow and ConverseLab cards | 00:20 |
| Healthy payment | PayFlow `/api/pay` | PayFlow checkout | Payment successful | 00:40 |
| Connection leak fault | Commander sandbox scenario `leak` | Commander → Demo lab | Connection leak → Deploy & run traffic | 01:05 |
| UNKNOWN start | `ResponseEngine` detection | Commander → Mission control | Started as UNKNOWN | 01:30 |
| Metrics/logs/traces | Adapter collectors | Mission control / Evidence explorer | E-001, E-002, E-003 | 01:30 |
| Negative evidence | Dependency/database investigators | Mission control / report | Bank outage checked; Database server outage checked | 01:45 |
| Source/Git evidence | `source_provider.py` | Evidence explorer / report | E-004 Git changes and diff | 01:55 |
| RCA | Deterministic fallback/provider contract | Mission control | RCA title, explanation, evidence IDs | 02:00 |
| Evidence Strength | Response engine heuristic | Mission control/report | 95/100, heuristic not probability | 02:05 |
| Context profiler | `context_optimization/profiler.py` | AI Context details | Profile and repeated-key evidence | 02:15 |
| JSON/TOON/HYBRID | `serializers/__init__.py`, codec | AI Context details | Candidate comparison table | 02:20 |
| AUTO and threshold | `router.py` | AI Context details | Selected strategy and reason | 02:30 |
| Integrity/round trip | `integrity_guard.py` | AI Context details | PASS/N/A anchor rows | 02:35 |
| Token budget | `token_budget.py` | AI Context details | NOT CONFIGURED or measured budget | 02:40 |
| Safe fallback | Router failure policy | AI Context card/details | JSON fallback reason | 02:45 |
| Restricted remediation | `PatchExecutor`, `patch_safety.py` | Review fix dialog | Exact diff, guardrail, MEDIUM risk | 02:50 |
| Human approval | Commander approval route | Review fix dialog | Approve sandbox fix | 03:15 |
| Fresh verification | Adapter-specific `verify` | Mission control | 18/18, p95, pool, probes | 03:35 |
| Resolved state | Response engine lifecycle | Mission control | Recovery verified | 03:55 |
| ConverseLab independence | `ConverseLabAdapter` | ConverseLab + Commander | Separate pipeline and application scope | 04:05 |
| TTS boundary | ConverseLab TTS provider | ConverseLab Demo lab | TTS failure, HTTP 503 | 04:10 |
| Postmortem/memory | `reporting.py`, history | Commander → Incident reports | Read incident report | 04:30 |

## Exact current values to show

The verified PayFlow incident displayed JSON selected, 3,361 original and selected tokens, 0.0% reduction, Evidence Integrity PASS, `tiktoken:o200k_base (local reference; model not mapped)`, deterministic fallback and PREPARED — NOT SENT. The report displayed 18/18 fresh payments, 142 ms p95, 0% pool utilization, 95/100 heuristic evidence strength and MEDIUM risk. Treat these as the verified run’s values; do not narrate them if a new run displays different measured values.
