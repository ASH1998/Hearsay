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

from hearsay_api.content import GreyhavenContent
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
class VisibleAmbientEcho:
    listener_id: str
    proposition_key: str
    speaker_id: str
    text: str


@dataclass(frozen=True)
class MemoryEffects:
    beliefs: tuple[PlannedBelief, ...] = ()
    relationships: tuple[PlannedRelationship, ...] = ()
    gossip_tick_number: int | None = None
    visible_ambient_echoes: tuple[VisibleAmbientEcho, ...] = ()


@dataclass(frozen=True)
class PromiseTransition:
    promisee_id: str
    status: Literal["kept", "broken"]


def plan_action_memory(
    request: ActionRequest,
    response: ActionResponse,
    embeddings: EmbeddingProvider,
    content: GreyhavenContent,
    retelling: InferenceResult[RumorRetelling] | None = None,
    dialogue_treatment: DialogueTreatment | None = None,
    promise_transitions: tuple[PromiseTransition, ...] = (),
    town_event_transitions: tuple[str, ...] = (),
) -> MemoryEffects:
    primary = _plan_primary_action_memory(
        request,
        response,
        embeddings,
        content,
        retelling,
        dialogue_treatment,
    )
    promise = _plan_promise_transitions(
        promise_transitions,
        response,
        embeddings,
    )
    town_events = _plan_town_event_transitions(town_event_transitions)
    pre_echo_beliefs = (
        primary.beliefs
        + promise.beliefs
        + town_events.beliefs
    )
    ambient_echoes = _plan_ambient_echoes(
        pre_echo_beliefs,
        response,
        embeddings,
        content,
    )
    return MemoryEffects(
        beliefs=pre_echo_beliefs + ambient_echoes.beliefs,
        relationships=(
            primary.relationships
            + promise.relationships
            + town_events.relationships
        ),
        gossip_tick_number=(
            primary.gossip_tick_number
            if primary.gossip_tick_number is not None
            else promise.gossip_tick_number
        ),
        visible_ambient_echoes=ambient_echoes.visible_ambient_echoes,
    )


def _plan_primary_action_memory(
    request: ActionRequest,
    response: ActionResponse,
    embeddings: EmbeddingProvider,
    content: GreyhavenContent,
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

    bram_approach_verbs = {
        ActionVerb.CONFRONT,
        ActionVerb.THREATEN_BRAM,
        ActionVerb.FLATTER_BRAM,
        ActionVerb.NEGOTIATE_BRAM,
        ActionVerb.LIE_TO_BRAM,
    }
    if request.verb in bram_approach_verbs and request.target_id == "bram":
        approach_verb = (
            ActionVerb.NEGOTIATE_BRAM.value
            if request.verb == ActionVerb.CONFRONT
            else request.verb.value
        )
        approach = content.bram_approaches_by_verb[approach_verb]
        original = approach.original_claim
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
                        "approach": approach_verb,
                        "election_contribution": approach.election_contribution,
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
                        "approach": approach_verb,
                        "election_contribution": approach.election_contribution,
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
                    trust_delta=approach.relationship_delta / 100,
                    affinity_delta=approach.relationship_delta / 200,
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

    argument_choice_verbs = {
        ActionVerb.SIDE_WITH_BRAM,
        ActionVerb.SIDE_WITH_NESSA,
        ActionVerb.CALM_ARGUMENT,
    }
    if request.verb in argument_choice_verbs:
        choice = content.argument_choices_by_verb[request.verb.value]
        beliefs: list[PlannedBelief] = []
        for holder_id, contribution in (
            choice.holder_election_contributions.items()
        ):
            narrative = choice.memory_text
            text_embedding = embeddings.embed(narrative)
            beliefs.append(
                PlannedBelief(
                    proposition_key="public-argument-player-intervention",
                    subject_kind="event",
                    subject_id="bram-nessa-argument",
                    predicate="player_intervened_in_argument",
                    holder_id=holder_id,
                    narrative_text=narrative,
                    normalized_position={
                        "stance": "witnessed",
                        "choice": request.verb.value,
                        "public": True,
                        "election_contribution": contribution,
                    },
                    confidence=1.0,
                    salience=0.95,
                    source_kind="player_action",
                    source_id="player",
                    embedding=text_embedding.vector,
                    embedding_model_id=text_embedding.model_id,
                )
            )
        return MemoryEffects(
            beliefs=tuple(beliefs),
            relationships=(
                PlannedRelationship(
                    a_kind="npc",
                    a_id="bram",
                    b_kind="player",
                    b_id="player",
                    trust_delta=choice.bram_relationship_delta / 100,
                    affinity_delta=choice.bram_relationship_delta / 200,
                ),
                PlannedRelationship(
                    a_kind="npc",
                    a_id="nessa",
                    b_kind="player",
                    b_id="player",
                    trust_delta=choice.nessa_relationship_delta / 100,
                    affinity_delta=choice.nessa_relationship_delta / 200,
                ),
            ),
        )

    if request.verb == ActionVerb.ACCEPT_NESSA_FAVOR:
        text = (
            "Nessa entrusted the player with the storm-dated harbor log "
            "to show Constable Elias."
        )
        embedded = embeddings.embed(text)
        return MemoryEffects(
            beliefs=(
                PlannedBelief(
                    proposition_key="nessa-storm-harbor-log",
                    subject_kind="favor",
                    subject_id="nessa_harbor_log",
                    predicate="harbor_log_proves_storm_timing",
                    holder_id="nessa",
                    narrative_text=text,
                    normalized_position={
                        "status": "entrusted",
                        "nessa_protected_crews": True,
                    },
                    confidence=1.0,
                    salience=0.95,
                    source_kind="firsthand",
                    source_id="nessa",
                    embedding=embedded.vector,
                    embedding_model_id=embedded.model_id,
                ),
            ),
            relationships=(
                PlannedRelationship(
                    a_kind="npc",
                    a_id="nessa",
                    b_kind="player",
                    b_id="player",
                    trust_delta=0.1,
                ),
            ),
        )

    if request.verb == ActionVerb.DELIVER_HARBOR_LOG:
        text = content.favors_by_id["nessa_harbor_log"].correction_text
        embedded = embeddings.embed(text)
        harbor_beliefs = tuple(
            PlannedBelief(
                proposition_key="nessa-storm-harbor-log",
                subject_kind="favor",
                subject_id="nessa_harbor_log",
                predicate="harbor_log_proves_storm_timing",
                holder_id=holder_id,
                narrative_text=text,
                normalized_position={
                    "status": "verified",
                    "nessa_protected_crews": True,
                    "election_contribution": contribution,
                },
                confidence=1.0,
                salience=1.0,
                source_kind="documentary_evidence",
                source_id="harbor_log",
                embedding=embedded.vector,
                embedding_model_id=embedded.model_id,
            )
            for holder_id, contribution in (
                ("nessa", 0.45),
                ("elias", 0.4),
            )
        )
        return MemoryEffects(
            beliefs=harbor_beliefs,
            relationships=(
                PlannedRelationship(
                    a_kind="npc",
                    a_id="nessa",
                    b_kind="player",
                    b_id="player",
                    trust_delta=0.25,
                ),
                PlannedRelationship(
                    a_kind="npc",
                    a_id="elias",
                    b_kind="player",
                    b_id="player",
                    trust_delta=0.1,
                ),
            ),
        )

    if request.verb == ActionVerb.CORRECT_STORM_RUMOR:
        text = content.favors_by_id["nessa_harbor_log"].correction_text
        embedded = embeddings.embed(text)
        return MemoryEffects(
            beliefs=(
                PlannedBelief(
                    proposition_key="nessa-storm-harbor-log",
                    subject_kind="favor",
                    subject_id="nessa_harbor_log",
                    predicate="harbor_log_proves_storm_timing",
                    holder_id="pip",
                    narrative_text=text,
                    normalized_position={
                        "status": "corrected_publicly",
                        "nessa_protected_crews": True,
                        "election_contribution": 0.35,
                    },
                    confidence=0.98,
                    salience=1.0,
                    source_kind="documentary_evidence",
                    source_id="elias",
                    embedding=embedded.vector,
                    embedding_model_id=embedded.model_id,
                    parent_holder_id="elias",
                    mutation_note=(
                        "The player preserves Elias's evidence-backed correction."
                    ),
                    trust_at_time=0.9,
                    retelling_provider_id="deterministic",
                    retelling_model_id="hearsay-evidence-correction-v1",
                    inference_attempts=0,
                    inference_latency_ms=0,
                ),
            ),
        )

    if request.verb == ActionVerb.ASK_NESSA_ENDORSEMENT:
        nessa_text = (
            "Nessa publicly endorsed the player for proving the storm protected "
            "crews rather than abandoned cargo."
        )
        dock_text = (
            "Nessa says the newcomer brought proof when the harbor was being blamed."
        )
        nessa_embedding = embeddings.embed(nessa_text)
        dock_embedding = embeddings.embed(dock_text)
        return MemoryEffects(
            beliefs=(
                PlannedBelief(
                    proposition_key="nessa-storm-harbor-log",
                    subject_kind="favor",
                    subject_id="nessa_harbor_log",
                    predicate="harbor_log_proves_storm_timing",
                    holder_id="nessa",
                    narrative_text=nessa_text,
                    normalized_position={
                        "status": "endorsed",
                        "nessa_protected_crews": True,
                        "election_contribution": 0.6,
                    },
                    confidence=1.0,
                    salience=1.0,
                    source_kind="firsthand",
                    source_id="nessa",
                    embedding=nessa_embedding.vector,
                    embedding_model_id=nessa_embedding.model_id,
                ),
                *(
                    PlannedBelief(
                        proposition_key="nessa-storm-harbor-log",
                        subject_kind="favor",
                        subject_id="nessa_harbor_log",
                        predicate="harbor_log_proves_storm_timing",
                        holder_id=holder_id,
                        narrative_text=dock_text,
                        normalized_position={
                            "status": "endorsed",
                            "nessa_protected_crews": True,
                            "election_contribution": 0.35,
                        },
                        confidence=0.92,
                        salience=0.9,
                        source_kind="hearsay",
                        source_id="nessa",
                        embedding=dock_embedding.vector,
                        embedding_model_id=dock_embedding.model_id,
                        parent_holder_id="nessa",
                        mutation_note=(
                            "The dock workers turn Nessa's endorsement into faction backing."
                        ),
                        trust_at_time=0.9,
                        retelling_provider_id="deterministic",
                        retelling_model_id="hearsay-faction-endorsement-v1",
                        inference_attempts=0,
                        inference_latency_ms=0,
                    )
                    for holder_id in ("jonas", "mae")
                ),
            ),
            relationships=(
                PlannedRelationship(
                    a_kind="npc",
                    a_id="nessa",
                    b_kind="player",
                    b_id="player",
                    trust_floor=0.8,
                    affinity_delta=0.2,
                ),
            ),
        )

    if request.verb == ActionVerb.ACCEPT_ORIN_CONFESSION:
        secret = content.favors_by_id["orin_election_confession"].correction_text
        orin_text = (
            "Orin entrusted the player with a dying guild clerk's account: "
            "Rhea changed two marks in the previous election tally."
        )
        orin_embedding = embeddings.embed(orin_text)
        player_embedding = embeddings.embed(secret)
        return MemoryEffects(
            beliefs=(
                PlannedBelief(
                    proposition_key="orin-rhea-election-confession",
                    subject_kind="favor",
                    subject_id="orin_election_confession",
                    predicate="rhea_altered_previous_election_tally",
                    holder_id="orin",
                    narrative_text=orin_text,
                    normalized_position={
                        "resolution": "entrusted",
                        "rhea_altered_tally": True,
                    },
                    confidence=0.98,
                    salience=1.0,
                    source_kind="confession",
                    source_id="guild_clerk",
                    embedding=orin_embedding.vector,
                    embedding_model_id=orin_embedding.model_id,
                ),
                PlannedBelief(
                    proposition_key="orin-rhea-election-confession",
                    subject_kind="favor",
                    subject_id="orin_election_confession",
                    predicate="rhea_altered_previous_election_tally",
                    holder_id="player",
                    narrative_text=secret,
                    normalized_position={
                        "resolution": "entrusted",
                        "rhea_altered_tally": True,
                    },
                    confidence=0.98,
                    salience=1.0,
                    source_kind="confession",
                    source_id="orin",
                    embedding=player_embedding.vector,
                    embedding_model_id=player_embedding.model_id,
                    parent_holder_id="orin",
                    mutation_note="Orin gives the player the clerk's account intact.",
                    trust_at_time=0.8,
                    retelling_provider_id="deterministic",
                    retelling_model_id="hearsay-confession-transfer-v1",
                    inference_attempts=0,
                    inference_latency_ms=0,
                ),
            ),
            relationships=(
                PlannedRelationship(
                    a_kind="npc",
                    a_id="orin",
                    b_kind="player",
                    b_id="player",
                    trust_delta=0.1,
                ),
            ),
        )

    if request.verb in {
        ActionVerb.REVEAL_ORIN_CONFESSION,
        ActionVerb.CONCEAL_ORIN_CONFESSION,
    }:
        confession_choice = content.favor_choices_by_verb[
            request.verb.value
        ]
        resolution = confession_choice.resolution
        player_text = (
            f"The player chose to {resolution.removesuffix('ed')} Orin's "
            "account that Rhea altered two marks in the previous tally."
        )
        player_embedding = embeddings.embed(player_text)
        confession_beliefs: list[PlannedBelief] = [
            PlannedBelief(
                proposition_key="orin-rhea-election-confession",
                subject_kind="favor",
                subject_id="orin_election_confession",
                predicate="rhea_altered_previous_election_tally",
                holder_id="player",
                narrative_text=player_text,
                normalized_position={
                    "resolution": resolution,
                    "rhea_altered_tally": True,
                },
                confidence=1.0,
                salience=1.0,
                source_kind="player_decision",
                source_id="player",
                embedding=player_embedding.vector,
                embedding_model_id=player_embedding.model_id,
            )
        ]
        for holder_id, contribution in (
            confession_choice.holder_election_contributions.items()
        ):
            text_embedding = embeddings.embed(confession_choice.memory_text)
            parent_holder_id = confession_choice.transmission_parents[holder_id]
            confession_beliefs.append(
                PlannedBelief(
                    proposition_key="orin-rhea-election-confession",
                    subject_kind="favor",
                    subject_id="orin_election_confession",
                    predicate="rhea_altered_previous_election_tally",
                    holder_id=holder_id,
                    narrative_text=confession_choice.memory_text,
                    normalized_position={
                        "resolution": resolution,
                        "rhea_altered_tally": True,
                        "election_contribution": contribution,
                    },
                    confidence=1.0 if holder_id in {"orin", "elias"} else 0.94,
                    salience=1.0,
                    source_kind=(
                        "direct_disclosure"
                        if resolution == "revealed"
                        else "moral_endorsement"
                    ),
                    source_id=parent_holder_id,
                    embedding=text_embedding.vector,
                    embedding_model_id=text_embedding.model_id,
                    parent_holder_id=parent_holder_id,
                    mutation_note=(
                        "The player discloses Orin's account without changing it."
                        if resolution == "revealed"
                        else "Orin turns the sealed confidence into a public blessing."
                    ),
                    trust_at_time=0.85,
                    retelling_provider_id="deterministic",
                    retelling_model_id=f"hearsay-confession-{resolution}-v1",
                    inference_attempts=0,
                    inference_latency_ms=0,
                )
            )
        return MemoryEffects(
            beliefs=tuple(confession_beliefs),
            relationships=tuple(
                PlannedRelationship(
                    a_kind="npc",
                    a_id=resident_id,
                    b_kind="player",
                    b_id="player",
                    trust_delta=delta / 100,
                    affinity_delta=delta / 200,
                )
                for resident_id, delta in (
                    confession_choice.relationship_deltas.items()
                )
            ),
            gossip_tick_number=(
                response.snapshot.world_tick
                if "pip" in confession_choice.holder_election_contributions
                else None
            ),
        )

    if request.verb == ActionVerb.ACCEPT_TALIA_FAVOR:
        fact = content.favors_by_id["talia_sick_house"].correction_text
        talia_text = (
            "Talia entrusted the player with Oswin's ordinary fever, a willow "
            "draught, and a request to protect his sick room from panic."
        )
        talia_embedding = embeddings.embed(talia_text)
        player_embedding = embeddings.embed(fact)
        return MemoryEffects(
            beliefs=(
                PlannedBelief(
                    proposition_key="talia-oswin-sick-house",
                    subject_kind="favor",
                    subject_id="talia_sick_house",
                    predicate="oswin_has_ordinary_fever",
                    holder_id="talia",
                    narrative_text=talia_text,
                    normalized_position={
                        "resolution": "entrusted",
                        "oswin_fever_ordinary": True,
                        "bread_safe": True,
                    },
                    confidence=1.0,
                    salience=0.95,
                    source_kind="medical_firsthand",
                    source_id="talia",
                    embedding=talia_embedding.vector,
                    embedding_model_id=talia_embedding.model_id,
                ),
                PlannedBelief(
                    proposition_key="talia-oswin-sick-house",
                    subject_kind="favor",
                    subject_id="talia_sick_house",
                    predicate="oswin_has_ordinary_fever",
                    holder_id="player",
                    narrative_text=fact,
                    normalized_position={
                        "resolution": "entrusted",
                        "oswin_fever_ordinary": True,
                        "bread_safe": True,
                    },
                    confidence=1.0,
                    salience=0.95,
                    source_kind="private_warning",
                    source_id="talia",
                    embedding=player_embedding.vector,
                    embedding_model_id=player_embedding.model_id,
                    parent_holder_id="talia",
                    mutation_note="Talia gives the medical facts to the player intact.",
                    trust_at_time=0.9,
                    retelling_provider_id="deterministic",
                    retelling_model_id="hearsay-private-warning-v1",
                    inference_attempts=0,
                    inference_latency_ms=0,
                ),
            ),
            relationships=(
                PlannedRelationship(
                    a_kind="npc",
                    a_id="talia",
                    b_kind="player",
                    b_id="player",
                    trust_delta=0.1,
                ),
            ),
        )

    if request.verb in {
        ActionVerb.HELP_OSWIN_QUIETLY,
        ActionVerb.GOSSIP_OSWIN_ILLNESS,
    }:
        favor_choice = content.favor_choices_by_verb[request.verb.value]
        resolution = favor_choice.resolution
        player_text = (
            "The player quietly delivered Talia's draught and kept Oswin's "
            "ordinary fever private."
            if resolution == "helped_quietly"
            else (
                "The player told Pip that Oswin had an ordinary fever, "
                "making Talia's private warning public."
            )
        )
        player_embedding = embeddings.embed(player_text)
        sick_house_beliefs: list[PlannedBelief] = [
            PlannedBelief(
                proposition_key="talia-oswin-sick-house",
                subject_kind="favor",
                subject_id="talia_sick_house",
                predicate="oswin_has_ordinary_fever",
                holder_id="player",
                narrative_text=player_text,
                normalized_position={
                    "resolution": resolution,
                    "oswin_fever_ordinary": True,
                    "bread_safe": True,
                },
                confidence=1.0,
                salience=1.0,
                source_kind="player_decision",
                source_id="player",
                embedding=player_embedding.vector,
                embedding_model_id=player_embedding.model_id,
            )
        ]
        for holder_id, contribution in (
            favor_choice.holder_election_contributions.items()
        ):
            text_embedding = embeddings.embed(favor_choice.memory_text)
            parent_holder_id = favor_choice.transmission_parents[holder_id]
            sick_house_beliefs.append(
                PlannedBelief(
                    proposition_key="talia-oswin-sick-house",
                    subject_kind="favor",
                    subject_id="talia_sick_house",
                    predicate="oswin_has_ordinary_fever",
                    holder_id=holder_id,
                    narrative_text=favor_choice.memory_text,
                    normalized_position={
                        "resolution": resolution,
                        "oswin_fever_ordinary": True,
                        "bread_safe": True,
                        "election_contribution": contribution,
                    },
                    confidence=1.0 if holder_id in {"talia", "oswin"} else 0.94,
                    salience=0.95,
                    source_kind=(
                        "quiet_family_endorsement"
                        if resolution == "helped_quietly"
                        else "public_health_gossip"
                    ),
                    source_id=parent_holder_id,
                    embedding=text_embedding.vector,
                    embedding_model_id=text_embedding.model_id,
                    parent_holder_id=parent_holder_id,
                    mutation_note=(
                        "Talia shares the player's quiet help across family lines."
                        if resolution == "helped_quietly"
                        else "The player gives Pip a private health fact for public warning."
                    ),
                    trust_at_time=0.85,
                    retelling_provider_id="deterministic",
                    retelling_model_id=f"hearsay-sick-house-{resolution}-v1",
                    inference_attempts=0,
                    inference_latency_ms=0,
                )
            )
        return MemoryEffects(
            beliefs=tuple(sick_house_beliefs),
            relationships=tuple(
                PlannedRelationship(
                    a_kind="npc",
                    a_id=resident_id,
                    b_kind="player",
                    b_id="player",
                    trust_delta=delta / 100,
                    affinity_delta=delta / 200,
                )
                for resident_id, delta in favor_choice.relationship_deltas.items()
            ),
            gossip_tick_number=(
                response.snapshot.world_tick
                if "pip" in favor_choice.holder_election_contributions
                else None
            ),
        )

    if request.verb == ActionVerb.ACCEPT_ELIAS_FAVOR:
        fact = content.favors_by_id["elias_wrongful_arrest"].correction_text
        elias_text = (
            "Elias entrusted the player with the omitted correction proving "
            "Tob Rill was jailed on Rhea's unsupported word."
        )
        elias_embedding = embeddings.embed(elias_text)
        player_embedding = embeddings.embed(fact)
        return MemoryEffects(
            beliefs=(
                PlannedBelief(
                    proposition_key="elias-tob-wrongful-arrest",
                    subject_kind="favor",
                    subject_id="elias_wrongful_arrest",
                    predicate="tob_wrongfully_jailed",
                    holder_id="elias",
                    narrative_text=elias_text,
                    normalized_position={
                        "resolution": "entrusted",
                        "tob_wrongfully_jailed": True,
                        "seal_found_in_rhea_desk": True,
                    },
                    confidence=1.0,
                    salience=1.0,
                    source_kind="official_record",
                    source_id="elias",
                    embedding=elias_embedding.vector,
                    embedding_model_id=elias_embedding.model_id,
                ),
                PlannedBelief(
                    proposition_key="elias-tob-wrongful-arrest",
                    subject_kind="favor",
                    subject_id="elias_wrongful_arrest",
                    predicate="tob_wrongfully_jailed",
                    holder_id="player",
                    narrative_text=fact,
                    normalized_position={
                        "resolution": "entrusted",
                        "tob_wrongfully_jailed": True,
                        "seal_found_in_rhea_desk": True,
                    },
                    confidence=1.0,
                    salience=1.0,
                    source_kind="official_record",
                    source_id="elias",
                    embedding=player_embedding.vector,
                    embedding_model_id=player_embedding.model_id,
                    parent_holder_id="elias",
                    mutation_note="Elias gives the omitted correction to the player intact.",
                    trust_at_time=0.9,
                    retelling_provider_id="deterministic",
                    retelling_model_id="hearsay-official-record-transfer-v1",
                    inference_attempts=0,
                    inference_latency_ms=0,
                ),
            ),
            relationships=(
                PlannedRelationship(
                    a_kind="npc",
                    a_id="elias",
                    b_kind="player",
                    b_id="player",
                    trust_delta=0.1,
                ),
            ),
        )

    if request.verb in {
        ActionVerb.INVESTIGATE_ELIAS_ARREST,
        ActionVerb.COVER_ELIAS_ARREST,
    }:
        favor_choice = content.favor_choices_by_verb[request.verb.value]
        resolution = favor_choice.resolution
        player_text = (
            "The player reopened Tob Rill's arrest and made Elias enter the "
            "missing correction into the public constable ledger."
            if resolution == "investigated"
            else (
                "The player helped Elias burn the omitted correction while "
                "Tob Rill watched from the constable-post doorway."
            )
        )
        player_embedding = embeddings.embed(player_text)
        arrest_beliefs: list[PlannedBelief] = [
            PlannedBelief(
                proposition_key="elias-tob-wrongful-arrest",
                subject_kind="favor",
                subject_id="elias_wrongful_arrest",
                predicate="tob_wrongfully_jailed",
                holder_id="player",
                narrative_text=player_text,
                normalized_position={
                    "resolution": resolution,
                    "tob_wrongfully_jailed": True,
                    "seal_found_in_rhea_desk": True,
                },
                confidence=1.0,
                salience=1.0,
                source_kind="player_decision",
                source_id="player",
                embedding=player_embedding.vector,
                embedding_model_id=player_embedding.model_id,
            )
        ]
        for holder_id, contribution in (
            favor_choice.holder_election_contributions.items()
        ):
            text_embedding = embeddings.embed(favor_choice.memory_text)
            parent_holder_id = favor_choice.transmission_parents[holder_id]
            arrest_beliefs.append(
                PlannedBelief(
                    proposition_key="elias-tob-wrongful-arrest",
                    subject_kind="favor",
                    subject_id="elias_wrongful_arrest",
                    predicate="tob_wrongfully_jailed",
                    holder_id=holder_id,
                    narrative_text=favor_choice.memory_text,
                    normalized_position={
                        "resolution": resolution,
                        "tob_wrongfully_jailed": True,
                        "seal_found_in_rhea_desk": True,
                        "election_contribution": contribution,
                    },
                    confidence=1.0 if holder_id in {"elias", "tob"} else 0.94,
                    salience=1.0,
                    source_kind=(
                        "corrected_public_record"
                        if resolution == "investigated"
                        else "witnessed_cover_up"
                    ),
                    source_id=parent_holder_id,
                    embedding=text_embedding.vector,
                    embedding_model_id=text_embedding.model_id,
                    parent_holder_id=parent_holder_id,
                    mutation_note=(
                        "The correction moves through the residents who verify it."
                        if resolution == "investigated"
                        else "Tob carries the witnessed destruction beyond the post."
                    ),
                    trust_at_time=0.85,
                    retelling_provider_id="deterministic",
                    retelling_model_id=f"hearsay-wrongful-arrest-{resolution}-v1",
                    inference_attempts=0,
                    inference_latency_ms=0,
                )
            )
        return MemoryEffects(
            beliefs=tuple(arrest_beliefs),
            relationships=tuple(
                PlannedRelationship(
                    a_kind="npc",
                    a_id=resident_id,
                    b_kind="player",
                    b_id="player",
                    trust_delta=delta / 100,
                    affinity_delta=delta / 200,
                )
                for resident_id, delta in favor_choice.relationship_deltas.items()
            ),
            gossip_tick_number=(
                response.snapshot.world_tick
                if "pip" in favor_choice.holder_election_contributions
                else None
            ),
        )

    if request.verb == ActionVerb.GIVE_SQUARE_SPEECH:
        text = (
            "The newcomer addressed Greyhaven as a candidate, but Pip thought "
            "the performance outran the proof."
        )
        embedded = embeddings.embed(text)
        return MemoryEffects(
            beliefs=(
                PlannedBelief(
                    proposition_key="player-square-speech",
                    subject_kind="event",
                    subject_id=f"day-{response.snapshot.day}-square-speech",
                    predicate="player_addressed_square",
                    holder_id="pip",
                    narrative_text=text,
                    normalized_position={
                        "day": response.snapshot.day,
                        "status": "heard",
                        "election_contribution": -0.01,
                    },
                    confidence=1.0,
                    salience=0.9,
                    source_kind="firsthand",
                    source_id="player",
                    embedding=embedded.vector,
                    embedding_model_id=embedded.model_id,
                ),
            ),
        )

    return MemoryEffects()


def _plan_town_event_transitions(
    transitions: tuple[str, ...],
) -> MemoryEffects:
    if "public_argument_begins" not in transitions:
        return MemoryEffects()
    return MemoryEffects(
        relationships=(
            PlannedRelationship(
                a_kind="npc",
                a_id="bram",
                b_kind="npc",
                b_id="nessa",
                trust_delta=-0.35,
                affinity_delta=-0.2,
            ),
            PlannedRelationship(
                a_kind="npc",
                a_id="nessa",
                b_kind="npc",
                b_id="bram",
                trust_delta=-0.35,
                affinity_delta=-0.2,
            ),
        )
    )


def _plan_ambient_echoes(
    beliefs: tuple[PlannedBelief, ...],
    response: ActionResponse,
    embeddings: EmbeddingProvider,
    content: GreyhavenContent,
) -> MemoryEffects:
    snapshot = response.snapshot
    if snapshot.world_tick == 0 or snapshot.action_count % 2 != 0:
        return MemoryEffects()
    pip_sources = [
        belief
        for belief in beliefs
        if belief.holder_id == "pip"
    ]
    if not pip_sources:
        return MemoryEffects()
    source = max(pip_sources, key=lambda belief: belief.salience)
    pip = next(npc for npc in snapshot.npcs if npc.id == "pip")
    candidates = sorted(
        npc.id
        for npc in snapshot.npcs
        if npc.id in content.ambients_by_id
        and npc.location_id == pip.location_id
    )
    if not candidates:
        return MemoryEffects()

    hop_count = min(
        len(candidates),
        2 + ((snapshot.seed + snapshot.world_tick) % 3),
    )
    offset = (snapshot.seed + snapshot.world_tick) % len(candidates)
    listeners = (
        candidates[offset:]
        + candidates[:offset]
    )[:hop_count]
    echo_beliefs: list[PlannedBelief] = []
    visible_echoes: list[VisibleAmbientEcho] = []
    for listener_id in listeners:
        ambient = content.ambients_by_id[listener_id]
        retold_text, mutation_note = _retell_ambient_echo(
            source.narrative_text,
            ambient.echo_style,
        )
        text_embedding = embeddings.embed(retold_text)
        echo_beliefs.append(
            PlannedBelief(
                proposition_key=source.proposition_key,
                subject_kind=source.subject_kind,
                subject_id=source.subject_id,
                predicate=source.predicate,
                holder_id=listener_id,
                narrative_text=retold_text,
                normalized_position={
                    **source.normalized_position,
                    "echo_hop": 2,
                    "echo_style": ambient.echo_style,
                },
                confidence=max(source.confidence - 0.08, 0.1),
                salience=max(source.salience - 0.12, 0.1),
                source_kind="hearsay",
                source_id="pip",
                embedding=text_embedding.vector,
                embedding_model_id=text_embedding.model_id,
                parent_holder_id="pip",
                mutation_note=mutation_note,
                trust_at_time=0.55,
                retelling_provider_id="deterministic",
                retelling_model_id="hearsay-ambient-echo-v1",
                inference_attempts=0,
                inference_latency_ms=0,
            )
        )
        visible_echoes.append(
            VisibleAmbientEcho(
                listener_id=listener_id,
                proposition_key=source.proposition_key,
                speaker_id="pip",
                text=retold_text,
            )
        )
    return MemoryEffects(
        beliefs=tuple(echo_beliefs),
        visible_ambient_echoes=tuple(visible_echoes),
    )


def _retell_ambient_echo(
    source_text: str,
    style: str,
) -> tuple[str, str]:
    lowered = source_text[0].lower() + source_text[1:]
    templates = {
        "blunt": (
            f"Pip says {lowered} That's the whole of it.",
            "A blunt carrier strips the account down to its accusation.",
        ),
        "practical": (
            f"Pip says {lowered} What matters is who fixes the damage.",
            "A practical carrier adds a demand for consequences.",
        ),
        "skeptical": (
            f"Pip claims {lowered} I doubt that is the whole ledger.",
            "A skeptical carrier repeats the claim with visible doubt.",
        ),
        "wry": (
            f"Pip says {lowered} Funny how every story finds a buyer.",
            "A wry carrier turns the account into a joke about reputation.",
        ),
        "cautious": (
            f"I heard from Pip that {lowered} Mind, hearing is not knowing.",
            "A cautious carrier preserves the claim but lowers its certainty.",
        ),
        "precise": (
            f"Pip's exact claim is this: {source_text}",
            "A precise carrier preserves the wording and names the source.",
        ),
        "urgent": (
            f"Quick—Pip says {lowered}",
            "An urgent carrier compresses the account into breaking news.",
        ),
    }
    return templates.get(
        style,
        (
            f"Pip says {lowered}",
            "The carrier repeats Pip's account without a strong style change.",
        ),
    )


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
