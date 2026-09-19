"""Typed internal context requests; public application contracts remain JSON."""
from dataclasses import dataclass, field, asdict
from typing import Any, Literal

Purpose = Literal['RCA', 'INCIDENT_MEMORY', 'INVESTIGATOR_CONTEXT']

@dataclass(frozen=True)
class Policy:
    strategy: str = 'AUTO'
    minimum_expected_token_saving: float = .05
    safety_margin_tokens: int = 512

@dataclass(frozen=True)
class ContextOptimizationRequest:
    payload: Any
    purpose: Purpose
    application_id: str
    incident_id: str
    model_name: str | None = None
    model_context_limit: int | None = None
    system_prompt_tokens: int = 0
    tool_definition_tokens: int = 0
    reserved_output_tokens: int = 4500
    policy: Policy = field(default_factory=Policy)
    metadata: dict = field(default_factory=dict)

@dataclass
class ContextOptimizationResult:
    request_id: str
    purpose: str
    application_id: str
    incident_id: str
    timestamp: float
    selected_strategy: str
    serialized_context: str
    metrics: dict

    def public(self):
        value = asdict(self)
        value.pop('serialized_context')
        value.update(value.pop('metrics'))
        return value
