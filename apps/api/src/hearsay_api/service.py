from __future__ import annotations

from typing import Literal, cast
from uuid import UUID, uuid4

import structlog

from hearsay_api.content import GreyhavenContent, load_content
from hearsay_api.election import resolve_election
from hearsay_api.inference import (
    DeterministicInferenceProvider,
    DialogueRequest,
    InferenceResult,
    RumorRetelling,
    RumorRetellingRequest,
    SafeInferenceProvider,
)
from hearsay_api.memory import (
    DeterministicEmbeddingProvider,
    DialogueTreatment,
    EmbeddingProvider,
    PromiseTransition,
    derive_dialogue_treatment,
    plan_action_memory,
)
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
    DialogueMemoryRef,
    DialogueState,
    LocationState,
    MemoryLineageResponse,
    MemoryRecallRequest,
    MemoryRecallResponse,
    NpcState,
    PlayerState,
    PromiseState,
    RunSnapshot,
    WorldEvent,
)


class InvalidActionError(ValueError):
    pass


logger = structlog.get_logger(__name__)


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
        embeddings: EmbeddingProvider | None = None,
        inference: SafeInferenceProvider | None = None,
        max_concurrency_retries: int = 4,
    ) -> None:
        self.repository = repository or InMemoryRunRepository()
        self.content = content or load_content()
        self.embeddings = embeddings or DeterministicEmbeddingProvider()
        deterministic_inference = DeterministicInferenceProvider()
        self.inference = inference or SafeInferenceProvider(
            primary=deterministic_inference,
            fallback=deterministic_inference,
            max_attempts=1,
        )
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
            for item in self.content.residents
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

    def get_memory_lineage(
        self,
        run_id: UUID,
        proposition_key: str | None = None,
    ) -> MemoryLineageResponse:
        return self.repository.list_memory_lineage(run_id, proposition_key)

    def recall_memories(
        self,
        run_id: UUID,
        request: MemoryRecallRequest,
    ) -> MemoryRecallResponse:
        query_embedding = self.embeddings.embed_query(request.query)
        return self.repository.recall_memories(
            run_id,
            request.holder_id,
            request.query,
            query_embedding.vector,
            request.limit,
        )

    def take_action(self, run_id: UUID, request: ActionRequest) -> ActionResponse:
        cached = self.repository.get_action_result(run_id, request.idempotency_key)
        if cached is not None:
            return cached

        for attempt in range(self.max_concurrency_retries + 1):
            snapshot = self._hydrate_content(self.repository.get(run_id))
            promise_status_before = {
                promise.id: promise.status
                for promise in snapshot.promises
            }
            if snapshot.status != "active":
                raise InvalidActionError("This run has already ended.")

            consumed_time = request.verb not in FREE_ACTIONS
            event = self._apply_action(snapshot, request)
            snapshot.recent_events = ([event] + snapshot.recent_events)[:8]
            if consumed_time:
                self._advance_clock(snapshot, request.verb)
                promise_events = self._resolve_expired_promises(snapshot)
                snapshot.recent_events = (
                    promise_events + snapshot.recent_events
                )[:8]
                if snapshot.action_count % 2 == 0:
                    self._run_gossip_tick(snapshot)
            if snapshot.action_count >= 18 and snapshot.election is None:
                lineage = self.repository.list_memory_lineage(run_id)
                snapshot.election = resolve_election(
                    snapshot,
                    self.content,
                    lineage,
                )
                snapshot.recent_events = (
                    [
                        self._event(
                            "election_resolved",
                            (
                                f"Greyhaven votes {snapshot.election.player_votes}–"
                                f"{snapshot.election.rhea_votes}. "
                                f"{snapshot.election.ending.title}."
                            ),
                        )
                    ]
                    + snapshot.recent_events
                )[:8]
            promise_transitions = tuple(
                PromiseTransition(
                    promisee_id=promise.promisee_id,
                    status=cast(Literal["kept", "broken"], promise.status),
                )
                for promise in snapshot.promises
                if promise_status_before.get(promise.id) != promise.status
                and promise.status in {"kept", "broken"}
            )
            snapshot.revision += 1

            retelling: InferenceResult[RumorRetelling] | None = None
            dialogue_treatment: DialogueTreatment | None = None
            if request.verb == ActionVerb.CONFRONT and request.target_id == "bram":
                original_claim = "The newcomer confronted Bram about tripling the shipment price."
                retelling = self.inference.retell_rumor(
                    RumorRetellingRequest(
                        original_claim=original_claim,
                        speaker_id="bram",
                        listener_id="pip",
                        trust=0.6,
                        context=(
                            f"Greyhaven market row on day {snapshot.day}, "
                            f"{snapshot.phase}; town tick {snapshot.world_tick}."
                        ),
                    )
                )
                pip = next(npc for npc in snapshot.npcs if npc.id == "pip")
                pip.speech = retelling.value.retold_claim
            if request.verb == ActionVerb.TALK:
                dialogue_treatment = self._apply_memory_driven_dialogue(
                    run_id,
                    snapshot,
                    request,
                )

            response = ActionResponse(
                action_id=uuid4(),
                consumed_time=consumed_time,
                snapshot=snapshot,
            )
            memory_effects = plan_action_memory(
                request,
                response,
                self.embeddings,
                retelling,
                dialogue_treatment,
                promise_transitions,
            )
            try:
                return self.repository.update(
                    run_id,
                    snapshot,
                    request,
                    request.idempotency_key,
                    response,
                    memory_effects,
                )
            except ConcurrentRunUpdateError:
                if attempt == self.max_concurrency_retries:
                    raise
        raise AssertionError("Unreachable concurrency retry state.")

    def _apply_memory_driven_dialogue(
        self,
        run_id: UUID,
        snapshot: RunSnapshot,
        request: ActionRequest,
    ) -> DialogueTreatment | None:
        assert request.target_id is not None
        question = request.content
        if not question:
            return None
        try:
            recalled = self.recall_memories(
                run_id,
                MemoryRecallRequest(
                    holder_id=request.target_id,
                    query=question,
                    limit=4,
                ),
            )
        except Exception as error:
            logger.warning(
                "dialogue_recall_failed",
                operation="talk",
                reason=type(error).__name__,
            )
            return None

        memories = [
            (f"[contested] {memory.narrative_text}" if memory.contested else memory.narrative_text)
            for memory in recalled.memories
        ]
        npc = self._require_npc(snapshot, request.target_id)
        treatment = derive_dialogue_treatment(
            recalled.memories,
            npc.relationship,
        )
        npc.relationship = treatment.relationship_score
        result = self.inference.generate_dialogue(
            DialogueRequest(
                npc_id=request.target_id,
                player_message=question,
                recalled_memories=memories,
                current_mood=(
                    "guarded"
                    if any(memory.contested for memory in recalled.memories)
                    else "neutral"
                ),
            )
        )
        snapshot.dialogue = DialogueState(
            speaker_id=npc.id,
            speaker_name=npc.name,
            text=result.value.text,
            recalled_memories=[
                DialogueMemoryRef(
                    belief_id=memory.belief_id,
                    version=memory.version,
                    proposition_key=memory.proposition_key,
                    contested=memory.contested,
                )
                for memory in recalled.memories
            ],
            provider_id=result.provider_id,
            model_id=result.model_id,
            fallback_used=result.fallback_used,
            fallback_reason=result.fallback_reason,
            treatment_cue=treatment.cue,
            available_choices=list(treatment.choices),
        )
        return treatment

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
            principal = self.content.residents_by_id[npc.id]
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
        if request.verb == ActionVerb.SETTLE_SHIPMENT:
            if request.target_id != "bram":
                raise InvalidActionError("Marta's shipment must be settled with Bram.")
            promise = next(
                (
                    item
                    for item in snapshot.promises
                    if item.promisee_id == "marta" and item.status == "active"
                ),
                None,
            )
            if promise is None:
                raise InvalidActionError("There is no active shipment promise to settle.")
            promise.status = "kept"
            self._add_traits(snapshot, "Reliable", "Generous")
            snapshot.dialogue = DialogueState(
                speaker_id="bram",
                speaker_name="Bram Coyle",
                text=(
                    "Fine. Marta's crates leave my ledger today. "
                    "Greyhaven will hear what your word cost you."
                ),
            )
            return self._event(
                "promise_kept",
                "Bram releases Marta's shipment. You kept your word before evening.",
            )
        if request.verb == ActionVerb.DECLARE_CANDIDACY:
            if request.target_id != "rhea":
                raise InvalidActionError("Declare your candidacy to Rhea at the guildhouse.")
            if snapshot.day < 2:
                raise InvalidActionError("Greyhaven will not accept declarations before day two.")
            if snapshot.player.candidate:
                raise InvalidActionError("You already declared your candidacy.")
            snapshot.player.candidate = True
            snapshot.dialogue = DialogueState(
                speaker_id="rhea",
                speaker_name="Rhea Kest",
                text=(
                    "Then stand in the square at midnight and learn whether "
                    "Greyhaven remembers your name kindly."
                ),
            )
            return self._event(
                "candidacy_declared",
                "You declare for mayor. Rhea's smile does not reach her eyes.",
            )
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
        elif any(promise.status == "broken" for promise in snapshot.promises):
            pip.speech = "Evening came. Marta got no crates, only the newcomer's empty word."
        elif any(promise.status == "kept" for promise in snapshot.promises):
            pip.speech = "The newcomer paid Bram's price. Marta's crates are moving at last."
        elif snapshot.promises:
            pip.speech = "Marta found herself a hero—or another empty promise."
        else:
            pip.speech = "The newcomer is asking questions already."

    @classmethod
    def _resolve_expired_promises(
        cls,
        snapshot: RunSnapshot,
    ) -> list[WorldEvent]:
        phase_order = {
            "morning": 0,
            "afternoon": 1,
            "evening": 2,
            "night": 3,
        }
        events: list[WorldEvent] = []
        for promise in snapshot.promises:
            deadline_reached = (
                snapshot.day > promise.deadline_day
                or (
                    snapshot.day == promise.deadline_day
                    and phase_order[snapshot.phase] >= phase_order[promise.deadline_phase]
                )
            )
            if promise.status != "active" or not deadline_reached:
                continue
            promise.status = "broken"
            cls._add_traits(snapshot, "Dishonest", "Troublemaker")
            events.append(
                cls._event(
                    "promise_broken",
                    "Evening arrives without Marta's shipment. Greyhaven marks your word broken.",
                )
            )
        return events

    @staticmethod
    def _add_traits(snapshot: RunSnapshot, *traits: str) -> None:
        for trait in traits:
            if trait not in snapshot.player.traits:
                snapshot.player.traits.append(trait)

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
