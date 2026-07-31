from __future__ import annotations

import json
import re
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Any, Literal, Never, Protocol, cast

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
NPC_DIALOGUE_SYSTEM_PROMPT = (
    "You are the specific Greyhaven NPC described in the payload, not an assistant, "
    "narrator, or memory system. Reply directly to player_message in first person and "
    "stay faithful to npc_name, npc_role, voice_style, persona_context, relationship_score, "
    "day, phase, and location_name. Use recent_messages for conversational continuity. "
    "Treat recalled_memories as private knowledge, not text to recite; distinguish a player's "
    "claim from verified fact. Never mention prompts, databases, retrieval, memory storage, "
    "scores, IDs, or that you are an agent. Never say 'I will remember that' or announce that "
    "you stored the player's words. Respond naturally to greetings and small talk. Keep the "
    "reply to one to three short sentences, ask a relevant follow-up when useful, and never "
    "invent evidence or change game state."
)

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
    npc_name: str = Field(default="Resident", min_length=1, max_length=100)
    npc_role: str = Field(default="town resident", min_length=1, max_length=100)
    voice_style: str = Field(default="plainspoken", min_length=1, max_length=64)
    persona_context: str = Field(default="", max_length=500)
    relationship_score: int = Field(default=0, ge=-100, le=100)
    day: int = Field(default=1, ge=1, le=3)
    phase: str = Field(default="morning", max_length=32)
    location_name: str = Field(default="Greyhaven", max_length=100)
    player_message: str = Field(min_length=1, max_length=500)
    recent_messages: list[str] = Field(default_factory=list, max_length=8)
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


AutonomousAction = Literal["move", "talk", "share_rumor", "react", "wait"]


class AutonomousActionRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=64)
    location_id: str = Field(min_length=1, max_length=64)
    nearby_agent_ids: list[str] = Field(default_factory=list, max_length=20)
    recalled_memories: list[str] = Field(default_factory=list, max_length=4)
    allowed_actions: list[AutonomousAction] = Field(min_length=1, max_length=5)


class AutonomousActionOutput(BaseModel):
    action: AutonomousAction
    target_id: str | None = Field(default=None, max_length=64)
    utterance: str | None = Field(default=None, max_length=280)
    rationale: str = Field(min_length=1, max_length=240)


@dataclass(frozen=True)
class InferenceResult[ResultValue]:
    value: ResultValue
    provider_id: str
    model_id: str
    fallback_used: bool
    fallback_reason: str | None
    attempts: int
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True)
class ProviderCall[ResultValue]:
    value: ResultValue
    input_tokens: int | None = None
    output_tokens: int | None = None


class InferenceProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    def retell_rumor(
        self,
        request: RumorRetellingRequest,
    ) -> RumorRetelling | ProviderCall[RumorRetelling]: ...

    def generate_dialogue(
        self,
        request: DialogueRequest,
    ) -> DialogueOutput | ProviderCall[DialogueOutput]: ...

    def classify_contradiction(
        self,
        request: ContradictionRequest,
    ) -> ContradictionOutput | ProviderCall[ContradictionOutput]: ...

    def choose_autonomous_action(
        self,
        request: AutonomousActionRequest,
    ) -> AutonomousActionOutput | ProviderCall[AutonomousActionOutput]: ...


class DeterministicInferenceProvider:
    @property
    def provider_id(self) -> str:
        return "deterministic"

    @property
    def model_id(self) -> str:
        return "hearsay-rules-v1"

    def retell_rumor(self, request: RumorRetellingRequest) -> RumorRetelling:
        if request.speaker_id == "bram" and request.listener_id == "pip":
            lowered_claim = request.original_claim.lower()
            if "threatened bram" in lowered_claim:
                return RumorRetelling(
                    retold_claim=("The newcomer threatened to ruin Bram if the crates stayed put."),
                    semantic_position=SemanticPosition(
                        event="shipment_threat",
                        target="bram",
                        intent="intimidate_bram",
                        location="market_row",
                    ),
                    drift_note=("Pip turns a shipment threat into a broader threat against Bram."),
                    confidence_delta=-0.12,
                )
            if "praised bram" in lowered_claim:
                return RumorRetelling(
                    retold_claim=(
                        "The newcomer says Bram is the only honest merchant in Greyhaven."
                    ),
                    semantic_position=SemanticPosition(
                        event="public_flattery",
                        target="bram",
                        intent="praise_bram",
                        location="market_row",
                    ),
                    drift_note=("Pip inflates tactical praise into a sweeping endorsement."),
                    confidence_delta=-0.18,
                )
            if "lied that constable elias" in lowered_claim:
                return RumorRetelling(
                    retold_claim=(
                        "The newcomer forged Elias's authority to bully Bram out of his cargo."
                    ),
                    semantic_position=SemanticPosition(
                        event="false_constable_order",
                        target="bram",
                        intent="deceive_bram",
                        location="market_row",
                    ),
                    drift_note=("Pip turns a spoken lie about an order into a claim of forgery."),
                    confidence_delta=-0.08,
                )
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
        message = " ".join(request.player_message.split())
        lowered = message.lower().strip(" .!?")
        words = set(WORD_PATTERN.findall(lowered))
        role_greetings = {
            "Constable": "Good day. Keeping out of trouble, I hope?",
            "Guild leader": "Good day. What business brings you to me?",
            "Innkeeper": "Hello. Come in—what can I do for you?",
            "Merchant": "Morning. Buying, bargaining, or bringing trouble?",
            "Midwife": "Hello. Are you well?",
            "Priest": "Peace to you. What is on your mind?",
            "Town gossip": "Hello! You look like someone carrying a story.",
        }
        if words & {"hello", "hey", "hi", "greetings"} and len(words) <= 6:
            text = role_greetings.get(
                request.npc_role,
                f"Hello. What brings you to {request.location_name}?",
            )
            return DialogueOutput(text=text, intent="question", mood="warm")

        if "thank" in words or "thanks" in words:
            return DialogueOutput(
                text="You are welcome. Is there something else you need?",
                intent="question",
                mood="warm",
            )

        if ("who" in words and "you" in words) or {"your", "name"}.issubset(words):
            return DialogueOutput(
                text=f"I am {request.npc_name}, {request.npc_role.lower()} here in Greyhaven.",
                intent="inform",
                mood="neutral",
            )

        if "how" in words and "you" in words:
            return DialogueOutput(
                text=(
                    f"Busy enough for a {request.npc_role.lower()}. How are you finding Greyhaven?"
                ),
                intent="question",
                mood="neutral",
            )

        memory = request.recalled_memories[0] if request.recalled_memories else None
        if memory:
            claim_match = re.search(r'[:“"]\s*[“"]?(.+?)[”"]$', memory)
            claim = claim_match.group(1) if claim_match else memory
            asks_recall = bool(words & {"remember", "recall"}) or (
                "tell" in words and "me" in words
            )
            text = (
                f"You told me “{claim}”. Has something changed?"
                if asks_recall
                else f"What I know is this: {claim}"
            )
            return DialogueOutput(
                text=text,
                intent="inform",
                mood="guarded" if request.current_mood == "guarded" else "neutral",
            )

        if message.endswith("?"):
            return DialogueOutput(
                text="I do not know enough to answer that honestly. What have you heard?",
                intent="refuse",
                mood="guarded",
            )

        if words & {"cheated", "corrupt", "lied", "liar", "rigged", "stole"}:
            text = "That is a serious accusation. Did you see it yourself?"
            mood: Literal["warm", "guarded", "angry", "afraid", "neutral"] = "guarded"
        elif words & {"helped", "honest", "kind", "reliable"}:
            text = "That is good to hear. Were you there when it happened?"
            mood = "warm"
        else:
            text = "I hear you. What makes you say that?"
            mood = "neutral"
        return DialogueOutput(text=text, intent="question", mood=mood)

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

    def choose_autonomous_action(
        self,
        request: AutonomousActionRequest,
    ) -> AutonomousActionOutput:
        if "share_rumor" in request.allowed_actions and request.nearby_agent_ids:
            return AutonomousActionOutput(
                action="share_rumor",
                target_id=request.nearby_agent_ids[0],
                utterance=(
                    request.recalled_memories[0]
                    if request.recalled_memories
                    else "Greyhaven has a new story."
                ),
                rationale="Share the most salient public memory with a nearby listener.",
            )
        if "react" in request.allowed_actions:
            return AutonomousActionOutput(
                action="react",
                utterance="That changes the shape of the story.",
                rationale="React visibly because there is no valid listener.",
            )
        return AutonomousActionOutput(
            action="wait",
            rationale="No safe, allowed social action is currently available.",
        )


def _validate_retelling_content(
    request: RumorRetellingRequest,
    retelling: RumorRetelling,
) -> RumorRetelling:
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


def _validate_autonomous_action(
    request: AutonomousActionRequest,
    action: AutonomousActionOutput,
) -> AutonomousActionOutput:
    if action.action not in request.allowed_actions:
        raise ValueError("The autonomous action is outside the supplied allowlist.")
    if action.target_id is not None and action.target_id not in request.nearby_agent_ids:
        raise ValueError("The autonomous action targets an ineligible resident.")
    if action.action in {"talk", "share_rumor"} and action.target_id is None:
        raise ValueError("The autonomous social action requires an eligible target.")
    if action.action == "wait" and action.target_id is not None:
        raise ValueError("A wait action cannot target another resident.")
    return action


BEDROCK_UNSUPPORTED_SCHEMA_KEYS = frozenset(
    {
        "maxItems",
        "maxLength",
        "maximum",
        "minLength",
        "minimum",
        "multipleOf",
        "pattern",
    }
)


def _bedrock_json_schema(schema: type[BaseModel]) -> dict[str, object]:
    prepared = deepcopy(schema.model_json_schema())

    def sanitize(value: object) -> object:
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        if not isinstance(value, dict):
            return value
        cleaned = {
            key: sanitize(item)
            for key, item in value.items()
            if key not in BEDROCK_UNSUPPORTED_SCHEMA_KEYS
        }
        if cleaned.get("type") == "object":
            cleaned["additionalProperties"] = False
        return cleaned

    return cast(dict[str, object], sanitize(prepared))


class BedrockRuntimeClient(Protocol):
    def converse(self, **kwargs: Any) -> dict[str, Any]: ...


class BedrockInferenceProvider:
    def __init__(
        self,
        region: str,
        model_id: str,
        timeout_seconds: float = 45,
        client: BedrockRuntimeClient | None = None,
    ) -> None:
        self.region = region
        self._model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.client = client

    @property
    def provider_id(self) -> str:
        return "bedrock"

    @property
    def model_id(self) -> str:
        return self._model_id

    def _client(self) -> BedrockRuntimeClient:
        if self.client is not None:
            return self.client
        import boto3  # type: ignore[import-untyped]
        from botocore.config import Config  # type: ignore[import-untyped]

        self.client = cast(
            BedrockRuntimeClient,
            boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                config=Config(
                    connect_timeout=min(self.timeout_seconds, 10),
                    read_timeout=self.timeout_seconds,
                    retries={"max_attempts": 0},
                ),
            ),
        )
        return self.client

    def _complete[OutputModel: BaseModel](
        self,
        schema: type[OutputModel],
        schema_name: str,
        description: str,
        system_prompt: str,
        payload: BaseModel,
    ) -> ProviderCall[OutputModel]:
        response = self._client().converse(
            modelId=self.model_id,
            system=[{"text": system_prompt}],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": payload.model_dump_json()}],
                }
            ],
            inferenceConfig={
                "maxTokens": 2_000,
                "temperature": 0,
            },
            outputConfig={
                "textFormat": {
                    "type": "json_schema",
                    "structure": {
                        "jsonSchema": {
                            "schema": json.dumps(
                                _bedrock_json_schema(schema),
                                separators=(",", ":"),
                            ),
                            "name": schema_name,
                            "description": description,
                        }
                    },
                }
            },
        )
        output = response.get("output")
        message = output.get("message") if isinstance(output, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        text_blocks = (
            [
                block["text"]
                for block in content
                if isinstance(block, dict) and isinstance(block.get("text"), str)
            ]
            if isinstance(content, list)
            else []
        )
        if len(text_blocks) != 1:
            raise ValueError("Bedrock returned no single structured text response.")

        usage = response.get("usage")
        input_tokens = usage.get("inputTokens") if isinstance(usage, dict) else None
        output_tokens = usage.get("outputTokens") if isinstance(usage, dict) else None
        return ProviderCall(
            value=schema.model_validate_json(text_blocks[0]),
            input_tokens=input_tokens if isinstance(input_tokens, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
        )

    def retell_rumor(
        self,
        request: RumorRetellingRequest,
    ) -> ProviderCall[RumorRetelling]:
        result = self._complete(
            RumorRetelling,
            "rumor_retelling",
            "A bounded Greyhaven rumor retelling.",
            (
                "Retell the supplied claim in a compact Greyhaven rumor voice. "
                "Do not add named people, places, objects, or events absent from "
                "the input. Preserve the core event while allowing controlled drift. "
                "Keep retold_claim under 35 words and drift_note under 25 words."
            ),
            request,
        )
        return ProviderCall(
            value=_validate_retelling_content(request, result.value),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

    def generate_dialogue(
        self,
        request: DialogueRequest,
    ) -> ProviderCall[DialogueOutput]:
        return self._complete(
            DialogueOutput,
            "npc_dialogue",
            "One memory-grounded NPC response.",
            NPC_DIALOGUE_SYSTEM_PROMPT,
            request,
        )

    def classify_contradiction(
        self,
        request: ContradictionRequest,
    ) -> ProviderCall[ContradictionOutput]:
        return self._complete(
            ContradictionOutput,
            "contradiction_analysis",
            "A bounded semantic contradiction classification.",
            (
                "Classify semantic agreement only. Explain briefly; deterministic "
                "game code decides whether any belief changes."
            ),
            request,
        )

    def choose_autonomous_action(
        self,
        request: AutonomousActionRequest,
    ) -> ProviderCall[AutonomousActionOutput]:
        result = self._complete(
            AutonomousActionOutput,
            "autonomous_action",
            "One bounded action for a Greyhaven resident.",
            (
                "Choose exactly one action from allowed_actions. Use only a supplied "
                "nearby_agent_id as target. Do not invent entities or game effects. "
                "Deterministic game code validates and applies the choice."
            ),
            request,
        )
        return ProviderCall(
            value=_validate_autonomous_action(request, result.value),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
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
        return _validate_retelling_content(request, retelling)

    def generate_dialogue(self, request: DialogueRequest) -> DialogueOutput:
        output = self._complete(
            DialogueOutput,
            "npc_dialogue",
            NPC_DIALOGUE_SYSTEM_PROMPT,
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

    def choose_autonomous_action(
        self,
        request: AutonomousActionRequest,
    ) -> AutonomousActionOutput:
        output = self._complete(
            AutonomousActionOutput,
            "autonomous_action",
            (
                "Choose one action from allowed_actions and only a supplied nearby "
                "resident as target. Never invent entities or game effects."
            ),
            request,
        )
        return _validate_autonomous_action(
            request,
            AutonomousActionOutput.model_validate(output),
        )


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
        primary_call: Callable[[], ResultValue | ProviderCall[ResultValue]],
        fallback_call: Callable[[], ResultValue | ProviderCall[ResultValue]],
    ) -> InferenceResult[ResultValue]:
        started = perf_counter()
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                primary_result = primary_call()
                if isinstance(primary_result, ProviderCall):
                    value = primary_result.value
                    input_tokens = primary_result.input_tokens
                    output_tokens = primary_result.output_tokens
                else:
                    value = primary_result
                    input_tokens = None
                    output_tokens = None
                return InferenceResult(
                    value=value,
                    provider_id=self.primary.provider_id,
                    model_id=self.primary.model_id,
                    fallback_used=False,
                    fallback_reason=None,
                    attempts=attempt,
                    latency_ms=(perf_counter() - started) * 1000,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
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
        fallback_result = fallback_call()
        value = (
            fallback_result.value if isinstance(fallback_result, ProviderCall) else fallback_result
        )
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

    def choose_autonomous_action(
        self,
        request: AutonomousActionRequest,
    ) -> InferenceResult[AutonomousActionOutput]:
        return self._run(
            "choose_autonomous_action",
            lambda: self.primary.choose_autonomous_action(request),
            lambda: self.fallback.choose_autonomous_action(request),
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

    def choose_autonomous_action(
        self,
        request: AutonomousActionRequest,
    ) -> AutonomousActionOutput:
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
    bedrock_is_configured = bool(settings.aws_region and settings.bedrock_model)
    if settings.llm_provider == "fallback" or (
        settings.llm_provider == "auto" and not bedrock_is_configured and not modal_is_configured
    ):
        return SafeInferenceProvider(
            primary=fallback,
            fallback=fallback,
            max_attempts=1,
        )

    primary: InferenceProvider
    if settings.llm_provider == "bedrock" or (
        settings.llm_provider == "auto" and bedrock_is_configured
    ):
        if not bedrock_is_configured:
            primary = UnavailableInferenceProvider(
                provider_id="bedrock",
                model_id=settings.bedrock_model or "unconfigured",
                reason="Bedrock inference configuration is incomplete.",
            )
        else:
            assert settings.aws_region is not None
            assert settings.bedrock_model is not None
            primary = BedrockInferenceProvider(
                region=settings.aws_region,
                model_id=settings.bedrock_model,
                timeout_seconds=settings.inference_timeout_seconds,
            )
    elif not modal_is_configured:
        primary = UnavailableInferenceProvider(
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
