from __future__ import annotations

import math
from uuid import UUID, uuid4

import pytest

from hearsay_api.memory import (
    EMBEDDING_DIMENSIONS,
    DeterministicEmbeddingProvider,
    EmbeddingResult,
    SafeEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
)
from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import (
    ActionRequest,
    CreateRunRequest,
    MemoryRecallResponse,
)
from hearsay_api.service import GameService
from test_api import create_run, make_client


class FakeArray:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def tolist(self) -> list[float]:
        return self.values


class FakeSentenceModel:
    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        self.dimensions = dimensions
        self.last_text: str | None = None

    def encode(
        self,
        sentences: str,
        *,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> FakeArray:
        self.last_text = sentences
        value = 1 / math.sqrt(self.dimensions)
        return FakeArray([value] * self.dimensions)


class FailingEmbeddingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def embed(self, text: str) -> EmbeddingResult:
        self.calls += 1
        raise OSError("a path or network detail that must not escape")

    def embed_query(self, text: str) -> EmbeddingResult:
        self.calls += 1
        raise OSError("a path or network detail that must not escape")


def test_deterministic_embedding_is_normalized_and_stable() -> None:
    provider = DeterministicEmbeddingProvider()

    first = provider.embed("Bram challenged the market price")
    second = provider.embed("Bram challenged the market price")

    assert first.vector == second.vector
    assert len(first.vector) == EMBEDDING_DIMENSIONS
    assert abs(sum(value * value for value in first.vector) - 1.0) < 1e-9
    assert first.model_id == "hearsay-hash-384-v1"


def test_sentence_transformer_provider_validates_and_labels_real_shape() -> None:
    model = FakeSentenceModel()
    provider = SentenceTransformerEmbeddingProvider(model=model)

    result = provider.embed("Bram challenged the market price")

    assert len(result.vector) == EMBEDDING_DIMENSIONS
    assert abs(sum(value * value for value in result.vector) - 1.0) < 1e-6
    assert result.provider_id == "sentence-transformers"
    assert result.model_id == "BAAI/bge-small-en-v1.5"
    assert result.fallback_used is False
    provider.embed_query("What happened to Bram?")
    assert model.last_text == (
        "Represent this sentence for searching relevant passages: What happened to Bram?"
    )


def test_sentence_transformer_provider_rejects_the_wrong_dimensions() -> None:
    provider = SentenceTransformerEmbeddingProvider(
        model=FakeSentenceModel(dimensions=12),
    )

    with pytest.raises(ValueError, match="12 dimensions"):
        provider.embed("Bram challenged the market price")


def test_safe_embedding_provider_uses_truthful_fallback_provenance() -> None:
    primary = FailingEmbeddingProvider()
    provider = SafeEmbeddingProvider(primary=primary)

    result = provider.embed("Bram challenged the market price")
    second = provider.embed_query("What happened to Bram?")

    assert result.fallback_used is True
    assert result.fallback_reason == "OSError"
    assert result.provider_id == "deterministic"
    assert result.model_id == "hearsay-hash-384-v1"
    assert len(result.vector) == EMBEDDING_DIMENSIONS
    assert second.fallback_used is True
    assert primary.calls == 1


def test_signature_loop_exposes_complete_memory_lineage_and_recall() -> None:
    with make_client() as client:
        run = create_run(client)
        run_id = run["run_id"]
        for verb, target in (("promise_help", "marta"), ("confront", "bram")):
            response = client.post(
                f"/v1/runs/{run_id}/actions",
                json={
                    "idempotency_key": str(uuid4()),
                    "verb": verb,
                    "target_id": target,
                },
            )
            assert response.status_code == 200

        lineage_response = client.get(f"/v1/runs/{run_id}/memories")
        assert lineage_response.status_code == 200
        lineage = lineage_response.json()
        assert len(lineage["versions"]) == 3
        assert len(lineage["transmissions"]) == 1

        transmission = lineage["transmissions"][0]
        assert transmission["speaker_id"] == "bram"
        assert transmission["listener_id"] == "pip"
        assert transmission["from_belief_id"] is not None
        assert transmission["to_belief_id"] is not None
        assert "malicious intent" in transmission["mutation_note"]

        recall_response = client.post(
            f"/v1/runs/{run_id}/memories/recall",
            json={
                "holder_id": "pip",
                "query": "What happened to Bram in market row?",
                "limit": 4,
            },
        )
        assert recall_response.status_code == 200
        recalled = recall_response.json()
        assert recalled["memories"][0]["proposition_key"] == "bram-price-confrontation"
        assert "ruin Bram" in recalled["memories"][0]["narrative_text"]


def test_repeated_claim_creates_an_immutable_superseded_version() -> None:
    with make_client() as client:
        run = create_run(client)
        run_id = run["run_id"]
        for _ in range(2):
            response = client.post(
                f"/v1/runs/{run_id}/actions",
                json={
                    "idempotency_key": str(uuid4()),
                    "verb": "confront",
                    "target_id": "bram",
                },
            )
            assert response.status_code == 200

        lineage = client.get(
            f"/v1/runs/{run_id}/memories",
            params={"proposition_key": "bram-price-confrontation"},
        ).json()
        bram_versions = [
            version for version in lineage["versions"] if version["holder_id"] == "bram"
        ]
        assert [version["version"] for version in bram_versions] == [1, 2]
        assert [version["active"] for version in bram_versions] == [False, True]
        assert len(lineage["transmissions"]) == 2


def test_npc_dialogue_uses_holder_scoped_recalled_memory() -> None:
    with make_client() as client:
        run = create_run(client)
        run_id = run["run_id"]
        for verb, target in (("promise_help", "marta"), ("confront", "bram")):
            response = client.post(
                f"/v1/runs/{run_id}/actions",
                json={
                    "idempotency_key": str(uuid4()),
                    "verb": verb,
                    "target_id": target,
                },
            )
            assert response.status_code == 200

        response = client.post(
            f"/v1/runs/{run_id}/actions",
            json={
                "idempotency_key": str(uuid4()),
                "verb": "talk",
                "target_id": "pip",
                "content": "What happened between the newcomer and Bram?",
            },
        )

        assert response.status_code == 200
        dialogue = response.json()["snapshot"]["dialogue"]
        assert dialogue["speaker_id"] == "pip"
        assert "ruin Bram" in dialogue["text"]
        assert dialogue["provider_id"] == "deterministic"
        assert dialogue["model_id"] == "hearsay-rules-v1"
        assert dialogue["fallback_used"] is False
        assert dialogue["recalled_memories"][0]["proposition_key"] == ("bram-price-confrontation")


def test_dialogue_recall_failure_preserves_the_authored_opening() -> None:
    class FailingRecallRepository(InMemoryRunRepository):
        def recall_memories(
            self,
            run_id: UUID,
            holder_id: str,
            query_text: str,
            query_embedding: tuple[float, ...],
            limit: int,
        ) -> MemoryRecallResponse:
            raise RuntimeError("database detail that must not enter dialogue")

    service = GameService(repository=FailingRecallRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=42))

    response = service.take_action(
        created.run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb="talk",
            target_id="marta",
            content="What do you remember?",
        ),
    )

    assert response.snapshot.dialogue is not None
    assert response.snapshot.dialogue.text == (service.content.principals_by_id["marta"].opening)
    assert response.snapshot.dialogue.recalled_memories == []
