# Adaptive Context Intelligence: implementation note

The hardened baseline has 36 passing test methods. The project root is not a Git repository; nested runtime Git repositories contain approved recovery config edits. Preserve them. No prior context_optimization module, TOON dependency or tokenizer was found.

Reuse the dataclass/standard-library architecture, application isolation, normalized evidence, ai_reasoning.py's one Responses provider call, existing patch safety, and completed-incident persistence. The frontend is vanilla JavaScript/CSS, not React. No framework migration is needed.

Add one context_optimization package containing typed requests/results, profiling, tokenizer, serializers, structural/anchor integrity validation, budget calculation and deterministic routing. Use a maintained TOON implementation with decoding. Keep JSON as the safe baseline. Add measured benchmark fixtures and targeted unit/integration/UI tests.

Modify ai_reasoning.py at its bounded-evidence boundary. Measure INCIDENT_MEMORY and INVESTIGATOR_CONTEXT subsets with the same engine, then optimize the final RCA envelope. There is only one actual provider call; do not invent collector agents or extra calls. Without credentials, perform measurements and retain deterministic diagnosis; label the selected context as prepared but not sent.

Attach metadata-only optimization results to the existing incident; completed incidents persist through existing storage. Extend scoped report/API/Copilot surfaces and add an incident AI Context card/details modal in the existing frontend. Raw serialized context is not included in normal dashboard responses.

Risks: TOON dependency availability, tokenizer model mismatch, malformed data, overhead, Unicode/source-diff fidelity, application scope and model budget. Validate round trips and all data/anchors, redact only a copied LLM view, label tokenizer/context-limit uncertainty, reject over-budget sends, and fall back to validated JSON on optimizer failure. No lossy optimization or pool/patch/verification changes.

Verify serializers/router/guards with actual token counts, mock the real provider boundary, exercise both existing heroes with context metrics, rerun the entire regression suite, and inspect UI states/themes. Benchmarks report token counts and optimizer time separately from unmeasured live-model latency.
