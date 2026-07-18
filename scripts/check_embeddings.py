from __future__ import annotations

import math
import os
from pathlib import Path

from hearsay_api.config import Settings
from hearsay_api.memory import EMBEDDING_DIMENSIONS, create_embedding_provider

REPO_ROOT = Path(__file__).resolve().parents[1]


def cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def main() -> int:
    os.environ.setdefault(
        "HF_HOME",
        str(REPO_ROOT / ".cache" / "huggingface"),
    )
    os.environ.setdefault(
        "TORCH_HOME",
        str(REPO_ROOT / ".cache" / "torch"),
    )
    settings = Settings()
    provider = create_embedding_provider(settings)

    anchor = provider.embed("Bram raised the price of Marta's shipment.")
    similar = provider.embed_query("Who made Marta's shipment more expensive?")
    unrelated = provider.embed_query("Where did rain fall near the chapel?")
    if anchor.fallback_used or similar.fallback_used or unrelated.fallback_used:
        reason = anchor.fallback_reason or similar.fallback_reason or unrelated.fallback_reason
        raise RuntimeError(
            "The configured local embedding model fell back "
            f"({reason or 'unknown provider error'})."
        )
    for result in (anchor, similar, unrelated):
        if len(result.vector) != EMBEDDING_DIMENSIONS:
            raise RuntimeError("The local model did not return 384 dimensions.")
        norm = math.sqrt(sum(value * value for value in result.vector))
        if abs(norm - 1.0) > 1e-5:
            raise RuntimeError("The local model did not return a normalized vector.")

    similar_score = cosine(anchor.vector, similar.vector)
    unrelated_score = cosine(anchor.vector, unrelated.vector)
    if similar_score <= unrelated_score:
        raise RuntimeError("The local model failed the semantic-similarity smoke check.")
    print(
        f"Local embeddings passed with '{anchor.model_id}': "
        f"similar={similar_score:.3f}, unrelated={unrelated_score:.3f}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
