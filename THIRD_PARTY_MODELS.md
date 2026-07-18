# Third-party models

## BAAI/bge-small-en-v1.5

- Purpose: local 384-dimensional embeddings for NPC memories and recall queries.
- Publisher: Beijing Academy of Artificial Intelligence (BAAI).
- Source: <https://huggingface.co/BAAI/bge-small-en-v1.5>
- License: MIT, as declared by the upstream model card.
- Runtime: `sentence-transformers` 5.6.x on the application host, CPU by
  default.
- Reproducibility: the exact model identifier is configured by
  `HEARSAY_EMBEDDING_MODEL`; downloaded weights are cached under the ignored
  repository path `.cache/huggingface`.

Stored memories use normalized passage embeddings. Recall queries use the
upstream English retrieval instruction before normalization. Every persisted
belief version records the model identifier that produced its vector. If the
model cannot load or returns an invalid vector, Hearsay logs a sanitized reason
and uses the explicitly identified deterministic hash fallback.
