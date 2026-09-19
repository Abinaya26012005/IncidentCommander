# IncidentCommander AI — exact five-minute video demo guide

**Status: TESTED** — This guide is based on the current browser UI and verified local runtime. It does not change application behavior. Target edited duration is **4:55**, leaving five seconds under the five-minute limit.

## Verified websites and tab order

| Tab | Website | URL | Use |
|---|---|---|---|
| 1 | IncidentCommander AI | `http://127.0.0.1:8787/` | Control plane, evidence, RCA, approval and reports |
| 2 | PayFlow | `http://127.0.0.1:8788/` | Customer checkout and visible impact |
| 3 | ConverseLab | `http://127.0.0.1:8797/` | Independent Chat/Voice application |

Commander’s actual Applications page says: “One control plane. Different worlds.” It displays healthy PayFlow with four HTTP services and healthy ConverseLab with six HTTP services. The application selector changes scope; it does not merge evidence.

## Pre-recording setup

From the project root:

```powershell
python run.py
```

Confirm:

```powershell
Invoke-RestMethod http://127.0.0.1:8787/health
Invoke-RestMethod http://127.0.0.1:8788/health
Invoke-RestMethod http://127.0.0.1:8797/health
```

All must return healthy. Open the three tabs in the order above. In Commander, select PayFlow and open Applications once so both application cards are visible. In PayFlow, press `Pay ₹3,599.00 →` once and wait for `✓ Payment successful`. In ConverseLab, leave the Agent playground ready; a healthy Chat and Voice request can be captured as a separate raw clip.

Begin the hero only when:

- Commander shows no active incident and PayFlow is healthy.
- PayFlow checkout is loaded and its payment form is visible.
- ConverseLab Demo lab shows no active TTS fault.
- No background traffic is running.
- The browser has no unrelated notifications or tabs visible.

Do not reset source with destructive Git commands. If an earlier demo left a fault active, use the application’s own `Reset sandbox` or `Restore healthy baseline` controls described below.

## Exact five-minute timeline

| Time | Duration | Website / URL | Page | Starting state | Action / exact click | Expected result | Screen focus | What to show | What not to show | Voice-over | Overlay | Technical claim / evidence | Transition / backup |
|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|
| 00:00–00:20 | 20s | Commander / 8787 | Applications | Three services healthy | Click `Applications` | PayFlow and ConverseLab cards both say `HEALTHY` | Center cards | One control plane, two apps | Sidebar detail | “When production fails, detecting it is easier than proving why.” | `ONE COMMANDER — MULTIPLE APPLICATIONS` | Adapter cards and shared-engine callout | If cards take time, use the preloaded Commander overview clip |
| 00:20–00:40 | 20s | Diagram / architecture doc | Ecosystem diagram | `ARCHITECTURE.md` ready as B-roll | Show Mermaid ecosystem diagram or Commander Applications callout | Shared engine and two adapters are legible | Crop to diagram | PayFlow → adapter, ConverseLab → adapter, shared engine | Raw source files | “Applications keep normal JSON APIs; Commander shares investigation, policy, approval and reporting.” | `SHARED ENGINE · APPLICATION ADAPTERS` | `ARCHITECTURE.md` ecosystem diagram | If diagram is unavailable, stay on Applications and narrate |
| 00:40–01:05 | 25s | PayFlow / 8788 | Secure checkout | Checkout form visible | Click `Pay ₹3,599.00 →` | `✓ Payment successful`, transaction and order IDs appear | Payment result | Healthy customer journey | Card values close-up; no real data | “This is a local sandbox. HTTP is real, the bank is simulated, and no money moves.” | `HEALTHY PAYMENT` | PayFlow `/api/pay` response and transaction history | If result is delayed, hold until confirmation; do not cut before it appears |
| 01:05–01:30 | 25s | Commander / 8787 | Demo lab | PayFlow healthy | Click `Demo lab`; in featured `Connection leak`, click `Deploy & run traffic`, then `Deploy experiment` in the confirmation dialog | Traffic is sent and Commander begins observing degradation | Featured scenario card and toast | `UNKNOWN UNTIL INVESTIGATED`, connection leak description | Hidden scenario labels beyond the visible card; terminal | “The fault is controlled, but the investigation starts without being handed the expected root cause.” | `PRODUCTION INCIDENT · UNKNOWN ROOT CAUSE` | `data-scenario="leak"` dispatches a real local experiment and 14 requests | If modal is missed, click `Deploy & run traffic` again and confirm |
| 01:30–02:15 | 45s | Commander / 8787 | Mission control | Incident detected; page polling every 1.3s | Return via `Mission control`; wait for incident card; optionally click `Evidence explorer` | RCA, timeline, evidence sources and negative checks appear | RCA card and timeline | E-001 Metrics, E-002 Logs, E-003 Traces, E-004 Git, E-006/E-007 health | Long raw JSON | “The bank and database are healthy, so healthy dependencies become negative evidence. The pool is the symptom; missing cleanup is the root cause.” | `METRICS + LOGS + TRACES + SOURCE` | Actual report lists 57.1% failures, 100% pool, healthy bank/database and source diff | If incident still investigates, cut waiting and resume on RCA card |
| 02:15–02:50 | 35s | Commander / 8787 | Mission control → AI Context | AI Context card visible | Scroll to `AI Context`; click `View details →` | Dialog shows candidate table and integrity/budget/memory sections | Dialog center | JSON/TOON/HYBRID rows, selected strategy, tokens, integrity, fallback | Do not claim TOON always wins; do not show fake numbers | “Adaptive Context measures candidates at the AI reasoning boundary. Efficiency never overrides evidence integrity.” | `JSON vs TOON vs HYBRID · INTEGRITY FIRST` | Verified run: JSON 3,361→3,361, 0.0%, PASS, local reference tokenizer, PREPARED — NOT SENT | If selected values differ, read the current visible values only |
| 02:50–03:35 | 45s | Commander / 8787 | Review fix dialog | Incident status `awaiting_approval` | Click `Review fix →`; show diff/risk; click `Approve sandbox fix` | Approval records; status moves through execution to verification | Diff, MEDIUM risk and button | Exact cleanup diff, policy, validation checks, approval control | Do not show hidden source editing or shell | “Commander does not blindly execute an LLM recommendation. The repair is scoped, validated, risk-assessed and human-approved.” | `HUMAN APPROVAL REQUIRED` | `Review the proposed fix`, `MEDIUM RISK`, `Approve sandbox fix`; PatchExecutor/hash policy | Record the pre-approval frame separately; if approval is already complete, use a clean earlier clip |
| 03:35–04:05 | 30s | Commander / 8787 → PayFlow / 8788 | Mission control recovery | Verification running or complete | Keep Commander on `Recovery verification`; then switch to PayFlow and press payment once | 18/18, p95, pool and dependency checks pass; PayFlow payment succeeds | Verification card then PayFlow result | `RECOVERY VERIFIED`, 18/18, 142 ms, 0% pool, `PayFlow is back` | Patch-applied screen alone | “Patch applied does not mean incident resolved. Fresh application traffic proves recovery.” | `PATCH APPLIED ≠ RESOLVED` → `FRESH TRAFFIC VERIFICATION` | PayFlow adapter requires 18 fresh requests, p95 <500 ms, pool <80%, healthy DB/bank | If a check fails, stop and use recovery section; never narrate resolved |
| 04:05–04:30 | 25s | ConverseLab / 8797 → Commander / 8787 | Agent playground / Demo lab | ConverseLab healthy | In Agent playground run Chat and Voice clips; click `Demo lab`; on `TTS failure`, click `Inject failure ↗`; run Voice | Text remains valid while speech delivery returns HTTP 503 | Pipeline steps and TTS card | STT/Knowledge/LLM 200, TTS 503, simulated-provider disclosure | Do not record a second full approval lifecycle | “The same engine handles a different application through an adapter. Healthy upstream components isolate TTS.” | `ONE COMMANDER — MULTIPLE APPLICATIONS` | ConverseLab Demo lab says text succeeds but speech returns HTTP 503; pipeline is real local HTTP | If time is tight, use the prepared TTS raw clip and switch Commander scope only |
| 04:30–04:50 | 20s | Commander / 8787 | Incident reports | PayFlow resolved | Click `Incident reports`; first `Read incident report ↗` | Report dialog shows timeline, evidence, RCA, remediation, approval, verification and AI Context | Report sections | `Recovery verified`, evidence IDs, postmortem and context section | Download dialog or huge markdown | “The report preserves the incident timeline and evidence-backed recovery as local incident memory.” | `POSTMORTEM + INCIDENT MEMORY` | `report()` output and persisted history | If report list is long, use first resolved card only |
| 04:50–04:55 | 5s | Commander / 8787 | Applications | Both apps healthy | Return to `Applications` | Both cards show `HEALTHY` | Two cards | Closing state | Any active fault | “From alert to evidence-backed recovery: one Commander, two applications, verified results.” | `FROM ALERT TO VERIFIED RECOVERY` | Applications page health cards | End on this frame |

## EXACT CLICK-BY-CLICK RECORDING MAP

### SHOT 01 — two applications

Open `http://127.0.0.1:8787/`. Click `Applications`. Record 00:00–00:20. Keep the two application cards centered. Stop when both show `HEALTHY` and the shared-engine callout is readable.

### SHOT 02 — architecture

Show the ecosystem Mermaid diagram in `ARCHITECTURE.md` as an edited B-roll frame, or keep Commander Applications visible. Record 00:20–00:40. Do not browse source code.

### SHOT 03 — healthy PayFlow

Switch to `http://127.0.0.1:8788/`. Click `Pay ₹3,599.00 →`. Wait for `✓ Payment successful`. Record 00:40–01:05. Crop to the payment result and order/transaction IDs.

### SHOT 04 — inject the PayFlow failure

Switch to Commander. Click `Demo lab`. In the featured `Connection leak` card click `Deploy & run traffic`. In the confirmation modal click `Deploy experiment`. Record the launch and cut the actual wait. The lab states that 14 real application requests are sent.

### SHOT 05 — show impact and investigation

Click `Mission control`. Wait for an incident card. Show `Started as UNKNOWN`, degraded metrics, RCA, `E-001`, `E-002`, `E-003`, `E-004`, `Bank outage checked` and `Database server outage checked`. Use `Evidence explorer` for a readable evidence list if needed.

### SHOT 06 — source and evidence

Click `Evidence explorer`; open the `Git changes` row, then return to Mission control. Show the source diff and evidence ID. Do not claim the hidden scenario was passed to the investigator; the visible timeline says it inspected measured signals and changes without a fault label.

### SHOT 07 — Adaptive Context

On Mission control scroll to `AI Context`. Click `View details →`. Keep the dialog open. Show candidate rows for JSON, TOON and HYBRID, tokens, bytes, integrity, round-trip status, utility, memory, boundary operations and fallback. Read the actual selected values on screen.

### SHOT 08 — remediation approval

Close details. When status is `awaiting_approval`, click `Review fix →`. Show the `Review the proposed fix` dialog, exact diff, `MEDIUM RISK`, validation badges, policy and success criteria. Record a clean frame before clicking `Approve sandbox fix`; then click it and capture the status transition.

### SHOT 09 — verified recovery

Stay on Mission control. Show `Recovery verification`, `ALL CHECKS PASSED`, `18/18 successful`, p95, pool and dependency probes. Switch to PayFlow and click the Pay button again. End on successful checkout and Commander `PayFlow is back. Recovery verified.`

### SHOT 10 — ConverseLab mini-story

Switch to ConverseLab. In Agent playground click `Chat`, send the prefilled `When is my payment due?`, wait for `COMPLETED`; click `Voice`, click `Run voice test`, wait for `Speech synthesis HTTP 200`. Click `Demo lab`; in `TTS failure` click `Inject failure ↗`. Return to playground, select Voice, click `Run voice test`; show text plus `speech delivery failed` and TTS HTTP 503. Use Commander’s application selector to choose ConverseLab and show its scoped incident/evidence if already detected.

### SHOT 11 — report and close

In Commander click `Incident reports`; on the first resolved PayFlow card click `Read incident report ↗`. Show the report sections and `AI Context Optimization`. Close it and click `Applications` for the final two-healthy-app frame.

## WHERE EVERY IMPORTANT FEATURE LIVES

| Feature | Website | Page/section | How to reach it |
|---|---|---|---|
| App overview | Commander | Applications | Click `Applications` |
| PayFlow health | PayFlow / Commander | Checkout / Mission control | Open 8788 or Commander PayFlow |
| Incident detection | Commander | Mission control | Click `Mission control` after traffic |
| Metrics | Commander | Evidence explorer / E-001 | Click `Evidence explorer`, then Metrics |
| Logs | Commander | Evidence explorer / E-002 | Open Logs row |
| Traces | Commander | Evidence explorer / E-003 | Open Traces row |
| Source changes | Commander | Evidence explorer / E-004 | Open Git changes row |
| Dependency health | Commander | Mission control/report / E-006 | `Bank outage checked` and report Evidence |
| Database health | Commander | Mission control/report / E-007 | `Database server outage checked` |
| RCA | Commander | Mission control | RCA card under incident journey |
| Evidence Strength | Commander | Mission control/report | `95 /100`, heuristic not probability |
| AI Context | Commander | Mission control | Scroll to `AI Context` |
| JSON candidate | Commander | AI Context details | Click `View details →` |
| TOON candidate | Commander | AI Context details | Candidate comparison row |
| HYBRID candidate | Commander | AI Context details | Candidate comparison row |
| Token budget | Commander | AI Context details | `Token Budget` section; may be NOT CONFIGURED |
| Integrity Guard | Commander | AI Context details | `Evidence Integrity` section |
| Remediation | Commander | Review fix dialog | Click `Review fix →` |
| Risk | Commander | Review fix dialog/report | `MEDIUM RISK` in verified PayFlow run |
| Approval | Commander | Review fix dialog | `Approve sandbox fix` |
| Verification | Commander | Mission control | `Recovery verification` |
| Postmortem | Commander | Incident reports | `Read incident report ↗` |
| ConverseLab health | ConverseLab | Agent playground/System status | `Services connected`, pipeline cards |
| ConverseLab TTS incident | ConverseLab + Commander | Demo lab + scoped Commander | `TTS failure` → `Inject failure ↗`; select ConverseLab |
| Copilot | Commander | Ask Commander drawer | Optional; skip main video |

## Adaptive Context visual storyboard

Use the details dialog, not a raw JSON dump. The verified PayFlow dialog showed:

1. `Optimization decision · JSON` and the policy reason.
2. Candidate comparison rows: JSON, TOON and HYBRID with tokens, bytes and integrity.
3. `Token Budget NOT CONFIGURED` plus reservations.
4. `Evidence Integrity PASS` with PASS/N/A categories.
5. Incident memory and boundary operations: INCIDENT_MEMORY, INVESTIGATOR_CONTEXT and RCA.
6. Measured overhead and tokenizer label.

If a new run selects TOON or HYBRID, highlight the selected row and current measured reduction. If it selects JSON or rejects a candidate, say that the fallback is the safety feature. TOON is not used for PayFlow/ConverseLab REST or storage.

## Remediation safety storyboard

The review dialog directly exposes the exact diff, `MEDIUM RISK`, registered-path policy, deployment SHA precondition, validation badges, rollback statement and success criteria. The executor details are backend-controlled and **NOT DIRECTLY VISIBLE IN UI** beyond the policy text; explain them with the overlay `RESTRICTED EXECUTOR · NO SHELL ACCESS` rather than showing code execution.

## ConverseLab storyboard

Healthy: Agent playground → Chat → `Send message ↗`; Voice → `Run voice test ↗`; pipeline shows Knowledge/LLM and STT/Knowledge/LLM/TTS HTTP 200. Failure: Demo lab → `TTS failure` → `Inject failure ↗`; Voice request shows valid assistant text plus `Simulated speech delivery failed`, pipeline shows TTS HTTP 503. The Demo lab itself says controls do not send an answer to Commander; Commander receives observed telemetry later.

## Postmortem and Copilot

The final 20 seconds should show `Incident reports` → first resolved PayFlow card → `Read incident report ↗`. This report includes incident impact, timeline, evidence IDs, root cause, remediation, risk, approval, verification, recovery metrics and AI Context Optimization. Historical reports remain in the list and are the implemented incident memory.

Copilot is available from the `Ask Commander` drawer and is covered by UI tests, but it is **not recommended for the main five-minute video**: it adds a second interaction surface after the stronger evidence/RCA story. Use it as B-roll with a question such as “What context optimization was selected for this incident?” only if the primary recording is complete.

## Waiting periods and editing

| Step | Real wait | Recording treatment |
|---|---:|---|
| Commander polling after launch | 1.3-second refresh cadence; usually several seconds | Record launch, cut repeated polling, resume on incident |
| PayFlow background traffic | 14 concurrent requests from scenario action | Capture one failure frame; cut the wait |
| Investigation/context preparation | Usually seconds locally | Keep final RCA and AI Context; cut spinner |
| Approval/apply/reload | Seconds | Keep pre-approval, click, then resume on verification |
| PayFlow verification | Two batches, 12 + 6, about 2 seconds observed | Keep the final checks; use a short time-lapse if needed |
| ConverseLab TTS detection | Two affected voice requests recommended | Capture one failure and one Commander evidence frame |

Never imply a result before the underlying action has completed.

## What not to record

Do not spend time on package installation, long startup terminals, GitHub push, source-folder browsing, raw database/runtime files, full test execution, every evidence tile, raw JSON dumps, or a second complete ConverseLab approval lifecycle. Put architecture and test detail in the diagram, README, `ARCHITECTURE.md` and Q&A. Do not show secrets, local paths, hidden scenario payloads or provider credentials.

## Zoom and cropping plan

- Applications: crop both health cards and shared-engine sentence.
- PayFlow: crop payment result, not the entire form.
- Incident: crop application, severity, UNKNOWN status and affected service.
- Evidence: crop source type, evidence ID and one-line summary.
- RCA: crop root-cause title, explanation and evidence chips.
- AI Context: crop selected strategy, tokens, reduction and integrity; then the details rows.
- Remediation: crop diff, risk and approval button.
- Verification: crop 18/18, p95, pool, dependency probes and `RECOVERY VERIFIED`.
- ConverseLab: crop pipeline statuses and TTS HTTP 503.
- Report: crop headings and recovery/context sections.

## If something goes wrong while recording

- **Commander does not load:** check `8787/health`; confirm `python run.py` is still running. Do not start a duplicate launcher on an occupied port.
- **PayFlow does not load:** check `8788/health`; keep Commander open and retry only after service health returns.
- **ConverseLab does not load:** check `8797/health`; do not claim the mini-demo until its services are connected.
- **Port occupied:** identify the existing launcher/process and use it if healthy; stop it only through normal process controls before restarting.
- **PayFlow starts unhealthy or pool is nonzero:** open Commander Demo lab and click `Reset sandbox`, wait for healthy, then make one successful payment.
- **Stale incident appears:** use `Reset sandbox`; completed reports remain intentionally in incident memory.
- **Connection leak already active:** do not inject again; reset, verify the payment and pool, then begin.
- **TTS fault already active:** ConverseLab Demo lab → `Restore healthy baseline`; verify Voice HTTP 200 before recording.
- **Incident does not trigger:** confirm the scenario actually deployed, start the lab’s background traffic, and wait for repeated real failures. Do not invent an incident.
- **Evidence has not appeared:** wait for Commander polling; open Mission control again. If still absent, stop the clip and use a previously verified raw clip.
- **AI Context missing:** confirm an incident has been investigated; refresh Mission control and check `/context-ui.js`/`/context.css` load 200.
- **Approval missing:** the incident is not yet `awaiting_approval` or the plan failed validation. Do not bypass it.
- **Verification not starting:** check that approval completed; stay on Mission control until fresh checks appear.
- **Voice request does not complete:** check ConverseLab health and use typed input; do not claim audio was generated.
- **Browser stale:** reload the tab or navigate back to the exact localhost URL; preserve the healthy runtime.

## Safe claims and claims to avoid

Safe: one Commander monitors two independent local applications; RCA cites collected evidence IDs; healthy dependencies are used as negative evidence; repairs are restricted and approval-gated; fresh traffic verifies recovery; Adaptive Context measures JSON, TOON and Hybrid at the AI boundary; invalid candidates fall back safely.

Avoid: TOON always saves tokens, TOON improves reasoning automatically, TOON replaces JSON, TOON fixes HTTP limits, Evidence Strength is probability, live production banking/speech/AI, arbitrary application repair, zero hallucinations, or production readiness.

## Final recording checklist

- [ ] 8787, 8788 and 8797 healthy.
- [ ] Commander Applications shows PayFlow and ConverseLab.
- [ ] PayFlow healthy payment captured.
- [ ] Connection leak launched from Demo lab.
- [ ] Failed request and UNKNOWN incident captured.
- [ ] Metrics/logs/traces/source/negative evidence captured.
- [ ] RCA and evidence strength captured.
- [ ] AI Context card/details captured with current measured values.
- [ ] Review fix and MEDIUM risk captured before approval.
- [ ] `Approve sandbox fix` captured.
- [ ] Fresh verification and 18/18 captured.
- [ ] PayFlow succeeds after recovery.
- [ ] ConverseLab Chat/Voice healthy clip captured.
- [ ] TTS failure and Commander scope captured.
- [ ] Incident report/postmortem captured.
- [ ] End with both applications healthy.

**VIDEO DEMO DOCUMENTATION READY**
