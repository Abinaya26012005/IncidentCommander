# Multi-application upgrade and acceptance report

Verified locally on 19 September 2026. This report supersedes the earlier PayFlow-only reports. Status labels describe evidence, not just source-code presence.

## 1. EXISTING ARCHITECTURE FOUND

**TESTED.** The original Python/HTML/JavaScript Commander monitored PayFlow through four HTTP services and SQLite. It already had real source/Git watching, restricted patch validation, approvals, rollback, fresh payment verification, reports, copilot and themes. The baseline 20-test suite passed before refactoring. Single-application state, evidence collection, metric rendering and payment verification were the main coupling points.

## 2. GENERIC ABSTRACTIONS ADDED

**TESTED.** Added MonitoredApplication, ApplicationAdapter, registry-based routing, normalized application/incident scope and a shared ResponseEngine. Reused the investigator, confidence computation, patch executor and report flow. Each application has independent lifecycle state and scoped persistence. The same diagnosis function passed a test with the application and failing dependency renamed.

## 3. PAYFLOW CHANGES

**TESTED.** Moved PayFlow-specific collection, repair translation, presentation and verification into its adapter. Preserved existing source/config behavior, SQLite transactions, 11 fault classes, manual edits and completed incident history. Existing regression tests still pass. A new live manual source edit produced INC-8DB18E4A, which recovered after browser approval.

## 4. CONVERSELAB ARCHITECTURE

**TESTED.** A separately running application with its own frontend, backend process, runtime config repository and HTTP gateway. It continues serving independently of Commander's UI. The frontend starts a real asynchronous request and polls actual backend stage outcomes; it does not synthesize completion timers. It shares no PayFlow business state.

## 5. CONVERSELAB SERVICES

**TESTED:** gateway, conversation orchestration, STT, Knowledge, LLM and TTS have separate HTTP listeners, health endpoints, timings, logs and spans. They run in one ConverseLab process rather than six isolated processes. **SIMULATED:** the external-provider behavior behind STT/LLM/TTS; typed speech input and delivery markers replace audio. Knowledge uses real local keyword retrieval over four seed documents.

## 6. OBSERVABILITY

**TESTED.** Actual request counts, channel success/failure rates, measured latency, service logs, request spans and correlation IDs. Each app feeds ten evidence categories into the shared model. ConverseLab adds independent probes for all six listeners. Git/config evidence contains actual local changes. Recent activity is bounded; completed reports persist separately. Health is current, whereas service error percentages summarize retained logs and can include previous failures.

## 7. INCIDENTCOMMANDER INTEGRATION

**TESTED.** Application selector, application cards, app-specific metrics/topology, filterable current incident list, runbooks and reports. Both resolved live incidents were visible together. Cross-application evidence and approval attempts are rejected. Application scope is a logical local boundary; it is not a production tenant authorization system.

## 8. FAILURE SCENARIOS

**TESTED.** All four ConverseLab scenarios complete their failure → evidence → approval → repair → verification paths: Knowledge HTTP 500, STT latency, TTS HTTP 503, and invalid prompt/config output. A direct filesystem prompt edit is also covered. TTS and PayFlow manual source edits were demonstrated in the browser. **NOT IMPLEMENTED:** the optional fifth standalone LLM-outage/rate-limit demo.

## 9. RCA FLOW

**TESTED.** Incidents start UNKNOWN. Shared correlation examines runtime logs/spans, measured degradation, dependency probes, changes, runbooks and memory. Fault creation does not pass scenario IDs or an injected cause into incident evidence. Generic dependency/latency/output-contract rules coexist with preserved PayFlow rules in one investigator. **IMPLEMENTED BUT NOT TESTED live:** optional structured OpenAI enrichment; its parser, citation validation and failure behavior were tested using mocks. The demonstrated mode is explicitly Offline evidence engine.

## 10. NEGATIVE EVIDENCE

**TESTED.** During TTS failure, STT, Knowledge and LLM had successful actual spans and independent healthy probes. Generated text survived while voice delivery failed; a browser chat request succeeded during the same outage. Knowledge failure stops before generation. Healthy endpoint probes are distinguished from proof that a stage was actually reached. Runbook retrieval was corrected to score failed/slow observations, with regression assertions for TTS versus Knowledge. Seeded history is matched by component and error code.

## 11. REMEDIATION

**TESTED.** The same policy and restricted executor enforce declared capabilities, allowed files, validation, exact application/plan context, deployment revision and content hashes. Repairs wait for approval. ConverseLab modifies only its config.json; PayFlow's source/config capabilities are preserved. Shared rollback safety tests reject newer human changes and restore exact audited content. **IMPLEMENTED BUT NOT TESTED separately:** a ConverseLab-specific end-to-end rollback after a completed repair; the shared executor rollback is covered by existing tests.

## 12. VERIFICATION

**TESTED.** PayFlow's live manual-edit recovery passed 18/18 fresh payments, p95 151 ms, pool 0%, and bank/database probes. The final ConverseLab recovery passed 5/5 fresh voice and 3/3 fresh chat requests, complete valid pipelines, eight unique traces and four dependency probes; maximum observed request latency was 507 ms against an 1800 ms budget. Verification dispatch comes from the selected adapter. A successful patch alone cannot resolve the incident.

## 13. COPILOT INTEGRATION

**TESTED.** Reused the existing copilot. Automated tests check app-scoped answers; the browser confirmed a ConverseLab TTS explanation and correct incident/component label. Compact, expanded, Escape and close behavior were exercised. Context switching keeps each app's displayed chat separate. Copilot conversation does not grant patch approval. Offline answers are guided from collected evidence.

## 14. DARK/LIGHT MODE

**TESTED.** Commander and ConverseLab were inspected in light/dark modes. ConverseLab preference survived reload; the shared existing theme persistence/state tests passed. PayFlow's theme behavior remains covered by the existing shared-state tests and its checkout worked in the browser. **IMPLEMENTED BUT NOT TESTED comprehensively:** every new screen at all mobile breakpoints. ConverseLab's attempted viewport override did not change the existing tab's 1440-pixel width, so it is not counted as a successful mobile check. Commander was also viewed at 480 pixels without document overflow.

## 15. TEST RESULTS

**TESTED.** Final full regression run: 29 test methods passed in 165.202 seconds. The UI shows 37 result rows because eight scenarios have additional breakdown rows. JavaScript syntax checks passed for both updated frontends. Browser console inspection returned no errors for Commander or ConverseLab during the final check. Tests use isolated HTTP ports and temporary Git/SQLite data.

## 16. END-TO-END RESULTS

**TESTED.** PayFlow: healthy browser transaction TXN-68992AA2 → direct source edit → failed browser checkout, support trace 79abf2eb173d → INC-8DB18E4A → browser approval → 18 recovery payments → successful browser retry TXN-52482C56. ConverseLab: healthy chat/voice → injected TTS config failure → generated text with HTTP 503 delivery → unaffected chat → approved repair → eight fresh recovery requests → successful voice retry. A final rerun, INC-FC087584, confirmed corrected RB-CONV-003 retrieval and recovery. Both apps were HEALTHY at final API inspection. Exact evidence is saved in the two MULTIAPP acceptance JSON files.

## 17. FEATURES ACTUALLY TESTED

**TESTED.** Healthy product requests; all four ConverseLab failures; preserved PayFlow failures; independent scoped incidents; simultaneous incidents; cross-app rejection; mixed evidence rejection; direct source/config changes; restricted patch checks; fresh adapter-specific verification; generic renamed-dependency diagnosis; history labels; actual browser failure/approval/retry; app switching; copilot; selected UI pages, themes and trace inspection. These tests establish the two demonstrated integrations, not arbitrary third-party compatibility.

## 18. FEATURES SIMULATED

**SIMULATED.** Bank provider, external speech/LLM providers, voice delivery, seed support-account content and explicitly labeled historical example SEED-CONV-001. Local fault injection controls modify real demo behavior. HTTP failures, delays, service boundaries, source/config changes and recovery checks are real local execution. No audio or real payments are generated.

## 19. FEATURES NOT VERIFIED

**IMPLEMENTED BUT NOT TESTED live:** optional OpenAI enrichment and provider extension interfaces against external systems. **NOT IMPLEMENTED:** remote GitHubProvider, live STT/TTS integration, audio playback/recording, production observability connectors, production auth and a fifth LLM-outage scenario. No third real application was integrated. Mobile ConverseLab behavior, other browsers/platforms and load/soak reliability were not fully verified. LocalGitProvider is the implemented alias; the project did not contain the claimed remote GitHub provider.

## 20. REMAINING RISKS

The prototype is designed for trusted local demonstrations. One in-progress incident is maintained per application; compounded faults and arbitrary source changes can require engineer review. Shared diagnosis supports observed patterns, not unrestricted root-cause discovery. Source capabilities are deliberately narrow; a third application needs an adapter and tests. A restart preserves completed reports but loses current in-memory incident/request state. Recent metrics age out and can differ from the incident's saved evidence. Rollback can restore a fault. Large machine-load spikes can affect latency budgets. The internal approval checks do not replace production identity, access control, isolation or durable orchestration.

The defensible claim is: **PayFlow and ConverseLab are independent local systems integrated through one shared evidence, investigation, policy, remediation and verification architecture.**
