from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol

from hearsay_api.inference import (
    DeterministicInferenceProvider,
    InferenceResult,
    RumorRetelling,
    RumorRetellingRequest,
)
from hearsay_api.schemas import ActionRequest, ActionResponse, ActionVerb

EMBEDDING_DIMENSIONS = 384
TOKEN_PATTERN = re.compile(r"[a-z0-9']+")


class EmbeddingProvider(Protocol):
    @property
    def model_id(self) -> str: ...

    def embed(self, text: str) -> tuple[float, ...]: ...


class DeterministicEmbeddingProvider:
    """Stable test/fallback embeddings without claiming model-quality semantics."""

    @property
    def model_id(self) -> str:
        return "hearsay-hash-384-v1"

    def embed(self, text: str) -> tuple[float, ...]:
        values = [0.0] * EMBEDDING_DIMENSIONS
        tokens = TOKEN_PATTERN.findall(text.lower()) or ["empty"]
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            first_index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
            second_index = int.from_bytes(digest[4:8], "big") % EMBEDDING_DIMENSIONS
            values[first_index] += 1.0 if digest[8] & 1 else -1.0
            values[second_index] += 0.5 if digest[9] & 1 else -0.5
        magnitude = math.sqrt(sum(value * value for value in values)) or 1.0
        return tuple(value / magnitude for value in values)


@dataclass(frozen=True)
class PlannedBelief:
    proposition_key: str
    subject_kind: str
    subject_id: str | None
    predicate: str
    holder_id: str
    narrative_text: str
    normalized_position: dict[str, object]
    confidence: float
    salience: float
    source_kind: str
    source_id: str | None
    embedding: tuple[float, ...]
    embedding_model_id: str
    parent_holder_id: str | None = None
    mutation_note: str | None = None
    trust_at_time: float | None = None
    retelling_provider_id: str | None = None
    retelling_model_id: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    inference_attempts: int = 0
    inference_latency_ms: float | None = None


@dataclass(frozen=True)
class PlannedRelationship:
    a_kind: str
    a_id: str
    b_kind: str
    b_id: str
    trust_delta: float = 0.0
    affinity_delta: float = 0.0
    fear_delta: float = 0.0
    debt_delta: float = 0.0


@dataclass(frozen=True)
class MemoryEffects:
    beliefs: tuple[PlannedBelief, ...] = ()
    relationships: tuple[PlannedRelationship, ...] = ()
    gossip_tick_number: int | None = None


def plan_action_memory(
    request: ActionRequest,
    response: ActionResponse,
    embeddings: EmbeddingProvider,
    retelling: InferenceResult[RumorRetelling] | None = None,
) -> MemoryEffects:
    if request.verb == ActionVerb.PROMISE_HELP and request.target_id == "marta":
        text = "The newcomer promised to release Marta's shipment from Bram before evening."
        return MemoryEffects(
            beliefs=(
                PlannedBelief(
                    proposition_key="player-promise-marta-shipment",
                    subject_kind="promise",
                    subject_id="marta-shipment",
                    predicate="player_promised_help",
                    holder_id="marta",
                    narrative_text=text,
                    normalized_position={
                        "stance": "accepted",
                        "player_committed": True,
                        "deadline": "day-1-evening",
                    },
                    confidence=0.98,
                    salience=1.0,
                    source_kind="player",
                    source_id="player",
                    embedding=embeddings.embed(text),
                    embedding_model_id=embeddings.model_id,
                ),
            ),
            relationships=(
                PlannedRelationship(
                    a_kind="npc",
                    a_id="marta",
                    b_kind="player",
                    b_id="player",
                    trust_delta=0.1,
                    affinity_delta=0.05,
                    debt_delta=0.25,
                ),
            ),
        )

    if request.verb == ActionVerb.CONFRONT and request.target_id == "bram":
        original = "The newcomer confronted Bram about tripling the shipment price."
        if retelling is None:
            fallback_provider = DeterministicInferenceProvider()
            fallback_value = fallback_provider.retell_rumor(
                RumorRetellingRequest(
                    original_claim=original,
                    speaker_id="bram",
                    listener_id="pip",
                    trust=0.6,
                    context="A public dispute in Greyhaven market row.",
                )
            )
            retelling = InferenceResult(
                value=fallback_value,
                provider_id=fallback_provider.provider_id,
                model_id=fallback_provider.model_id,
                fallback_used=False,
                fallback_reason=None,
                attempts=1,
                latency_ms=0,
            )
        retold = retelling.value.retold_claim
        tick_number = response.snapshot.world_tick if response.snapshot.world_tick > 0 else None
        return MemoryEffects(
            beliefs=(
                PlannedBelief(
                    proposition_key="bram-price-confrontation",
                    subject_kind="event",
                    subject_id="bram",
                    predicate="player_challenged_bram_price",
                    holder_id="bram",
                    narrative_text=original,
                    normalized_position={
                        "stance": "witnessed",
                        "price_challenged": True,
                        "public": True,
                    },
                    confidence=1.0,
                    salience=0.95,
                    source_kind="player_action",
                    source_id="player",
                    embedding=embeddings.embed(original),
                    embedding_model_id=embeddings.model_id,
                ),
                PlannedBelief(
                    proposition_key="bram-price-confrontation",
                    subject_kind="event",
                    subject_id="bram",
                    predicate="player_challenged_bram_price",
                    holder_id="pip",
                    narrative_text=retold,
                    normalized_position={
                        **retelling.value.semantic_position.model_dump(exclude_none=True),
                        "stance": "accepted",
                        "price_challenged": True,
                        "public": True,
                    },
                    confidence=min(
                        max(0.88 + retelling.value.confidence_delta, 0.0),
                        1.0,
                    ),
                    salience=0.9,
                    source_kind="hearsay",
                    source_id="bram",
                    embedding=embeddings.embed(retold),
                    embedding_model_id=embeddings.model_id,
                    parent_holder_id="bram",
                    mutation_note=retelling.value.drift_note,
                    trust_at_time=0.6,
                    retelling_provider_id=retelling.provider_id,
                    retelling_model_id=retelling.model_id,
                    fallback_used=retelling.fallback_used,
                    fallback_reason=retelling.fallback_reason,
                    inference_attempts=retelling.attempts,
                    inference_latency_ms=retelling.latency_ms,
                ),
            ),
            relationships=(
                PlannedRelationship(
                    a_kind="npc",
                    a_id="bram",
                    b_kind="player",
                    b_id="player",
                    trust_delta=-0.15,
                    affinity_delta=-0.1,
                ),
                PlannedRelationship(
                    a_kind="npc",
                    a_id="pip",
                    b_kind="npc",
                    b_id="bram",
                    trust_delta=0.1,
                ),
            ),
            gossip_tick_number=tick_number,
        )

    return MemoryEffects()
