# Judge Q&A

1. **What problem?** Evidence-backed incident response from detection through approved repair and fresh verification.
2. **Why agentic AI?** It observes, investigates, selects a response, proposes an action and verifies the result inside policy boundaries.
3. **Different from a chatbot?** It operates on live local telemetry and constrained actions, not conversation alone.
4. **How find root cause?** Correlated metrics, logs, traces, health, source/config and history produce a bounded RCA.
5. **Prevent hallucinated evidence?** RCA evidence IDs must exist in the scoped evidence store.
6. **Know which app failed?** Every adapter, incident, evidence row and context operation carries `application_id`.
7. **Prevent mixing?** Scope filters reject cross-application reads and writes; tests cover this.
8. **If AI is wrong?** Validation, deterministic fallback, risk policy, approval and fresh verification block unsafe resolution.
9. **Why approval?** A human must authorize the restricted source/config change.
10. **Arbitrary shell?** No. Patch safety rejects shell, imports, indirect execution and unregistered paths.
11. **Evidence Strength?** A heuristic score, not probability.
12. **Why TOON?** Repetitive structured AI context can sometimes use fewer measured tokens.
13. **Why not always?** Small or irregular payloads can be larger or fail strict validation.
14. **What is Hybrid?** A reversible representation preserving structured and prose regions.
15. **How AUTO chooses?** Measure candidates, validate, apply budget and minimum-saving policy, then choose utility winner.
16. **Prove savings?** Store actual candidate token/byte counts and timings in context results and benchmarks.
17. **If TOON loses data?** Reject it and fall back to a valid representation, usually JSON.
18. **Why JSON?** It is the canonical baseline and safe fallback.
19. **TOON in REST APIs?** No.
20. **TOON in database?** No; operational evidence remains JSON-compatible.
21. **Does ConverseLab use it?** No; only Commander’s RCA boundary does.
22. **Does PayFlow use it?** No; only Commander’s RCA boundary does.
23. **Where implemented?** `context_optimization/serializers`, `router.py` and `ai_reasoning.py`.
24. **LLM boundary?** The single structured request in `ai_reasoning.py` after context preparation.
25. **Live AI?** Not in this acceptance run; the UI honestly shows deterministic fallback.
26. **STT/TTS real?** Local HTTP simulators with real pipeline behavior, not production providers.
27. **Bank real?** A deterministic local simulator; no money moves.
28. **Connection leak?** Removing cleanup fills the pool; Commander detects DB_POOL_EXHAUSTED and repairs the registered function.
29. **TTS failure?** TTS returns HTTP 503 while upstream text generation remains successful.
30. **Verify repair?** Fresh application traffic plus latency, health and dependency checks.
31. **Verification failure?** Incident stays open and records failure; it is not falsely resolved.
32. **Secure remediation?** Exact hashes, registered paths, AST/config validation and approval.
33. **Enterprise integration?** Add an adapter and real telemetry/provider connectors behind the same scoped contracts.
34. **Kubernetes/cloud?** Add authenticated multi-tenant storage, queues, signed artifacts, workload identity and rollout controls.
35. **Third application?** Implement `ApplicationAdapter`, evidence normalization, topology, repair capabilities and verification.
36. **Unique?** It combines evidence-constrained remediation with measured, integrity-guarded context representation selection.
37. **Limitations?** Local sandbox, simulated providers, unconfigured external AI and reference tokenizer.
38. **What did 59 tests verify?** Context, both heroes, isolation, safety, approval, repair, verification, UI contracts and regression behavior.
39. **Why useful for AIOps?** Incident payloads are repetitive and bounded; safe adaptive context can reduce cost without dropping evidence.
40. **Next?** Production connectors, provider-specific tokenizers, durable audit storage and authenticated deployment.
