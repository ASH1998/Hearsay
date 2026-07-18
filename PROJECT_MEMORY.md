# Hearsay Project Memory

## Standing decisions

- The Game Design Document is newer and preferred for all game-design decisions:
  - `docs/Hearsay_Game_Design_Document.md`
- The earlier v2 Hackathon Blueprint remains the technical and submission contract:
  - `docs/Hearsay_Hackathon_Blueprint_FINAL_v2.md`
- Therefore:
  - Game, content, player experience, presentation, and production scope → Game Design Document.
  - CockroachDB/AWS integration, database correctness proofs, benchmark, MCP Historian, and hackathon compliance → Hackathon Blueprint plus the current official rules.
- All project files and artifacts must remain under `F:\github\Hearsay`.

## Project direction

Hearsay is a living 3D social-memory game set in Greyhaven. The player influences a town of NPCs through conversations, promises, favors, rumors, and reputation, culminating in a mayoral election. CockroachDB is the canonical persistent memory and simulation-state layer; the technical proof must remain visible, real, and auditable.

