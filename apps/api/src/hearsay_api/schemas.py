from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Phase = Literal["morning", "afternoon", "evening", "night"]
RunStatus = Literal["active", "completed"]
Weather = Literal["clear", "rain"]
VoteChoice = Literal["player", "rhea"]
EndingKey = Literal[
    "landslide",
    "narrow_win",
    "narrow_loss",
    "humiliation",
    "exposed",
    "run_out_of_town",
]


class ActionVerb(StrEnum):
    MOVE = "move"
    OBSERVE = "observe"
    READ_NOTICE_BOARD = "read_notice_board"
    TALK = "talk"
    PROMISE_HELP = "promise_help"
    SETTLE_SHIPMENT = "settle_shipment"
    DECLARE_CANDIDACY = "declare_candidacy"
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


class DialogueMemoryRef(BaseModel):
    belief_id: UUID
    version: int
    proposition_key: str
    contested: bool = False


class DialogueChoiceState(BaseModel):
    id: str
    label: str
    prompt: str


class DialogueState(BaseModel):
    speaker_id: str
    speaker_name: str
    text: str
    recalled_memories: list[DialogueMemoryRef] = Field(default_factory=list)
    provider_id: str | None = None
    model_id: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    treatment_cue: str | None = None
    available_choices: list[DialogueChoiceState] = Field(default_factory=list)


class WorldEvent(BaseModel):
    id: UUID
    kind: str
    text: str
    visible: bool = True


class PlayerState(BaseModel):
    display_name: str
    location_id: str
    traits: list[str] = Field(default_factory=list)
    candidate: bool = False


class VoteInputState(BaseModel):
    id: UUID
    kind: Literal["base", "trait", "relationship", "belief"]
    key: str
    value: str | float | bool | None
    weight: float
    contribution: float
    explanation: str
    belief_id: UUID | None = None
    belief_version: int | None = None
    decisive_rank: int | None = Field(default=None, ge=1, le=3)


class VoteState(BaseModel):
    id: UUID
    voter_id: str
    choice: VoteChoice
    player_score: float
    inputs: list[VoteInputState]


class EndingState(BaseModel):
    key: EndingKey
    title: str
    summary: str
    player_won: bool
    decisive_voter_ids: list[str] = Field(default_factory=list)


class ElectionState(BaseModel):
    id: UUID
    player_votes: int = Field(ge=0, le=20)
    rhea_votes: int = Field(ge=0, le=20)
    winner: VoteChoice
    tie_favors_rhea: bool
    votes: list[VoteState]
    ending: EndingState


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
    election: ElectionState | None = None
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


class HistorianTraceRequest(BaseModel):
    proposition_key: str = Field(
        min_length=1,
        max_length=96,
        pattern=r"^[a-z0-9][a-z0-9._:-]*$",
    )


class HistorianAuditState(BaseModel):
    id: UUID
    run_id: UUID
    operation: Literal["trace_rumor"] = "trace_rumor"
    proposition_key: str
    provider_id: str
    attempted_provider_id: str
    tool_name: str | None = None
    auth_mode: str
    cluster_fingerprint: str | None = None
    managed_mcp: bool
    sponsor_proof: bool
    success: bool
    fallback_used: bool
    fallback_reason: str | None = None
    query_id: str
    result_counts: dict[str, int] = Field(default_factory=dict)
    latency_ms: float = Field(ge=0)
    created_at: datetime

    @model_validator(mode="after")
    def sponsor_proof_requires_successful_managed_read(self) -> HistorianAuditState:
        if self.sponsor_proof and not (
            self.managed_mcp
            and self.success
            and not self.fallback_used
            and self.tool_name == "select_query"
            and self.auth_mode == "service-account-api-key"
        ):
            raise ValueError(
                "Historian sponsor proof requires a successful independently "
                "authenticated Managed MCP select_query."
            )
        return self


class HistorianTraceResponse(BaseModel):
    audit: HistorianAuditState
    lineage: MemoryLineageResponse


class MemoryRecallRequest(BaseModel):
    holder_id: str = Field(min_length=1, max_length=64)
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=8, ge=1, le=20)


class RecalledMemory(BaseModel):
    belief_id: UUID
    version: int
    proposition_key: str
    narrative_text: str
    normalized_position: dict[str, object]
    semantic_similarity: float
    final_score: float
    confidence: float
    salience: float
    source_id: str | None
    contested: bool = False


class MemoryRecallResponse(BaseModel):
    trace_id: UUID
    run_id: UUID
    holder_id: str
    query: str
    memories: list[RecalledMemory]
