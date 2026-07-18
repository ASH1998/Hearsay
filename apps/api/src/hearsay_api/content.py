from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class LocationContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    position: tuple[float, float, float]
    neighbors: tuple[str, ...]


class PrincipalContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    role: str
    location: str
    color: str
    opening: str


class GreyhavenContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int
    locations: tuple[LocationContent, ...]
    principals: tuple[PrincipalContent, ...]
    public_traits: tuple[str, ...]

    @model_validator(mode="after")
    def validate_references(self) -> GreyhavenContent:
        location_ids = [location.id for location in self.locations]
        principal_ids = [principal.id for principal in self.principals]
        if len(location_ids) != len(set(location_ids)):
            raise ValueError("Location IDs must be unique.")
        if len(principal_ids) != len(set(principal_ids)):
            raise ValueError("Principal IDs must be unique.")
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
        for principal in self.principals:
            if principal.location not in known_locations:
                raise ValueError(
                    f"Principal {principal.id} has unknown location {principal.location}."
                )
        if len(self.public_traits) != len(set(self.public_traits)):
            raise ValueError("Public traits must be unique.")
        return self

    @property
    def locations_by_id(self) -> dict[str, LocationContent]:
        return {location.id: location for location in self.locations}

    @property
    def principals_by_id(self) -> dict[str, PrincipalContent]:
        return {principal.id: principal for principal in self.principals}


@lru_cache
def load_content() -> GreyhavenContent:
    repository_root = Path(__file__).resolve().parents[4]
    content_path = repository_root / "packages" / "content" / "greyhaven.json"
    raw: dict[str, Any] = json.loads(content_path.read_text(encoding="utf-8"))
    return GreyhavenContent.model_validate(raw)
