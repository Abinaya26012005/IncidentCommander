# Five-minute voice-over

Target edited duration: about 4:55. Read at a measured pace; pauses are visual, not extra narration.

## 00:00–00:20

“When production fails, detecting the failure is often easier than proving why it failed. This demo follows one incident from a healthy payment to a real local regression, evidence-backed diagnosis, approved repair and fresh verification.”

## 00:20–00:40

“IncidentCommander is one control plane for two independent applications: PayFlow and ConverseLab. Each application keeps its normal JSON APIs and telemetry. Application adapters provide the application-specific evidence and verification, while investigation, policy, approval and reporting are shared.”

## 00:40–01:05

“I’ll start with a normal PayFlow checkout. This is a local sandbox: the transaction path is real HTTP, the bank is simulated, and no money moves. A successful payment establishes the healthy customer journey before the incident.”

## 01:05–01:30

“In Commander’s Demo Lab I deploy the featured Connection leak experiment and run real traffic. The customer symptom is failed checkout and a saturated pool. The investigation starts as UNKNOWN; it is not handed the expected root cause or repair.”

## 01:30–02:15

“Commander correlates metrics, logs, traces, source and Git changes, deployment data, dependency probes, database health, runbooks and incident memory. The bank and database are healthy, so they are negative evidence. The exhausted pool is the symptom. The missing connection cleanup in the deployed payment function is the root cause.”

“That distinction matters operationally: a correlated error is an observation, not a conclusion. The timeline keeps the original signals, the supporting evidence IDs and the alternatives that were ruled out, so a reviewer can follow the decision without seeing hidden chain-of-thought.”

## 02:15–02:50

“Before the reasoning boundary, Adaptive Context Intelligence profiles the collected RCA context and measures JSON, TOON and Hybrid candidates. It records real tokens, bytes, timing, tokenizer, budget and integrity. The selected representation is the highest valid utility under policy. If a candidate changes a critical anchor or fails round-trip validation, it is rejected and the system safely falls back. TOON is an LLM-context representation here; it does not replace application APIs or storage. Efficiency never overrides evidence integrity.”

## 02:50–03:35

“The proposed repair is a narrow source change: restore connection cleanup. The review shows the exact diff, registered scope, validation checks and MEDIUM risk. Commander does not blindly execute an LLM recommendation. Human approval is required, and the button is Approve sandbox fix. The restricted executor checks hashes and policy before applying the change.”

## 03:35–04:05

“Patch applied does not mean incident resolved. Commander now sends fresh application traffic and checks latency, pool utilization, database health and bank health. Recovery is verified only after all checks pass: eighteen of eighteen fresh payments succeed, p95 is below the limit, and the pool returns to zero percent.”

## 04:05–04:30

“Now I switch to ConverseLab, an independent conversational application. Chat and typed Voice use a different topology. In its Demo Lab I inject TTS failure. Text generation still succeeds, but speech delivery returns HTTP 503. Healthy STT, Knowledge and LLM steps provide negative evidence while Commander isolates TTS through the ConverseLab adapter.”

## 04:30–04:50

“The final incident report preserves the timeline, evidence IDs, RCA, remediation, approval, verification and context measurements. It is incident memory for this local sandbox, not a claim of production reliability.”

“The same report also records provider disclosure and recovery metrics, so the audience can distinguish a verified local result from a promise about an external production system.”

## 04:50–04:55

“From alert to evidence-backed recovery: one Commander, two applications, controlled action and verified results.”
