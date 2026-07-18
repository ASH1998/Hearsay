from __future__ import annotations

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
