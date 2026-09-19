# Deployment verification — 20 September 2026

## Status

Deployment package implemented and tested locally. **PUBLIC DEPLOYMENT BLOCKED — RENDER AUTHENTICATION REQUIRED.** The dashboard redirected to its sign-in page. No Render resources were provisioned, no paid transaction was made, and no public URL or public end-to-end success is claimed.

## Preserved baseline

Original application files, UI, manifests, lockfile, tests, local ports, six-slot pool, PatchExecutor, approval, isolation and context routing were not edited. Deployment is optional through new files. The only existing configuration change extends `.gitignore` to exclude environment variants while allowing a placeholder example.

Original 8787/8788/8797 roots and health endpoints returned HTTP 200. Browser checks confirmed Commander Applications, Mission Control, Demo Lab, Evidence Explorer, AI Context details and Incident Reports; PayFlow performed a successful new sandbox payment; ConverseLab rendered its existing Demo Lab. Existing local runtime data was not reset for deployment tests.

## Automated results

- Full `python run_tests.py`: **62 test methods passed in 284.382 seconds** (original 59 plus the initial 3 deployment tests).
- After the Windows child-environment correction and initial HTML-link correction, focused `python -m unittest discover -s tests -p test_deployment.py -v`: **4 tests passed in 26.193 seconds**. The fourth test confirms tiktoken remains available while demo/cloud/provider credentials are excluded from child processes. The entire now-63-method suite was not rerun after that focused correction.
- Real HTTP gateway tests used temporary runtime data and isolated ports: anonymous API rejection, wrong login, same-origin enforcement, concurrent judge lock, private-route denial, direct execution denial, expiration and rate limits.
- PayFlow gateway flow: healthy payment → leak → real HTTP 503 with trace retained → plan approval → resolved with 18 distinct verification traces → healthy payment.
- ConverseLab gateway flow: healthy voice → TTS fault → retained text and TTS HTTP 503 → approval → resolved with 8 fresh requests → healthy voice.
- AI Context API output compared structurally equal before/after gateway. Presentation link adaptation leaves evidence unchanged. Existing context regression tests passed, including round-trip/fallback and budget guards.
- End/reset invalidated access and cleared both current incidents through existing engine controls.

## Browser and supervisor rehearsal

An additional optional-launcher instance used public rehearsal port 10000, internal bases 9087/9097, and separate temporary runtime. It did not replace the user's live processes.

Browser verified: login; one-origin application navigation; Commander and prefixed PayFlow/ConverseLab assets; successful PayFlow checkout; asynchronous voice completion with all four stages HTTP 200 and simulated speech label; guarded PayFlow scenario dialog, live evidence and measured AI Context, proposed patch and risk, explicit approval, 18/18 recovery and saved report. Browser console check returned no errors for that rehearsal tab.

The first launcher rehearsal correctly displayed ESTIMATE rather than hiding unavailable BPE. Investigation found the restricted Windows environment omitted APPDATA, which is needed for this machine's user-installed tiktoken. The optional launcher now retains APPDATA/LOCALAPPDATA without credentials; the focused subprocess test confirms actual o200k_base BPE availability. Existing application tokenizer code was untouched. Docker installs the package globally and pre-caches o200k_base.

Supervisor failure test stopped one identified temporary child. All rehearsal service ports closed, while original 8787/8788/8797 remained open. Restart reused only the temporary runtime: previous browser session was rejected; new login succeeded; completed report INC-21A6CD47 remained available. This demonstrates local persistence semantics, not Render disk verification.

## Security and remaining acceptance

Candidate repository scan found no private-key headers, common GitHub/provider/cloud key patterns, candidate `.env` files or files larger than 10 MB. Passwords in tests are explicitly non-production placeholders. Real demo credentials must be set in platform secrets. Container COPY rules exclude development Git metadata, credentials and runtime. This bounded scan is not an exhaustive security certification.

Still required on the platform: Render login and paid-resource review; Docker build; Linux process/signal behavior; mounted-disk permissions; real HTTPS Secure-cookie/Origin behavior; public PayFlow and ConverseLab complete flows; public reset, restart/persistence and resource-usage checks. Docker is not installed here, so no local image-build success is claimed.

Use DEPLOYMENT.md for exact setup and the public acceptance checklist. Do not submit a localhost URL or an invented Render hostname.
