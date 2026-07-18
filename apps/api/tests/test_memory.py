from __future__ import annotations

from uuid import uuid4

from hearsay_api.memory import (
    EMBEDDING_DIMENSIONS,
    DeterministicEmbeddingProvider,
)
from test_api import create_run, make_client


def test_deterministic_embedding_is_normalized_and_stable() -> None:
    provider = DeterministicEmbeddingProvider()

    first = provider.embed("Bram challenged the market price")
    second = provider.embed("Bram challenged the market price")

    assert first == second
    assert len(first) == EMBEDDING_DIMENSIONS
    assert abs(sum(value * value for value in first) - 1.0) < 1e-9


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
