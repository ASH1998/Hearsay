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
from typing import TYPE_CHECKING, Literal, Protocol, cast

import structlog

from hearsay_api.inference import (
    DeterministicInferenceProvider,
    InferenceResult,
    RumorRetelling,
    RumorRetellingRequest,
)
from hearsay_api.schemas import (
    ActionRequest,
    ActionResponse,
    ActionVerb,
    DialogueChoiceState,
    RecalledMemory,
)

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
    trust_floor: float | None = None
    trust_ceiling: float | None = None


@dataclass(frozen=True)
class DialogueTreatment:
    relationship_score: int
    cue: str
    choices: tuple[DialogueChoiceState, ...]
    trust_floor: float | None = None
    trust_ceiling: float | None = None


@dataclass(frozen=True)
class MemoryEffects:
    beliefs: tuple[PlannedBelief, ...] = ()
    relationships: tuple[PlannedRelationship, ...] = ()
    gossip_tick_number: int | None = None


@dataclass(frozen=True)
class PromiseTransition:
    promisee_id: str
    status: Literal["kept", "broken"]


def plan_action_memory(
    request: ActionRequest,
    response: ActionResponse,
    embeddings: EmbeddingProvider,
    retelling: InferenceResult[RumorRetelling] | None = None,
    dialogue_treatment: DialogueTreatment | None = None,
    promise_transitions: tuple[PromiseTransition, ...] = (),
) -> MemoryEffects:
    primary = _plan_primary_action_memory(
        request,
        response,
        embeddings,
        retelling,
        dialogue_treatment,
    )
    promise = _plan_promise_transitions(
        promise_transitions,
        response,
        embeddings,
    )
    return MemoryEffects(
        beliefs=primary.beliefs + promise.beliefs,
        relationships=primary.relationships + promise.relationships,
        gossip_tick_number=(
            primary.gossip_tick_number
            if primary.gossip_tick_number is not None
            else promise.gossip_tick_number
        ),
    )


def _plan_primary_action_memory(
    request: ActionRequest,
    response: ActionResponse,
    embeddings: EmbeddingProvider,
    retelling: InferenceResult[RumorRetelling] | None = None,
    dialogue_treatment: DialogueTreatment | None = None,
) -> MemoryEffects:
    if (
        request.verb == ActionVerb.TALK
        and request.target_id is not None
        and dialogue_treatment is not None
        and (
            dialogue_treatment.trust_floor is not None
            or dialogue_treatment.trust_ceiling is not None
        )
    ):
        return MemoryEffects(
            relationships=(
                PlannedRelationship(
                    a_kind="npc",
                    a_id=request.target_id,
                    b_kind="player",
                    b_id="player",
                    trust_floor=dialogue_treatment.trust_floor,
                    trust_ceiling=dialogue_treatment.trust_ceiling,
                ),
            )
        )

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


def _plan_promise_transitions(
    transitions: tuple[PromiseTransition, ...],
    response: ActionResponse,
    embeddings: EmbeddingProvider,
) -> MemoryEffects:
    beliefs: list[PlannedBelief] = []
    relationships: list[PlannedRelationship] = []
    for transition in transitions:
        if transition.promisee_id != "marta":
            continue
        kept = transition.status == "kept"
        marta_text = (
            "The newcomer kept their promise and secured Marta's shipment before evening."
            if kept
            else "The newcomer broke their promise; Marta's shipment was still held at evening."
        )
        pip_text = (
            "The newcomer actually paid the price and got Marta's crates released on time."
            if kept
            else "The newcomer's grand promise to Marta was empty when evening came."
        )
        marta_embedding = embeddings.embed(marta_text)
        pip_embedding = embeddings.embed(pip_text)
        position = {
            "stance": "confirmed",
            "player_committed": False,
            "deadline": "day-1-evening",
            "promise_status": transition.status,
        }
        beliefs.extend(
            (
                PlannedBelief(
                    proposition_key="player-promise-marta-shipment",
                    subject_kind="promise",
                    subject_id="marta-shipment",
                    predicate="player_promised_help",
                    holder_id="marta",
                    narrative_text=marta_text,
                    normalized_position=position,
                    confidence=1.0,
                    salience=1.0,
                    source_kind="world_event",
                    source_id="player",
                    embedding=marta_embedding.vector,
                    embedding_model_id=marta_embedding.model_id,
                ),
                PlannedBelief(
                    proposition_key="player-promise-marta-shipment",
                    subject_kind="promise",
                    subject_id="marta-shipment",
                    predicate="player_promised_help",
                    holder_id="pip",
                    narrative_text=pip_text,
                    normalized_position={
                        **position,
                        "stance": "accepted",
                        "public": True,
                    },
                    confidence=0.9 if kept else 0.94,
                    salience=0.95,
                    source_kind="hearsay",
                    source_id="marta",
                    embedding=pip_embedding.vector,
                    embedding_model_id=pip_embedding.model_id,
                    parent_holder_id="marta",
                    mutation_note=(
                        "Pip turns the cost of keeping the promise into public admiration."
                        if kept
                        else "Pip turns a missed deadline into a judgment about the player's word."
                    ),
                    trust_at_time=0.85,
                    retelling_provider_id="deterministic",
                    retelling_model_id="hearsay-promise-consequence-v1",
                    inference_attempts=0,
                    inference_latency_ms=0,
                ),
            )
        )
        relationships.extend(
            (
                PlannedRelationship(
                    a_kind="npc",
                    a_id="marta",
                    b_kind="player",
                    b_id="player",
                    trust_delta=0.2 if kept else -0.45,
                    affinity_delta=0.15 if kept else -0.25,
                    debt_delta=-0.25,
                    trust_floor=0.7 if kept else None,
                    trust_ceiling=0.25 if not kept else None,
                ),
                PlannedRelationship(
                    a_kind="npc",
                    a_id="pip",
                    b_kind="npc",
                    b_id="marta",
                    trust_delta=0.05,
                ),
            )
        )
    return MemoryEffects(
        beliefs=tuple(beliefs),
        relationships=tuple(relationships),
        gossip_tick_number=(
            response.snapshot.world_tick
            if beliefs and response.snapshot.world_tick > 0
            else None
        ),
    )


def derive_dialogue_treatment(
    memories: list[RecalledMemory],
    current_relationship: int,
) -> DialogueTreatment:
    if any(memory.contested for memory in memories):
        return DialogueTreatment(
            relationship_score=min(current_relationship, -5),
            cue="Guarded: they are weighing conflicting accounts.",
            choices=(
                DialogueChoiceState(
                    id="ask_for_evidence",
                    label="Ask what would prove it",
                    prompt="What evidence would settle this for you?",
                ),
                DialogueChoiceState(
                    id="clarify_account",
                    label="Clarify your account",
                    prompt="Let me clarify what really happened.",
                ),
            ),
            trust_ceiling=0.45,
        )

    proposition_keys = {memory.proposition_key for memory in memories}
    if "bram-price-confrontation" in proposition_keys:
        return DialogueTreatment(
            relationship_score=min(current_relationship, -10),
            cue="Cold: the market-row rumor has changed their treatment of you.",
            choices=(
                DialogueChoiceState(
                    id="ask_what_they_heard",
                    label="Ask what they heard",
                    prompt="Tell me exactly what you heard about Bram and me.",
                ),
                DialogueChoiceState(
                    id="set_record_straight",
                    label="Set the record straight",
                    prompt="I want to correct the story about Bram.",
                ),
            ),
            trust_ceiling=0.4,
        )

    promise_memories = [
        memory
        for memory in memories
        if memory.proposition_key == "player-promise-marta-shipment"
    ]
    promise_status = next(
        (
            memory.normalized_position.get("promise_status")
            for memory in promise_memories
            if memory.normalized_position.get("promise_status") is not None
        ),
        None,
    )
    if promise_status == "broken":
        return DialogueTreatment(
            relationship_score=min(current_relationship, -20),
            cue="Bitter: they remember that evening arrived before your help did.",
            choices=(
                DialogueChoiceState(
                    id="apologize_for_broken_promise",
                    label="Apologize",
                    prompt="I broke my word to Marta. I am sorry.",
                ),
                DialogueChoiceState(
                    id="ask_to_rebuild_trust",
                    label="Ask how to make amends",
                    prompt="What would it take to earn back the town's trust?",
                ),
            ),
            trust_ceiling=0.25,
        )

    if promise_status == "kept":
        return DialogueTreatment(
            relationship_score=max(current_relationship, 20),
            cue="Grateful: they remember that you paid a real cost to keep your word.",
            choices=(
                DialogueChoiceState(
                    id="ask_for_endorsement",
                    label="Ask for endorsement",
                    prompt="I kept my word. Will you speak for me in the election?",
                ),
                DialogueChoiceState(
                    id="call_in_goodwill",
                    label="Call in the goodwill",
                    prompt="Can you help me now that Marta's shipment is free?",
                ),
            ),
            trust_floor=0.7,
        )

    if promise_memories:
        return DialogueTreatment(
            relationship_score=max(current_relationship, 10),
            cue="Warmer: they remember the promise you made.",
            choices=(
                DialogueChoiceState(
                    id="ask_for_favor",
                    label="Ask for a favor",
                    prompt="Since you remember my promise, will you help me?",
                ),
                DialogueChoiceState(
                    id="ask_for_support",
                    label="Ask for support",
                    prompt="Can I count on your support if I keep my word?",
                ),
            ),
            trust_floor=0.6,
        )

    return DialogueTreatment(
        relationship_score=current_relationship,
        cue="Neutral: no recalled claim changes their treatment yet.",
        choices=(
            DialogueChoiceState(
                id="ask_about_town",
                label="Ask about the town",
                prompt="What should a newcomer know about Greyhaven?",
            ),
        ),
    )
