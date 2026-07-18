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


class PrincipalContent(ResidentContent):
    pass


class AmbientContent(ResidentContent):
    pass


class EndingContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    summary: str


class GreyhavenContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int
    locations: tuple[LocationContent, ...]
    principals: tuple[PrincipalContent, ...]
    ambients: tuple[AmbientContent, ...]
    endings: tuple[EndingContent, ...]
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


@lru_cache
def load_content() -> GreyhavenContent:
    repository_root = Path(__file__).resolve().parents[4]
    content_path = repository_root / "packages" / "content" / "greyhaven.json"
    raw: dict[str, Any] = json.loads(content_path.read_text(encoding="utf-8"))
    return GreyhavenContent.model_validate(raw)
