# Three websites

## IncidentCommander AI

- URL: `http://127.0.0.1:8787/`
- Purpose: shared incident-response control plane for PayFlow and ConverseLab.
- Screens: Applications, Incident list, Mission control, Evidence explorer, Service map, Incident reports, Demo lab, Validation suite, Runbooks.
- Health: `GET /health`.
- Interactions: application selector, incident review, evidence details, approval, validation, Copilot, theme toggle and AI Context details.
- Dependencies: Commander process plus the two application gateways for live probes.
- Telemetry: normalized metrics, logs, traces, health, source/config/deployment and history evidence.
- Healthy behavior: both applications appear scoped and healthy with no active incident.
- Hero behavior: UNKNOWN incident appears with evidence, RCA, constrained plan, approval and fresh verification.

## PayFlow

- URL: `http://127.0.0.1:8788/`
- Purpose: customer-facing local checkout application.
- Services: gateway 8788, payment 8789, bank 8790, order 8791.
- Health: `GET /health`; state/telemetry are available from the gateway API.
- Interaction: use the test card and Pay button; transaction history shows local activity.
- Demo controls: Commander Demo lab injects source/config faults; the customer page remains a normal checkout.
- Healthy behavior: successful local payment with traceable transaction.
- Hero behavior: connection leak causes failed payments and pool saturation; approved cleanup repair restores 18/18 fresh payments.
- Simulation: the bank is a deterministic local simulator; no money moves.

## ConverseLab

- URL: `http://127.0.0.1:8797/`
- Purpose: customer-facing conversational AI workspace with Chat and Voice test modes.
- Services: STT 8798, Knowledge 8799, LLM 8800, TTS 8801, conversation 8802.
- Health: each service exposes `/health`; gateway exposes `/api/state` and `/api/telemetry`.
- Interaction: Agent playground accepts chat and typed voice; Voice test and Demo lab expose intentional sandbox controls.
- Healthy behavior: chat answers and voice returns text plus simulated speech delivery.
- Hero behavior: TTS HTTP 503 leaves text generation successful while voice delivery fails; Commander identifies the boundary and verifies five voice plus three chat requests after repair.
- Simulation: STT, LLM and TTS are local demo providers; no microphone, audio hardware or external provider is claimed.

## Shared contract

PayFlow and ConverseLab use JSON application APIs. Commander owns normalized evidence, isolation, RCA, context optimization, policy, approval, execution, verification and postmortem. TOON is used only at Commander’s AI context boundary.
