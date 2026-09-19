# Run the demo

## Prerequisites

Install Python 3.10+, Git and Node.js. From this directory run `pip install -r requirements-context.txt` and `npm install`. Do not set OpenAI credentials for the deterministic demo; the UI should say `LIVE AI — NOT CONFIGURED`.

## Start

```powershell
cd C:\Users\Admin\Documents\Codex\2026-09-17\i-x20\outputs\incidentcommander
python run.py
```

Expected URLs are printed by the launcher. Open all three:

```powershell
Start-Process http://127.0.0.1:8787
Start-Process http://127.0.0.1:8788
Start-Process http://127.0.0.1:8797
```

## Health checks

```powershell
Invoke-RestMethod http://127.0.0.1:8787/health
Invoke-RestMethod http://127.0.0.1:8788/health
Invoke-RestMethod http://127.0.0.1:8797/health
```

## Healthy smoke tests

On PayFlow press the test Pay button and confirm a successful transaction. On ConverseLab send one Chat message and one typed Voice request; confirm a text answer and simulated voice delivery.

## PayFlow hero

1. Open Commander Demo lab and choose PayFlow connection leak.
2. Deploy the fault and run traffic until the pool saturates and payments fail.
3. Open the UNKNOWN incident; review logs, metrics, traces, source/Git and healthy database/bank probes.
4. Open AI Context and explain measured JSON/TOON/HYBRID candidates, integrity and fallback.
5. Review RCA and restricted `Restore connection cleanup` plan.
6. Approve the plan.
7. Show execution and verification: 18/18 fresh payments, p95 under 500 ms, pool under 80%.
8. Return to PayFlow, make a successful payment, then open the postmortem.

## ConverseLab hero

1. Send healthy Chat and typed Voice requests.
2. Open Demo lab, choose TTS failure, deploy and send Voice requests.
3. Show text still succeeds while simulated voice delivery fails.
4. In Commander select ConverseLab and review the UNKNOWN incident.
5. Show TTS failure with healthy STT, Knowledge and LLM negative evidence.
6. Open AI Context and explain the selected candidate or safe JSON fallback.
7. Approve the bounded config restoration.
8. Show five fresh Voice and three fresh Chat successes, then return to ConverseLab.

## Reset and stop

Use each application’s Reset/restore control after a rejected or abandoned demo. Confirm `/health` and no active incident before presenting. Press Ctrl+C in the launcher terminal to stop all children. If a port is busy, stop the old launcher rather than starting a duplicate.

## Troubleshooting

- `ERR_CONNECTION_REFUSED`: start `python run.py` and wait for the printed health-ready state.
- Static asset 404: verify Commander is serving `/context-ui.js` and `/context.css`; restart only after checking the port owner.
- Missing dependency: rerun `pip install -r requirements-context.txt` and `npm install`.
- Provider credentials unavailable: keep deterministic fallback; do not add fake credentials.
- TOON codec failure: candidate rejection and JSON fallback are expected safety behavior.
