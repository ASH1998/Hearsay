from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

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
    echo_style: str


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


class TownEventContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    start_day: int = Field(ge=1, le=3)
    start_phase: str
    end_day: int = Field(ge=1, le=3)
    end_phase: str
    schedule_location_override: str | None = None
    start_text: str
    end_text: str
    active_awareness: dict[str, str]
    resolved_awareness: dict[str, str]


class ArgumentChoiceContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_verb: str
    label: str
    dialogue_speaker_id: str
    dialogue: str
    event_kind: str
    event_text: str
    memory_text: str
    bram_relationship_delta: int = Field(ge=-100, le=100)
    nessa_relationship_delta: int = Field(ge=-100, le=100)
    traits: tuple[str, ...] = ()
    holder_election_contributions: dict[str, float]


class FavorContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    giver_id: str
    content: str
    accept_dialogue: str
    complete_dialogue: str
    correction_text: str


class FavorChoiceContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    favor_id: str
    action_verb: str
    label: str
    resolution: Literal[
        "revealed",
        "concealed",
        "helped_quietly",
        "gossiped_publicly",
        "investigated",
        "covered_up",
        "verified_source",
        "embellished",
    ]
    dialogue: str
    event_kind: str
    event_text: str
    memory_text: str
    resident_speeches: dict[str, str] = Field(default_factory=dict)
    relationship_deltas: dict[str, int]
    holder_election_contributions: dict[str, float]
    transmission_parents: dict[str, str] = Field(default_factory=dict)
    traits: tuple[str, ...] = ()
    grants_endorsement: bool = False

    @model_validator(mode="after")
    def validate_choice(self) -> FavorChoiceContent:
        expected_resolution = {
            "reveal_orin_confession": "revealed",
            "conceal_orin_confession": "concealed",
            "help_oswin_quietly": "helped_quietly",
            "gossip_oswin_illness": "gossiped_publicly",
            "investigate_elias_arrest": "investigated",
            "cover_elias_arrest": "covered_up",
            "verify_pip_source": "verified_source",
            "embellish_pip_rumor": "embellished",
        }.get(self.action_verb)
        if expected_resolution is not None and self.resolution != expected_resolution:
            raise ValueError("Favor action and resolution must agree.")
        if any(delta < -100 or delta > 100 for delta in self.relationship_deltas.values()):
            raise ValueError("Favor relationship deltas must be within -100..100.")
        if any(
            contribution < -1 or contribution > 1
            for contribution in self.holder_election_contributions.values()
        ):
            raise ValueError("Favor election contributions must be within -1..1.")
        return self


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
    town_events: tuple[TownEventContent, ...]
    argument_choices: tuple[ArgumentChoiceContent, ...]
    favors: tuple[FavorContent, ...]
    favor_choices: tuple[FavorChoiceContent, ...]
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
        schedules_by_id = {schedule.id: schedule for schedule in self.schedule_templates}
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
            raise ValueError("Greyhaven must define exactly the six authoritative endings.")
        required_bram_approaches = {
            "threaten_bram",
            "flatter_bram",
            "negotiate_bram",
            "lie_to_bram",
        }
        approach_verbs = {approach.action_verb for approach in self.bram_approaches}
        if approach_verbs != required_bram_approaches:
            raise ValueError("Bram must define threaten, flatter, negotiate, and lie approaches.")
        for approach in self.bram_approaches:
            unknown_traits = set(approach.traits) - set(self.public_traits)
            if unknown_traits:
                raise ValueError(
                    f"Bram approach {approach.action_verb} has unknown traits: "
                    f"{sorted(unknown_traits)}."
                )
        event_ids = [event.id for event in self.town_events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("Town event IDs must be unique.")
        if "storm" not in event_ids:
            raise ValueError("Greyhaven's never-cut storm event is required.")
        known_phases = {"morning", "afternoon", "evening", "night"}
        for event in self.town_events:
            if {event.start_phase, event.end_phase} - known_phases:
                raise ValueError(f"Town event {event.id} uses an unknown phase.")
            if (
                event.schedule_location_override is not None
                and event.schedule_location_override not in known_locations
            ):
                raise ValueError(f"Town event {event.id} has an unknown schedule override.")
            unknown_residents = (set(event.active_awareness) | set(event.resolved_awareness)) - set(
                resident_ids
            )
            if unknown_residents:
                raise ValueError(
                    f"Town event {event.id} has unknown aware residents: "
                    f"{sorted(unknown_residents)}."
                )
        required_argument_choices = {
            "side_with_bram",
            "side_with_nessa",
            "calm_argument",
        }
        argument_verbs = {choice.action_verb for choice in self.argument_choices}
        if argument_verbs != required_argument_choices:
            raise ValueError("The public argument requires Bram, Nessa, and calm choices.")
        for choice in self.argument_choices:
            if choice.dialogue_speaker_id not in resident_ids:
                raise ValueError(f"Argument choice {choice.action_verb} has an unknown speaker.")
            unknown_traits = set(choice.traits) - set(self.public_traits)
            unknown_holders = set(choice.holder_election_contributions) - set(resident_ids)
            if unknown_traits or unknown_holders:
                raise ValueError(f"Argument choice {choice.action_verb} has invalid references.")
        favor_ids = [favor.id for favor in self.favors]
        if len(favor_ids) != len(set(favor_ids)):
            raise ValueError("Favor IDs must be unique.")
        required_favors = {
            "nessa_harbor_log",
            "orin_election_confession",
            "talia_sick_house",
            "elias_wrongful_arrest",
            "pip_ballot_source",
        }
        if not required_favors.issubset(favor_ids):
            raise ValueError(
                "Nessa's harbor log, Orin's confession, Talia's sick-house "
                "favor, Elias's wrongful-arrest favor, and Pip's source-tracing "
                "favor are required."
            )
        if any(favor.giver_id not in resident_ids for favor in self.favors):
            raise ValueError("Every favor giver must be a known resident.")
        required_favor_choices = {
            "reveal_orin_confession",
            "conceal_orin_confession",
            "help_oswin_quietly",
            "gossip_oswin_illness",
            "investigate_elias_arrest",
            "cover_elias_arrest",
            "verify_pip_source",
            "embellish_pip_rumor",
        }
        favor_choice_verbs = {choice.action_verb for choice in self.favor_choices}
        if favor_choice_verbs != required_favor_choices:
            raise ValueError(
                "Authored favors require Orin's reveal/conceal and "
                "Talia's help/gossip, Elias's investigate/cover-up, and "
                "Pip's verify/embellish choices."
            )
        for favor_choice in self.favor_choices:
            unknown_traits = set(favor_choice.traits) - set(self.public_traits)
            unknown_relationships = set(favor_choice.relationship_deltas) - set(resident_ids)
            unknown_holders = set(favor_choice.holder_election_contributions) - set(resident_ids)
            unknown_speakers = set(favor_choice.resident_speeches) - set(resident_ids)
            unknown_parent_holders = set(favor_choice.transmission_parents) - set(
                favor_choice.holder_election_contributions
            )
            unknown_parents = (
                set(favor_choice.transmission_parents.values()) - set(resident_ids) - {"player"}
            )
            missing_parent_routes = set(favor_choice.holder_election_contributions) - set(
                favor_choice.transmission_parents
            )
            available_parents = {"player"}
            invalid_parent_order = False
            for holder_id in favor_choice.holder_election_contributions:
                parent_id = favor_choice.transmission_parents.get(holder_id)
                if parent_id not in available_parents:
                    invalid_parent_order = True
                available_parents.add(holder_id)
            if (
                favor_choice.favor_id not in favor_ids
                or unknown_traits
                or unknown_relationships
                or unknown_holders
                or unknown_speakers
                or unknown_parent_holders
                or unknown_parents
                or missing_parent_routes
                or invalid_parent_order
            ):
                raise ValueError(f"Favor choice {favor_choice.action_verb} has invalid references.")
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
    def ambients_by_id(self) -> dict[str, AmbientContent]:
        return {ambient.id: ambient for ambient in self.ambients}

    @property
    def endings_by_id(self) -> dict[str, EndingContent]:
        return {ending.id: ending for ending in self.endings}

    @property
    def bram_approaches_by_verb(self) -> dict[str, BramApproachContent]:
        return {approach.action_verb: approach for approach in self.bram_approaches}

    @property
    def town_events_by_id(self) -> dict[str, TownEventContent]:
        return {event.id: event for event in self.town_events}

    @property
    def argument_choices_by_verb(self) -> dict[str, ArgumentChoiceContent]:
        return {choice.action_verb: choice for choice in self.argument_choices}

    @property
    def favors_by_id(self) -> dict[str, FavorContent]:
        return {favor.id: favor for favor in self.favors}

    @property
    def favor_choices_by_verb(self) -> dict[str, FavorChoiceContent]:
        return {choice.action_verb: choice for choice in self.favor_choices}

    @property
    def schedules_by_id(self) -> dict[str, ScheduleTemplateContent]:
        return {schedule.id: schedule for schedule in self.schedule_templates}

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
