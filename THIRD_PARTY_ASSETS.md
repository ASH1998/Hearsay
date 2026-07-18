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

No source archive is shipped to players. The selected outputs are optimized,
checksummed, and size-budgeted by `scripts/build_assets.py`; exact source URLs,
purposes, runtime paths, and file hashes are recorded in
`assets/manifest.json`. Attribution is retained voluntarily even though CC0 does
not require it.
