from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from hearsay_api.config import Settings, get_settings
from hearsay_api.inference import create_inference_provider
from hearsay_api.memory import create_embedding_provider
from hearsay_api.persistence import create_repository
from hearsay_api.repository import RunNotFoundError
from hearsay_api.schemas import (
    ActionRequest,
    ActionResponse,
    CreateRunRequest,
    CreateRunResponse,
    MemoryLineageResponse,
    MemoryRecallRequest,
    MemoryRecallResponse,
    RunSnapshot,
)
from hearsay_api.service import GameService, InvalidActionError


def create_app(
    service: GameService | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    game_service = service or GameService(
        repository=create_repository(resolved_settings),
        embeddings=create_embedding_provider(resolved_settings),
        inference=create_inference_provider(resolved_settings),
        max_concurrency_retries=resolved_settings.transaction_max_retries,
    )
    application = FastAPI(
        title="Hearsay Game API",
        version="0.1.0",
        description="Authoritative game state, actions, and memory-proof surfaces.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[resolved_settings.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health", tags=["operations"])
    def health() -> dict[str, str]:
        persistence_ok = game_service.repository.check_health()
        return {
            "status": "ok" if persistence_ok else "degraded",
            "environment": resolved_settings.environment,
            "persistence": game_service.repository.backend_name,
        }

    @application.post(
        "/v1/runs",
        response_model=CreateRunResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["runs"],
    )
    def create_run(request: CreateRunRequest) -> CreateRunResponse:
        return game_service.create_run(request)

    @application.get(
        "/v1/runs/{run_id}/snapshot",
        response_model=RunSnapshot,
        tags=["runs"],
    )
    def get_snapshot(run_id: UUID) -> RunSnapshot:
        try:
            return game_service.get_snapshot(run_id)
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="Run not found.") from error

    @application.post(
        "/v1/runs/{run_id}/actions",
        response_model=ActionResponse,
        tags=["actions"],
    )
    def take_action(
        run_id: UUID,
        request: ActionRequest,
    ) -> ActionResponse:
        try:
            return game_service.take_action(run_id, request)
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="Run not found.") from error
        except InvalidActionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @application.get(
        "/v1/runs/{run_id}/memories",
        response_model=MemoryLineageResponse,
        tags=["memory"],
    )
    def get_memory_lineage(
        run_id: UUID,
        proposition_key: str | None = None,
    ) -> MemoryLineageResponse:
        try:
            return game_service.get_memory_lineage(run_id, proposition_key)
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="Run not found.") from error

    @application.post(
        "/v1/runs/{run_id}/memories/recall",
        response_model=MemoryRecallResponse,
        tags=["memory"],
    )
    def recall_memories(
        run_id: UUID,
        request: MemoryRecallRequest,
    ) -> MemoryRecallResponse:
        try:
            return game_service.recall_memories(run_id, request)
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="Run not found.") from error

    @application.websocket("/v1/runs/{run_id}/stream")
    async def stream_run(websocket: WebSocket, run_id: UUID) -> None:
        await websocket.accept()
        try:
            await websocket.send_json(game_service.get_snapshot(run_id).model_dump(mode="json"))
            while True:
                message = await websocket.receive_text()
                if message == "snapshot":
                    snapshot = game_service.get_snapshot(run_id)
                    await websocket.send_json(snapshot.model_dump(mode="json"))
        except RunNotFoundError:
            await websocket.close(code=4404, reason="Run not found.")
        except WebSocketDisconnect:
            return

    return application


app = create_app()
