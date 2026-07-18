from __future__ import annotations

from uuid import uuid4

from hearsay_api.conflicts import (
    CurrentBelief,
    IncomingClaim,
    classify_positions,
    resolve_conflict,
)
from hearsay_api.memory import DeterministicEmbeddingProvider


def make_claim(
    position: dict[str, object],
    *,
    source_trust: float = 0.8,
    evidence_weight: float = 0.4,
    corroboration: float = 0.5,
    recency: float = 1.0,
    bias_alignment: float = 0.0,
) -> IncomingClaim:
    embeddings = DeterministicEmbeddingProvider()
    narrative = f"The source claims {position}."
    return IncomingClaim(
        proposition_key="relic-culprit",
        subject_kind="mystery",
        subject_id="relic-theft",
        predicate="relic_stolen_by",
        holder_id="elias",
        narrative_text=narrative,
        normalized_position=position,
        source_kind="npc",
        source_id="marta",
        source_trust=source_trust,
        evidence_weight=evidence_weight,
        corroboration=corroboration,
        recency=recency,
        bias_alignment=bias_alignment,
        salience=1.0,
        embedding=embeddings.embed(narrative),
        embedding_model_id=embeddings.model_id,
    )


def make_current(
    position: dict[str, object] | None = None,
    confidence: float = 0.7,
) -> CurrentBelief:
    return CurrentBelief(
        belief_id=uuid4(),
        version=4,
        narrative_text="Elias currently suspects Talia.",
        normalized_position=position or {"suspect": "talia"},
        confidence=confidence,
        salience=1.0,
        contested=False,
    )


def test_classification_ignores_nonfactual_stance_metadata() -> None:
    classification = classify_positions(
        {"suspect": "bram", "stance": "accepted"},
        {"suspect": "bram", "stance": "rejected"},
    )

    assert classification == "supports"


def test_first_claim_is_accepted_with_source_provenance() -> None:
    decision = resolve_conflict(None, make_claim({"suspect": "talia"}))

    assert decision.outcome == "accepted"
    assert decision.create_version is True
    assert decision.contested is False


def test_supporting_claim_corroborates_and_increases_confidence() -> None:
    decision = resolve_conflict(
        make_current({"suspect": "bram"}),
        make_claim({"suspect": "bram"}),
    )

    assert decision.classification == "supports"
    assert decision.outcome == "corroborated"
    assert decision.confidence > 0.7


def test_close_conflicting_claim_marks_belief_contested_without_overwrite() -> None:
    current = make_current()
    decision = resolve_conflict(
        current,
        make_claim({"suspect": "bram"}),
    )

    assert decision.classification == "contradicts"
    assert decision.outcome == "contested"
    assert decision.contested is True
    assert decision.normalized_position == current.normalized_position
    assert decision.confidence < current.confidence


def test_weak_conflicting_claim_is_rejected_without_a_new_version() -> None:
    current = make_current()
    decision = resolve_conflict(
        current,
        make_claim(
            {"suspect": "bram"},
            source_trust=0.1,
            evidence_weight=0,
            corroboration=0,
            recency=0,
        ),
    )

    assert decision.outcome == "rejected"
    assert decision.create_version is False
    assert decision.normalized_position == current.normalized_position


def test_strong_conflicting_claim_can_replace_the_active_position() -> None:
    decision = resolve_conflict(
        make_current(),
        make_claim(
            {"suspect": "bram"},
            source_trust=1,
            evidence_weight=1,
            corroboration=1,
            recency=1,
            bias_alignment=1,
        ),
    )

    assert decision.outcome == "accepted"
    assert decision.normalized_position == {"suspect": "bram"}
    assert decision.contested is False


def test_uncomparable_claim_is_stored_as_needing_more_evidence() -> None:
    decision = resolve_conflict(
        make_current(),
        make_claim({"location": "chapel"}),
    )

    assert decision.classification == "uncertain"
    assert decision.outcome == "needs_evidence"
    assert decision.create_version is False
    assert decision.contested is True
