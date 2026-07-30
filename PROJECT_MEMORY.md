# Hearsay Project Memory

## Standing decisions

- The Game Design Document is newer and preferred for all game-design decisions:
  - `docs/Hearsay_Game_Design_Document.md`
- The earlier v2 Hackathon Blueprint remains the technical and submission contract:
  - `docs/Hearsay_Hackathon_Blueprint_FINAL_v2.md`
- Therefore:
  - Game, content, player experience, presentation, and production scope → Game Design Document.
  - CockroachDB/AWS integration, database correctness proofs, benchmark, MCP Historian, and hackathon compliance → Hackathon Blueprint plus the current official rules.
- User-approved hackathon release reduction (2026-07-30):
  - `docs/IMPLEMENTATION_PLAN.md` governs the narrowed release roster, critical
    path, asset requirements, and milestone order.
  - Five featured agents: Marta, Bram, Pip, Talia, and Rhea.
  - Existing larger-town systems are preserved but do not block release.
  - Bedrock Claude, S3 replay evidence, AWS deployment, CockroachDB vector
    recall, and a real Managed MCP Historian are release-critical.
- All project files and artifacts must remain under `F:\github\Hearsay`.

## Project direction

Hearsay is a living 2D social-memory game set in Greyhaven. The player influences a compact featured cast through conversations, promises, favors, rumors, and reputation, culminating in a mayoral election. CockroachDB is the canonical persistent memory and simulation-state layer; the technical proof must remain visible, real, and auditable.

The submission's north star is long-term NPC memory. A memory must live outside
the model context, survive browser/API/application restarts, remain
character-specific, be semantically retrieved later, alter an autonomous action
or vote, preserve immutable revision and transmission history, and be
independently traceable through the Managed MCP Historian. Bedrock is stateless
inference and S3 is replay evidence; neither is authoritative memory.

Local inference defaults to the deterministic fallback. Do not invoke a paid
Bedrock or Modal model during development unless the user explicitly approves
that proof call. The production provider is lazy, and starting the API alone
must not initialize a Bedrock client.
