from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Phase = Literal["morning", "afternoon", "evening", "night"]
RunStatus = Literal["active", "completed"]
Weather = Literal["clear", "rain"]


class ActionVerb(StrEnum):
    MOVE = "move"
    OBSERVE = "observe"
    READ_NOTICE_BOARD = "read_notice_board"
    TALK = "talk"
    PROMISE_HELP = "promise_help"
    CONFRONT = "confront"
    SLEEP = "sleep"


class CreateRunRequest(BaseModel):
    display_name: str = Field(default="Newcomer", min_length=1, max_length=40)
    seed: int = Field(default=1729, ge=0, le=2_147_483_647)


class ActionRequest(BaseModel):
    idempotency_key: UUID
    verb: ActionVerb
    target_id: str | None = Field(default=None, max_length=64)
    content: str | None = Field(default=None, max_length=500)


class LocationState(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    position: tuple[float, float, float]
    neighbors: tuple[str, ...] = ()


class NpcState(BaseModel):
    id: str
    name: str
    role: str
    location_id: str
    color: str
    relationship: int = Field(default=0, ge=-100, le=100)
    speech: str | None = None


class PromiseState(BaseModel):
    id: UUID
    promisee_id: str
    content: str
    deadline_day: int
    deadline_phase: Phase
    status: Literal["active", "kept", "broken"] = "active"


class DialogueState(BaseModel):
    speaker_id: str
    speaker_name: str
    text: str


class WorldEvent(BaseModel):
    id: UUID
    kind: str
    text: str
    visible: bool = True


class PlayerState(BaseModel):
    display_name: str
    location_id: str
    traits: list[str] = Field(default_factory=list)


class RunSnapshot(BaseModel):
    run_id: UUID
    seed: int
    revision: int = Field(default=0, ge=0)
    status: RunStatus = "active"
    day: int = Field(default=1, ge=1, le=3)
    phase: Phase = "morning"
    action_count: int = Field(default=0, ge=0, le=18)
    world_tick: int = Field(default=0, ge=0)
    weather: Weather = "clear"
    player: PlayerState
    locations: list[LocationState]
    npcs: list[NpcState]
    promises: list[PromiseState] = Field(default_factory=list)
    dialogue: DialogueState | None = None
    recent_events: list[WorldEvent] = Field(default_factory=list)


class CreateRunResponse(BaseModel):
    run_id: UUID
    snapshot: RunSnapshot


class ActionResponse(BaseModel):
    action_id: UUID
    consumed_time: bool
    snapshot: RunSnapshot


class MemoryVersionState(BaseModel):
    belief_id: UUID
    version: int
    proposition_key: str
    holder_id: str
    narrative_text: str
    normalized_position: dict[str, object]
    confidence: float
    salience: float
    source_kind: str
    source_id: str | None
    embedding_model_id: str
    active: bool
    contested: bool = False
    created_at: datetime | None = None


class TransmissionState(BaseModel):
    id: UUID
    proposition_key: str
    speaker_id: str | None
    listener_id: str
    from_belief_id: UUID | None
    from_version: int | None
    to_belief_id: UUID
    to_version: int
    original_text: str | None
    retold_text: str
    mutation_note: str | None
    trust_at_time: float | None
    provider_id: str = "deterministic"
    model_id: str
    fallback_used: bool = False
    fallback_reason: str | None = None
    inference_attempts: int = 0
    inference_latency_ms: float | None = None
    created_at: datetime | None = None


class BeliefInputState(BaseModel):
    id: UUID
    proposition_key: str
    holder_id: str
    source_kind: str
    source_id: str | None
    narrative_text: str
    normalized_position: dict[str, object]
    source_trust: float
    evidence_weight: float
    corroboration: float
    recency: float
    bias_alignment: float
    incoming_strength: float
    classification: str
    outcome: str
    rationale: str
    observed_version: int | None
    evaluated_against_version: int | None
    resulting_belief_id: UUID | None
    resulting_version: int | None
    transaction_attempts: int
    recalculated_after_conflict: bool
    created_at: datetime | None = None


class MemoryLineageResponse(BaseModel):
    run_id: UUID
    proposition_key: str | None = None
    versions: list[MemoryVersionState]
    transmissions: list[TransmissionState]
    inputs: list[BeliefInputState]


class MemoryRecallRequest(BaseModel):
    holder_id: str = Field(min_length=1, max_length=64)
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=8, ge=1, le=20)


class RecalledMemory(BaseModel):
    belief_id: UUID
    version: int
    proposition_key: str
    narrative_text: str
    semantic_similarity: float
    final_score: float
    confidence: float
    salience: float
    source_id: str | None


class MemoryRecallResponse(BaseModel):
    trace_id: UUID
    run_id: UUID
    holder_id: str
    query: str
    memories: list[RecalledMemory]
