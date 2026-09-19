> Historical PayFlow-only report. See MULTIAPP-REPORT.md for the current two-application build and verification.

# Verified demo report

This file supersedes the earlier three-scenario report.

The upgraded application passed 20 automated test methods, including all eleven failure lifecycles. Eight scenario breakdowns are also shown, giving 28 result cards. Consult `test-results.json` for the most recent actual run, timestamp, scope, and durations.

Manual acceptance used a direct edit to `runtime/payflow-repo/payment_logic.py`, not scenario injection. It created UNKNOWN incident **INC-8804101**. Explicit browser approval applied the displayed patch. Recovery checks: **18/18 successful**, **150 ms p95**, **0% pool usage**, and healthy DB/bank probes. A separate customer payment then succeeded: **TXN-9C7E69D1**, order **ORD-73F10D**, **101 ms**.

Copilot controls were checked at desktop/mobile widths in both themes. Both apps' theme preferences survived refresh. Closing/reopening preserved the conversation.

The acceptance used the **offline evidence engine**. Live LLM reasoning and unknown model-generated patch execution remain **IMPLEMENTED BUT NOT TESTED** without configured credentials. The mocked adapter test is not evidence of a live provider run.

Read `UPGRADE-REPORT.md` for the requested 20-section disclosure, and `manual-acceptance.json` for captured incident/source/verification evidence.
