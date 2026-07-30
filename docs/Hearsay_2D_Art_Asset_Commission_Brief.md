# Hearsay — 2D Art and Asset Commission Brief

**Project:** Hearsay
**World:** Greyhaven
**Document purpose:** Art-direction, quotation, production, and delivery brief for a professional 2D game artist
**Target presentation:** Original three-quarter/top-down pixel art with the readability and modularity associated with polished 64 px-grid strategy and town-simulation games
**Reference:** [Tiny Swords by Pixel Frog](https://pixelfrog-assets.itch.io/tiny-swords) for scale, readability, modular construction, and animation clarity only. Do not copy its designs, silhouettes, buildings, palette, or individual assets.

---

## 1. Project in one paragraph

Hearsay is a narrative social-simulation game set in Greyhaven, a compact harbor town of twenty residents. The player arrives as a stranger with three days to earn trust, trade favors, make promises, spread or correct rumors, and stand for mayor. The town remembers what the player says. Residents move through daily schedules, speak to one another, visibly pass rumors, react to public events, and vote based on their memories. There is no combat and no magic. The visual fantasy is a lively storybook town whose warmth makes its grudges, secrets, and political tension feel personal.

The 2D pivot changes the renderer, not the game. The important visual promise remains: if something matters in the simulation, the player should be able to see it happen in the world.

---

## 2. Visual direction

### 2.1 Desired impression

- Charming at first glance; politically tense on closer inspection.
- Bold, readable silhouettes at gameplay scale.
- Chunky shapes, restrained detail, deliberate pixel clusters, and expressive animation.
- A grounded late-medieval/early-renaissance harbor town rather than heroic high fantasy.
- Weathered timber, pale stone, faded cloth, damp cobbles, salt-stained docks, and warm windows.
- Characters should feel like specific working people, not interchangeable fantasy classes.
- The town should remain legible when twenty characters, speech bubbles, rain, and UI are present.

### 2.2 Originality requirement

Tiny Swords is a production reference, not a style-copy request. Hearsay must have its own:

- Character proportions and face language.
- Greyhaven architecture.
- Coastal palette.
- Costume shapes.
- Icons, UI ornament, and typography treatment.
- Props and event imagery.

The artist should avoid recognizable copies of Tiny Swords units, buildings, ribbons, buttons, terrain arrangements, or palette combinations.

### 2.3 Shape language

- **People:** Large heads and hands, compact torsos, short readable limbs, clear occupational props.
- **Friendly/civic shapes:** Rounded rooflines, broad doorways, circles, worn soft corners.
- **Institutional/power shapes:** Tall rectangles, steep roofs, iron braces, strong verticals.
- **Harbor shapes:** Diagonals, rope curves, uneven posts, wind-pulled cloth.
- **Rumor imagery:** Airy curls, tails, linked dots, repeated quotation shapes.
- **Promise imagery:** Knots, seals, tied ribbons, clock wedges.
- **Election imagery:** Bells, ballot slips, tally marks, wax seals, public notices.

### 2.4 Palette

The overall world palette should be coastal and slightly desaturated so character accents and interaction effects remain visible.

Suggested world families:

| Use | Direction |
|---|---|
| Sea and wet shadow | Slate blue, deep blue-green, storm navy |
| Grass and scrub | Muted moss, olive, dry sage |
| Stone and roads | Warm grey, mushroom, sand, faded mauve shadow |
| Timber | Umber, smoked oak, salt-grey wood |
| Plaster | Aged cream, parchment, pale clay |
| Roofs | Weathered red-brown, charcoal, muted teal slate |
| Warm light | Honey, amber, candle cream |
| Civic warning | Oxide red |
| Information/rumor | Pale cyan or lavender-white |

Avoid a uniformly brown medieval scene. Every district should have a recognizable color identity without becoming saturated or toy-like.

### 2.5 Pixel treatment

- Hard-edged pixel art with no smoothing or vector-like anti-aliasing.
- Consistent outline strategy across characters and environment.
- Prefer colored outlines over pure black except at the deepest contact points.
- One consistent top-left light direction for world assets.
- Baked ambient/contact shadows should use one shared opacity and hue.
- Materials must be distinguishable through clusters and value, not noisy texture.
- No sub-pixel animation.

---

## 3. Camera, grid, and technical scale

These specifications are intended to make the first delivery immediately usable in a browser renderer. The artist may propose a better equivalent before production begins.

| Item | Specification |
|---|---|
| Projection | Three-quarter/top-down orthographic |
| Base terrain grid | 64 × 64 px |
| Source animation rate | 10 fps / 100 ms per frame |
| Character frame canvas | 128 × 128 px, transparent |
| Typical standing height | Approximately 52–64 px from foot to top of head |
| Character anchor | Bottom-center foot position, identical across every frame |
| Source directions | South/front, north/back, east/side; west may be engine-mirrored |
| World scale | One character occupies approximately one 64 px navigation cell |
| Gameplay viewport target | 1280 × 720 logical canvas, integer-scaled where possible |
| Whole town target | Approximately 36 × 24 terrain cells, scrollable |
| File color mode | RGBA PNG, sRGB |
| Editable source | Aseprite preferred; layered PSD accepted |

If east-facing sprites are mirrored for west movement, costumes and props must not contain unreadable text or permanently one-sided objects. Important asymmetry should be supplied in both side directions.

---

## 4. Character animation contract

Movement is a core requirement. A character is not considered delivered if only a standing sprite exists.

### 4.1 Standard animation set for all 21 characters

The cast consists of twenty residents plus the player.

| Animation | Frames per direction | Directions | Notes |
|---|---:|---:|---|
| Idle | 4 | 3 source directions | Breathing, weight shift, small occupational personality |
| Walk | 6 | 3 source directions | Clear foot contact and passing poses; no sliding |
| Talk | 6 | 3 source directions | Conversational hand/shoulder movement, not lip sync |
| Listen | 4 | 3 source directions | Small responsive loop; visually distinct from idle |

### 4.2 Principal-only reaction animations

The eight principal NPCs also require:

- Agree/nod: 4 frames.
- Refuse/head shake: 4 frames.
- Surprise: 4–6 frames.
- Anger/argument gesture: 6 frames.
- Approval/relief: 4–6 frames.
- Dejection: 4–6 frames.

These reactions may be front-facing only if budget requires, but must preserve the same foot anchor as gameplay sprites.

### 4.3 Shared crowd animations

Create reusable body-language animations that can be recolored or lightly edited across the ambient cast:

- Cheer/applaud.
- Murmur/gossip.
- Point/react.
- Sit on stool or bench.
- Carry crate.
- Carry basket.
- Pull or handle rope.
- Knock on a door.

### 4.4 Animation quality bar

- Feet make visible contact with the ground.
- Head, torso, and limbs move as one coherent body.
- No disconnected parts, floating accessories, or changing body proportions.
- Clothing hems and hair react subtly but do not flicker.
- The walk cycle reads correctly at 1× size without interpolation.
- Idle animations should not synchronize when several NPCs stand together.

---

## 5. Principal NPC character sheets

Each principal needs:

1. A gameplay sprite set.
2. A dialogue portrait from chest or waist up.
3. Six portrait expressions: neutral, warm, suspicious, angry, worried, pleased.
4. A small 32 × 32 px relationship icon or portrait token.
5. A palette strip and turnaround sheet.

The listed colors are existing character identifiers and should be preserved as recognizable costume accents, not necessarily used as the dominant full outfit.

### 5.1 Marta Vale — Innkeeper

**Identifier color:** Rust orange `#D86F45`
**Age read:** Late 40s to early 50s
**Build and silhouette:** Broad-shouldered, grounded, sleeves rolled, stable stance. She should look capable of carrying a keg and ending an argument without raising her voice.
**Face and hair:** Weather-warmed face, strong brows, auburn hair going grey at the temples, tied into a practical bun.
**Costume:** Cream work blouse, rust waistcoat or bodice, dark long skirt or trousers, heavy apron with patched pockets, sturdy boots.
**Props:** Ring of keys, folded rag, ledger pencil, optional tankard or serving tray.
**Personality in motion:** Efficient and economical. Her talk gesture is an open palm becoming a pointed instruction. Her angry pose is controlled rather than explosive.
**Narrative read:** Protective of the Gull & Anchor because the inn is where Greyhaven forms its opinions. She hears everything and knows who pays for silence.
**Do not:** Make her a cheerful generic tavern hostess, barmaid, or fantasy pin-up.

### 5.2 Elias Ward — Constable

**Identifier color:** Constable blue `#496E8F`
**Age read:** Early to mid-40s
**Build and silhouette:** Tall, square, upright, slightly rigid. A long coat gives him a strong vertical shape.
**Face and hair:** Close-cropped dark hair with grey at the temples; tired eyes; clean-shaven or very short stubble.
**Costume:** Faded blue civic coat, leather belt, practical trousers, polished but old boots, simple metal town badge. No ornate armor.
**Props:** Ledger book, whistle, baton, key ring. A sheathed utility sword may exist but should not dominate his design.
**Personality in motion:** Precise, guarded, scans the room before speaking. Hands often clasped behind his back.
**Narrative read:** Believes order matters more than popularity and carries guilt over jailing the wrong person.
**Do not:** Present him as a heroic knight or heavily armed soldier.

### 5.3 Father Orin — Priest

**Identifier color:** Ash violet `#806F8E`
**Age read:** Late 50s to mid-60s
**Build and silhouette:** Tall and narrow, slightly stooped from listening rather than frailty. Robes form a calm tapered shape.
**Face and hair:** Long thoughtful face, greying hair around a receding crown, neatly kept short beard optional.
**Costume:** Ash-violet robe, aged cream stole, dark walking shoes, patched outer cloak for rain. The faith is local and civic; avoid real-world religious symbols.
**Props:** Small book, plain wooden bead cord, folded confession notes, chapel key.
**Personality in motion:** Measured hands, slow nods, deliberate pauses. Anger appears as sudden stillness.
**Narrative read:** Trusted moral authority who protects confidences but cares deeply about appearances and holds a confession that could affect the election.
**Do not:** Make him a magical cleric, bishop, cultist, or caricature.

### 5.4 Nessa Reed — Fisher and fleet voice

**Identifier color:** Harbor teal `#2B8C86`
**Age read:** Mid-30s to early 40s
**Build and silhouette:** Wiry, strong forearms, wide sea stance. Wind-blown scarf or short oilskin creates an angular silhouette.
**Face and hair:** Salt-tanned skin, sharp eyes, dark hair in a rough braid or under a knit cap.
**Costume:** Teal oilskin vest or short coat, rolled trousers, striped undershirt, rope belt, tall wet-weather boots.
**Props:** Coiled rope, fish knife in a work sheath, harbor log, small net float.
**Personality in motion:** Blunt pointing, wide braced gestures, quick dismissive shrug. Walk has purposeful forward lean.
**Narrative read:** Protects crews and food supply. Once smuggled cargo and regrets it. She speaks for the dock workers against merchants who price risk from dry land.
**Do not:** Make her a pirate, sailor adventurer, or mermaid-coded fantasy character.

### 5.5 Bram Coyle — Merchant

**Identifier color:** Ledger gold `#B68B37`
**Age read:** Early to late 40s
**Build and silhouette:** Well-fed, composed, slightly forward belly, immaculate coat, one hand often protecting a ledger.
**Face and hair:** Groomed dark hair, trimmed beard or moustache, calculating eyes, practiced customer smile.
**Costume:** Mustard-gold doublet or merchant coat, deep brown trousers, polished shoes, patterned but tasteful waistcoat, one visible ring.
**Props:** Brass scales, coin purse, contract roll, ledger, quill.
**Personality in motion:** Counts on fingers, weighs options in his palms, straightens cuffs when challenged. Anger is a snapped ledger or sharp pointed quill.
**Narrative read:** Profit first, pride immediately after. He fixes prices with outsiders and understands that money buys favors, posters, and witnesses.
**Do not:** Make him a grotesque miser or a harmless comic shopkeeper.

### 5.6 Talia Fen — Midwife

**Identifier color:** Herb green `#6C9B63`
**Age read:** Early to late 50s
**Build and silhouette:** Medium height, strong hands, layered shawl, broad satchel. Her shape should feel sheltering.
**Face and hair:** Kind but unsentimental face; silver-streaked dark hair in two wrapped braids or a low coil.
**Costume:** Herb-green shawl, practical linen dress or tunic, rolled sleeves, weathered apron, soft boots.
**Props:** Medical satchel, herb bundle, small bottle, folded cloth. Avoid modern medical symbols.
**Personality in motion:** Direct eye contact, reassuring hand, brisk walking animation. Anger is protective and immediate.
**Narrative read:** Knows every family's trouble and protects the vulnerable. Her influence is quiet, private, and spread across every faction.
**Do not:** Make her mystical, witch-coded, or an ornamental healer.

### 5.7 Pip Marr — Town gossip

**Identifier color:** Story pink `#BF5979`
**Age read:** Mid-20s to early 30s
**Gender presentation:** Intentionally androgynous
**Build and silhouette:** Lean, quick, slightly oversized scarf, messenger bag, restless hands.
**Face and hair:** Bright observant eyes, expressive eyebrows, short uneven hair that suggests constant motion.
**Costume:** Mauve-pink scarf, cropped jacket, slim practical trousers, worn fast boots, layers suited to moving between districts.
**Props:** Tiny notebook, charcoal stick, folded scraps, messenger satchel.
**Personality in motion:** Leans in, cups a hand near the mouth, pivots immediately to find the next listener. Talk animation should be the most animated in the cast.
**Narrative read:** Needs to be first with news and invents detail when truth is too slow. Pip is funny, dangerous, charming, and never merely malicious.
**Do not:** Use giant ears, rat imagery, a jester costume, or make Pip visually untrustworthy at first glance.

### 5.8 Rhea Kest — Guild leader and incumbent power

**Identifier color:** Oxblood `#8A4A42`
**Age read:** Late 40s to mid-50s
**Build and silhouette:** Tall, controlled, sharply tailored shoulders, long formal coat. She occupies space without broad gestures.
**Face and hair:** Angular mature face, dark hair in a severe high coil with one silver streak, steady unsmiling eyes.
**Costume:** Oxblood guild coat, charcoal dress or trousers, fine gloves, modest gold chain of office, seal at the waist.
**Props:** Guild seal, ballot-box key, poll book, folded compact.
**Personality in motion:** Minimal movement, small chin turns, measured hand offered like a contract. Anger should be a loss of stillness, not shouting.
**Narrative read:** The guild's grip made human. She rigged the prior election and controls the present ballot process, but she should look plausible as the experienced leader many residents still prefer.
**Do not:** Make her an obvious evil queen, sorceress, or decadent aristocrat.

---

## 6. Ambient resident character sheets

Ambient residents require the standard gameplay animation set, a neutral dialogue bust, two additional portrait expressions, and a 32 × 32 px token. Their silhouettes must remain unique even when shown as solid black shapes.

### 6.1 Jonas Pike — Dockhand

**Accent:** Blue-grey `#4F7F8F`
Large, heavy-lifting build; shaved head or close curls; sleeveless work vest, rope belt, thick gloves, broad boots. Carries a cargo hook or rope coil. Blunt, observant, and physically economical.

### 6.2 Mae Dorr — Dockhand

**Accent:** Slate blue `#52758C`
Compact, muscular woman; red-brown head wrap; short jacket, rolled sleeves, reinforced trousers. Carries a mallet or manifest board. Practical and more openly helpful than Jonas.

### 6.3 Oswin Bell — Baker

**Accent:** Bread brown `#A87B4F`
Round, flour-dusted silhouette; soft cap, rolled apron, warm face, oven mitt or bread paddle. Often carries a loaf basket. His illness event needs a pale/tired portrait variant and blanket or closed-door indicator.

### 6.4 Del Sayer — Fishwife

**Accent:** Sea green `#3B8B81`
Middle-aged to older woman, strong arms, layered waterproof apron, tied kerchief, fish basket or small scale. Wry face and wide planted stance. Should look like a respected harbor trader, not a comic scold.

### 6.5 Hettie Voss — Stall keeper

**Accent:** Mustard `#B28645`
Neat compact silhouette; high collar, tidy apron, round spectacles optional. Carries an abacus, inventory slate, or folded cloth. Skeptical, organized, and aligned with predictable guild trade.

### 6.6 Cal Moss — Stall keeper

**Accent:** Walnut `#9C7141`
Lanky man with rolled sleeves, soft cap, measuring cord, and portable balance scale. More casual than Hettie; a customer-watching posture and quick shrug.

### 6.7 Edda Grey — Town elder

**Accent:** Grey violet `#7A7088`
Elderly woman with upright posture, silver hair under a simple hood, long layered coat, carved walking stick. Sharp eyes and deliberate gestures. Age should read as authority, not helplessness.

### 6.8 Will Harker — Town elder

**Accent:** Hearth grey `#796B5D`
Elderly man, broad but softened with age, flat cap, old wool coat, heavy cane. Slightly stooped, skeptical expression, measured walk. His clothing should look carefully repaired.

### 6.9 Fen Lark — Farmhand

**Accent:** Field green `#718B50`
Young adult with sun-browned skin, loose work shirt, patched knees, straw or felt field hat. Carries a small produce crate or hand fork. Open stance, strong walk, little patience for speeches.

### 6.10 Lina Thread — Seamstress

**Accent:** Mauve `#9F6682`
Precise slim silhouette; pinned-up hair, fitted work jacket, measuring tape, thread spool, shears in safe belt sheath. Observes clothing and body language. Small exact gestures rather than broad motions.

### 6.11 Tob Rill — Tavern regular

**Accent:** Russet `#8A5E43`
Weathered man in his 50s, rumpled coat, old knit cap, mug or dice cup. A former wrongful prisoner, not a drunk joke. His guarded slouch should straighten noticeably when his name is cleared.

### 6.12 Kit Wren — Courier

**Accent:** Coral `#C07455`
Older teenager or young adult; smallest and fastest adult silhouette; short capelet, oversized satchel, quick boots, wind-reddened cheeks. Carries sealed letters and receipts. Walk/run animation should feel urgent without becoming a cartoon sprint.

---

## 7. Player character — The Newcomer

The player should read as an outsider without looking richer, more heroic, or more important than Greyhaven's residents.

### Required base design

- Androgynous young-to-middle-aged traveler.
- Neutral charcoal, cream, and weathered brown costume.
- Short travel cloak, satchel, plain boots, simple belt.
- One customizable scarf or sash color used as the player's visual identifier.
- No weapon displayed.
- Slightly cleaner clothing at arrival; optional damp/muddy overlay during storm.
- Full standard animation set plus interact, hand-over-item, read-board, and sleep/day-transition poses.

### Optional customization pack

Quote separately for:

- Four skin tones.
- Four hair shapes.
- Three hair colors.
- Six scarf colors.
- Two body silhouettes.

Modular pieces must use identical anchors and cannot increase collision or navigation footprint.

---

## 8. Greyhaven world description

Greyhaven is a small, weather-beaten harbor town that grew around a protected cove. It is prosperous enough to have a guildhouse and election, but small enough that everyone recognizes every coat crossing the square. The sea is always near: ropes dry on walls, gulls perch on roof ridges, salt pales the timber, and damp stones reflect window light.

The town is not ruined or filthy. It is maintained by working people with limited money. Repairs are visible, objects have owners, and public spaces feel used. Buildings should be slightly irregular and handmade, but the navigation routes must remain immediately readable.

### 8.1 District layout

North is the top of the map.

```text
                         NORTH / OPEN WATER

       Docks & harbor             Chapel
             │                       │
        Guildhouse ───── Square ─ Constable's post
             │           │   │       │
          Back alley   Board Market row
             │           │           │
       Gull & Anchor ─────┘     Midwife's cottage
             │                       │
             └──────── Road into town┘

                         SOUTH / COUNTRYSIDE
```

This is a navigation diagram, not a final composition. The artist should produce one color map mockup before individual building production.

### 8.2 District color identities

| District | Visual identity |
|---|---|
| Harbor and docks | Slate, teal, rope tan, wet black timber |
| Guild quarter | Oxblood banners, dark oak, controlled symmetry |
| Town square | Warm cobble, pale plaster, civic red accents |
| Market row | Mustard awnings, produce color, busy diagonals |
| Chapel rise | Ash violet, pale stone, quiet grass and candles |
| Constable's post | Faded blue, iron, clipped practical shapes |
| Midwife's lane | Herb green, cream plaster, garden clutter |
| Inn and alley | Rust, amber windows, smoked timber, shadowed passages |
| Road and outskirts | Moss, dirt, field stone, wind-bent trees |

---

## 9. Terrain and tile-set inventory

All terrain must tile seamlessly on the 64 px grid. Supply edge, inner-corner, outer-corner, and transition pieces.

### 9.1 Ground

- Short coastal grass: 6 variation tiles.
- Worn grass: 4 variation tiles.
- Dirt road center and edges.
- Mud road and puddle overlays.
- Town cobbles: 8 variation tiles.
- Fine guild paving: 4 variation tiles.
- Chapel stone path.
- Dock planks: horizontal, vertical, damaged, repaired.
- Sand, shingle, and seaweed shore.
- Building foundation and doorstep tiles.
- Dark alley ground overlay.
- Small garden soil plots.

### 9.2 Water and shoreline

- Animated deep water loop.
- Animated shallow water loop.
- Four-direction coast edges and all corner combinations.
- Foam and wave-break overlays.
- Wet reflection/sheen overlay for storm.
- Harbor shadow layer.
- Pier-post water ripples.

### 9.3 Elevation and boundaries

- Low stone wall set.
- Timber fence set with gates.
- Hedge and scrub set.
- Small retaining wall.
- Short grass bank or cliff edge.
- Stairs in all required facing directions.
- Invisible-navigation-compatible decorative edges; no ambiguous walkable areas.

---

## 10. Landmark building inventory

Buildings should be delivered in separated layers where useful: base, roof, door/sign, shadow, night-window glow, and event overlay. Roofs must not hide characters on primary navigation paths.

### 10.1 The Gull & Anchor

**Purpose:** Inn, social hub, first quest, evening and storm crowd.
**Footprint:** Approximately 5 × 4 tiles.
**Design:** Broad welcoming timber-and-plaster inn with an anchor-and-gull hanging sign, rust awning, side stack of barrels, visible front stoop, and a warm public-facing façade.
**Variants:** Day, warm evening windows, storm-bright windows, crowded-door overlay.
**Props:** Benches, casks, mugs, delivery crates, handcart, notice chalkboard, rain barrel.

### 10.2 Town square and well

**Purpose:** Gossip nexus, public argument, speeches, election finale.
**Footprint:** Approximately 9 × 8 open tiles.
**Design:** Broad cobbled space with a low circular well slightly off-center so crowds can form. Include permanent room for the notice board and temporary room for a stage or ballot table.
**Variants:** Ordinary day, argument crowd markers, festival decorations, election staging.
**Props:** Well, benches, hitching post, drain grates, civic bell or bell post, bunting anchors.

### 10.3 Market row

**Purpose:** Bram confrontation, trade, favors, Market Day.
**Footprint:** Approximately 8 × 5 tiles.
**Design:** Three permanent stall positions against mixed shopfronts, with a clear central lane. Mustard, rust, and faded teal awnings.
**Variants:** Closed, ordinary two-stall day, full three-stall Market Day, rain covers.
**Props:** Scales, baskets, bolts of cloth, bread, fish, produce, coins, crates, chalk prices with fictional marks only.

### 10.4 Chapel

**Purpose:** Confessions, moral pressure, elder gatherings.
**Footprint:** Approximately 4 × 5 tiles plus small yard.
**Design:** Modest pale-stone civic chapel with a steep roof, small bell, ash-violet door, and memorial garden. Use an original abstract Greyhaven faith symbol.
**Variants:** Day, candlelit evening windows, confession-door glow.
**Props:** Low grave or memorial stones, candles, flower offerings, bench, bell rope.

### 10.5 Docks and harbor

**Purpose:** Shipments, fisher community, storm set piece.
**Footprint:** Multiple modular piers across approximately 10 × 6 tiles.
**Design:** Two main piers, one small moored fishing boat, cargo landing, net-drying area, and strong view of animated water.
**Variants:** Normal tide, shipment arrival, abandoned storm docks, post-storm wet state.
**Props:** Mooring posts, ropes, nets, fish baskets, buoys, crab pots, cargo crane, crates, tarps, gull perches.

### 10.6 Constable's post

**Purpose:** Law, threats, public record, wrongful-arrest plot.
**Footprint:** Approximately 3 × 3 tiles.
**Design:** Compact blue-doored stone-and-timber office with barred document window, civic badge plaque, and exterior ledger stand. It should feel administrative, not like a dungeon.
**Variants:** Open, closed/night, lamp-lit record review.
**Props:** Ledger stand, key board, brazier, evidence crate, bench.

### 10.7 Midwife's cottage

**Purpose:** Illness event, private favors, vulnerable residents.
**Footprint:** Approximately 4 × 3 tiles plus herb garden.
**Design:** Cream cottage with green shutters, low roof, covered porch, drying herbs, and a clear lamp in the front window.
**Variants:** Ordinary, sick-house lamp, rain state.
**Props:** Herb beds, jars, basket, water basin, stool, laundry line, firewood.

### 10.8 Guildhouse

**Purpose:** Election machinery, endorsements, Rhea's power.
**Footprint:** Approximately 5 × 5 tiles.
**Design:** Tall, symmetrical dark-oak and pale-stone building with oxblood banners, broad steps, double doors, seal plaque, and visible public notice space. It is the grandest building but not a palace.
**Variants:** Closed doors, open count, compact posted, election night.
**Props:** Ballot box, poll book table, guild seals, rope barrier, witness stools, posting frame.

### 10.9 Back alley

**Purpose:** Secrets, private deals, night meetings.
**Footprint:** Narrow route between inn, guildhouse, and road.
**Design:** Layered walls, overhangs, stacked crates, laundry, drainage, and pockets of shadow while preserving walkability.
**Variants:** Day, lantern night, rain runoff.
**Props:** Crates, broken cartwheel, covered barrel, cat, drainpipe, hidden note marker.

### 10.10 Notice board

**Purpose:** Public traits, election notices, visible reputation.
**Design:** Large freestanding timber board that remains readable at gameplay scale. Provide an empty board plus layerable papers, chalk strips, portrait tokens, pins, seals, crossed-out notices, and rumor scribbles.
**Interaction states:** Normal, hover, newly updated, open UI transition.

### 10.11 Player's rented room

No separate walkable interior is required. Represent it through:

- An upstairs Gull & Anchor window.
- A small room-key icon.
- A sleep/day-summary vignette illustration.
- Optional compact cutaway art only if separately quoted.

### 10.12 Road out of town

**Purpose:** Arrival, navigation boundary, exile ending.
**Design:** Worn southbound road between low stone walls and wind-bent trees, with a Greyhaven signpost and distant field/sea suggestion.
**Variants:** Dawn arrival, ordinary day, storm, exile crowd.

---

## 11. Modular prop library

### Harbor

- Fishing boat and small cargo boat.
- Crates: closed, open, fish, cloth, marked shipment.
- Barrels, rope coils, nets, buoys, baskets, hooks, floats.
- Small crane/winch.
- Mooring posts and ladders.
- Fish-cleaning table.

### Market and food

- Three stall frames.
- Six awning colors/patterns.
- Bread, fish, produce, cloth, bottles, dry goods.
- Hand scales, weights, coin tray, ledgers.
- Baskets and sacks in full/half/empty states.

### Civic and election

- Ballot box: sealed, open, disputed.
- Poll book, quills, ink, wax seals.
- Posting table and public-count table.
- Guild banners and neutral town banners.
- Bell, rope barrier, speaking platform.
- Tally cards and vote tokens.

### Domestic and street

- Benches, stools, tables.
- Lamps and lantern posts.
- Doors, shutters, signs, steps, planters.
- Laundry, firewood, rain barrels.
- Carts, wheelbarrows, handcart.
- Cats, dogs, gulls, chickens as optional ambient creatures.

### Story-specific

- Marta's delayed shipment.
- Nessa's harbor log.
- Orin's sealed confession.
- Talia's willow draught.
- Elias's correction page and brazier.
- Kit's delivery receipt.
- Rhea's poll book and compact.
- Promise ribbon or knot token.

---

## 12. World animation and effects

### Always-on ambience

- Water: 6–8 frame loop.
- Shore foam: 4–6 frame loop.
- Chimney smoke: 6–8 frame loop.
- Flags and awnings: 6 frame wind loop.
- Lantern flame: 4 frame loop.
- Window candle: 3–4 frame loop.
- Gulls: idle, hop, short flight, perch.
- Small grass/flower movement where it does not create visual noise.

### Day phases

Do not repaint every asset four times. Supply overlay and lighting assets for:

- Morning: cool shadows, pale gold rim light.
- Afternoon: neutral warm daylight.
- Evening: violet shadows, amber windows.
- Night: blue-grey world tint, warm lamps, readable interaction highlights.

### Storm set piece

The storm is a required visual showcase.

- Diagonal rain in at least three seamless density layers.
- Ground splashes and roof runoff.
- Puddles and wet-cobble shine.
- Dark cloud/lighting overlay.
- Lightning flash frames.
- Wind-heavy flags, trees, awnings, and clothing variants.
- Empty dock presentation.
- Warm crowded inn windows.
- Optional distant wave impact.

The storm must preserve NPC, path, speech-bubble, and interaction readability.

---

## 13. Event-specific asset sets

### Market Day

- Two additional temporary stalls.
- Visiting-goods variants.
- Denser baskets and handcarts.
- Crowd placement decals or subtle ground markers.
- Busy stall animation.

### Public argument

- Bram and Nessa argument poses.
- Reusable crowd ring indicators.
- Point, murmur, shock, and faction-reaction animations.
- Two faction accent markers that do not resemble combat teams.

### Festival night

- Lantern strings.
- Neutral town bunting.
- Small music platform.
- Shared dance/clap loop.
- Food table and cups.

### Shipment arrival

- Cargo boat or offloading edge.
- Marked crates and tarpaulin.
- Crate-carry animation.
- Dock crane movement.

### Someone falls ill

- Lit cottage/window indicator.
- Closed-door marker.
- Medicine basket and draught.
- Tired/sick portrait for Oswin plus a reusable pale overlay if another resident is selected later.

### Election

- Ballot table and sealed box.
- Queue markers.
- Candidate tokens for player and Rhea.
- Vote-slip animation.
- Count/tally animation.
- Crowd cheer, silence, anger, and dismissal states.

---

## 14. Rumor, relationship, and interaction visual language

These elements are more important than decorative environment detail.

### Rumor bubbles

Supply scalable nine-slice speech bubbles and world bubbles:

- Ordinary conversation.
- Private whisper.
- Player-origin rumor.
- Mutated rumor.
- Correction/truth response.
- Angry public speech.

Each rumor bubble needs:

- Speaker tail variants in four directions.
- A short wording line area.
- Small origin/lineage pips.
- Pop-in frames or a simple scale-safe border animation.
- A drift/travel particle that can visibly move from speaker to listener.

Avoid comic-book explosions unless the scene is an argument.

### Relationship feedback

Create icons for:

- Trust increase/decrease.
- Affinity increase/decrease.
- Fear.
- Debt/favor owed.
- Endorsement.
- Promise made, due soon, kept, and broken.

These must read at 16, 24, and 32 px.

### Public traits

Create distinct icons for:

- Reliable.
- Generous.
- Dangerous.
- Dishonest.
- Influential.
- Troublemaker.

They should resemble hand-drawn civic shorthand that could plausibly appear on the notice board.

### World interaction

- Hover outline or glow.
- NPC selection ring.
- Destination marker.
- Eavesdrop radius/ear icon.
- New conversation indicator.
- Busy/unavailable marker.
- Quest/favor marker that does not use generic fantasy exclamation marks.

---

## 15. UI art requirements

The UI should feel like town paperwork handled by many hands: parchment, ink, stamps, thread, chalk, and ledger tabs. It must remain compact and should never cover most of the town.

### Core panels

- Conversation panel with portrait, name, role, text, and action choices.
- Town ledger.
- Promise list and countdown chips.
- Notice-board interface.
- Relationship detail panel.
- Rumor lineage/history panel.
- Day/phase clock.
- Action counter.
- Location label.
- Election tally.
- Day summary.
- Settings and pause.

### Reusable UI pieces

- Nine-slice parchment panels in light and dark variants.
- Tabs, buttons, action chips, dividers, scroll treatment.
- Wax seals, pins, ribbons, ink marks, checkbox/tally marks.
- Tooltips and toast notifications.
- Disabled, hover, pressed, selected, warning, and success states.
- Keyboard and mouse prompts.

### Typography

The artist does not need to create a full font unless quoted separately. UI frames must allow a highly readable licensed pixel font. Do not bake text into reusable assets, except fictional sign shapes supplied in editable layers.

---

## 16. Portrait and narrative illustration requirements

### Dialogue portraits

- Principals: six expressions each.
- Ambients: neutral, positive, negative.
- Player: neutral silhouette or selected appearance.
- Consistent crop, lighting, and transparent background.
- Faces must remain recognizable at approximately 160–220 px displayed height.

### Ending cards

Six 16:9 illustrations at a minimum working size of 1920 × 1080:

1. **The Town Turns — Landslide:** The player lifted above a cheering square while Rhea watches from the guild steps.
2. **By One Voice — Narrow win:** The final ballot held over the box; divided crowd; one relieved supporter.
3. **The Tied Bell — Narrow loss:** Rhea beneath the civic bell; the player in the edge of the crowd; one regretful voter looking back.
4. **No Seconding Voice — Humiliation:** Empty speaking platform, scattered notices, tavern laughter in the distance.
5. **The Story Unravels — Exposed:** Conflicting rumor papers and witnesses encircle the player as a false story tears apart.
6. **The Road Remembers — Run out of town:** The player walking south while Greyhaven's silhouettes and accusation bubbles recede behind.

These may be produced later than the core gameplay assets.

---

## 17. Audio asset brief

This section is for a sound designer or licensed-audio search, not necessarily the visual artist.

### Ambient loops

- Harbor: water, rope strain, gulls, distant work.
- Market: light crowd, baskets, coins, stall cloth.
- Inn: low conversation, hearth, crockery.
- Chapel: room tone, distant bell, wind.
- Night town: wind, occasional door, quiet water.
- Storm: rain base, roof rain, wind, distant waves.

### Interaction sounds

- Stone, dirt, wood, and wet footsteps.
- Speech-bubble pop and rumor transfer.
- Relationship increase/decrease.
- Promise made, due-soon warning, kept, broken.
- Ledger write, page turn, seal stamp.
- Notice-board pin.
- Clock phase advance.
- Door knock.
- Coin, crate, bottle, rope, bell.

### Event and finale

- Thunder set with distant/near variants.
- Market crowd swell.
- Public-argument crowd reactions.
- Festival hand drum and fiddle-like loop using original/licensed composition.
- Election ballot drop.
- Vote-tally drumroll.
- Win, loss, exposure, and exile stingers.

All loops must be seamless and supplied as WAV masters plus compressed web-ready versions.

---

## 18. Delivery structure and file naming

### Required source delivery

- Editable layered source files.
- Individual PNG sequences.
- Packed sprite sheets.
- Atlas metadata in JSON or a clearly documented frame grid.
- One palette file.
- One contact sheet per character and asset family.
- Preview GIF or MP4 for every animation set.
- Written license and commercial-use transfer terms.

### Folder structure

```text
hearsay_art/
  characters/
    player/
    principals/
      marta/
      elias/
      orin/
      nessa/
      bram/
      talia/
      pip/
      rhea/
    ambients/
      jonas/
      mae/
      oswin/
      del/
      hettie/
      cal/
      edda/
      will/
      fen/
      lina/
      tob/
      kit/
  portraits/
  terrain/
  buildings/
  props/
  effects/
  events/
  ui/
  endings/
  previews/
  palettes/
```

### Naming examples

```text
npc_marta_walk_s_00.png
npc_marta_walk_s_01.png
npc_marta_talk_e_00.png
npc_marta_portrait_suspicious.png
building_inn_base_day.png
building_inn_windows_night.png
fx_rumor_transfer_00.png
ui_trait_reliable_24.png
```

Use lowercase snake case, zero-padded frame numbers, and stable names after approval.

---

## 19. Production priorities and quotation packages

The artist should quote the work in separable packages so the game can reach a polished vertical slice before the full order is complete.

### Package A — Style test

- One Greyhaven color key.
- One small town-layout paint-over/mockup.
- Marta complete gameplay sprite set.
- Pip complete gameplay sprite set.
- One terrain sample with grass, cobble, road, and water.
- Gull & Anchor façade.
- One conversation panel and one rumor bubble.

**Approval gate:** Characters move cleanly, the town is readable at 1×, and the art feels original rather than like a Tiny Swords reskin.

### Package B — First ten minutes

- Player.
- Marta, Pip, Bram, and Rhea.
- Road, inn, square, market, docks, guildhouse.
- Core terrain and prop library.
- Core conversation UI.
- Promise and rumor effects.
- Shipment props.

**Approval gate:** Arrival, Marta's request, Pip's rumor transfer, Bram's confrontation, and Rhea's election invitation are fully presentable.

### Package C — Full town and cast

- Remaining principals.
- All twelve ambient residents.
- Chapel, constable's post, midwife's cottage, alley, notice board.
- Full day/night overlays.
- Full UI and icons.
- Remaining shared animations.

### Package D — Events and finale

- Storm.
- Market Day.
- Public argument.
- Festival night.
- Shipment arrival.
- Illness state.
- Election staging.
- Six ending cards.

### Optional Package E — Player customization and extra polish

- Modular player appearances.
- Additional portrait expressions.
- Additional ambient animals.
- Secondary building variants.
- Extra prop and animation variety.

---

## 20. Review and acceptance checklist

### Characters

- [ ] All 21 characters have complete heads, bodies, hands, feet, and attached accessories in every frame.
- [ ] Every character has idle, walk, talk, and listen animations.
- [ ] Feet do not slide during the walk cycle.
- [ ] Frame anchors do not jump.
- [ ] Every principal is recognizable from silhouette and identifier color alone.
- [ ] Ambient residents are visibly distinct from one another.
- [ ] Portraits match gameplay sprites.
- [ ] No costume accidentally implies combat or magic.

### World

- [ ] Terrain tiles repeat without visible seams.
- [ ] Walkable and blocked areas are obvious without debug overlays.
- [ ] Every named location is recognizable without relying only on UI labels.
- [ ] The square supports crowds without visual clutter.
- [ ] Buildings do not hide required interactions.
- [ ] Day, evening, night, and storm remain readable.

### Simulation feedback

- [ ] A rumor can be seen moving from one resident to another.
- [ ] Promise states are distinguishable immediately.
- [ ] Relationship changes read at gameplay scale.
- [ ] Public traits read at 16–32 px.
- [ ] Argument and election crowds do not resemble combat.

### Files

- [ ] Editable source files are included.
- [ ] All PNGs have correct transparency.
- [ ] Naming and folder structure are consistent.
- [ ] Sprite sheets include frame data.
- [ ] Animation previews are included.
- [ ] Commercial rights and third-party dependencies are documented.

---

## 21. What not to spend time on

- Combat animations, weapons, enemies, spell effects, or damage UI.
- Lip synchronization.
- Large explorable interiors.
- Eight-direction animation unless separately approved.
- Highly detailed face animation on world sprites.
- Physics-based cloth or water.
- Unique night repaint of every asset when overlays can solve it.
- Decorative assets that reduce path or NPC readability.
- Generic fantasy ornament unrelated to a working harbor town.

The budget should go first to clean movement, distinct residents, visible rumor transfer, the first ten minutes, and the storm.

---

## 22. Artist response requested

Please include:

1. Portfolio examples closest to this type of pixel-art production.
2. Proposed character and tile scale, with any recommended changes to this brief.
3. Price and delivery time for each package.
4. Number of review rounds included.
5. Whether animation, UI, portraits, and environment are all produced by the same artist.
6. Source-file format.
7. Commercial rights terms.
8. Earliest date for the Package A style test.
9. Any asset categories that should be simplified or separated to keep consistency.

No full production should begin until Package A is approved at actual gameplay scale.
