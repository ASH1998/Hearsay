from __future__ import annotations

import json
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from openai import OpenAI
from pydantic import ValidationError

from hearsay_api.config import Settings
from hearsay_api.inference import (
    BEDROCK_UNSUPPORTED_SCHEMA_KEYS,
    AutonomousActionOutput,
    AutonomousActionRequest,
    BedrockInferenceProvider,
    ContradictionOutput,
    ContradictionRequest,
    DeterministicInferenceProvider,
    DialogueOutput,
    DialogueRequest,
    ModalInferenceProvider,
    ProviderCall,
    RumorRetelling,
    RumorRetellingRequest,
    SafeInferenceProvider,
    create_inference_provider,
)
from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import ActionRequest, CreateRunRequest
from hearsay_api.service import GameService


class FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.arguments: dict[str, object] = {}

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.arguments = kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content),
                )
            ]
        )


class FakeOpenAI:
    def __init__(self, content: str) -> None:
        self.completions = FakeCompletions(content)
        self.chat = SimpleNamespace(completions=self.completions)


class FakeBedrockRuntime:
    def __init__(
        self,
        content: str,
        *,
        input_tokens: int = 37,
        output_tokens: int = 19,
    ) -> None:
        self.content = content
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.arguments: dict[str, object] = {}

    def converse(self, **kwargs: object) -> dict[str, object]:
        self.arguments = kwargs
        return {
            "output": {
                "message": {
                    "content": [{"text": self.content}],
                }
            },
            "usage": {
                "inputTokens": self.input_tokens,
                "outputTokens": self.output_tokens,
            },
        }


class FailingInferenceProvider(DeterministicInferenceProvider):
    @property
    def provider_id(self) -> str:
        return "modal"

    @property
    def model_id(self) -> str:
        return "unavailable-test-model"

    def retell_rumor(self, request: RumorRetellingRequest) -> RumorRetelling:
        raise TimeoutError("a secret-bearing provider message that must not escape")

    def generate_dialogue(self, request: DialogueRequest) -> DialogueOutput:
        raise TimeoutError("provider timed out")

    def classify_contradiction(
        self,
        request: ContradictionRequest,
    ) -> ContradictionOutput:
        raise TimeoutError("provider timed out")


class CustomRetellingProvider(DeterministicInferenceProvider):
    @property
    def provider_id(self) -> str:
        return "modal"

    @property
    def model_id(self) -> str:
        return "greyhaven-test-model"

    def retell_rumor(self, request: RumorRetellingRequest) -> RumorRetelling:
        return RumorRetelling(
            retold_claim="Bram says the newcomer meant to shame him before the market.",
            semantic_position={
                "event": "price_confrontation",
                "intent": "shame_bram",
                "stance": "rejected",
            },
            drift_note="The dispute became a claim about public humiliation.",
            confidence_delta=-0.1,
        )


class CustomAutonomousProvider(DeterministicInferenceProvider):
    @property
    def provider_id(self) -> str:
        return "bedrock"

    @property
    def model_id(self) -> str:
        return "greyhaven-autonomy-test-model"

    def choose_autonomous_action(
        self,
        request: AutonomousActionRequest,
    ) -> AutonomousActionOutput:
        return AutonomousActionOutput(
            action="share_rumor",
            target_id=request.nearby_agent_ids[-1],
            utterance="The market story needs another listener.",
            rationale="Choose a valid nearby listener from the bounded request.",
        )


def make_request() -> RumorRetellingRequest:
    return RumorRetellingRequest(
        original_claim="The newcomer confronted Bram about tripling the price.",
        speaker_id="bram",
        listener_id="pip",
        trust=0.6,
        context="Market row at noon.",
    )


def test_auto_provider_uses_modal_when_credentials_are_configured() -> None:
    settings = Settings(
        HEARSAY_LLM_PROVIDER="auto",
        MODAL_PROXY_URL="https://example.invalid",
        MODAL_PROXY_TOKEN_ID="token-id",
        MODAL_PROXY_TOKEN_SECRET="token-secret",
    )

    provider = create_inference_provider(settings)

    assert provider.provider_id == "modal"


def test_auto_provider_prefers_configured_bedrock_without_calling_it() -> None:
    settings = Settings(
        _env_file=None,
        HEARSAY_LLM_PROVIDER="auto",
        AWS_REGION="us-east-1",
        HEARSAY_BEDROCK_MODEL="us.anthropic.claude-sonnet-test-v1:0",
        MODAL_PROXY_URL="https://example.invalid",
        MODAL_PROXY_TOKEN_ID="token-id",
        MODAL_PROXY_TOKEN_SECRET="token-secret",
    )

    provider = create_inference_provider(settings)

    assert provider.provider_id == "bedrock"
    assert provider.model_id == "us.anthropic.claude-sonnet-test-v1:0"


def test_auto_provider_uses_deterministic_mode_without_modal_credentials() -> None:
    settings = Settings(
        _env_file=None,
        HEARSAY_LLM_PROVIDER="auto",
    )

    provider = create_inference_provider(settings)

    assert provider.provider_id == "deterministic"


def test_bedrock_provider_uses_converse_structured_output_and_records_usage() -> None:
    fake = FakeBedrockRuntime(
        RumorRetelling(
            retold_claim="The newcomer tried to shame Bram over his price.",
            semantic_position={"intent": "shame_bram"},
            drift_note="The price dispute gained a motive.",
            confidence_delta=-0.08,
        ).model_dump_json()
    )
    provider = BedrockInferenceProvider(
        region="us-east-1",
        model_id="us.anthropic.claude-sonnet-test-v1:0",
        client=fake,
    )

    result = provider.retell_rumor(make_request())

    assert isinstance(result, ProviderCall)
    assert result.value.semantic_position.intent == "shame_bram"
    assert result.input_tokens == 37
    assert result.output_tokens == 19
    assert fake.arguments["modelId"] == "us.anthropic.claude-sonnet-test-v1:0"

    output_config = cast(dict[str, object], fake.arguments["outputConfig"])
    text_format = cast(dict[str, object], output_config["textFormat"])
    structure = cast(dict[str, object], text_format["structure"])
    schema_config = cast(dict[str, object], structure["jsonSchema"])
    schema = json.loads(cast(str, schema_config["schema"]))

    def assert_supported(value: object) -> None:
        if isinstance(value, list):
            for item in value:
                assert_supported(item)
        if isinstance(value, dict):
            assert not (BEDROCK_UNSUPPORTED_SCHEMA_KEYS & value.keys())
            if value.get("type") == "object":
                assert value["additionalProperties"] is False
            for item in value.values():
                assert_supported(item)

    assert_supported(schema)


def test_bedrock_provider_rejects_invalid_structured_output() -> None:
    provider = BedrockInferenceProvider(
        region="us-east-1",
        model_id="us.anthropic.claude-sonnet-test-v1:0",
        client=FakeBedrockRuntime('{"retold_claim":"missing required fields"}'),
    )

    with pytest.raises(ValidationError):
        provider.retell_rumor(make_request())


def test_safe_bedrock_result_preserves_usage_without_external_calls() -> None:
    fake = FakeBedrockRuntime(
        RumorRetelling(
            retold_claim="The newcomer tried to shame Bram over his price.",
            semantic_position={"intent": "shame_bram"},
            drift_note="The price dispute gained a motive.",
            confidence_delta=-0.08,
        ).model_dump_json(),
        input_tokens=41,
        output_tokens=23,
    )
    provider = SafeInferenceProvider(
        primary=BedrockInferenceProvider(
            region="us-east-1",
            model_id="us.anthropic.claude-sonnet-test-v1:0",
            client=fake,
        ),
        max_attempts=1,
    )

    result = provider.retell_rumor(make_request())

    assert result.provider_id == "bedrock"
    assert result.fallback_used is False
    assert result.input_tokens == 41
    assert result.output_tokens == 23


def test_bedrock_provider_validates_a_bounded_autonomous_action() -> None:
    fake = FakeBedrockRuntime(
        AutonomousActionOutput(
            action="share_rumor",
            target_id="hettie",
            utterance="Bram tells it differently.",
            rationale="Hettie is nearby and has not heard this version.",
        ).model_dump_json(),
        input_tokens=31,
        output_tokens=17,
    )
    provider = BedrockInferenceProvider(
        region="us-east-1",
        model_id="us.anthropic.claude-sonnet-test-v1:0",
        client=fake,
    )

    result = provider.choose_autonomous_action(
        AutonomousActionRequest(
            agent_id="pip",
            location_id="market",
            nearby_agent_ids=["hettie", "cal"],
            recalled_memories=["The newcomer challenged Bram's price."],
            allowed_actions=["share_rumor", "wait"],
        )
    )

    assert result.value.action == "share_rumor"
    assert result.value.target_id == "hettie"
    assert result.input_tokens == 31
    assert result.output_tokens == 17


def test_invalid_bedrock_autonomous_target_uses_safe_fallback() -> None:
    fake = FakeBedrockRuntime(
        AutonomousActionOutput(
            action="share_rumor",
            target_id="invented-resident",
            rationale="Invalid target for fallback coverage.",
        ).model_dump_json()
    )
    provider = SafeInferenceProvider(
        primary=BedrockInferenceProvider(
            region="us-east-1",
            model_id="us.anthropic.claude-sonnet-test-v1:0",
            client=fake,
        ),
        max_attempts=1,
    )
    request = AutonomousActionRequest(
        agent_id="pip",
        location_id="market",
        nearby_agent_ids=["hettie"],
        recalled_memories=["The newcomer challenged Bram's price."],
        allowed_actions=["share_rumor", "wait"],
    )

    result = provider.choose_autonomous_action(request)

    assert result.fallback_used is True
    assert result.fallback_reason == "ValueError"
    assert result.value.action == "share_rumor"
    assert result.value.target_id == "hettie"


def test_modal_provider_requests_and_validates_a_strict_json_schema() -> None:
    fake = FakeOpenAI(
        RumorRetelling(
            retold_claim="The newcomer tried to shame Bram over his price.",
            semantic_position={"intent": "shame_bram"},
            drift_note="The price dispute gained a motive.",
            confidence_delta=-0.08,
        ).model_dump_json()
    )
    provider = ModalInferenceProvider(
        base_url="https://example.invalid",
        token_id="unused",
        token_secret="unused",
        model_id="test-model",
        client=cast(OpenAI, fake),
    )

    result = provider.retell_rumor(make_request())

    assert result.semantic_position.model_dump(exclude_none=True) == {"intent": "shame_bram"}
    response_format = cast(dict[str, object], fake.completions.arguments["response_format"])
    assert response_format["type"] == "json_schema"
    json_schema = cast(dict[str, object], response_format["json_schema"])
    assert json_schema["strict"] is True


def test_modal_provider_rejects_an_invalid_structured_response() -> None:
    fake = FakeOpenAI('{"retold_claim":"missing required fields"}')
    provider = ModalInferenceProvider(
        base_url="https://example.invalid",
        token_id="unused",
        token_secret="unused",
        model_id="test-model",
        client=cast(OpenAI, fake),
    )

    with pytest.raises(ValidationError):
        provider.retell_rumor(make_request())


def test_modal_provider_rejects_an_introduced_named_entity() -> None:
    fake = FakeOpenAI(
        RumorRetelling(
            retold_claim="Marta says the newcomer tried to shame Bram over his price.",
            semantic_position={"intent": "shame_bram"},
            drift_note="The price dispute gained a motive and a new source.",
            confidence_delta=-0.08,
        ).model_dump_json()
    )
    provider = ModalInferenceProvider(
        base_url="https://example.invalid",
        token_id="unused",
        token_secret="unused",
        model_id="test-model",
        client=cast(OpenAI, fake),
    )

    with pytest.raises(ValueError, match="named entity"):
        provider.retell_rumor(make_request())


def test_modal_provider_allows_a_capitalized_sentence_opening() -> None:
    fake = FakeOpenAI(
        RumorRetelling(
            retold_claim="Apparently, the newcomer tried to shame Bram over his price.",
            semantic_position={"intent": "shame_bram"},
            drift_note="The price dispute gained a motive.",
            confidence_delta=-0.08,
        ).model_dump_json()
    )
    provider = ModalInferenceProvider(
        base_url="https://example.invalid",
        token_id="unused",
        token_secret="unused",
        model_id="test-model",
        client=cast(OpenAI, fake),
    )

    result = provider.retell_rumor(make_request())

    assert result.retold_claim.startswith("Apparently")


def test_safe_provider_retries_then_returns_a_sanitized_fallback() -> None:
    provider = SafeInferenceProvider(
        primary=FailingInferenceProvider(),
        max_attempts=2,
    )

    result = provider.retell_rumor(make_request())

    assert result.fallback_used is True
    assert result.fallback_reason == "TimeoutError"
    assert result.attempts == 2
    assert result.provider_id == "modal"
    assert result.model_id == "unavailable-test-model"
    assert "ruin Bram" in result.value.retold_claim


def test_safe_provider_wraps_dialogue_and_contradiction_operations() -> None:
    provider = SafeInferenceProvider(
        primary=FailingInferenceProvider(),
        max_attempts=1,
    )

    dialogue = provider.generate_dialogue(
        DialogueRequest(npc_id="pip", player_message="What did you hear?")
    )
    contradiction = provider.classify_contradiction(
        ContradictionRequest(
            current_position={"intent": "help"},
            incoming_position={"intent": "harm"},
            source_trust=0.4,
        )
    )

    assert dialogue.fallback_used is True
    assert dialogue.value.intent == "refuse"
    assert contradiction.fallback_used is True
    assert contradiction.value.classification == "contradicts"


def test_service_persists_provider_provenance_with_the_transmission() -> None:
    repository = InMemoryRunRepository()
    primary = CustomRetellingProvider()
    service = GameService(
        repository=repository,
        inference=SafeInferenceProvider(primary=primary, max_attempts=1),
    )
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=42))

    response = service.take_action(
        created.run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb="confront",
            target_id="bram",
        ),
    )
    lineage = service.get_memory_lineage(created.run_id)

    pip = next(npc for npc in response.snapshot.npcs if npc.id == "pip")
    assert pip.speech == "Bram says the newcomer meant to shame him before the market."
    transmission = lineage.transmissions[0]
    assert transmission.provider_id == "modal"
    assert transmission.model_id == "greyhaven-test-model"
    assert transmission.fallback_used is False
    assert transmission.inference_attempts == 1
    assert transmission.inference_latency_ms is not None
    pip_version = next(version for version in lineage.versions if version.holder_id == "pip")
    assert pip_version.normalized_position["stance"] == "accepted"


def test_service_persists_bedrock_token_usage_with_the_transmission() -> None:
    fake = FakeBedrockRuntime(
        RumorRetelling(
            retold_claim="The newcomer tried to shame Bram over his price.",
            semantic_position={"intent": "shame_bram"},
            drift_note="The price dispute gained a motive.",
            confidence_delta=-0.08,
        ).model_dump_json(),
        input_tokens=53,
        output_tokens=29,
    )
    repository = InMemoryRunRepository()
    service = GameService(
        repository=repository,
        inference=SafeInferenceProvider(
            primary=BedrockInferenceProvider(
                region="us-east-1",
                model_id="us.anthropic.claude-sonnet-test-v1:0",
                client=fake,
            ),
            max_attempts=1,
        ),
    )
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=42))

    service.take_action(
        created.run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb="confront",
            target_id="bram",
        ),
    )
    transmission = service.get_memory_lineage(created.run_id).transmissions[0]

    assert transmission.provider_id == "bedrock"
    assert transmission.inference_input_tokens == 53
    assert transmission.inference_output_tokens == 29


def test_small_release_persists_bounded_agent_decision_and_selected_listener() -> None:
    repository = InMemoryRunRepository()
    service = GameService(
        repository=repository,
        inference=SafeInferenceProvider(
            primary=CustomAutonomousProvider(),
            max_attempts=1,
        ),
    )
    created = service.create_run(
        CreateRunRequest(
            display_name="Ada",
            seed=1729,
            release_profile="hackathon_small",
        )
    )
    service.take_action(
        created.run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb="promise_help",
            target_id="marta",
        ),
    )
    response = service.take_action(
        created.run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb="negotiate_bram",
            target_id="bram",
        ),
    )

    decision_event = next(
        event for event in response.snapshot.recent_events if event.kind == "agent_decision"
    )
    selected_listener = cast(str, decision_event.payload["target_id"])
    assert selected_listener in {"marta", "talia", "rhea"}
    assert decision_event.payload["provider_id"] == "bedrock"
    assert decision_event.payload["model_id"] == "greyhaven-autonomy-test-model"
    assert decision_event.payload["fallback_used"] is False

    lineage = service.get_memory_lineage(created.run_id, "bram-price-confrontation")
    selected_memory = next(
        version for version in lineage.versions if version.holder_id == selected_listener
    )
    assert selected_memory.normalized_position["decision_provider_id"] == "bedrock"
    assert (
        selected_memory.normalized_position["decision_model_id"] == "greyhaven-autonomy-test-model"
    )
    assert selected_memory.normalized_position["decision_action"] == "share_rumor"
