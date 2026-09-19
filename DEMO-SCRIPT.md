# Two applications. One incident-response platform.

## Prepare

Run `python run.py`. Open Commander on 8787, PayFlow on 8788 and ConverseLab on 8797. Use the application selector in Commander throughout. Confirm both applications are healthy and stop any background traffic. Reset a selected sandbox only when you intend to discard its local demo edits/current incident. Reports persist.

Explain the boundary: external bank and speech/LLM providers are local simulators. HTTP requests, observed failures, source/config changes, approvals and recovery tests are real. The demo works offline without an API key.

## Story 1: the judge breaks checkout (about 3 minutes)

1. Submit the prefilled test card in PayFlow. Show the successful transaction and order reference.
2. In Commander choose PayFlow → Demo lab. Open the actual source path shown there: `runtime/payflow-repo/payment_logic.py`.
3. Replace its healthy function with this small supported edit:

```python
def process(pool, charge, save):
    connection = pool.acquire()
    result = charge()
    save(connection, result)
    return result
```

4. Save. The watcher reloads the uncommitted change. Start background traffic in Commander, wait for failures, then stop it. Alternatively send at least nine test payments. The six-slot pool gradually fills because connections are never returned.
5. Retry PayFlow so the customer visibly gets a failed checkout. Commander begins with UNKNOWN; there was no scenario button in this path.
6. Open the source diff, error logs and failed trace. Contrast pool exhaustion with healthy database and bank probes.
7. Review fix. Point at the exact `try/finally` cleanup patch, PayFlow-only scope, original hashes, validation and approval requirement. The patch has not run yet.
8. Approve sandbox fix. Show 18 fresh payments, latency below 500 ms, pool below 80%, healthy bank/database and a resolved incident.
9. Retry the checkout yourself. Open the report. Say: “Recovery is proven with new transactions, not assumed because a patch applied.”

The tests cover rejecting or invalidating stale approvals and exact rollback. Do not end the presentation by rolling back: that intentionally restores the faulty code.

## Story 2: text exists, but voice fails (about 3 minutes)

1. Show the same Commander Applications page, then open ConverseLab. Its product UI is deliberately different.
2. In Agent playground send “When is my payment due?” as Chat, then Voice. Show Knowledge/LLM for chat and STT/Knowledge/LLM/TTS for voice. Read the explicit simulated-provider label.
3. ConverseLab → Demo lab → TTS failure → Inject failure → Inject experiment. This changes real local config; it does not tell the investigator the answer.
4. Voice test: send two voice requests promptly, within roughly 15 seconds. Both should show valid generated text followed by TTS HTTP 503 and “TEXT GENERATED · VOICE DELIVERY FAILED.” Try Chat: it should still succeed.
5. In Commander choose ConverseLab. Inspect the UNKNOWN incident, failed TTS spans and logs, the independent unhealthy TTS probe, and healthy STT/Knowledge/LLM observations. Open RB-CONV-003. Historical examples are marked seeded; actual completed incidents remain distinct.
6. Review the one-file config patch. Approve it. The shared engine calls the ConverseLab verification strategy: five fresh voice and three fresh chat requests, valid complete pipelines, bounded latency and healthy dependency probes.
7. Return to ConverseLab and run another voice request. Show successful delivery simulation and a new trace ID. Open Commander's completed report.
8. Return to Applications: both systems recover through one shared architecture.

Commander Demo lab also has Deploy & run traffic for each application; it injects the fault and automatically produces 14 real requests when you want a quicker rehearsal.

## Optional evidence challenges

- **Knowledge failure:** both channels fail at retrieval; generation is never reached. After approval both channels recover.
- **STT latency:** voice takes over 2.4 seconds; chat bypasses STT. Diagnosis uses the slow span and health evidence, not an outage assumption.
- **Bad prompt:** directly change `runtime/converselab/repo/config.json` prompt_version from v1 to v2-broken, save, and send two requests. The diff is uncommitted; the endpoint remains healthy while output validation fails. Approval restores v1.
- **Simultaneous failures:** the automated test proves distinct incidents and rejects cross-application approvals. Fixing one app must leave the other affected until its own approval.

Reset between independent rehearsals. Do not inject a second fault into an already active incident for the main presentation.

## Defensible closing sentence

“IncidentCommander is an application-agnostic Agentic SRE prototype. PayFlow and ConverseLab are independently running systems integrated through the same evidence, investigation, policy, remediation and verification architecture. Each adapter supplies its application's observations and safe recovery checks.”

If asked whether arbitrary systems work immediately: “A third application needs an adapter, declared capabilities and tests. We do not need a separate incident engine. Unknown failure mechanisms may still require engineer review or additional shared rules.”
