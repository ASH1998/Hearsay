from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

ConflictClassification = Literal["supports", "contradicts", "uncertain"]
ConflictOutcome = Literal[
    "accepted",
    "corroborated",
    "contested",
    "rejected",
    "needs_evidence",
]

NON_FACTUAL_POSITION_KEYS = {"public", "stance"}


@dataclass(frozen=True)
class IncomingClaim:
    proposition_key: str
    subject_kind: str
    subject_id: str | None
    predicate: str
    holder_id: str
    narrative_text: str
    normalized_position: dict[str, object]
    source_kind: str
    source_id: str | None
    source_trust: float
    evidence_weight: float
    corroboration: float
    recency: float
    bias_alignment: float
    salience: float
    embedding: tuple[float, ...]
    embedding_model_id: str


@dataclass(frozen=True)
class CurrentBelief:
    belief_id: UUID
    version: int
    narrative_text: str
    normalized_position: dict[str, object]
    confidence: float
    salience: float
    contested: bool


@dataclass(frozen=True)
class ConflictDecision:
    classification: ConflictClassification
    outcome: ConflictOutcome
    create_version: bool
    contested: bool
    narrative_text: str
    normalized_position: dict[str, object]
    confidence: float
    rationale: str
    incoming_strength: float


@dataclass(frozen=True)
class ClaimResolution:
    input_id: UUID
    belief_id: UUID
    belief_version: int
    classification: ConflictClassification
    outcome: ConflictOutcome
    contested: bool
    observed_version: int | None
    evaluated_against_version: int | None
    transaction_attempts: int
    recalculated_after_conflict: bool


def classify_positions(
    current: dict[str, object],
    incoming: dict[str, object],
) -> ConflictClassification:
    shared_keys = (set(current) & set(incoming)) - NON_FACTUAL_POSITION_KEYS
    if not shared_keys:
        return "uncertain"
    if any(current[key] != incoming[key] for key in shared_keys):
        return "contradicts"
    return "supports"


def score_incoming_claim(claim: IncomingClaim) -> float:
    score = (
        claim.source_trust * 0.45
        + claim.evidence_weight * 0.25
        + claim.corroboration * 0.15
        + claim.recency * 0.10
        + claim.bias_alignment * 0.05
    )
    return min(max(score, 0.0), 1.0)


def resolve_conflict(
    current: CurrentBelief | None,
    incoming: IncomingClaim,
) -> ConflictDecision:
    strength = score_incoming_claim(incoming)
    if current is None:
        return ConflictDecision(
            classification="supports",
            outcome="accepted",
            create_version=True,
            contested=False,
            narrative_text=incoming.narrative_text,
            normalized_position=incoming.normalized_position,
            confidence=max(strength, 0.35),
            rationale="No prior belief existed, so the sourced claim became active.",
            incoming_strength=strength,
        )

    classification = classify_positions(
        current.normalized_position,
        incoming.normalized_position,
    )
    if classification == "supports":
        confidence = min(
            1.0,
            current.confidence + (1.0 - current.confidence) * max(strength, 0.1) * 0.25,
        )
        return ConflictDecision(
            classification=classification,
            outcome="corroborated",
            create_version=True,
            contested=False,
            narrative_text=incoming.narrative_text,
            normalized_position=incoming.normalized_position,
            confidence=confidence,
            rationale="The incoming semantic position corroborated the active belief.",
            incoming_strength=strength,
        )

    if classification == "uncertain":
        return ConflictDecision(
            classification=classification,
            outcome="needs_evidence",
            create_version=False,
            contested=True,
            narrative_text=current.narrative_text,
            normalized_position=current.normalized_position,
            confidence=current.confidence,
            rationale="The claims shared no factual semantic field to compare.",
            incoming_strength=strength,
        )

    margin = strength - current.confidence
    if margin >= 0.15:
        return ConflictDecision(
            classification=classification,
            outcome="accepted",
            create_version=True,
            contested=False,
            narrative_text=incoming.narrative_text,
            normalized_position=incoming.normalized_position,
            confidence=max(strength, 0.35),
            rationale=(
                "The contradictory claim exceeded the active belief by the "
                "deterministic acceptance margin."
            ),
            incoming_strength=strength,
        )
    if margin <= -0.25:
        return ConflictDecision(
            classification=classification,
            outcome="rejected",
            create_version=False,
            contested=current.contested,
            narrative_text=current.narrative_text,
            normalized_position=current.normalized_position,
            confidence=current.confidence,
            rationale=(
                "The contradictory claim fell below the active belief by the "
                "deterministic rejection margin."
            ),
            incoming_strength=strength,
        )

    return ConflictDecision(
        classification=classification,
        outcome="contested",
        create_version=True,
        contested=True,
        narrative_text=current.narrative_text,
        normalized_position=current.normalized_position,
        confidence=max(0.1, current.confidence - 0.12),
        rationale=(
            "Neither position cleared the acceptance or rejection margin; "
            "the current position remains active at reduced confidence."
        ),
        incoming_strength=strength,
    )
