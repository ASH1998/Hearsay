from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from openai import OpenAI
from pydantic import ValidationError

from hearsay_api.config import Settings
from hearsay_api.inference import (
    ContradictionOutput,
    ContradictionRequest,
    DeterministicInferenceProvider,
    DialogueOutput,
    DialogueRequest,
    ModalInferenceProvider,
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


def test_auto_provider_uses_deterministic_mode_without_modal_credentials() -> None:
    settings = Settings(
        _env_file=None,
        HEARSAY_LLM_PROVIDER="auto",
    )

    provider = create_inference_provider(settings)

    assert provider.provider_id == "deterministic"


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
