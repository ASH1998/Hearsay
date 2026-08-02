"""Export deterministic browser replay bundles for the static Hearsay showcase."""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from uuid import UUID, uuid5

from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import ActionRequest, ActionVerb, CreateRunRequest, RunSnapshot
from hearsay_api.service import GameService

REPLAY_NAMESPACE: Final = UUID("efeb4883-527d-4a80-b611-6cb8a0eebc46")


@dataclass(frozen=True)
class ReplayStep:
    verb: ActionVerb
    target_id: str | None
    content: str | None
    title: str
    detail: str
    duration_ms: int = 5200
    public_statement: bool = False


WIN_STEPS: Final = (
    ReplayStep(
        ActionVerb.PROMISE_HELP,
        "marta",
        None,
        "A promise at the inn",
        "The newcomer promises Marta that the blocked shipment will be released.",
    ),
    ReplayStep(
        ActionVerb.NEGOTIATE_BRAM,
        "bram",
        None,
        "Terms on Market Row",
        "Rather than threaten Bram, the newcomer negotiates—and Pip carries "
        "away a harsher version.",
    ),
    ReplayStep(
        ActionVerb.SETTLE_SHIPMENT,
        "bram",
        None,
        "The promise is kept",
        "The shipment is paid for before the deadline. Marta's memory changes "
        "from promise to proof.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "marta",
        "What happened to the shipment I promised to release?",
        "Marta remembers",
        "Marta retrieves the kept promise and answers with earned warmth.",
        6500,
    ),
    ReplayStep(
        ActionVerb.ACCEPT_TALIA_FAVOR,
        "talia",
        None,
        "A private request",
        "Talia entrusts the newcomer with Oswin's illness.",
    ),
    ReplayStep(
        ActionVerb.HELP_OSWIN_QUIETLY,
        "talia",
        None,
        "Discretion over influence",
        "The newcomer helps quietly. Talia and Oswin remember who protected them.",
    ),
    ReplayStep(
        ActionVerb.DECLARE_CANDIDACY,
        "rhea",
        None,
        "A name on the ballot",
        "The newcomer declares a candidacy before Rhea.",
    ),
    ReplayStep(
        ActionVerb.ACCEPT_RHEA_COMPACT,
        "rhea",
        None,
        "Rhea's compact",
        "Rhea offers private control of the ballot count.",
    ),
    ReplayStep(
        ActionVerb.CHALLENGE_RHEA_BALLOT,
        "rhea",
        None,
        "Witnesses at the count",
        "The newcomer rejects secrecy and demands a witnessed public count.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "rhea",
        "What do you remember about the ballot safeguards?",
        "Rhea recalls the challenge",
        "The ballot dispute returns in Rhea's own words.",
        6500,
    ),
    ReplayStep(
        ActionVerb.TALK,
        "nessa",
        "What do you remember about Rhea?",
        "The harbor weighs the story",
        "Nessa compares the claim with what reached the docks.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "elias",
        "Rhea rigged the last election.",
        "A dangerous accusation",
        "Elias stores the claim as contested rather than accepting it as fact.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "orin",
        "Do you trust Rhea with the ballot?",
        "Trust is personal",
        "Orin answers from his own history, not the town's consensus.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "pip",
        "Tell everyone Rhea is corrupt.",
        "Pip retells it",
        "Pip changes the wording and passes the allegation onward.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "marta",
        "What rumors reached the inn?",
        "The inn remembers",
        "Marta separates the newcomer she knows from the rumor she heard.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "bram",
        "Who do you support in the election?",
        "Bram counts the cost",
        "Bram's vote is shaped by the market confrontation.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "talia",
        "What does the town remember about me?",
        "A protected confidence",
        "Talia remembers that influence was not purchased with Oswin's privacy.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "rhea",
        "What will voters remember tonight?",
        "Election night",
        "Twenty residents vote from their own relationships and remembered evidence.",
        9000,
    ),
)


LOSS_STEPS: Final = (
    ReplayStep(
        ActionVerb.PROMISE_HELP,
        "marta",
        None,
        "A promise at the inn",
        "The newcomer promises Marta that the blocked shipment will be released.",
    ),
    ReplayStep(
        ActionVerb.LIE_TO_BRAM,
        "bram",
        None,
        "A lie on Market Row",
        "The newcomer invokes Elias with forged authority. Bram remembers the "
        "threat behind the story.",
    ),
    ReplayStep(
        ActionVerb.SETTLE_SHIPMENT,
        "bram",
        None,
        "One promise kept",
        "Marta sees the shipment released and remembers the newcomer as reliable.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "marta",
        "What happened to the shipment I promised to release?",
        "Marta remembers",
        "The kept promise earns trust—but one good memory cannot decide the whole town.",
        6500,
    ),
    ReplayStep(
        ActionVerb.ACCEPT_TALIA_FAVOR,
        "talia",
        None,
        "A private request",
        "Talia entrusts the newcomer with Oswin's illness.",
    ),
    ReplayStep(
        ActionVerb.GOSSIP_OSWIN_ILLNESS,
        "talia",
        None,
        "Privacy becomes leverage",
        "The newcomer turns Oswin's illness into a public warning. The family "
        "remembers the betrayal.",
    ),
    ReplayStep(
        ActionVerb.DECLARE_CANDIDACY,
        "rhea",
        None,
        "A name on the ballot",
        "The newcomer declares a candidacy despite the damage already spreading.",
    ),
    ReplayStep(
        ActionVerb.ACCEPT_RHEA_COMPACT,
        "rhea",
        None,
        "Rhea's compact",
        "Rhea offers a private arrangement over the ballot count.",
    ),
    ReplayStep(
        ActionVerb.DEAL_WITH_RHEA,
        "rhea",
        None,
        "A private deal",
        "The newcomer accepts the compact. Some voters read pragmatism; others see secrecy.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "rhea",
        "What do you remember about the ballot safeguards?",
        "Rhea remembers the deal",
        "The private compact now sits behind every public assurance.",
        6500,
    ),
    ReplayStep(
        ActionVerb.TALK,
        "nessa",
        "What do you remember about Rhea?",
        "The harbor is unconvinced",
        "Nessa weighs the ballot story against the newcomer's treatment of Oswin.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "elias",
        "Rhea rigged the last election.",
        "An accusation without proof",
        "The claim enters memory, but contested words do not erase witnessed behavior.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "orin",
        "Do you trust Rhea with the ballot?",
        "Orin keeps his distance",
        "Orin stores the question and answers from his own experience.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "pip",
        "Tell everyone Rhea is corrupt.",
        "Pip carries the accusation",
        "The allegation spreads, changing slightly with every teller.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "marta",
        "What rumors reached the inn?",
        "Goodwill has limits",
        "Marta remembers the shipment, but she also remembers what the town learned about Oswin.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "bram",
        "Who do you support in the election?",
        "The market decides",
        "Bram weighs negotiation against the later campaign.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "talia",
        "What does the town remember about me?",
        "Talia does not forget",
        "Talia retrieves the violated confidence that changed her family's votes.",
    ),
    ReplayStep(
        ActionVerb.TALK,
        "rhea",
        "What will voters remember tonight?",
        "Election night",
        "The same twenty residents vote again—but this history produces a loss.",
        9000,
    ),
)


def shortest_path(snapshot: RunSnapshot, destination: str) -> list[str]:
    start = snapshot.player.location_id
    if start == destination:
        return []
    neighbors = {location.id: location.neighbors for location in snapshot.locations}
    queue: deque[tuple[str, list[str]]] = deque([(start, [])])
    visited = {start}
    while queue:
        location_id, path = queue.popleft()
        for neighbor in neighbors.get(location_id, ()):
            if neighbor in visited:
                continue
            next_path = [*path, neighbor]
            if neighbor == destination:
                return next_path
            visited.add(neighbor)
            queue.append((neighbor, next_path))
    raise RuntimeError(f"No route from {start!r} to {destination!r}.")


def take_action(
    service: GameService,
    run_id: UUID,
    replay_id: str,
    sequence: int,
    verb: ActionVerb,
    target_id: str | None = None,
    content: str | None = None,
    public_statement: bool = False,
) -> RunSnapshot:
    response = service.take_action(
        run_id,
        ActionRequest(
            idempotency_key=uuid5(REPLAY_NAMESPACE, f"{replay_id}:{sequence}:{verb}"),
            verb=verb,
            target_id=target_id,
            content=content,
            public_statement=public_statement,
        ),
    )
    return response.snapshot


def move_to_target(
    service: GameService,
    snapshot: RunSnapshot,
    replay_id: str,
    sequence: int,
    target_id: str | None,
) -> tuple[RunSnapshot, int]:
    if target_id is None or target_id == "square":
        destination = target_id
    else:
        target = next((npc for npc in snapshot.npcs if npc.id == target_id), None)
        destination = target.location_id if target is not None else target_id
    if destination is None:
        return snapshot, sequence
    for location_id in shortest_path(snapshot, destination):
        sequence += 1
        snapshot = take_action(
            service,
            snapshot.run_id,
            replay_id,
            sequence,
            ActionVerb.MOVE,
            location_id,
        )
    return snapshot, sequence


def export_bundle(
    replay_id: str,
    seed: int,
    title: str,
    subtitle: str,
    accent: str,
    steps: tuple[ReplayStep, ...],
    expected_ending: str,
) -> dict[str, object]:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(
        CreateRunRequest(
            display_name="Newcomer",
            seed=seed,
            release_profile="hackathon_small",
        )
    )
    snapshot = created.snapshot
    frames: list[dict[str, object]] = [
        {
            "duration_ms": 3000,
            "title": "Three days before the election",
            "detail": (
                "The newcomer arrives in Greyhaven, where every resident remembers "
                "a different version of the truth."
            ),
            "action": "arrival",
            "target_id": None,
            "snapshot": snapshot.model_dump(mode="json"),
        }
    ]
    sequence = 0
    for step in steps:
        snapshot, sequence = move_to_target(service, snapshot, replay_id, sequence, step.target_id)
        sequence += 1
        snapshot = take_action(
            service,
            snapshot.run_id,
            replay_id,
            sequence,
            step.verb,
            step.target_id,
            step.content,
            step.public_statement,
        )
        frames.append(
            {
                "duration_ms": step.duration_ms,
                "title": step.title,
                "detail": step.detail,
                "action": step.verb.value,
                "target_id": step.target_id,
                "snapshot": snapshot.model_dump(mode="json"),
            }
        )

    election = snapshot.election
    if election is None or election.ending.key != expected_ending:
        actual = election.ending.key if election is not None else "no election"
        raise RuntimeError(
            f"Replay {replay_id!r} expected {expected_ending!r}, produced {actual!r}."
        )
    return {
        "schema_version": 1,
        "id": replay_id,
        "title": title,
        "subtitle": subtitle,
        "accent": accent,
        "recorded_runtime": "deterministic local fallback",
        "outcome": {
            "ending": election.ending.key,
            "headline": election.ending.title,
            "summary": election.ending.summary,
            "player_votes": election.player_votes,
            "rhea_votes": election.rhea_votes,
        },
        "frames": frames,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("apps/web/public/replays"),
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    bundles = (
        export_bundle(
            "trusted-win",
            1729,
            "The Trusted Candidate",
            "A kept promise and protected confidence carry the newcomer into office.",
            "gold",
            WIN_STEPS,
            "landslide",
        ),
        export_bundle(
            "remembered-loss",
            1729,
            "The Town Remembers",
            "A forged authority and betrayed confidence return on election night.",
            "rust",
            LOSS_STEPS,
            "exposed",
        ),
    )
    manifest = []
    for bundle in bundles:
        output_path = args.output_dir / f"{bundle['id']}.json"
        output_path.write_text(
            json.dumps(bundle, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        outcome = bundle["outcome"]
        assert isinstance(outcome, dict)
        manifest.append(
            {key: bundle[key] for key in ("id", "title", "subtitle", "accent", "recorded_runtime")}
            | {"outcome": outcome}
        )

    (args.output_dir / "manifest.json").write_text(
        json.dumps(
            {"schema_version": 1, "replays": manifest},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    for bundle in bundles:
        print(
            f"{bundle['id']}: {len(bundle['frames'])} frames, "
            f"{bundle['outcome']['player_votes']}–{bundle['outcome']['rhea_votes']}"
        )


if __name__ == "__main__":
    main()
