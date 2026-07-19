from __future__ import annotations

from typing import Literal, cast
from uuid import UUID, uuid4

import structlog

from hearsay_api.content import BramApproachContent, GreyhavenContent, load_content
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
    VisibleAmbientEcho,
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
    FavorState,
    LocationState,
    MemoryLineageResponse,
    MemoryRecallRequest,
    MemoryRecallResponse,
    NpcEchoState,
    NpcState,
    PlayerState,
    PromiseState,
    RunSnapshot,
    TownEventState,
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

BRAM_APPROACH_VERBS = {
    ActionVerb.CONFRONT,
    ActionVerb.THREATEN_BRAM,
    ActionVerb.FLATTER_BRAM,
    ActionVerb.NEGOTIATE_BRAM,
    ActionVerb.LIE_TO_BRAM,
}

ARGUMENT_CHOICE_VERBS = {
    ActionVerb.SIDE_WITH_BRAM,
    ActionVerb.SIDE_WITH_NESSA,
    ActionVerb.CALM_ARGUMENT,
}

ORIN_CONFESSION_CHOICE_VERBS = {
    ActionVerb.REVEAL_ORIN_CONFESSION,
    ActionVerb.CONCEAL_ORIN_CONFESSION,
}

TALIA_SICK_HOUSE_CHOICE_VERBS = {
    ActionVerb.HELP_OSWIN_QUIETLY,
    ActionVerb.GOSSIP_OSWIN_ILLNESS,
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
                location_id=self.content.scheduled_location(
                    item.id,
                    day=1,
                    phase="morning",
                ),
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
        effective_limit = (
            min(request.limit, 3)
            if request.holder_id in self.content.ambients_by_id
            else request.limit
        )
        return self.repository.recall_memories(
            run_id,
            request.holder_id,
            request.query,
            query_embedding.vector,
            effective_limit,
        )

    def take_action(self, run_id: UUID, request: ActionRequest) -> ActionResponse:
        cached = self.repository.get_action_result(run_id, request.idempotency_key)
        if cached is not None:
            return cached

        for attempt in range(self.max_concurrency_retries + 1):
            snapshot = self._hydrate_content(self.repository.get(run_id))
            town_event_transitions: tuple[str, ...] = ()
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
                town_event_events = self._update_town_events(snapshot)
                town_event_transitions = tuple(
                    event.kind
                    for event in town_event_events
                )
                schedule_event = self._apply_schedules(snapshot)
                promise_events = self._resolve_expired_promises(snapshot)
                transition_events = list(town_event_events)
                if schedule_event is not None:
                    transition_events.append(schedule_event)
                snapshot.recent_events = (
                    promise_events
                    + snapshot.recent_events[:1]
                    + transition_events
                    + snapshot.recent_events[1:]
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
            if request.verb in BRAM_APPROACH_VERBS and request.target_id == "bram":
                approach = self._bram_approach(request.verb)
                original_claim = approach.original_claim
                retelling = self.inference.retell_rumor(
                    RumorRetellingRequest(
                        original_claim=original_claim,
                        speaker_id="bram",
                        listener_id="pip",
                        trust=0.6,
                        context=(
                            f"Greyhaven market row after the player chose "
                            f"{approach.action_verb} on day {snapshot.day}, "
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
                self.content,
                retelling,
                dialogue_treatment,
                promise_transitions,
                town_event_transitions,
            )
            self._apply_visible_ambient_echoes(
                snapshot,
                memory_effects.visible_ambient_echoes,
            )
            response.snapshot = snapshot
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
                text=npc.speech or principal.opening,
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
        if request.verb in BRAM_APPROACH_VERBS:
            if request.target_id != "bram":
                raise InvalidActionError("The opening shipment dispute targets Bram.")
            approach = self._bram_approach(request.verb)
            bram = self._require_npc(snapshot, "bram")
            bram.relationship = max(
                -100,
                min(100, bram.relationship + approach.relationship_delta),
            )
            self._add_traits(snapshot, *approach.traits)
            snapshot.dialogue = DialogueState(
                speaker_id="bram",
                speaker_name="Bram Coyle",
                text=approach.dialogue,
            )
            return self._event(approach.event_kind, approach.event_text)
        if request.verb in ARGUMENT_CHOICE_VERBS:
            argument = next(
                (
                    event
                    for event in snapshot.town_events
                    if event.key == "public_argument"
                    and event.status == "active"
                ),
                None,
            )
            if argument is None:
                raise InvalidActionError(
                    "Bram and Nessa are not currently arguing in the square."
                )
            if snapshot.player.argument_choice is not None:
                raise InvalidActionError(
                    "You already chose how to answer the public argument."
                )
            choice = self.content.argument_choices_by_verb[request.verb.value]
            snapshot.player.argument_choice = request.verb.value
            bram = self._require_npc(snapshot, "bram")
            nessa = self._require_npc(snapshot, "nessa")
            bram.relationship = max(
                -100,
                min(
                    100,
                    bram.relationship + choice.bram_relationship_delta,
                ),
            )
            nessa.relationship = max(
                -100,
                min(
                    100,
                    nessa.relationship + choice.nessa_relationship_delta,
                ),
            )
            self._add_traits(snapshot, *choice.traits)
            speaker = self._require_npc(
                snapshot,
                choice.dialogue_speaker_id,
            )
            snapshot.dialogue = DialogueState(
                speaker_id=speaker.id,
                speaker_name=speaker.name,
                text=choice.dialogue,
            )
            pip = self._require_npc(snapshot, "pip")
            pip.speech = choice.memory_text
            return self._event(choice.event_kind, choice.event_text)
        if request.verb == ActionVerb.ACCEPT_NESSA_FAVOR:
            if request.target_id != "nessa":
                raise InvalidActionError("The harbor-log favor comes from Nessa.")
            if snapshot.day < 2:
                raise InvalidActionError("Nessa offers the harbor log after the storm.")
            if any(favor.key == "nessa_harbor_log" for favor in snapshot.favors):
                raise InvalidActionError("You already answered Nessa's harbor-log favor.")
            content = self.content.favors_by_id["nessa_harbor_log"]
            snapshot.favors.append(
                FavorState(
                    id=uuid4(),
                    key=content.id,
                    giver_id=content.giver_id,
                    content=content.content,
                )
            )
            snapshot.dialogue = DialogueState(
                speaker_id="nessa",
                speaker_name="Nessa Reed",
                text=content.accept_dialogue,
            )
            return self._event(
                "nessa_favor_accepted",
                "You agree to carry Nessa's storm log to Elias.",
            )
        if request.verb == ActionVerb.DELIVER_HARBOR_LOG:
            if request.target_id != "elias":
                raise InvalidActionError("Nessa's harbor log must go to Elias.")
            favor = next(
                (
                    item
                    for item in snapshot.favors
                    if item.key == "nessa_harbor_log"
                ),
                None,
            )
            if favor is None or favor.status != "active":
                raise InvalidActionError("There is no active harbor-log favor.")
            favor.status = "completed"
            nessa = self._require_npc(snapshot, "nessa")
            elias = self._require_npc(snapshot, "elias")
            nessa.relationship = min(100, nessa.relationship + 25)
            elias.relationship = min(100, elias.relationship + 10)
            self._add_traits(snapshot, "Reliable")
            content = self.content.favors_by_id["nessa_harbor_log"]
            snapshot.dialogue = DialogueState(
                speaker_id="elias",
                speaker_name="Elias Ward",
                text=content.complete_dialogue,
            )
            return self._event(
                "harbor_log_delivered",
                "Elias accepts Nessa's dated harbor log as evidence.",
            )
        if request.verb == ActionVerb.CORRECT_STORM_RUMOR:
            if request.target_id != "pip":
                raise InvalidActionError("Correct the storm rumor with Pip.")
            favor = next(
                (
                    item
                    for item in snapshot.favors
                    if item.key == "nessa_harbor_log"
                ),
                None,
            )
            if favor is None or favor.status != "completed":
                raise InvalidActionError("Deliver the harbor log before correcting the rumor.")
            if favor.corrected_publicly:
                raise InvalidActionError("You already corrected the storm rumor.")
            favor.corrected_publicly = True
            content = self.content.favors_by_id["nessa_harbor_log"]
            pip = self._require_npc(snapshot, "pip")
            pip.speech = content.correction_text
            snapshot.dialogue = DialogueState(
                speaker_id="pip",
                speaker_name="Pip Marr",
                text="Evidence is terribly inconvenient. It does make a better story, though.",
            )
            return self._event(
                "storm_rumor_corrected",
                "You make Pip read the harbor log aloud to the square.",
            )
        if request.verb == ActionVerb.ASK_NESSA_ENDORSEMENT:
            if request.target_id != "nessa":
                raise InvalidActionError("Ask Nessa for the harbor endorsement.")
            favor = next(
                (
                    item
                    for item in snapshot.favors
                    if item.key == "nessa_harbor_log"
                ),
                None,
            )
            if favor is None or not favor.corrected_publicly:
                raise InvalidActionError(
                    "Correct Bram's storm story before asking Nessa to endorse you."
                )
            if "nessa" in snapshot.player.endorsements:
                raise InvalidActionError("Nessa already endorsed your candidacy.")
            snapshot.player.endorsements.append("nessa")
            self._add_traits(snapshot, "Influential")
            snapshot.dialogue = DialogueState(
                speaker_id="nessa",
                speaker_name="Nessa Reed",
                text="The harbor remembers who brought proof instead of another accusation.",
            )
            return self._event(
                "nessa_endorsement",
                "Nessa gives the newcomer the harbor faction's public backing.",
            )
        if request.verb == ActionVerb.ACCEPT_ORIN_CONFESSION:
            if request.target_id != "orin":
                raise InvalidActionError("Orin's confession can only be accepted from Orin.")
            if any(
                favor.key == "orin_election_confession"
                for favor in snapshot.favors
            ):
                raise InvalidActionError("You already accepted Orin's confidence.")
            content = self.content.favors_by_id["orin_election_confession"]
            snapshot.favors.append(
                FavorState(
                    id=uuid4(),
                    key=content.id,
                    giver_id=content.giver_id,
                    content=content.content,
                )
            )
            snapshot.dialogue = DialogueState(
                speaker_id="orin",
                speaker_name="Father Orin",
                text=content.accept_dialogue,
            )
            return self._event(
                "orin_confession_entrusted",
                "Orin entrusts you with a dying clerk's account of Rhea's last tally.",
            )
        if request.verb in ORIN_CONFESSION_CHOICE_VERBS:
            if request.target_id != "orin":
                raise InvalidActionError("Resolve Orin's confidence with Orin present.")
            favor = next(
                (
                    item
                    for item in snapshot.favors
                    if item.key == "orin_election_confession"
                ),
                None,
            )
            if favor is None or favor.status != "active":
                raise InvalidActionError("There is no unresolved confession in your care.")
            confession_choice = self.content.favor_choices_by_verb[
                request.verb.value
            ]
            favor.status = "completed"
            favor.resolution = confession_choice.resolution
            for resident_id, delta in (
                confession_choice.relationship_deltas.items()
            ):
                resident = self._require_npc(snapshot, resident_id)
                resident.relationship = max(
                    -100,
                    min(100, resident.relationship + delta),
                )
            self._add_traits(snapshot, *confession_choice.traits)
            if (
                confession_choice.grants_endorsement
                and "orin" not in snapshot.player.endorsements
            ):
                snapshot.player.endorsements.append("orin")
            for resident_id, speech in (
                confession_choice.resident_speeches.items()
            ):
                self._require_npc(snapshot, resident_id).speech = speech
            snapshot.dialogue = DialogueState(
                speaker_id="orin",
                speaker_name="Father Orin",
                text=confession_choice.dialogue,
            )
            return self._event(
                confession_choice.event_kind,
                confession_choice.event_text,
            )
        if request.verb == ActionVerb.ACCEPT_TALIA_FAVOR:
            if request.target_id != "talia":
                raise InvalidActionError("The sick-house favor comes from Talia.")
            if any(favor.key == "talia_sick_house" for favor in snapshot.favors):
                raise InvalidActionError("You already answered Talia's sick-house request.")
            content = self.content.favors_by_id["talia_sick_house"]
            snapshot.favors.append(
                FavorState(
                    id=uuid4(),
                    key=content.id,
                    giver_id=content.giver_id,
                    content=content.content,
                )
            )
            self._require_npc(snapshot, "oswin").speech = (
                "Talia says the fever is ordinary. Pip will make it a plague by noon."
            )
            snapshot.dialogue = DialogueState(
                speaker_id="talia",
                speaker_name="Talia Fen",
                text=content.accept_dialogue,
            )
            return self._event(
                "talia_sick_house_entrusted",
                "Talia asks you to carry care to Oswin without feeding the town's fear.",
            )
        if request.verb in TALIA_SICK_HOUSE_CHOICE_VERBS:
            if request.target_id != "talia":
                raise InvalidActionError("Resolve Talia's request with Talia present.")
            favor = next(
                (
                    item
                    for item in snapshot.favors
                    if item.key == "talia_sick_house"
                ),
                None,
            )
            if favor is None or favor.status != "active":
                raise InvalidActionError("There is no unresolved sick-house favor.")
            favor_choice = self.content.favor_choices_by_verb[request.verb.value]
            favor.status = "completed"
            favor.resolution = favor_choice.resolution
            for resident_id, delta in favor_choice.relationship_deltas.items():
                resident = self._require_npc(snapshot, resident_id)
                resident.relationship = max(
                    -100,
                    min(100, resident.relationship + delta),
                )
            self._add_traits(snapshot, *favor_choice.traits)
            if favor_choice.grants_endorsement:
                snapshot.player.endorsements.append("talia")
            for resident_id, speech in favor_choice.resident_speeches.items():
                self._require_npc(snapshot, resident_id).speech = speech
            snapshot.dialogue = DialogueState(
                speaker_id="talia",
                speaker_name="Talia Fen",
                text=favor_choice.dialogue,
            )
            return self._event(favor_choice.event_kind, favor_choice.event_text)
        if request.verb == ActionVerb.GIVE_SQUARE_SPEECH:
            if not snapshot.player.candidate:
                raise InvalidActionError("Declare your candidacy before addressing the square.")
            if snapshot.day in snapshot.player.square_speech_days:
                raise InvalidActionError("You already addressed the square today.")
            snapshot.player.square_speech_days.append(snapshot.day)
            self._add_traits(snapshot, "Influential")
            pip = self._require_npc(snapshot, "pip")
            pip.speech = (
                "The newcomer made the square listen. Listening is not the same as believing."
            )
            snapshot.dialogue = DialogueState(
                speaker_id="pip",
                speaker_name="Pip Marr",
                text=(
                    "Good rhythm. Strong ending. Half the town heard hope; "
                    "the other half heard rehearsal."
                ),
            )
            return self._event(
                "square_speech",
                "You make Greyhaven listen, though not every listener is persuaded.",
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

    def _bram_approach(self, verb: ActionVerb) -> BramApproachContent:
        content_verb = (
            ActionVerb.NEGOTIATE_BRAM.value
            if verb == ActionVerb.CONFRONT
            else verb.value
        )
        return self.content.bram_approaches_by_verb[content_verb]

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
    def _apply_schedules(self, snapshot: RunSnapshot) -> WorldEvent | None:
        destinations: dict[str, int] = {}
        moved = 0
        for npc in snapshot.npcs:
            desired_location = self._scheduled_location(
                snapshot,
                npc.id,
            )
            if npc.location_id == desired_location:
                continue
            npc.location_id = desired_location
            destinations[desired_location] = destinations.get(desired_location, 0) + 1
            moved += 1

        if moved == 0:
            return None

        destination_summary = ", ".join(
            (
                f"{self.content.locations_by_id[location_id].name} ({count})"
                for location_id, count in sorted(
                    destinations.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            )
        )
        return self._event(
            "schedule_shift",
            (
                f"{snapshot.phase.title()} routines move {moved} residents: "
                f"{destination_summary}."
            ),
        )

    def _scheduled_location(
        self,
        snapshot: RunSnapshot,
        resident_id: str,
    ) -> str:
        for event_state in snapshot.town_events:
            if event_state.status != "active":
                continue
            event = self.content.town_events_by_id[event_state.key]
            if event.schedule_location_override is not None:
                return event.schedule_location_override
        return self.content.scheduled_location(
            resident_id,
            snapshot.day,
            snapshot.phase,
        )

    def _update_town_events(
        self,
        snapshot: RunSnapshot,
    ) -> list[WorldEvent]:
        phase_order = {
            "morning": 0,
            "afternoon": 1,
            "evening": 2,
            "night": 3,
        }
        current_time = snapshot.day * 4 + phase_order[snapshot.phase]
        events: list[WorldEvent] = []
        for event_content in self.content.town_events:
            start_time = (
                event_content.start_day * 4
                + phase_order[event_content.start_phase]
            )
            end_time = (
                event_content.end_day * 4
                + phase_order[event_content.end_phase]
            )
            state = next(
                (
                    item
                    for item in snapshot.town_events
                    if item.key == event_content.id
                ),
                None,
            )
            if state is None and current_time >= start_time:
                state = TownEventState(
                    id=uuid4(),
                    key=event_content.id,
                    title=event_content.title,
                    status="active",
                    started_day=event_content.start_day,
                    started_phase=cast(
                        Literal["morning", "afternoon", "evening", "night"],
                        event_content.start_phase,
                    ),
                )
                snapshot.town_events.append(state)
                self._apply_event_awareness(
                    snapshot,
                    event_content.active_awareness,
                )
                events.append(
                    self._event(
                        f"{event_content.id}_begins",
                        event_content.start_text,
                    )
                )
            if (
                state is not None
                and state.status == "active"
                and current_time >= end_time
            ):
                state.status = "resolved"
                state.resolved_day = event_content.end_day
                state.resolved_phase = cast(
                    Literal["morning", "afternoon", "evening", "night"],
                    event_content.end_phase,
                )
                self._apply_event_awareness(
                    snapshot,
                    event_content.resolved_awareness,
                )
                events.append(
                    self._event(
                        f"{event_content.id}_clears",
                        event_content.end_text,
                    )
                )

        snapshot.weather = (
            "rain"
            if any(
                event.status == "active" and event.key == "storm"
                for event in snapshot.town_events
            )
            else "clear"
        )
        return events

    @staticmethod
    def _apply_event_awareness(
        snapshot: RunSnapshot,
        awareness: dict[str, str],
    ) -> None:
        for resident_id, speech in awareness.items():
            npc = next(item for item in snapshot.npcs if item.id == resident_id)
            npc.speech = speech

    @classmethod
    def _apply_visible_ambient_echoes(
        cls,
        snapshot: RunSnapshot,
        echoes: tuple[VisibleAmbientEcho, ...],
    ) -> None:
        if not echoes:
            return
        listener_names: list[str] = []
        for echo in echoes:
            npc = next(
                item
                for item in snapshot.npcs
                if item.id == echo.listener_id
            )
            npc.recent_echoes = (
                npc.recent_echoes
                + [
                    NpcEchoState(
                        proposition_key=echo.proposition_key,
                        speaker_id=echo.speaker_id,
                        text=echo.text,
                    )
                ]
            )[-3:]
            npc.speech = echo.text
            listener_names.append(npc.name)
        chatter_event = cls._event(
            "ambient_gossip",
            f"Pip's version reaches {', '.join(listener_names)}.",
        )
        snapshot.recent_events = (
            snapshot.recent_events[:1]
            + [chatter_event]
            + snapshot.recent_events[1:]
        )[:8]

    @staticmethod
    def _run_gossip_tick(snapshot: RunSnapshot) -> None:
        snapshot.world_tick += 1
        pip = next(npc for npc in snapshot.npcs if npc.id == "pip")
        storm_active = any(
            event.key == "storm" and event.status == "active"
            for event in snapshot.town_events
        )
        argument_active = any(
            event.key == "public_argument"
            and event.status == "active"
            for event in snapshot.town_events
        )
        if storm_active and any(
            promise.status == "broken"
            for promise in snapshot.promises
        ):
            pip.speech = (
                "The storm drove everyone inside to hear how evening exposed "
                "the newcomer's empty word."
            )
        elif storm_active and any(
            promise.status == "kept"
            for promise in snapshot.promises
        ):
            pip.speech = (
                "Even through the storm, Marta's crates are moving. "
                "The newcomer paid Bram's price."
            )
        elif storm_active:
            pip.speech = (
                "Nessa's boats stayed in. Bram says that makes every late crate her fault."
            )
        elif argument_active:
            pip.speech = (
                "Bram blames Nessa for the storm. "
                "Nessa says Bram counts drowned sailors as breakage."
            )
        elif any(event.kind == "bram_confronted" for event in snapshot.recent_events[:2]):
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
