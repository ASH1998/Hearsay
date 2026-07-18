# Hearsay Project Instructions

## Document authority

- `docs/Hearsay_Game_Design_Document.md` is the authoritative source for the game itself: player experience, game design, content, presentation, scope, production priorities, and what the player sees, does, and feels.
- `docs/Hearsay_Hackathon_Blueprint_FINAL_v2.md` was prepared earlier. Use it as the authority for hackathon submission requirements, CockroachDB and AWS integration, database proofs, benchmarks, the MCP Historian, compliance, and other technical requirements.
- When the documents conflict on game or design decisions, follow the Game Design Document.
- When they conflict on database proof, sponsor integration, or submission compliance, follow the Hackathon Blueprint, while validating it against the current official hackathon rules.
- Do not reinterpret the Blueprint's older game concept as overriding the Game Design Document.

## Workspace boundary

- Keep all Hearsay source code, documentation, plans, generated assets, configuration, benchmarks, test artifacts, and other project files inside this repository: `F:\github\Hearsay`.
- Do not create or move Hearsay project artifacts outside this directory unless the user explicitly asks.
- Temporary tool files may use system-managed temporary storage only when unavoidable; copy any artifact that belongs to the project back into this repository and do not treat temporary storage as canonical.
- Preserve existing files and user changes. Do not delete, relocate, or destructively overwrite project material without explicit authorization.

