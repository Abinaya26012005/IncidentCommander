# Five-minute recording checklist

## Before recording

- [ ] Run `python run.py` from the project root.
- [ ] Confirm `http://127.0.0.1:8787/health`, `:8788/health` and `:8797/health` return 200.
- [ ] Open tabs in this order: Commander, PayFlow, ConverseLab.
- [ ] Commander application selector is PayFlow; no active incident is running.
- [ ] PayFlow payment succeeds once.
- [ ] ConverseLab Chat and typed Voice each complete.
- [ ] Commander shows `LIVE AI — NOT CONFIGURED` if no credentials are configured.
- [ ] Use browser zoom that keeps buttons readable; hide unrelated windows/notifications.

## PayFlow capture

- [ ] Commander → Demo lab → `Connection leak` → `Deploy & run traffic`.
- [ ] PayFlow failed customer request captured.
- [ ] Commander UNKNOWN incident captured.
- [ ] E-001 Metrics, E-002 Logs, E-003 Traces, E-004 Git and E-006/E-007 negative evidence captured.
- [ ] RCA says pool exhaustion is the symptom and missing cleanup is the root cause.
- [ ] AI Context card and `View details →` captured.
- [ ] `Review fix →` and MEDIUM-risk review captured before approval.
- [ ] `Approve sandbox fix` captured.
- [ ] Verification shows 18/18, p95, pool and dependency checks.
- [ ] PayFlow successful payment after recovery captured.
- [ ] Incident report/postmortem captured.

## ConverseLab mini-demo

- [ ] ConverseLab Chat healthy.
- [ ] ConverseLab Voice healthy.
- [ ] Demo lab → `TTS failure` → `Inject failure ↗`.
- [ ] Voice failure captured; text response remains visible.
- [ ] Commander selector switched to ConverseLab.
- [ ] TTS HTTP 503 and healthy STT/Knowledge/LLM evidence captured.

## Finish

- [ ] End on Commander Applications or resolved report.
- [ ] No fault remains active; both application health endpoints return healthy.
- [ ] Do not show terminals, source dumps, credentials, installation, long waits or GitHub push.
