# Hearsay — Game Design Document
## The 2D Living Town: Design, Content, and Production Contract

> **Companion document.** The Hearsay Hackathon Blueprint (FINAL v2) remains the technical and submission contract: schema, transactions, benchmark, Director's Room, MCP Historian, compliance. THIS document is the game: what the player sees, does, and feels. Where the two conflict on game design, this document wins. Where they conflict on database proofs or submission requirements, the Blueprint wins.

> **Hackathon release-scope amendment — 2026-07-30.** The user approved a smaller playable release. `IMPLEMENTATION_PLAN.md` now governs the release roster, critical path, asset requirements, and milestone order. The larger town described below remains the long-term design and may continue to exist in the simulation, but 20 fully presented residents, a complete tileset, additional events, second favors, and bespoke animation for every character are not hackathon-release blockers. The core pillars, memory consequences, autonomous behavior, election payoff, and CockroachDB/AWS proof remain mandatory.

> **The one-line game:** You arrive a stranger in a living 2D town of twenty people who talk to each other about you — and in three days, they elect a mayor.

---

# 1. Design Pillars (test every decision against these)

1. **The town is alive and it shows.** Nothing happens off-screen that matters. **No event without a render** — if we can't afford to show it, it doesn't exist.
2. **Memory is the gameplay.** Favors, promises, rumors, grudges. The player wins or loses the election because of what the town remembers — and can find out exactly why.
3. **2D is a skin over the simulation.** Every truth (positions, schedules, conversations, rumors, promises, events) lives in CockroachDB. The renderer displays state; it never owns it. If the renderer dies, the game state survives — that is both an engineering rule and the sponsor story.
4. **Alive but auditable.** Randomness makes the town feel real; every random draw is logged as an event row. The world can always explain itself.
5. **Polish = juice, not fidelity.** Lighting, sound, motion, and reactivity — never custom models, lip sync, or cutscenes.

---

# 2. Player Fantasy and Core Loop

**Fantasy:** the newcomer who plays a whole town — earning trust, trading favors, planting whispers — and either gets elected mayor or gets run out on a rail.

```text
Arrive with nothing
   ↓
Meet townsfolk → learn needs, secrets, relationships
   ↓
Make promises · do favors · spread or bury information
   ↓
Time advances — NPCs live their day, talk to each other
   ↓
Watch your words travel (speech bubbles, changed treatment)
   ↓
Reputation shifts per-person; opportunities open and close
   ↓
Election day: every NPC votes from what they remember
   ↓
Win, lose — then ask the Historian WHY
```

**Session shape:** 3 in-game days ≈ 45–75 minutes of play. The first 10 minutes are designed hardest (see §8) — that's all a judge will play.

---

# 3. The Town: Greyhaven in 2D

## 3.1 One scene, twelve places

A single compact harbor-town scene. No loading, no interiors as separate scenes (interiors are camera-close exteriors or doorway vignettes).

Named waypoint locations (~15 nodes on a hand-authored graph):

| Location | Function | Who's usually here |
|---|---|---|
| The Gull & Anchor (inn) | Social hub, quest source, evening crowd | Marta; evenings: most of the town |
| Town square + well | Gossip nexus, announcements, ELECTION | Pip, ambient crowd |
| Market row (3 stalls) | Trade, favors, market-day event | Bram, shopkeepers |
| Chapel | Confessions, moral pressure | Father Orin |
| Docks + harbor | Shipments, fisher folk, storm drama | Nessa, dockhands |
| Constable's post | Law, threats, exposure risk | Elias |
| Midwife's cottage | Illness event, quiet favors | Talia |
| Guildhouse | Election machinery, endorsements | Guild leader |
| Back alley | Secrets, shady deals, night meetings | varies by night |
| Notice board | Public traits made visible (see §6.4) | — |
| Player's rented room | Save point fiction, day summary | — |
| The road out of town | Arrival cold open; exile ending | — |

## 3.2 Presentation stack

- **2D renderer** inside the existing Next.js app. One deploy, judges open a URL.
- **Assets:** original three-quarter/top-down pixel-art tiles, modular buildings, props, effects, portraits, and directional character sprites commissioned to the specification in `Hearsay_2D_Art_Asset_Commission_Brief.md`.
- **Movement:** waypoint graph with short sprite transitions, server-authoritative schedules. No physics engine or navmesh.
- **Camera:** readable fixed town view with restrained pan/follow where needed; conversations remain overlays.
- **Interaction:** click a reachable location or NPC → conversation overlay (portrait, name, relationship glyph, text, action chips). Move on the map, talk in UI.

## 3.3 Day cycle

Morning → afternoon → evening → night, driven by the action clock (see §7). Sky color, sun angle, warm windows at night, NPC schedules keyed to phase. The clock is always visible — it is the player's scarcest resource made ambient.

---

# 4. Characters: Twenty People, Two Tiers

The player must never be able to tell where the tier boundary is.

## 4.1 Tier 1 — Eight Principals (full agents)

Full memory (vector recall + relationships + promises + secrets + goals), premium-model dialogue, election weight, plot gravity.

| Character | Role | Drives | Secret | Election lever |
|---|---|---|---|---|
| Marta Vale | Innkeeper | Protect the inn's standing | Knows who pays for silence | The inn is where opinions form |
| Elias Ward | Constable | Order above all | Once jailed the wrong man | Endorsement = legitimacy |
| Father Orin | Priest | Souls and appearances | Holds a confession that matters | Moral blessing sways elders |
| Nessa Reed | Fisher | Keep the fleet fed | Smuggled once, regrets it | Speaks for the dock workers |
| Bram Coyle | Merchant | Profit, then pride | Price-fixing with outsiders | Money buys posters and favors |
| Talia Fen | Midwife | The vulnerable | Knows every family's troubles | Quiet influence across factions |
| Pip Marr | Town gossip | To be first with news | Invents details under pressure | Amplifier: reach × distortion |
| Rhea Kest | Guild leader | The guild's grip on the town | Rigged the last election | Controls the ballot process |

Each principal has: a voice card (diction, temper, taboo topics), 2 favors they can ask, 1 secret, 1 grudge or bond with another principal, and an election disposition function (what they weigh when voting).

## 4.2 Tier 2 — Twelve Ambients (light agents)

Real schedules, real walk cycles, real chatter — economy-model dialogue, shallow memory (last 3 interactions + the player's public traits + rumors that reached them). They receive and repeat rumors (they are the town's echo), give micro-favors (deliver, fetch, introduce), and vote in the election with simple weights.

Roster (names finalized in content pass): dockhand ×2, baker, fishwife, stall keeper ×2, elder ×2, farmhand, seamstress, tavern regular, courier kid.

**Design rule:** ambients never block the critical path. Every plot-critical interaction routes through a principal; ambients thicken the world and carry echoes.

## 4.3 What "agent" means here (both tiers)

Every NPC, on their turn: perceives (location, nearby NPCs, salient memories, active events) → decides (schedule step, or a social action: chat, share rumor, react, keep/break promise) → acts (movement + conversation + structured event writes). Tier 1 decides with the premium model and deep retrieval (relevance × importance × recency × relationship). Tier 2 decides with the economy model and a template-mix. All actions become rows; the Historian can replay anyone's day.
---

# 5. Player Verbs

In conversation (action chips + free text, LLM interprets into structured intents):

**Social:** ask about someone/something · offer help · make a promise (deadline attached) · request a favor · give a gift · apologize · flatter · insult · threaten quietly
**Information:** reveal a secret · spread a rumor · correct a rumor · conceal what you know · warn someone privately · recommend one NPC to another · introduce two NPCs
**Ambition:** ask for endorsement · recruit a supporter · negotiate a deal · call in a debt · declare candidacy (Day 2+) · give a square speech (once per day)

**World:** walk anywhere · observe conversations (approach a speech bubble to catch the drift — eavesdropping is a real verb) · read the notice board · sleep to end the day.

Every consequential verb writes a structured event: `{actor, verb, target, content_ref, timestamp, visibility}`. The LLM makes it feel like conversation; the event log makes it count.

---

# 6. The Social Simulation (game-facing rules)

## 6.1 Relationships are per-person, never global

Each NPC holds trust/affinity/fear/debt toward the player and toward each other. Marta can love you while Bram plots your ruin — and their friends drift toward their opinion at each gossip hop (attenuated by hop distance and the listener's own experience of you).

## 6.2 Promises (the sharpest memory mechanic)

`{promiser, promisee, content, deadline (in-game phase), fulfilled?, witnesses}`
- Visible in the player's ledger UI with countdown chips.
- KEPT: big trust with promisee + witnesses; a "reliable" echo may spread.
- BROKEN: trust crash + a rumor object is BORN automatically ("makes empty promises") with the promisee as origin — broken promises are self-propagating antagonists.
- NPCs also promise each other and the player; NPCs keep or break them per personality + circumstances (a storm can make Nessa miss a delivery — the event deck can create injustice, and the Historian can exonerate her).

## 6.3 Rumors (social objects with lineage)

`{origin, current_holders, hops[(speaker, listener, wording, tick)], privacy, valence, subject}`
- Wording drifts per hop by carrier personality (Pip exaggerates; Orin sanitizes; Bram weaponizes).
- The player can start them, deny them, out-shout them (square speech), or trace them (Historian, post-game).
- Rumors visibly travel: speech bubbles over NPC pairs show the actual current wording. Watching your own lie cross the square is the signature image of the game.

## 6.4 Public traits (the town's shorthand)

Six binary-ish traits derived from event patterns, not vibes: Reliable · Generous · Dangerous · Dishonest · Influential · Troublemaker. Displayed diegetically on the notice board as chalk gossip ("They say the newcomer pays their debts"). Traits set ambient NPCs' default greeting stance.

## 6.5 The election (the deterministic finale)

Election eve, every NPC computes a vote from weighted, logged inputs: direct relationship × promise record × rumors held (valence × credibility of chain) × faction pull (principals sway their circles) × own goals. The tally, each voter's top-3 decisive memories, and the margin are all rows. **The Historian's killer answer: "You lost by two votes. Here are the two people, and here is the rumor — and its origin — that turned each of them."**

Endings: Landslide · Narrow win · Narrow loss · Humiliation · Exposed (a lie unraveled publicly) · Run out of town (trait thresholds). Each is a staged square scene reusing crowd choreography.

---

# 7. Time, Ticks, and the Event Deck

## 7.1 Clock

3 in-game days × 4 phases (morning/afternoon/evening/night). Player actions consume phase segments; sleep skips to morning. ~12 meaningful actions/day → 45–75 min total.

## 7.2 Simulation ticks

- **Action tick** after every 2 player actions: 2–4 NPC social hops (weighted random: affinity + proximity + salience + noise), schedule steps, promise checks.
- **Drift tick** (wall-clock, for instances left overnight): 1–2 economy-model hops. Return next day: the story moved without you.

## 7.3 The Event Deck — with the No-Render-No-Event rule

Each morning draws 1–2 events. **An event ships only with all three layers: world render + behavior change + dialogue awareness.** Can't afford a layer → the event is cut from the deck, not shipped invisible.

| Event | World render | Behavior change | Dialogue awareness |
|---|---|---|---|
| **Storm** (never cut — the money shot) | Rain particles, dark sky, wet fog, thunder audio, warm windows | Docks empty; crowd packs the inn; deliveries fail (promise jeopardy!) | "Nessa's boats stayed in — she'll be foul-tempered today." |
| Market day | Extra stalls, crowd density ×2, market audio | Ambients cluster market row; Bram busy = harder to reach | "Half the coast is here today. Good day to be seen." |
| Public argument | Two principals shouting in the square, crowd ring forms | Their mutual trust drops; factions pick sides for a day | "Did you hear Bram and Nessa this morning? Over money, of course." |
| Festival night | Lanterns, square gathering, music (reuses election crowd system) | Everyone reachable in one place; secrets slip easier (trust +ε on chats) | "One night a year, even Elias dances." |
| Shipment arrives | Crates on the dock, dockhands haul, gulls | Fetch/deliver micro-favors spawn; Bram's mood improves | "That crate's had three owners before it touched the dock, mark me." |
| Someone falls ill | NPC absent from route; lamp lit at their cottage; Talia diverts | Their favors/pledges pause; visiting them = strong favor | "Talia's been at the baker's cottage since dawn." |

Every draw → event row (seed, effects, affected schedules). Aliveness that can testify.

---

# 8. The First Ten Minutes (judge-critical path)

Scripted-but-natural opening; everything after is systemic.

1. **0:00** Arrive on the road at dawn; town wakes around you (lights, first walkers). One control hint, no tutorial walls.
2. **1:00** Marta intercepts (scripted first encounter): the inn's shipment is stuck at the docks; Bram wants triple to release it. First choice with teeth: pay from your thin purse / persuade Bram / promise Marta you'll fix it by evening (promise UI appears).
3. **4:00** Walking to the docks you pass Pip mid-gossip — speech bubble visibly carrying news of *your arrival*, already slightly wrong. The game teaches its own theme.
4. **6:00** The Bram confrontation: threaten, flatter, deal, or lie. Whatever you do, by the next tick an NPC pair is visibly discussing it.
5. **9:00** Rhea Kest, watching from the guildhouse steps: "Elections in three days. The town could use a fresh name — or a useful fool." Ambition selected (mayor). Ledger and notice board light up.

Ten minutes in, a judge has: made a promise, seen a rumor about themselves travel, and been handed the election. All three pillars, felt.

---

# 9. Juice Checklist (the polish contract)

**Ship all of these (cheap, high-feel):** day/night lighting cycle · rain + thunder · footsteps on wood vs stone · ambient loops (gulls, market, tavern) · speech-bubble pop + drift animation · conversation camera ease-in · hover outline on interactables · relationship glyph pulse on change · promise chip countdown · vote-tally drumroll on election night · ending card art per ending.

**Banned (fidelity traps):** custom character models · lip sync/facial animation · cutscene camera systems · physics interactions · interiors as separate scenes · weather beyond rain · water simulation beyond a scrolling shader.

---

# 10. Randomness Policy

- Weighted-random: gossip pairing, event deck, wording drift, ambient chatter, NPC promise fidelity under pressure.
- Deterministic: consequence application, trait derivation, election math, ground-truth secrets, all thresholds.
- Every random draw is seeded and logged. Player-facing promise: *"The town surprises you; the Historian can still explain you."*

---

# 11. Tech Architecture (game layer)

```
Browser
  ├── 2D scene (town, characters, weather, bubbles)   ← renders state
  └── UI overlay (conversation, ledger, notice board, clock)
        │ WebSocket (state deltas) / REST (actions)
        ▼
Game server (Node or FastAPI, on EC2)
  ├── Deterministic rules: clock, consequences, traits, election
  ├── Tick engine: schedules, gossip pairing, event deck
  ├── Bedrock orchestration: premium (T1 + player) / economy (T2, drift)
  ├── Intent parser: free text → structured verbs (structured outputs)
  └── CockroachDB: events, memories, promises, rumors+hops,
        relationships, schedules, votes, event-deck draws, Ledger
              ▲ read-only MCP: the Historian (post-game + Director's Room)
```

Renderer-crash test (pillar 3, literal): refresh mid-storm → identical world state re-renders. Cheap to build, great 10-second video beat.

## 11.1 Cost envelope

Premium model: player↔T1 conversations + T1 decisions (~12 actions × 3 days + ticks ≈ manageable per session). Economy model: all T2, all drift, wording mutation. Embeddings local (per Blueprint). Per-session cap with in-fiction degradation ("Marta is swamped with the lunch crowd"). Telemetry row per call; $/session in the README.

---

# 12. Production Plan (AI-accelerated, honest buffers)

Claude Code + Codex compress code-writing ~10x. They do NOT compress: asset curation, feel-tuning, cluster benchmark runs, provisioning, human playtests, video recording. Plan accordingly.

**Days 1–3 — Proof spine.** Schema+migrations, event log, promises, rumor objects with hops, relationship math, vector recall, precise concurrency race, greybox 2D town (markers on waypoints), conversation overlay with intent parsing. *Gate: promise → break → rumor born → hop → treatment change, all in DB, visibly represented on the map.*
**Days 4–6 — Agents + election.** 8 principals (voice cards, secrets, favors), tick engine, election math + Historian "why I lost" query, Director's Room worker-kill audit wired. *Gate: full 3-day arc playable ugly, election explains itself.*
**Days 7–9 — Benchmark + Tier 2.** Three-arm benchmark run on real cluster, frozen to S3. 12 ambients (schedules, echo behavior, micro-favors). Drift ticks. Town Ledger. *Gate: all Blueprint proofs DONE. Nothing after this day may touch them.*
**Days 10–14 — The real town.** Professional 2D asset pass, 20 readable characters, day cycle, event deck ×4 events with all three layers (storm first), audio pass, juice checklist. *Gate: first-10-minutes flow feels like a game to someone who isn't you.*
**Days 15–17 — Playtest + tune.** 3 human playtesters minimum (not optional, not AI-simulatable). Fix comprehension, pacing, dead spots. Cost telemetry check.
**Days 18–20 — Ship.** Video per Blueprint storyboard + 30s of storm/vibes, README, replay bundles, judge-flow rehearsal ×3 from clean browser. Submit early.
**Buffer: ~10 days** before Aug 18 — because asset integration and game feel always eat more time than planned.

## 12.1 Scope-cut order (game side)

Event deck 4→2 (storm survives anything) → ambients 12→8 → festival ending scenes → notice-board diegesis (plain UI panel fallback) → decorative map motion → audio variety. **Never cut:** first-10-minutes flow, storm, speech-bubble rumor travel, election explanation, anything in the Blueprint's never-cut list.

---

# 13. Definition of Done

- [ ] A stranger plays 45+ minutes without instruction and can say what the game is about
- [ ] Every shipped event has all three visibility layers
- [ ] A rumor the player started is visibly overheard crossing the square, mutated
- [ ] A broken promise measurably changes an NPC's treatment AND spreads
- [ ] Election ending names the decisive memories; Historian answers "why did I lose?"
- [ ] 20 characters on screen across a day; no player-visible tier seam
- [ ] Refresh mid-storm restores identical world state
- [ ] All Blueprint v2 proofs (race, worker-kill audit, benchmark, MCP Historian, Ledger) intact and demoed
- [ ] First 10 minutes rehearsed against a stopwatch
- [ ] Someone laughed, winced, or swore at Pip during a playtest

*The closing rule: when in doubt, make the town show it — or cut it.*
