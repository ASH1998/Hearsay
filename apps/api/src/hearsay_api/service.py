from __future__ import annotations

from uuid import UUID, uuid4

from hearsay_api.content import GreyhavenContent, load_content
from hearsay_api.repository import (
    ConcurrentRunUpdateError,
    InMemoryRunRepository,
    RunRepository,
)
from hearsay_api.schemas import (
    ActionRequest,
    ActionResponse,
    ActionVerb,
    CreateRunRequest,
    CreateRunResponse,
    DialogueState,
    LocationState,
    NpcState,
    PlayerState,
    PromiseState,
    RunSnapshot,
    WorldEvent,
)


class InvalidActionError(ValueError):
    pass


FREE_ACTIONS = {
    ActionVerb.MOVE,
    ActionVerb.OBSERVE,
    ActionVerb.READ_NOTICE_BOARD,
}


class GameService:
    def __init__(
        self,
        repository: RunRepository | None = None,
        content: GreyhavenContent | None = None,
        max_concurrency_retries: int = 4,
    ) -> None:
        self.repository = repository or InMemoryRunRepository()
        self.content = content or load_content()
        self.max_concurrency_retries = max_concurrency_retries

    def create_run(self, request: CreateRunRequest) -> CreateRunResponse:
        run_id = uuid4()
        locations = [
            LocationState(
                id=item.id,
                name=item.name,
                position=item.position,
                neighbors=item.neighbors,
            )
            for item in self.content.locations
        ]
        npcs = [
            NpcState(
                id=item.id,
                name=item.name,
                role=item.role,
                location_id=item.location,
                color=item.color,
                speech=item.opening if item.id == "marta" else None,
            )
            for item in self.content.principals
        ]
        snapshot = RunSnapshot(
            run_id=run_id,
            seed=request.seed,
            player=PlayerState(display_name=request.display_name, location_id="road"),
            locations=locations,
            npcs=npcs,
            recent_events=[
                WorldEvent(
                    id=uuid4(),
                    kind="arrival",
                    text="Dawn reaches Greyhaven just ahead of you.",
                )
            ],
        )
        self.repository.create(snapshot)
        return CreateRunResponse(run_id=run_id, snapshot=snapshot)

    def get_snapshot(self, run_id: UUID) -> RunSnapshot:
        return self._hydrate_content(self.repository.get(run_id))

    def take_action(self, run_id: UUID, request: ActionRequest) -> ActionResponse:
        cached = self.repository.get_action_result(run_id, request.idempotency_key)
        if cached is not None:
            return cached

        for attempt in range(self.max_concurrency_retries + 1):
            snapshot = self._hydrate_content(self.repository.get(run_id))
            if snapshot.status != "active":
                raise InvalidActionError("This run has already ended.")

            consumed_time = request.verb not in FREE_ACTIONS
            event = self._apply_action(snapshot, request)
            snapshot.recent_events = ([event] + snapshot.recent_events)[:8]
            if consumed_time:
                self._advance_clock(snapshot, request.verb)
                if snapshot.action_count % 2 == 0:
                    self._run_gossip_tick(snapshot)
            snapshot.revision += 1

            response = ActionResponse(
                action_id=uuid4(),
                consumed_time=consumed_time,
                snapshot=snapshot,
            )
            try:
                return self.repository.update(
                    run_id,
                    snapshot,
                    request,
                    request.idempotency_key,
                    response,
                )
            except ConcurrentRunUpdateError:
                if attempt == self.max_concurrency_retries:
                    raise
        raise AssertionError("Unreachable concurrency retry state.")

    def _apply_action(self, snapshot: RunSnapshot, request: ActionRequest) -> WorldEvent:
        if request.verb == ActionVerb.MOVE:
            return self._move(snapshot, request.target_id)
        if request.verb == ActionVerb.OBSERVE:
            snapshot.dialogue = DialogueState(
                speaker_id="pip",
                speaker_name="Pip Marr",
                text="The newcomer arrived with a royal purse. Or a warrant. One of those.",
            )
            return self._event("observe", "You catch the drift of a story already changing.")
        if request.verb == ActionVerb.READ_NOTICE_BOARD:
            visible_traits = snapshot.player.traits or ["unknown"]
            return self._event(
                "notice_board",
                f"The chalk verdict reads: {', '.join(visible_traits)}.",
            )
        if request.verb == ActionVerb.TALK:
            npc = self._require_npc(snapshot, request.target_id)
            principal = self.content.principals_by_id[npc.id]
            snapshot.dialogue = DialogueState(
                speaker_id=npc.id,
                speaker_name=npc.name,
                text=principal.opening,
            )
            return self._event("conversation", f"You speak with {npc.name}.")
        if request.verb == ActionVerb.PROMISE_HELP:
            if request.target_id != "marta":
                raise InvalidActionError("The opening shipment promise is made to Marta.")
            if any(promise.promisee_id == "marta" for promise in snapshot.promises):
                raise InvalidActionError("You already made Marta this promise.")
            snapshot.promises.append(
                PromiseState(
                    id=uuid4(),
                    promisee_id="marta",
                    content="Release the inn's shipment from Bram before evening.",
                    deadline_day=snapshot.day,
                    deadline_phase="evening",
                )
            )
            snapshot.dialogue = DialogueState(
                speaker_id="marta",
                speaker_name="Marta Vale",
                text="Before evening, then. Greyhaven remembers a promise.",
            )
            return self._event("promise_made", "You promise Marta you will free her shipment.")
        if request.verb == ActionVerb.CONFRONT:
            if request.target_id != "bram":
                raise InvalidActionError("The opening confrontation targets Bram.")
            bram = self._require_npc(snapshot, "bram")
            bram.relationship = max(-100, bram.relationship - 5)
            snapshot.dialogue = DialogueState(
                speaker_id="bram",
                speaker_name="Bram Coyle",
                text="You bargain like someone who thinks witnesses are friends.",
            )
            return self._event(
                "bram_confronted",
                "Your argument with Bram carries farther than either of you intended.",
            )
        if request.verb == ActionVerb.SLEEP:
            snapshot.dialogue = None
            return self._event("sleep", "Greyhaven keeps talking after your lamp goes dark.")
        raise InvalidActionError(f"Unsupported action: {request.verb}")

    def _move(self, snapshot: RunSnapshot, target_id: str | None) -> WorldEvent:
        if target_id is None or target_id not in self.content.locations_by_id:
            raise InvalidActionError("Choose a valid Greyhaven location.")
        current = self.content.locations_by_id[snapshot.player.location_id]
        if target_id not in current.neighbors:
            raise InvalidActionError("Walk to a connected Greyhaven waypoint first.")
        snapshot.player.location_id = target_id
        location = self.content.locations_by_id[target_id]
        return self._event("movement", f"You walk to {location.name}.")

    @staticmethod
    def _advance_clock(snapshot: RunSnapshot, verb: ActionVerb) -> None:
        if verb == ActionVerb.SLEEP:
            completed_days = (snapshot.action_count // 6) + 1
            snapshot.action_count = min(completed_days * 6, 18)
        else:
            snapshot.action_count = min(snapshot.action_count + 1, 18)

        if snapshot.action_count >= 18:
            snapshot.day = 3
            snapshot.phase = "night"
            snapshot.status = "completed"
            return

        snapshot.day = min((snapshot.action_count // 6) + 1, 3)
        action_in_day = snapshot.action_count % 6
        if action_in_day <= 1:
            snapshot.phase = "morning"
        elif action_in_day <= 3:
            snapshot.phase = "afternoon"
        elif action_in_day == 4:
            snapshot.phase = "evening"
        else:
            snapshot.phase = "night"
        snapshot.weather = (
            "rain" if snapshot.day == 1 and snapshot.phase in {"evening", "night"} else "clear"
        )

    @staticmethod
    def _run_gossip_tick(snapshot: RunSnapshot) -> None:
        snapshot.world_tick += 1
        pip = next(npc for npc in snapshot.npcs if npc.id == "pip")
        if any(event.kind == "bram_confronted" for event in snapshot.recent_events[:2]):
            pip.speech = "The newcomer tried to ruin Bram in the middle of market row."
        elif snapshot.promises:
            pip.speech = "Marta found herself a hero—or another empty promise."
        else:
            pip.speech = "The newcomer is asking questions already."

    @staticmethod
    def _require_npc(snapshot: RunSnapshot, npc_id: str | None) -> NpcState:
        npc = next((item for item in snapshot.npcs if item.id == npc_id), None)
        if npc is None:
            raise InvalidActionError("Choose a valid Greyhaven resident.")
        return npc

    def _hydrate_content(self, snapshot: RunSnapshot) -> RunSnapshot:
        snapshot.locations = [
            location.model_copy(
                update={
                    "neighbors": self.content.locations_by_id[location.id].neighbors,
                }
            )
            for location in snapshot.locations
        ]
        return snapshot

    @staticmethod
    def _event(kind: str, text: str) -> WorldEvent:
        return WorldEvent(id=uuid4(), kind=kind, text=text)
