export const RELEASE_PROFILE_ID = "hackathon_small";

export const FEATURED_NPC_IDS = [
  "marta",
  "bram",
  "pip",
  "talia",
  "rhea",
] as const;

export const RELEASE_LOCATION_IDS = [
  "road",
  "inn",
  "square",
  "market",
  "midwife",
  "guildhouse",
] as const;

export const SUPPORTING_NPC_IDS = ["nessa", "elias", "orin"] as const;

const featuredNpcIds = new Set<string>(FEATURED_NPC_IDS);
const releaseLocationIds = new Set<string>(RELEASE_LOCATION_IDS);
const supportingNpcIds = new Set<string>(SUPPORTING_NPC_IDS);

export type ReleaseTier = "featured" | "supporting" | "background";

export function releaseTierForNpc(npcId: string): ReleaseTier {
  if (featuredNpcIds.has(npcId)) return "featured";
  if (supportingNpcIds.has(npcId)) return "supporting";
  return "background";
}

export function isFeaturedNpc(npcId: string) {
  return featuredNpcIds.has(npcId);
}

export function isReleaseLocation(locationId: string) {
  return releaseLocationIds.has(locationId);
}

export function isAutonomousEvent(kind: string) {
  return (
    kind.includes("agent") ||
    kind.includes("gossip") ||
    kind.includes("schedule") ||
    kind.includes("rumor") ||
    kind.includes("retell") ||
    kind.includes("transmission")
  );
}
