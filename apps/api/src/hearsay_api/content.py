from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LocationContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    position: tuple[float, float, float]
    neighbors: tuple[str, ...]


class ResidentContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    role: str
    location: str
    color: str
    opening: str
    voter_bias: float = Field(ge=-1, le=1)
    schedule_id: str


class PrincipalContent(ResidentContent):
    pass


class AmbientContent(ResidentContent):
    pass


class EndingContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    summary: str


class BramApproachContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_verb: str
    label: str
    dialogue: str
    event_kind: str
    event_text: str
    original_claim: str
    relationship_delta: int = Field(ge=-100, le=100)
    traits: tuple[str, ...] = ()
    election_contribution: float = Field(ge=-1, le=1)


class ScheduleTemplateContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    days: tuple[tuple[str, ...], ...]

    @model_validator(mode="after")
    def validate_shape(self) -> ScheduleTemplateContent:
        if len(self.days) != 3 or any(len(day) != 4 for day in self.days):
            raise ValueError(
                "Schedule templates require three days of "
                "morning/afternoon/evening/night locations."
            )
        return self


class GreyhavenContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int
    locations: tuple[LocationContent, ...]
    principals: tuple[PrincipalContent, ...]
    ambients: tuple[AmbientContent, ...]
    endings: tuple[EndingContent, ...]
    bram_approaches: tuple[BramApproachContent, ...]
    schedule_templates: tuple[ScheduleTemplateContent, ...]
    public_traits: tuple[str, ...]

    @model_validator(mode="after")
    def validate_references(self) -> GreyhavenContent:
        location_ids = [location.id for location in self.locations]
        resident_ids = [resident.id for resident in self.residents]
        if len(location_ids) != len(set(location_ids)):
            raise ValueError("Location IDs must be unique.")
        if len(resident_ids) != len(set(resident_ids)):
            raise ValueError("Resident IDs must be unique across both tiers.")
        if len(self.principals) != 8 or len(self.ambients) != 12:
            raise ValueError("Greyhaven requires eight principals and twelve ambients.")
        known_locations = set(location_ids)
        for location in self.locations:
            if location.id in location.neighbors:
                raise ValueError(f"Location {location.id} cannot neighbor itself.")
            missing = set(location.neighbors) - known_locations
            if missing:
                raise ValueError(
                    f"Location {location.id} has unknown neighbors: {sorted(missing)}."
                )
            for neighbor in location.neighbors:
                reverse = next(item for item in self.locations if item.id == neighbor)
                if location.id not in reverse.neighbors:
                    raise ValueError(
                        f"Waypoint edge {location.id} -> {neighbor} must be bidirectional."
                    )
        for resident in self.residents:
            if resident.location not in known_locations:
                raise ValueError(
                    f"Resident {resident.id} has unknown location {resident.location}."
                )
        schedule_ids = [schedule.id for schedule in self.schedule_templates]
        if len(schedule_ids) != len(set(schedule_ids)):
            raise ValueError("Schedule template IDs must be unique.")
        schedules_by_id = {
            schedule.id: schedule
            for schedule in self.schedule_templates
        }
        for resident in self.residents:
            if resident.schedule_id not in schedules_by_id:
                raise ValueError(
                    f"Resident {resident.id} has unknown schedule {resident.schedule_id}."
                )
        for schedule in self.schedule_templates:
            for day in schedule.days:
                missing = set(day) - known_locations
                if missing:
                    raise ValueError(
                        f"Schedule {schedule.id} has unknown locations: {sorted(missing)}."
                    )
        if len(self.public_traits) != len(set(self.public_traits)):
            raise ValueError("Public traits must be unique.")
        required_endings = {
            "landslide",
            "narrow_win",
            "narrow_loss",
            "humiliation",
            "exposed",
            "run_out_of_town",
        }
        ending_ids = {ending.id for ending in self.endings}
        if ending_ids != required_endings:
            raise ValueError(
                "Greyhaven must define exactly the six authoritative endings."
            )
        required_bram_approaches = {
            "threaten_bram",
            "flatter_bram",
            "negotiate_bram",
            "lie_to_bram",
        }
        approach_verbs = {
            approach.action_verb
            for approach in self.bram_approaches
        }
        if approach_verbs != required_bram_approaches:
            raise ValueError(
                "Bram must define threaten, flatter, negotiate, and lie approaches."
            )
        for approach in self.bram_approaches:
            unknown_traits = set(approach.traits) - set(self.public_traits)
            if unknown_traits:
                raise ValueError(
                    f"Bram approach {approach.action_verb} has unknown traits: "
                    f"{sorted(unknown_traits)}."
                )
        return self

    @property
    def locations_by_id(self) -> dict[str, LocationContent]:
        return {location.id: location for location in self.locations}

    @property
    def principals_by_id(self) -> dict[str, PrincipalContent]:
        return {principal.id: principal for principal in self.principals}

    @property
    def residents(self) -> tuple[ResidentContent, ...]:
        return (*self.principals, *self.ambients)

    @property
    def residents_by_id(self) -> dict[str, ResidentContent]:
        return {resident.id: resident for resident in self.residents}

    @property
    def endings_by_id(self) -> dict[str, EndingContent]:
        return {ending.id: ending for ending in self.endings}

    @property
    def bram_approaches_by_verb(self) -> dict[str, BramApproachContent]:
        return {
            approach.action_verb: approach
            for approach in self.bram_approaches
        }

    @property
    def schedules_by_id(self) -> dict[str, ScheduleTemplateContent]:
        return {
            schedule.id: schedule
            for schedule in self.schedule_templates
        }

    def scheduled_location(
        self,
        resident_id: str,
        day: int,
        phase: str,
    ) -> str:
        resident = self.residents_by_id[resident_id]
        schedule = self.schedules_by_id[resident.schedule_id]
        phase_index = {
            "morning": 0,
            "afternoon": 1,
            "evening": 2,
            "night": 3,
        }[phase]
        return schedule.days[day - 1][phase_index]


@lru_cache
def load_content() -> GreyhavenContent:
    repository_root = Path(__file__).resolve().parents[4]
    content_path = repository_root / "packages" / "content" / "greyhaven.json"
    raw: dict[str, Any] = json.loads(content_path.read_text(encoding="utf-8"))
    return GreyhavenContent.model_validate(raw)
