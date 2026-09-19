# Public hackathon demo deployment

## Architecture

One Render Docker web service, one persistent `/data` disk, one replica. Only the optional authenticated gateway listens publicly. Commander, PayFlow and ConverseLab keep their internal loopback services and existing patch/evidence architecture. `deploy/launch.py` supervises all three processes; a child exit stops the deployment so the platform can restart it. Tini forwards container signals and reaps orphan processes.

Read [DEPLOYMENT-AUDIT.md](DEPLOYMENT-AUDIT.md) and [DEPLOYMENT-VERIFICATION.md](DEPLOYMENT-VERIFICATION.md) for limitations and actual verification. A public deployment is not verified by a local test.

## Local Development

Existing workflow is unchanged: `python run.py`, then Commander on 8787, PayFlow on 8788 and ConverseLab on 8797. It does not enable gateway authentication. `python run_tests.py` uses isolated temporary test data and ports.

For a separate deployment rehearsal, set the gateway configuration through your shell environment, choose unused internal/public ports and a separate IC_DATA_DIR, then run `python deploy/launch.py`. Never point a rehearsal at the active local runtime. PUBLIC_ORIGIN must exactly match the browser origin, without a trailing slash. HTTP is accepted only for localhost rehearsal. All public use requires HTTPS through the hosting platform.

## Deployment

1. Publish this deployment configuration to the existing GitHub repository using a normal non-forced push. Preserve any unrelated work.
2. Sign in at [Render dashboard](https://dashboard.render.com/). Select New → Blueprint and connect `Abinaya26012005/IncidentCommander`, branch main, using the root `render.yaml`.
3. Review the paid 1 CPU / 2 GB service and 1 GB disk charges shown by Render before provisioning. This is not a free-tier deployment. Do not enable replicas, previews or autoscaling. Automatic deploys are disabled to avoid interrupting a judge session.
4. Enter a new demo-only password of at least 16 characters for DEMO_PASSWORD in the platform secret field. Username is demo. Do not reuse a personal password, put credentials in Git, or paste cloud tokens into the application.
5. Deploy. The gateway uses Render's RENDER_EXTERNAL_URL. For a custom domain, set PUBLIC_ORIGIN to its exact HTTPS origin instead. The configured origin must be the URL judges use, because writes enforce Origin checks.
6. Inspect build/start logs. Confirm `/data` is writable by UID 10001; if the mounted disk permissions prevent startup, correct that designated mount's ownership in the platform environment without changing application source or exposing a root public process. Do not bypass authentication to troubleshoot.
7. Wait for `/healthz` to return HTTP 200 with ready true. Then complete the public acceptance checklist below. Container image construction and Linux runtime behavior must be checked on Render; local Windows tests cannot establish them.

The build installs existing pinned Python/context and TOON dependencies. Python 3.14 and Node 22 are container runtime choices; manifests/lockfiles are unchanged. Initial build downloads image layers, packages and tokenizer data. Subsequent build duration depends on platform caching. The image excludes personal `.git`, `.env`, runtime history and node_modules; the codec is installed inside the build from the lockfile.

## Environment Variables

Names only:

- DEMO_AUTH_ENABLED
- DEMO_USERNAME
- DEMO_PASSWORD
- PUBLIC_ORIGIN
- RENDER_EXTERNAL_URL
- PORT
- IC_BASE_PORT
- CL_BASE_PORT
- IC_DATA_DIR
- TIKTOKEN_CACHE_DIR

DEMO_AUTH_ENABLED is mandatory for the optional launcher. PUBLIC_ORIGIN overrides the platform URL when supplied. Internal base ports normally need no change. The launcher creates IC_CONTROL_TOKEN privately for inter-service patch authorization; it is not a deployment credential. Provider credentials are not inherited by application children in this public sandbox configuration. LIVE AI remains NOT CONFIGURED and prepared contexts remain honestly PREPARED — NOT SENT.

## URLs

On the actual Render-provided HTTPS origin:

| Path | Purpose |
| --- | --- |
| `/login` | Demo-only credentials |
| `/demo` | Judge navigation and end/reset session |
| `/` | IncidentCommander |
| `/payflow/` | PayFlow |
| `/converselab/` | ConverseLab |
| `/healthz` | Public aggregate readiness, no diagnostics |

Do not submit a guessed hostname or localhost address to the hackathon. Copy the assigned, verified HTTPS URL only after public acceptance passes.

## Demo Credentials and Session Safety

Credentials are configured through platform secrets. The repository contains no deployable password. Login grants one exclusive 20-minute lease across all three applications. A concurrent login receives “Demo currently in use”. Cookies are HttpOnly, SameSite Strict and Secure on HTTPS. Writes require the exact configured Origin. Login/actions/requests are rate limited, bodies bounded, and routes allowlisted. Internal patch APIs, telemetry internals, arbitrary paths, shell commands and environment files are not public routes.

The lease is absolute; background polling does not extend it. An expired lease denies further access. The next login resets both sandboxes before admitting a new judge. This is a serialized shared sandbox, not separate tenant storage. Completed reports and fictional transaction history remain visible to later judges. Use fictional input only. The gateway does not replace a managed edge firewall or protection against large-scale denial of service.

## Health Checks

`/healthz` reports readiness of the three gateway processes, intentionally staying ready during an injected application fault. Authenticated `/payflow/api/health`, ConverseLab state and Commander telemetry show actual dependency/application health. Fresh payments and voice requests provide functional verification.

## Reset

Use the existing application's Reset sandbox/Restore healthy baseline controls while investigating. `/demo` → End session and reset sandbox disables traffic and invokes both existing resets, then invalidates the cookie. It never deletes source or runtime Git repositories. Reset is refused during investigation/execution; wait and retry. Completed reports persist. Restart invalidates sessions and loses active in-memory incident state; next login restores a healthy sandbox. Do not restart during a judged incident.

## Public Acceptance Checklist

- Unauthenticated roots show login; private APIs reject anonymous requests. HTTP public access redirects to HTTPS at Render.
- Login works with configured demo credentials; incorrect login fails; a second browser cannot acquire the lease.
- Commander Applications, Mission Control, Demo Lab, Evidence Explorer, AI Context and Incident Reports load. No navigable/fetch URL points to judge localhost.
- PayFlow healthy payment succeeds. Inject Connection leak, observe real failed traffic and UNKNOWN incident, inspect all evidence including Git/source changes, RCA, risk and validated plan. Approve the sandbox fix; confirm 18 fresh successful requests and another successful payment.
- AI Context shows measured JSON/TOON/HYBRID candidates, integrity/round-trip result, fallback, memory, budget status, overhead and honest AI/provider status.
- ConverseLab chat and voice work with simulated-provider labels. Inject TTS failure; voice retains text and reports TTS HTTP 503. Investigate in Commander, approve, and verify 8 fresh requests and recovered voice.
- Cross-origin writes and internal `/patch/*`, `/.env`, `/.git/config` routes are rejected.
- End/reset session; next login starts with no active incident, healthy payment and healthy voice.
- Restart the Render service between sessions; completed reports persist, old session is invalid and a new login resets correctly.
- Observe resource usage and disk growth during rehearsal; do not change the six-slot pool or evidence safeguards to compensate for undersized hosting.

## Submission

Only after public acceptance: submit the actual public Commander URL, username demo and the separately configured demo-only password. Never supply platform credentials. Authentication/platform provisioning is a human handoff boundary if no authorized session is available.
