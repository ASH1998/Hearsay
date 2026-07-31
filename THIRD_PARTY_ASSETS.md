# Third-party assets

Hearsay uses third-party art and audio only after each selected runtime file has
been recorded in `assets/manifest.json` with its source, license, checksum, and
purpose. Raw archives remain untracked under `assets/downloads/`.

## Selected runtime source packs

| Creator | Pack | Runtime use | License |
|---|---|---|---|
| Quaternius | Medieval Village MegaKit | Shipment wagon | CC0 1.0 |
| Quaternius | Stylized Nature MegaKit | Greyhaven trees | CC0 1.0 |
| Quaternius | Fantasy Props MegaKit | Market stall | CC0 1.0 |
| Quaternius | Modular Character Outfits — Fantasy | Player and principal NPC variants | CC0 1.0 |
| Quaternius | Universal Animation Library | Idle, walk, and talk clips | CC0 1.0 |
| Kenney | UI Pack: Adventure | Town Ledger paper texture | CC0 1.0 |
| Kenney | UI Audio | Confirmation and hover cues | CC0 1.0 |
| Kenney | Pirate Kit | Inn, houses, docks, barrel, and fish bucket | CC0 1.0 |
| Maeve Devs (formerly EmanuelleDev) | Farm RPG — Tiny Asset Pack | Focused-release terrain, buildings, props, residents, portraits, and UI framing | Pack license |

No source archive is shipped to players. The selected outputs are optimized,
checksummed, and size-budgeted by the relevant preparation script. Exact source
URLs, purposes, runtime paths, and file hashes for the active Farm RPG set are
recorded in `assets/manifest.json`.

## Farm RPG — Tiny Asset Pack

The focused Greyhaven world uses a deliberately selected runtime subset under
`apps/web/public/world/farm-rpg/`. It is prepared reproducibly by
`scripts/prepare-farm-rpg-assets.ps1` from the user's local licensed source pack.
The complete source pack is never copied into the public web directory.

- Creator: **Maeve Devs**, formerly credited as **EmanuelleDev**
- Original pack: <https://maevedevs.itch.io/farm-rpg>
- Local bundled license:
  `assets/Farm RPG - Tiny Asset Pack - (All in One) - new/Lincese   Info.txt`
- Terms checked: 2026-07-31

The pack permits personal and commercial project use and modification. The
bundled license requires creator credit. The current product license prohibits
resale or redistribution of the source or modified asset pack, crypto/NFT use,
and AI training. Hearsay ships only integrated runtime crops and composites.

## Retained Tiny Swords prototype

The former Pixel Frog Tiny Swords prototype files remain under
`apps/web/public/world/greyhaven/` to preserve prior work, but the default
focused Greyhaven renderer does not request them. Cleanup or deletion requires
separate authorization.

- Original pack: <https://pixelfrog-assets.itch.io/tiny-swords>
- Creator: **Pixel Frog**
- Runtime status: retained legacy files, not loaded by the focused release

Model licensing is recorded separately in `THIRD_PARTY_MODELS.md`.
