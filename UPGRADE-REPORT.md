> Historical PayFlow-only report. See MULTIAPP-REPORT.md for the current two-application build and verification.

# Upgrade and acceptance report

Implementation preserved the existing local Python application. Status labels below distinguish actual execution from code-only or simulated capabilities. Full machine-readable evidence: `test-results.json` and `manual-acceptance.json`.

## 1. EXISTING ARCHITECTURE FOUND

**TESTED.** Two Python processes, Commander on 8787 and PayFlow's four HTTP services on 8788–8791; SQLite, local Git, plain HTML/CSS/JS, three existing incident lifecycles, approval, 18-payment verification, persistent completed reports. All eight original tests passed before changes and remain in the final suite. Existing runtime history was preserved.

## 2. FILES MODIFIED

**TESTED.** `common.py`, `run.py`, `payflow.py`, `commander.py`, `investigator.py`, `run_tests.py`, `tests/test_system.py`, `web/index.html`, `web/app.js`, `web/payflow.html`, `web/payflow.js`. Documentation updated: `README.md`, `DEMO-SCRIPT.md`, and `VERIFIED-DEMO-REPORT.md`. Runtime source was deliberately edited and repaired for acceptance; `config.json` gained compatible default keys. `test-results.json` contains the executed suite report.

## 3. FILES ADDED

**TESTED.** `source_provider.py`, `patch_safety.py`, `patch_probe.py`, `tests/test_upgrade.py`, `web/ux.js`, `web/theme.css`. Added acceptance/documentation artifacts: `manual-acceptance.json`, `UPGRADE-REPORT.md`. Patch audit files are created under runtime. The portable archive excludes private runtime history and credentials.

## 4. COPILOT FIX

**TESTED.** Closed/panel/expanded transitions; floating launcher; visible close, minimize, and expand/restore; Escape restores the panel. Conversation survives close/reopen. Browser checks covered desktop and 390px mobile in dark/light. Shared state transitions also have automated tests. Conversation refresh persistence is **NOT IMPLEMENTED**; theme refresh persistence is separate and tested.

## 5. DARK/LIGHT MODE

**TESTED.** Shared tokens cover navigation, cards, charts, dialogs, copilot, evidence, diffs, statuses, checkout, and transaction history. Both applications' theme choices persisted after refresh. Representative browser views were inspected in both themes; exhaustive cross-browser visual regression is **NOT IMPLEMENTED**.

## 6. PAYFLOW EXPANSION

**TESTED.** Preserved four purposeful HTTP services and real SQLite persistence. Added bounded concurrency, configurable dependencies/routes/pool/processing delay, source reload, exception source frames, customer order confirmation, and recent transaction history. **SIMULATED:** bank, database availability facade, and controlled injected outages.

## 7. RCA SCENARIOS IMPLEMENTED

**TESTED.** Eleven full lifecycles: connection leak, bank outage, bad timeout, bank latency, database unavailable, null code regression, order failure, bank endpoint error, pool sizing, gateway routing, local processing latency. Original three remain. Optional cache scenario is **NOT IMPLEMENTED**. Rules inspect observable errors, source, config, traces, and independent probes; scenario identifiers are not sent to the investigator.

## 8. LOCAL SOURCE CHANGE SUPPORT

**TESTED.** Allowlisted local files, hashes, mtimes, working diff, uncommitted status, recent commits, changed lines, debounce, controlled reload, and reload error reporting. Actual manual filesystem edit caused actual failures without a scenario endpoint. Small supported edits only; unrestricted repository/Python execution is **NOT IMPLEMENTED**.

## 9. UNKNOWN INCIDENT SUPPORT

**TESTED.** Detection begins with UNKNOWN. Manual cleanup regression resolves from evidence. An unfamiliar RuntimeError produces logs/source frames, one additional evidence pass, INSUFFICIENT EVIDENCE, and no executable proposal without a configured LLM. **IMPLEMENTED BUT NOT TESTED:** real-provider reasoning for previously unknown code.

## 10. PATCH GENERATION

**TESTED.** Evidence-driven cleanup and known source/config repair proposals, exact diff display, original hashes, syntax/AST/config checks, isolated success/error cleanup probes. **IMPLEMENTED BUT NOT TESTED:** live model-generated patch on an unknown regression. **SIMULATED:** adapter transport in its contract test; it is explicitly labeled mocked.

## 11. PATCH SAFETY

**TESTED.** Two-file allowlist; traversal/secret/system/Commander paths rejected; no model shell; unsupported constructs, commands, imports, loops, and indirect execution rejected; stale hashes and invalid behavior rejected; exact originals/results audited; atomic replacement and rollback that protects newer edits. This is a restricted trusted demo, not a hardened OS sandbox.

## 12. HUMAN APPROVAL

**TESTED.** No source mutation before approval; explicit browser approval in manual acceptance; rejected and stale plans cannot apply. Risk is determined outside the model. Separate rollback action. A private per-launch token protects the internal apply endpoint. Multi-user identity/authorization is **NOT IMPLEMENTED**.

## 13. ACTUAL REPAIR

**TESTED.** Manual incident INC-8804101 applied the displayed cleanup patch to the real file, reloaded the function, and restored payments. Source contents were read back and verified. Original-content rollback was exercised in automated integration tests.

## 14. VERIFICATION

**TESTED.** Manual run: 18/18 fresh checkout requests passed, p95 150 ms against <500 ms, pool 0% against <80%, independent DB/bank probes healthy. Two batches include a two-second observation interval. Failed verification remains open. This short sandbox window does not establish production reliability.

## 15. TEST RESULTS

**TESTED.** 20 automated methods, with eight additional scenario breakdown rows (28 UI cards). Includes original eight tests, all eleven incident lifecycles, manual edits, rollback, forbidden patches, insufficient evidence, UI state, and mocked adapter validation. See the final timestamp/durations in `test-results.json`. JavaScript syntax was also checked. Live OpenAI network calls are excluded.

## 16. MANUAL END-TO-END TEST RESULT

**TESTED.** A: copilot/theme controls and persistence. B: healthy customer TXN-75F251EC. C: direct source edit removed cleanup; nine HTTP requests yielded three failures; separate UI checkout failed (reference 8892a76b02a3). D: UNKNOWN incident INC-8804101 collected E-001 through E-010 without scenario input. E: RCA cited collected evidence. F: validated patch displayed, source unchanged. G: explicit browser approval repaired source. H: 18/18 recovery checks. I: separate customer TXN-9C7E69D1, order ORD-73F10D, 101 ms. J: complete automated regression suite passed. The manual run used the offline evidence engine.

## 17. FEATURES THAT ARE REAL

**TESTED.** HTTP services, SQLite writes/pool, source changes, local Git diffs/history, watch/reload, measured metrics/logs/traces, independent probes, evidence citations, human approval, validated edits, audit/rollback, fresh verification, persisted completed reports, local themes/copilot state, and actual executed test results.

## 18. FEATURES THAT ARE SIMULATED

**SIMULATED.** Local bank/payment provider; controlled dependency outages and injected delay; store/card/customer data; mocked provider transport in one test. Guided copilot and default evidence engine are deterministic implementations, not a live LLM. No real money is moved. There is no fabricated incident history.

## 19. FEATURES NOT YET VERIFIED

**IMPLEMENTED BUT NOT TESTED.** Live Responses API/model compatibility and a previously unknown regression repaired by a real model. No OPENAI_API_KEY/OPENAI_MODEL were configured for this acceptance. **NOT IMPLEMENTED:** optional cache case, live cloud connectors, public deployment, cross-browser automation, production load/security qualification.

## 20. REMAINING RISKS

**TESTED scope:** trusted loopback demo with two supported files and bounded edits. Active incidents/recent displayed transactions are process-local, while completed reports and SQLite records persist. Rollback may restore the original fault. Host load may exceed the strict 500 ms recovery threshold; the app correctly leaves that incident open. Multi-file replacement is sequential with compensating restoration, not a filesystem transaction. A local external editor can race file operations. AST restrictions are not production isolation. Keep demo source/config free of secrets before enabling cloud analysis. General-purpose arbitrary-code repair, production auth/telemetry, long observation windows, and stronger isolation are **NOT IMPLEMENTED**.
