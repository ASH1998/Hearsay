from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class LocationContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    position: tuple[float, float, float]


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
