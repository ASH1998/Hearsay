from __future__ import annotations

import hashlib
import math
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import TYPE_CHECKING, Protocol, cast

import structlog

from hearsay_api.inference import (
    DeterministicInferenceProvider,
    InferenceResult,
    RumorRetelling,
    RumorRetellingRequest,
)
from hearsay_api.schemas import ActionRequest, ActionResponse, ActionVerb

EMBEDDING_DIMENSIONS = 384
TOKEN_PATTERN = re.compile(r"[a-z0-9']+")
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from hearsay_api.config import Settings


class EmbeddingArray(Protocol):
    def tolist(self) -> list[float]: ...


class SentenceEmbeddingModel(Protocol):
    def encode(
        self,
        sentences: str,
        *,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> EmbeddingArray: ...


@dataclass(frozen=True)
class EmbeddingResult:
    vector: tuple[float, ...]
    provider_id: str
    model_id: str
    fallback_used: bool = False
    fallback_reason: str | None = None
    latency_ms: float = 0


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> EmbeddingResult: ...

    def embed_query(self, text: str) -> EmbeddingResult: ...


class DeterministicEmbeddingProvider:
    """Stable test/fallback embeddings without claiming model-quality semantics."""

    @property
    def model_id(self) -> str:
        return "hearsay-hash-384-v1"

    def embed(self, text: str) -> EmbeddingResult:
        started = perf_counter()
        values = [0.0] * EMBEDDING_DIMENSIONS
        tokens = TOKEN_PATTERN.findall(text.lower()) or ["empty"]
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            first_index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
            second_index = int.from_bytes(digest[4:8], "big") % EMBEDDING_DIMENSIONS
            values[first_index] += 1.0 if digest[8] & 1 else -1.0
            values[second_index] += 0.5 if digest[9] & 1 else -0.5
        magnitude = math.sqrt(sum(value * value for value in values)) or 1.0
        return EmbeddingResult(
            vector=tuple(value / magnitude for value in values),
            provider_id="deterministic",
            model_id=self.model_id,
            latency_ms=(perf_counter() - started) * 1000,
        )

    def embed_query(self, text: str) -> EmbeddingResult:
        return self.embed(text)


class SentenceTransformerEmbeddingProvider:
    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        cache_dir: Path = Path(".cache/huggingface"),
        model: SentenceEmbeddingModel | None = None,
    ) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._model = model
        self._model_lock = Lock()

    def _load_model(self) -> SentenceEmbeddingModel:
        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is None:
                os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
                os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
                from sentence_transformers import SentenceTransformer

                self.cache_dir.mkdir(parents=True, exist_ok=True)
                self._model = cast(
                    SentenceEmbeddingModel,
                    SentenceTransformer(
                        self.model_name,
                        cache_folder=str(self.cache_dir),
                        device="cpu",
                        trust_remote_code=False,
                    ),
                )
        return self._model

    def _embed(self, text: str) -> EmbeddingResult:
        started = perf_counter()
        encoded = self._load_model().encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        vector = tuple(float(value) for value in encoded.tolist())
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                "The configured embedding model returned "
                f"{len(vector)} dimensions instead of {EMBEDDING_DIMENSIONS}."
            )
        if not all(math.isfinite(value) for value in vector):
            raise ValueError("The configured embedding model returned non-finite values.")
        return EmbeddingResult(
            vector=vector,
            provider_id="sentence-transformers",
            model_id=self.model_name,
            latency_ms=(perf_counter() - started) * 1000,
        )

    def embed(self, text: str) -> EmbeddingResult:
        return self._embed(text)

    def embed_query(self, text: str) -> EmbeddingResult:
        return self._embed(f"{BGE_QUERY_INSTRUCTION}{text}")


class SafeEmbeddingProvider:
    def __init__(
        self,
        primary: EmbeddingProvider,
        fallback: EmbeddingProvider | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback or DeterministicEmbeddingProvider()
        self._primary_failure_reason: str | None = None
        self._failure_lock = Lock()

    def _run(
        self,
        operation: str,
        primary_call: Callable[[], EmbeddingResult],
        fallback_call: Callable[[], EmbeddingResult],
    ) -> EmbeddingResult:
        started = perf_counter()
        reason = self._primary_failure_reason
        if reason is None:
            try:
                return primary_call()
            except Exception as error:
                reason = type(error).__name__
                with self._failure_lock:
                    self._primary_failure_reason = reason
                logger.warning(
                    "embedding_fallback_used",
                    operation=operation,
                    reason=reason,
                )
        fallback = fallback_call()
        return EmbeddingResult(
            vector=fallback.vector,
            provider_id=fallback.provider_id,
            model_id=fallback.model_id,
            fallback_used=True,
            fallback_reason=reason,
            latency_ms=(perf_counter() - started) * 1000,
        )

    def embed(self, text: str) -> EmbeddingResult:
        return self._run(
            "embed",
            lambda: self.primary.embed(text),
            lambda: self.fallback.embed(text),
        )

    def embed_query(self, text: str) -> EmbeddingResult:
        return self._run(
            "embed_query",
            lambda: self.primary.embed_query(text),
            lambda: self.fallback.embed_query(text),
        )


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    fallback = DeterministicEmbeddingProvider()
    if settings.embedding_provider == "fallback":
        return fallback
    primary = SentenceTransformerEmbeddingProvider(
        model_name=settings.embedding_model,
        cache_dir=settings.embedding_cache_dir,
    )
    return SafeEmbeddingProvider(primary=primary, fallback=fallback)


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
        text_embedding = embeddings.embed(text)
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
                    embedding=text_embedding.vector,
                    embedding_model_id=text_embedding.model_id,
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
        original_embedding = embeddings.embed(original)
        retold_embedding = embeddings.embed(retold)
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
                    embedding=original_embedding.vector,
                    embedding_model_id=original_embedding.model_id,
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
                    embedding=retold_embedding.vector,
                    embedding_model_id=retold_embedding.model_id,
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
