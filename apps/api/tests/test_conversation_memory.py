from __future__ import annotations

from uuid import UUID, uuid4

from hearsay_api.election import resolve_election
from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import ActionRequest, ActionVerb, CreateRunRequest
from hearsay_api.service import GameService


def talk(
    service: GameService,
    run_id: UUID,
    npc_id: str,
    message: str,
    *,
    public: bool = False,
):
    return service.take_action(
        run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb=ActionVerb.TALK,
            target_id=npc_id,
            content=message,
            public_statement=public,
        ),
    )


def test_any_resident_can_remember_a_private_free_form_conversation() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(
        CreateRunRequest(
            display_name="Ada",
            seed=1729,
            release_profile="hackathon_small",
        )
    )

    assert created.snapshot.action_budget == 18
    first = talk(
        service,
        created.run_id,
        "nessa",
        "Rhea rigged the last election and that was unfair.",
    )
    assert first.snapshot.action_count == 1
    assert [message.speaker for message in first.snapshot.conversation_history] == [
        "npc",
        "player",
        "npc",
    ]
    assert first.snapshot.conversation_history[1].public_statement is False
    assert "Rhea rigged the last election" in first.snapshot.conversation_history[1].text

    lineage = service.get_memory_lineage(created.run_id, "conversation-about-rhea")
    assert {memory.holder_id for memory in lineage.versions} == {"nessa"}
    memory = lineage.versions[0]
    assert memory.normalized_position["memory_scope"] == "individual"
    assert memory.normalized_position["election_contribution"] == 0.18

    recalled = talk(
        service,
        created.run_id,
        "nessa",
        "What did I tell you about Rhea and the election?",
    )
    assert recalled.snapshot.dialogue is not None
    assert len(recalled.snapshot.conversation_history) == 5
    assert any(
        item.scope == "individual" and item.proposition_key == "conversation-about-rhea"
        for item in recalled.snapshot.dialogue.recalled_memories
    )
    assert any(
        "Rhea rigged the last election" in item.summary
        for item in recalled.snapshot.dialogue.recalled_memories
    )


def test_public_chat_creates_town_memory_and_versioned_rumor_hops() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(
        CreateRunRequest(
            display_name="Ada",
            seed=1729,
            release_profile="hackathon_small",
        )
    )
    talk(service, created.run_id, "nessa", "What is happening at the harbor?")
    response = talk(
        service,
        created.run_id,
        "pip",
        "Tell everyone that Rhea is corrupt and rigged the vote.",
        public=True,
    )

    lineage = service.get_memory_lineage(created.run_id, "conversation-about-rhea")
    holders = {memory.holder_id for memory in lineage.versions}
    assert {"pip", "town"}.issubset(holders)
    assert any(memory.normalized_position["memory_scope"] == "town" for memory in lineage.versions)
    assert lineage.transmissions
    assert any(edge.speaker_id == "pip" for edge in lineage.transmissions)
    assert any(npc.recent_echoes for npc in response.snapshot.npcs)
    pip_player_message = next(
        message
        for message in response.snapshot.conversation_history
        if message.npc_id == "pip" and message.speaker == "player"
    )
    assert pip_player_message.public_statement is True

    another = talk(
        service,
        created.run_id,
        "marta",
        "What is the town saying about Rhea?",
    )
    assert another.snapshot.dialogue is not None
    assert any(item.scope == "town" for item in another.snapshot.dialogue.recalled_memories)


def test_pip_conversation_is_private_unless_the_player_selects_town_sharing() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(
        CreateRunRequest(
            display_name="Ada",
            seed=1729,
            release_profile="hackathon_small",
        )
    )
    response = talk(
        service,
        created.run_id,
        "pip",
        "Rhea rigged the election, but keep this between us.",
    )

    lineage = service.get_memory_lineage(created.run_id, "conversation-about-rhea")
    assert {memory.holder_id for memory in lineage.versions} == {"pip"}
    assert lineage.transmissions == []
    player_message = next(
        message for message in response.snapshot.conversation_history if message.speaker == "player"
    )
    assert player_message.public_statement is False


def test_voter_uses_their_own_chat_memory_as_a_cited_election_input() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=1729))
    talk(
        service,
        created.run_id,
        "nessa",
        "Rhea cheated and rigged the last election.",
    )
    snapshot = service.get_snapshot(created.run_id)
    snapshot.player.candidate = True
    election = resolve_election(
        snapshot,
        service.content,
        service.get_memory_lineage(created.run_id),
    )

    nessa_vote = next(vote for vote in election.votes if vote.voter_id == "nessa")
    chat_input = next(item for item in nessa_vote.inputs if item.key == "conversation-about-rhea")
    assert chat_input.kind == "belief"
    assert chat_input.contribution == 0.18
    assert chat_input.belief_id is not None
    assert chat_input.belief_version == 1


def test_ambient_voter_uses_a_claim_about_another_resident() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=1729))
    talk(
        service,
        created.run_id,
        "kit",
        "Bram lied and stole from the harbor.",
    )
    snapshot = service.get_snapshot(created.run_id)
    snapshot.player.candidate = True
    election = resolve_election(
        snapshot,
        service.content,
        service.get_memory_lineage(created.run_id),
    )

    kit_vote = next(vote for vote in election.votes if vote.voter_id == "kit")
    chat_input = next(item for item in kit_vote.inputs if item.key == "conversation-about-bram")
    assert chat_input.contribution == -0.04
    assert chat_input.explanation == (
        "They remember what the player personally told them about bram."
    )
    assert chat_input.belief_id is not None
