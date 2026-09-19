# Your demo: what the controls mean

Open Commander at http://127.0.0.1:8787, PayFlow at http://127.0.0.1:8788 and ConverseLab at http://127.0.0.1:8797 after running `python run.py`.

## IncidentCommander

| Control | What it does / what to say |
|---|---|
| Application selector | Changes the current application's metrics, incident, evidence, topology, runbooks, reports and copilot context. It does not inject a fault. |
| Applications | Shows all registered applications and their observed status. Open workspace selects that application. |
| Incident list | Shows current incident records across applications. All applications / PayFlow / ConverseLab filter the list. Open application incident selects its workspace. Completed reports remain under Incident reports. |
| Mission control | Main investigation screen: customer impact, lifecycle, diagnosis, ruled-out causes, verification and timeline. |
| Test payment / Test voice conversation | Sends one real local request through the selected application. |
| Open PayFlow / Open ConverseLab | Opens the selected customer-facing product. |
| Evidence explorer | Lists the collected observations. Source filters narrow the list; a row or E-001-style citation opens raw evidence. |
| Service map / Explore | Shows the selected adapter's service graph and observed/configuration-derived degradation. The graph changes when you select another application. |
| Incident reports / View report | Opens the completed incident record and generated postmortem. These are actual recovery records; seeded examples are separately labeled in evidence. |
| Demo lab | Local experiments, direct-edit source path and traffic controls. Fault creation changes the app; diagnosis receives observations. |
| Deploy & run traffic | Injects the selected local fault and sends 14 real requests. Use a healthy baseline between experiments. |
| Start / Stop background traffic | Continuously sends demo requests until stopped. Stop before presenting a clean recovery check. |
| Reset sandbox | Restores the selected app's healthy demo source/config and clears its current incident/runtime activity. Completed reports are retained. Review the confirmation because this overwrites manual demo edits. |
| Runbooks | Shows the selected application's troubleshooting procedures. Retrieval during an incident uses observed failures/slow stages. |
| Validation suite | Displays the most recently generated test report. It does not run the suite; run `python run_tests.py` in a terminal to refresh results. There are 36 methods and 8 additional scenario breakdown rows, not 44 independent test methods. |
| Review fix | Opens the proposed diff, exact application/file scope, risk, revision, safety checks and recovery criteria. Opening it does not change source. |
| Approve sandbox fix | Records approval for that plan, applies the restricted edit and begins fresh recovery checks. Cross-app, stale-plan and changed-source approvals are rejected. |
| Reject patch | Rejects the current proposal without applying it. |
| Close review | Closes the patch review without executing or reinvestigating. |
| Reinvestigate | Collects evidence again for an open failed recovery; it does not approve a patch. |
| Escalate | Records a local engineer-review note and keeps the incident OPEN. No external notification is sent. |
| Roll back patch | Restores audited pre-patch content only if no newer edit exists. This can bring the original fault back; it is not the normal end of a successful demo. |
| How the evidence score was calculated | Explains the Python-calculated supporting factors. 95/100 is an evidence score, not a calibrated 95% probability. |
| A ruled-out cause | Opens the explanation and evidence for checking an alternative such as bank or STT outage. |
| Presentation guide | Opens the compact suggested demo sequence. |
| Light / Dark | Changes this app's appearance and persists the preference in this browser. |

### Copilot

**Ask Commander** opens the existing shared assistant. Its context label identifies the application and incident. Quick prompts explain evidence, changes, causes, alternatives and safety. The text field and Send submit a question within that scope. In offline mode answers are guided from the incident data; they are not unrestricted LLM conversation.

**Expand** opens the larger chat view; **Minimize** returns to the launcher; **Close** hides the panel. Escape steps down from expanded to compact, then to the launcher. Chat messages do not authorize patches: use Review fix and Approve sandbox fix. Each application's chat display is kept separate in the page session.

## ConverseLab

| Control | What it does / what to say |
|---|---|
| Overview | Summarizes recent conversations, success, latency and services. |
| Agent playground | Main chat/voice testing console with the answer and measured service pipeline. |
| Chat | Uses Knowledge → LLM; speech stages are skipped. |
| Voice / Voice test | Uses typed simulated spoken input through STT → Knowledge → LLM → TTS. It does not record your microphone or play generated audio. |
| Payment due date / Track an order / Return policy | Fills an example question; Send runs it. |
| Send message / Run voice test | Starts a real HTTP request. The UI displays pending state until the backend returns actual stage results. |
| KB citation beneath an answer | Opens the seeded document used as retrieval context. |
| Conversations | Shows recent in-memory requests, including Commander verification traffic. |
| Inspect trace | Reopens that request's answer, channel, IDs and measured pipeline. |
| Knowledge | Displays the four seeded support documents. This is deterministic keyword retrieval, not a vector database. |
| System status | Shows the services and health information reported by the backend. |
| Demo lab → Inject failure / Deploy configuration | Opens a confirmation for one of four changes: Knowledge HTTP 500, slow STT, TTS HTTP 503 or invalid prompt output. It does not itself send conversational traffic. |
| Inject experiment | Applies the selected local config change. Run two affected conversations promptly afterward so the monitor observes repeated degradation. |
| Restore healthy baseline | Restores ConverseLab configuration and clears recent runtime activity. Commander completed incident reports remain. |
| IncidentCommander link | Opens Commander with ConverseLab selected. |
| Light / Dark | Persists ConverseLab's independent theme preference. |

Pipeline checks are actual HTTP outcomes. TTS failure should show **TEXT GENERATED · VOICE DELIVERY FAILED**: a useful answer exists, but delivery did not succeed. Conversation/request/trace IDs connect that visible outcome to service logs. Provider badges explicitly identify simulated STT, LLM and TTS.

## PayFlow

Use only the prefilled demo card. **Pay** submits a local sandbox transaction; no money is charged or real card processed. The result includes a transaction/order reference on success or a support trace on failure. **Recent transactions** also includes recovery traffic, which explains the burst of successful rows after approval. Its theme toggle persists independently.

## A clear explanation for judges

“These are two independent applications. I can break checkout or voice delivery. The same Commander collects evidence, identifies the failing boundary, asks for a scoped approval and proves recovery with new requests. The external AI and speech providers are deterministic simulators; the HTTP failures, traces, config/source patches and verification are real.”

AI MODE records LIVE AI or DETERMINISTIC FALLBACK. Without credentials it also shows LIVE AI — NOT CONFIGURED. The patch review independently identifies AI GENERATED or DETERMINISTIC FALLBACK. Evidence Strength is a heuristic score. Before/after metrics compare recorded observations, not invented targets. View report and Download report share the backend report.
