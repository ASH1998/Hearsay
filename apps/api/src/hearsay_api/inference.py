from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Literal, Never, Protocol

import structlog
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

logger = structlog.get_logger(__name__)
WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z'-]*")
CAPITALIZED_TOKEN_PATTERN = re.compile(r"\b[A-Z][A-Za-z'-]*")
GRAMMATICAL_CAPITALS = {"a", "an", "he", "i", "it", "she", "the", "they", "we"}
KNOWN_GREYHAVEN_ENTITIES = {
    "bram",
    "elias",
    "greyhaven",
    "marta",
    "nessa",
    "orin",
    "pip",
    "rhea",
    "talia",
}

if TYPE_CHECKING:
    from hearsay_api.config import Settings


class RumorRetellingRequest(BaseModel):
    original_claim: str = Field(min_length=1, max_length=500)
    speaker_id: str = Field(min_length=1, max_length=64)
    listener_id: str = Field(min_length=1, max_length=64)
    trust: float = Field(ge=0, le=1)
    context: str = Field(default="", max_length=500)


class SemanticPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suspect: str | None = Field(default=None, max_length=64)
    action: str | None = Field(default=None, max_length=64)
    object: str | None = Field(default=None, max_length=96)
    event: str | None = Field(default=None, max_length=64)
    target: str | None = Field(default=None, max_length=64)
    intent: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=64)
    stance: str | None = Field(default=None, max_length=64)


class RumorRetelling(BaseModel):
    retold_claim: str = Field(min_length=1, max_length=500)
    semantic_position: SemanticPosition
    drift_note: str = Field(min_length=1, max_length=300)
    confidence_delta: float = Field(ge=-0.25, le=0.1)


class DialogueRequest(BaseModel):
    npc_id: str = Field(min_length=1, max_length=64)
    player_message: str = Field(min_length=1, max_length=500)
    recalled_memories: list[str] = Field(default_factory=list, max_length=8)
    current_mood: str = Field(default="guarded", max_length=32)


class DialogueOutput(BaseModel):
    text: str = Field(min_length=1, max_length=700)
    intent: Literal["inform", "question", "refuse", "warn", "bargain"]
    mood: Literal["warm", "guarded", "angry", "afraid", "neutral"]
    disclosed_claim_keys: list[str] = Field(default_factory=list, max_length=8)


class ContradictionRequest(BaseModel):
    current_position: dict[str, object]
    incoming_position: dict[str, object]
    source_trust: float = Field(ge=0, le=1)
    evidence_weight: float = Field(default=0, ge=-1, le=1)


class ContradictionOutput(BaseModel):
    classification: Literal["supports", "contradicts", "neutral", "uncertain"]
    rationale: str = Field(min_length=1, max_length=400)
    confidence: float = Field(ge=0, le=1)


@dataclass(frozen=True)
class InferenceResult[ResultValue]:
    value: ResultValue
    provider_id: str
    model_id: str
    fallback_used: bool
    fallback_reason: str | None
    attempts: int
    latency_ms: float


class InferenceProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    def retell_rumor(self, request: RumorRetellingRequest) -> RumorRetelling: ...

    def generate_dialogue(self, request: DialogueRequest) -> DialogueOutput: ...

    def classify_contradiction(
        self,
        request: ContradictionRequest,
    ) -> ContradictionOutput: ...


class DeterministicInferenceProvider:
    @property
    def provider_id(self) -> str:
        return "deterministic"

    @property
    def model_id(self) -> str:
        return "hearsay-rules-v1"

    def retell_rumor(self, request: RumorRetellingRequest) -> RumorRetelling:
        if request.speaker_id == "bram" and request.listener_id == "pip":
            return RumorRetelling(
                retold_claim=("The newcomer tried to ruin Bram in the middle of market row."),
                semantic_position=SemanticPosition(
                    event="price_confrontation",
                    target="bram",
                    intent="ruin_bram",
                    location="market_row",
                ),
                drift_note=("A price dispute became a claim about malicious intent."),
                confidence_delta=max(
                    -0.25,
                    -0.28 + min(request.trust, 1.0) * 0.2,
                ),
            )
        return RumorRetelling(
            retold_claim=request.original_claim,
            semantic_position=SemanticPosition(stance="repeated_without_change"),
            drift_note="The deterministic fallback preserved the original claim.",
            confidence_delta=-0.05,
        )

    def generate_dialogue(self, request: DialogueRequest) -> DialogueOutput:
        memory = request.recalled_memories[0] if request.recalled_memories else None
        text = (
            f"I remember this much: {memory}"
            if memory
            else "I have heard nothing I would stake my name on."
        )
        return DialogueOutput(
            text=text,
            intent="inform" if memory else "refuse",
            mood="guarded",
        )

    def classify_contradiction(
        self,
        request: ContradictionRequest,
    ) -> ContradictionOutput:
        shared_keys = set(request.current_position) & set(request.incoming_position)
        differs = any(
            request.current_position[key] != request.incoming_position[key] for key in shared_keys
        )
        return ContradictionOutput(
            classification="contradicts" if differs else "supports",
            rationale=(
                "Shared semantic fields disagree."
                if differs
                else "No shared semantic field disagrees."
            ),
            confidence=0.9 if shared_keys else 0.55,
        )


class ModalInferenceProvider:
    def __init__(
        self,
        base_url: str,
        token_id: str,
        token_secret: str,
        model_id: str,
        timeout_seconds: float = 45,
        client: OpenAI | None = None,
    ) -> None:
        normalized_url = base_url.rstrip("/")
        if not normalized_url.endswith("/v1"):
            normalized_url = f"{normalized_url}/v1"
        self._model_id = model_id
        self.client = client or OpenAI(
            api_key="modal-proxy",
            base_url=normalized_url,
            default_headers={
                "Modal-Key": token_id,
                "Modal-Secret": token_secret,
            },
            timeout=timeout_seconds,
            max_retries=0,
        )

    @property
    def provider_id(self) -> str:
        return "modal"

    @property
    def model_id(self) -> str:
        return self._model_id

    def _complete(
        self,
        schema: type[BaseModel],
        schema_name: str,
        system_prompt: str,
        payload: BaseModel,
    ) -> BaseModel:
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.model_dump_json()},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
            temperature=0,
            max_tokens=2_000,
        )
        content = response.choices[0].message.content
        if not content:
            finish_reason = response.choices[0].finish_reason
            raise ValueError(
                "The inference provider returned no structured content "
                f"(finish_reason={finish_reason})."
            )
        return schema.model_validate_json(content)

    def retell_rumor(self, request: RumorRetellingRequest) -> RumorRetelling:
        output = self._complete(
            RumorRetelling,
            "rumor_retelling",
            (
                "Retell the supplied claim in a compact Greyhaven rumor voice. "
                "Do not add named people, places, objects, or events absent from "
                "the input. Preserve the core event while allowing controlled drift. "
                "Return one JSON object only. Keep retold_claim under 35 words and "
                "drift_note under 25 words. Use only the declared semantic fields."
            ),
            request,
        )
        retelling = RumorRetelling.model_validate(output)
        if len(WORD_PATTERN.findall(retelling.retold_claim)) > 35:
            raise ValueError("The retold claim exceeds the 35-word content limit.")
        allowed_tokens = {
            token.lower()
            for token in WORD_PATTERN.findall(f"{request.original_claim} {request.context}")
        }
        introduced_names = set()
        for match in CAPITALIZED_TOKEN_PATTERN.finditer(retelling.retold_claim):
            token = match.group(0)
            normalized = token.lower()
            if normalized in allowed_tokens or normalized in GRAMMATICAL_CAPITALS:
                continue
            if normalized in KNOWN_GREYHAVEN_ENTITIES or match.start() > 0:
                introduced_names.add(token)
        if introduced_names:
            raise ValueError("The retold claim introduced an undeclared named entity.")
        return retelling

    def generate_dialogue(self, request: DialogueRequest) -> DialogueOutput:
        output = self._complete(
            DialogueOutput,
            "npc_dialogue",
            (
                "Write one concise in-character Greyhaven response using only the "
                "provided memories. Never invent evidence or change game state."
            ),
            request,
        )
        return DialogueOutput.model_validate(output)

    def classify_contradiction(
        self,
        request: ContradictionRequest,
    ) -> ContradictionOutput:
        output = self._complete(
            ContradictionOutput,
            "contradiction_analysis",
            (
                "Classify semantic agreement only. Explain briefly; deterministic "
                "game code decides whether any belief changes."
            ),
            request,
        )
        return ContradictionOutput.model_validate(output)


class SafeInferenceProvider:
    def __init__(
        self,
        primary: InferenceProvider,
        fallback: InferenceProvider | None = None,
        max_attempts: int = 2,
    ) -> None:
        self.primary = primary
        self.fallback = fallback or DeterministicInferenceProvider()
        self.max_attempts = max(1, max_attempts)

    @property
    def provider_id(self) -> str:
        return self.primary.provider_id

    @property
    def model_id(self) -> str:
        return self.primary.model_id

    def _run[ResultValue](
        self,
        operation: str,
        primary_call: Callable[[], ResultValue],
        fallback_call: Callable[[], ResultValue],
    ) -> InferenceResult[ResultValue]:
        started = perf_counter()
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                value = primary_call()
                return InferenceResult(
                    value=value,
                    provider_id=self.primary.provider_id,
                    model_id=self.primary.model_id,
                    fallback_used=False,
                    fallback_reason=None,
                    attempts=attempt,
                    latency_ms=(perf_counter() - started) * 1000,
                )
            except Exception as error:
                last_error = error
                logger.warning(
                    "inference_attempt_failed",
                    provider=self.primary.provider_id,
                    model=self.primary.model_id,
                    operation=operation,
                    attempt=attempt,
                    reason=type(error).__name__,
                )

        reason = type(last_error).__name__ if last_error is not None else "UnknownError"
        value = fallback_call()
        logger.warning(
            "inference_fallback_used",
            provider=self.primary.provider_id,
            model=self.primary.model_id,
            operation=operation,
            attempts=self.max_attempts,
            reason=reason,
        )
        return InferenceResult(
            value=value,
            provider_id=self.primary.provider_id,
            model_id=self.primary.model_id,
            fallback_used=True,
            fallback_reason=reason,
            attempts=self.max_attempts,
            latency_ms=(perf_counter() - started) * 1000,
        )

    def retell_rumor(
        self,
        request: RumorRetellingRequest,
    ) -> InferenceResult[RumorRetelling]:
        return self._run(
            "retell_rumor",
            lambda: self.primary.retell_rumor(request),
            lambda: self.fallback.retell_rumor(request),
        )

    def generate_dialogue(
        self,
        request: DialogueRequest,
    ) -> InferenceResult[DialogueOutput]:
        return self._run(
            "generate_dialogue",
            lambda: self.primary.generate_dialogue(request),
            lambda: self.fallback.generate_dialogue(request),
        )

    def classify_contradiction(
        self,
        request: ContradictionRequest,
    ) -> InferenceResult[ContradictionOutput]:
        return self._run(
            "classify_contradiction",
            lambda: self.primary.classify_contradiction(request),
            lambda: self.fallback.classify_contradiction(request),
        )


class UnavailableInferenceProvider:
    def __init__(self, provider_id: str, model_id: str, reason: str) -> None:
        self._provider_id = provider_id
        self._model_id = model_id
        self.reason = reason

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def model_id(self) -> str:
        return self._model_id

    def _raise(self) -> Never:
        raise RuntimeError(self.reason)

    def retell_rumor(self, request: RumorRetellingRequest) -> RumorRetelling:
        self._raise()

    def generate_dialogue(self, request: DialogueRequest) -> DialogueOutput:
        self._raise()

    def classify_contradiction(
        self,
        request: ContradictionRequest,
    ) -> ContradictionOutput:
        self._raise()


def create_inference_provider(settings: Settings) -> SafeInferenceProvider:
    fallback = DeterministicInferenceProvider()
    token_id = (
        settings.modal_proxy_token_id.get_secret_value()
        if settings.modal_proxy_token_id is not None
        else None
    )
    token_secret = (
        settings.modal_proxy_token_secret.get_secret_value()
        if settings.modal_proxy_token_secret is not None
        else None
    )
    modal_is_configured = bool(settings.modal_proxy_url and token_id and token_secret)
    if settings.llm_provider == "fallback" or (
        settings.llm_provider == "auto" and not modal_is_configured
    ):
        return SafeInferenceProvider(
            primary=fallback,
            fallback=fallback,
            max_attempts=1,
        )

    if not modal_is_configured:
        primary: InferenceProvider = UnavailableInferenceProvider(
            provider_id="modal",
            model_id=settings.modal_model,
            reason="Modal inference configuration is incomplete.",
        )
    else:
        assert settings.modal_proxy_url is not None
        assert token_id is not None
        assert token_secret is not None
        primary = ModalInferenceProvider(
            base_url=settings.modal_proxy_url,
            token_id=token_id,
            token_secret=token_secret,
            model_id=settings.modal_model,
            timeout_seconds=settings.inference_timeout_seconds,
        )
    return SafeInferenceProvider(
        primary=primary,
        fallback=fallback,
        max_attempts=settings.inference_max_attempts,
    )
