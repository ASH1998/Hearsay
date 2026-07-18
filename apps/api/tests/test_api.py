from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient

from hearsay_api.config import Settings
from hearsay_api.main import create_app
from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import CreateRunRequest
from hearsay_api.service import GameService


def make_client() -> TestClient:
    service = GameService(repository=InMemoryRunRepository())
    app = create_app(
        service=service,
        settings=Settings(HEARSAY_ENV="test", web_origin="http://testserver"),
    )
    return TestClient(app)


def create_run(client: TestClient) -> dict[str, object]:
    response = client.post("/v1/runs", json={"display_name": "Ada", "seed": 42})
    assert response.status_code == 201
    return response.json()


def test_create_run_returns_authoritative_opening_snapshot() -> None:
    with make_client() as client:
        body = create_run(client)

        snapshot = body["snapshot"]
        assert isinstance(snapshot, dict)
        assert snapshot["player"]["display_name"] == "Ada"
        assert snapshot["player"]["location_id"] == "road"
        assert snapshot["day"] == 1
        assert snapshot["phase"] == "morning"
        assert len(snapshot["locations"]) == 12
        assert len(snapshot["npcs"]) == 8


def test_free_movement_does_not_consume_time() -> None:
    with make_client() as client:
        run = create_run(client)
        response = client.post(
            f"/v1/runs/{run['run_id']}/actions",
            json={
                "idempotency_key": str(uuid4()),
                "verb": "move",
                "target_id": "square",
            },
        )

        assert response.status_code == 200
        assert response.json()["consumed_time"] is False
        snapshot = response.json()["snapshot"]
        assert snapshot["action_count"] == 0
        assert snapshot["player"]["location_id"] == "square"


def test_two_consequential_actions_advance_tick_and_make_rumor_visible() -> None:
    with make_client() as client:
        run = create_run(client)
        run_id = run["run_id"]

        first = client.post(
            f"/v1/runs/{run_id}/actions",
            json={
                "idempotency_key": str(uuid4()),
                "verb": "promise_help",
                "target_id": "marta",
            },
        )
        second = client.post(
            f"/v1/runs/{run_id}/actions",
            json={
                "idempotency_key": str(uuid4()),
                "verb": "confront",
                "target_id": "bram",
            },
        )

        assert first.status_code == 200
        assert second.status_code == 200
        snapshot = second.json()["snapshot"]
        assert snapshot["action_count"] == 2
        assert snapshot["world_tick"] == 1
        pip = next(npc for npc in snapshot["npcs"] if npc["id"] == "pip")
        assert "Bram" in pip["speech"]


def test_actions_are_idempotent() -> None:
    with make_client() as client:
        run = create_run(client)
        key = str(uuid4())
        payload = {
            "idempotency_key": key,
            "verb": "talk",
            "target_id": "marta",
        }

        first = client.post(f"/v1/runs/{run['run_id']}/actions", json=payload)
        second = client.post(f"/v1/runs/{run['run_id']}/actions", json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()
        assert second.json()["snapshot"]["action_count"] == 1
        assert second.json()["snapshot"]["revision"] == 1


def test_concurrent_actions_retry_against_one_coherent_revision() -> None:
    service = GameService(repository=InMemoryRunRepository())
    run = service.create_run(CreateRunRequest(display_name="Ada", seed=42))
    requests = [
        {
            "idempotency_key": uuid4(),
            "verb": "talk",
            "target_id": target,
        }
        for target in ("marta", "bram")
    ]

    def act(payload: dict[str, object]) -> int:
        from hearsay_api.schemas import ActionRequest

        result = service.take_action(
            run.run_id,
            ActionRequest.model_validate(payload),
        )
        return result.snapshot.revision

    with ThreadPoolExecutor(max_workers=2) as executor:
        revisions = list(executor.map(act, requests))

    snapshot = service.get_snapshot(run.run_id)
    assert set(revisions) == {1, 2}
    assert snapshot.revision == 2
    assert snapshot.action_count == 2
    assert snapshot.world_tick == 1


def test_snapshot_restores_state_after_client_refresh() -> None:
    with make_client() as client:
        run = create_run(client)
        run_id = run["run_id"]
        client.post(
            f"/v1/runs/{run_id}/actions",
            json={
                "idempotency_key": str(uuid4()),
                "verb": "move",
                "target_id": "docks",
            },
        )

        restored = client.get(f"/v1/runs/{run_id}/snapshot")
        assert restored.status_code == 200
        assert restored.json()["player"]["location_id"] == "docks"


def test_websocket_returns_current_snapshot() -> None:
    with make_client() as client:
        run = create_run(client)
        with client.websocket_connect(f"/v1/runs/{run['run_id']}/stream") as websocket:
            snapshot = websocket.receive_json()
            assert snapshot["run_id"] == run["run_id"]
            websocket.send_text("snapshot")
            assert websocket.receive_json()["day"] == 1


def test_unknown_run_is_404() -> None:
    with make_client() as client:
        response = client.get(f"/v1/runs/{uuid4()}/snapshot")
        assert response.status_code == 404


def test_content_can_be_instantiated_independently() -> None:
    request = CreateRunRequest(display_name="Test", seed=1)
    assert request.seed == 1
