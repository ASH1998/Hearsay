from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from hearsay_api.content import GreyhavenContent
from hearsay_api.schemas import (
    ElectionState,
    EndingKey,
    EndingState,
    MemoryLineageResponse,
    MemoryVersionState,
    RunSnapshot,
    VoteChoice,
    VoteInputState,
    VoteState,
)

TRAIT_CONTRIBUTIONS = {
    "Reliable": 0.12,
    "Generous": 0.08,
    "Dangerous": -0.4,
    "Dishonest": -0.25,
    "Influential": 0.15,
    "Troublemaker": -0.15,
}


@dataclass(frozen=True)
class PendingInput:
    kind: Literal["base", "trait", "relationship", "belief"]
    key: str
    value: str | float | bool | None
    weight: float
    contribution: float
    explanation: str
    belief_id: UUID | None = None
    belief_version: int | None = None


def resolve_election(
    snapshot: RunSnapshot,
    content: GreyhavenContent,
    lineage: MemoryLineageResponse,
) -> ElectionState:
    active_by_holder: dict[str, list[MemoryVersionState]] = {}
    for memory in lineage.versions:
        if memory.active:
            active_by_holder.setdefault(memory.holder_id, []).append(memory)

    votes: list[VoteState] = []
    for resident in content.residents:
        pending = [
            PendingInput(
                kind="base",
                key="voter_bias",
                value=resident.voter_bias,
                weight=1,
                contribution=resident.voter_bias,
                explanation=(
                    f"{resident.name}'s authored starting disposition toward a newcomer."
                ),
            )
        ]
        for trait in snapshot.player.traits:
            contribution = TRAIT_CONTRIBUTIONS.get(trait)
            if contribution is None:
                continue
            pending.append(
                PendingInput(
                    kind="trait",
                    key=trait,
                    value=True,
                    weight=contribution,
                    contribution=contribution,
                    explanation=f"The notice board marks the player as {trait}.",
                )
            )

        npc = next(item for item in snapshot.npcs if item.id == resident.id)
        relationship_contribution = (npc.relationship / 100) * 0.4
        if relationship_contribution:
            pending.append(
                PendingInput(
                    kind="relationship",
                    key="direct_standing",
                    value=npc.relationship,
                    weight=0.4,
                    contribution=relationship_contribution,
                    explanation=(
                        f"{resident.name}'s direct standing with the player is "
                        f"{npc.relationship:+d}."
                    ),
                )
            )

        resident_memories = active_by_holder.get(resident.id, [])
        if resident.id in content.ambients_by_id:
            resident_memories = resident_memories[-3:]
        for memory in resident_memories:
            proposition_key = memory.proposition_key
            contribution = 0.0
            explanation = ""
            value: str | float | bool | None = None
            if proposition_key == "player-promise-marta-shipment":
                status_value = memory.normalized_position.get("promise_status")
                value = status_value if isinstance(status_value, str) else None
                if value == "kept":
                    contribution = 0.35
                    explanation = "They remember that the shipment promise was kept."
                elif value == "broken":
                    contribution = -0.5
                    explanation = "They remember that evening exposed a broken promise."
            elif proposition_key == "bram-price-confrontation":
                approach = memory.normalized_position.get("approach")
                value = approach if isinstance(approach, str) else "market_dispute"
                raw_contribution = memory.normalized_position.get(
                    "election_contribution",
                )
                contribution = (
                    float(raw_contribution)
                    if isinstance(raw_contribution, int | float)
                    else -0.25
                )
                explanation = (
                    "They retain the market-row account of the player's "
                    f"{value.replace('_bram', '').replace('_', ' ')} approach."
                )
            elif proposition_key == "public-argument-player-intervention":
                choice = memory.normalized_position.get("choice")
                value = choice if isinstance(choice, str) else None
                raw_contribution = memory.normalized_position.get(
                    "election_contribution",
                )
                contribution = (
                    float(raw_contribution)
                    if isinstance(raw_contribution, int | float)
                    else 0.0
                )
                explanation = (
                    "They remember how the player answered Bram and Nessa's "
                    f"argument: {(value or 'unknown').replace('_', ' ')}."
                )
            elif proposition_key == "nessa-storm-harbor-log":
                status = memory.normalized_position.get("status")
                value = status if isinstance(status, str) else None
                raw_contribution = memory.normalized_position.get(
                    "election_contribution",
                )
                contribution = (
                    float(raw_contribution)
                    if isinstance(raw_contribution, int | float)
                    else 0.0
                )
                explanation = (
                    "They remember the harbor log proved Nessa protected her "
                    f"crews; favor status: {value or 'known'}."
                )
            if (
                contribution
                and memory.normalized_position.get("echo_hop") == 2
            ):
                echo_style = memory.normalized_position.get("echo_style")
                contribution *= (
                    -0.05
                    if echo_style == "skeptical"
                    else 0.1
                )
                explanation = (
                    "Ambient echo, attenuated by distance and carrier style: "
                    f"{explanation}"
                )
            if not contribution:
                continue
            pending.append(
                PendingInput(
                    kind="belief",
                    key=proposition_key,
                    value=value,
                    weight=1,
                    contribution=contribution,
                    explanation=explanation,
                    belief_id=memory.belief_id,
                    belief_version=memory.version,
                )
            )

        if not snapshot.player.candidate:
            pending.append(
                PendingInput(
                    kind="base",
                    key="not_a_candidate",
                    value=True,
                    weight=-10,
                    contribution=-10,
                    explanation="The player never declared a candidacy.",
                )
            )
        score = sum(item.contribution for item in pending)
        decisive_indexes = {
            index: rank
            for rank, index in enumerate(
                sorted(
                    range(len(pending)),
                    key=lambda index: abs(pending[index].contribution),
                    reverse=True,
                )[:3],
                start=1,
            )
        }
        vote_id = uuid5(NAMESPACE_URL, f"{snapshot.run_id}:election:{resident.id}")
        inputs = [
            VoteInputState(
                id=uuid5(
                    NAMESPACE_URL,
                    f"{vote_id}:input:{index}:{item.kind}:{item.key}",
                ),
                kind=item.kind,
                key=item.key,
                value=item.value,
                weight=item.weight,
                contribution=item.contribution,
                explanation=item.explanation,
                belief_id=item.belief_id,
                belief_version=item.belief_version,
                decisive_rank=decisive_indexes.get(index),
            )
            for index, item in enumerate(pending)
        ]
        votes.append(
            VoteState(
                id=vote_id,
                voter_id=resident.id,
                choice="player" if score > 0 else "rhea",
                player_score=score,
                inputs=inputs,
            )
        )

    player_votes = sum(vote.choice == "player" for vote in votes)
    rhea_votes = len(votes) - player_votes
    winner: VoteChoice = "player" if player_votes > rhea_votes else "rhea"
    ending_key = classify_ending(
        player_votes=player_votes,
        traits=set(snapshot.player.traits),
        candidate=snapshot.player.candidate,
    )
    ending_content = content.endings_by_id[ending_key]
    memory_votes = [
        vote
        for vote in votes
        if any(item.kind == "belief" for item in vote.inputs)
    ]
    ordered_decisive = sorted(
        memory_votes,
        key=lambda item: abs(item.player_score),
    ) + [
        vote
        for vote in sorted(votes, key=lambda item: abs(item.player_score))
        if vote not in memory_votes
    ]
    decisive_voters = [vote.voter_id for vote in ordered_decisive[:3]]
    return ElectionState(
        id=uuid5(NAMESPACE_URL, f"{snapshot.run_id}:election"),
        player_votes=player_votes,
        rhea_votes=rhea_votes,
        winner=winner,
        tie_favors_rhea=player_votes == rhea_votes,
        votes=votes,
        ending=EndingState(
            key=ending_key,
            title=ending_content.title,
            summary=ending_content.summary,
            player_won=winner == "player",
            decisive_voter_ids=decisive_voters,
        ),
    )


def classify_ending(
    *,
    player_votes: int,
    traits: set[str],
    candidate: bool = True,
) -> EndingKey:
    if {"Dangerous", "Troublemaker"}.issubset(traits):
        return "run_out_of_town"
    if "Dishonest" in traits:
        return "exposed"
    if not candidate or player_votes <= 7:
        return "humiliation"
    if player_votes >= 14:
        return "landslide"
    if player_votes >= 11:
        return "narrow_win"
    return "narrow_loss"
