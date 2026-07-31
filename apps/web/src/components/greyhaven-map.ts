export const TILE_SIZE = 64;
export const WORLD_COLUMNS = 30;
export const WORLD_ROWS = 18;
export const WORLD_WIDTH = WORLD_COLUMNS * TILE_SIZE;
export const WORLD_HEIGHT = WORLD_ROWS * TILE_SIZE;

export interface MapPoint {
  x: number;
  y: number;
}

export interface MapRect extends MapPoint {
  height: number;
  width: number;
}

export type LandmarkId =
  | "alley"
  | "chapel"
  | "constable"
  | "docks"
  | "guildhouse"
  | "inn"
  | "market"
  | "midwife"
  | "notice_board"
  | "road"
  | "room"
  | "square";

export type LandmarkInteraction =
  | "journal"
  | "resident"
  | "room"
  | "rumor"
  | "status";

export interface LandmarkDefinition {
  id: LandmarkId;
  interaction: LandmarkInteraction;
  label: string;
  mapLabel: string;
  point: MapPoint;
  prompt: string;
  summary: string;
}

export const LANDMARKS: Record<LandmarkId, LandmarkDefinition> = {
  docks: {
    id: "docks",
    interaction: "resident",
    label: "Docks & harbor",
    mapLabel: "Docks",
    point: { x: 5, y: 5.25 },
    prompt: "Listen at the docks",
    summary:
      "Salt, wet rope, and delayed cargo. Nessa's crews know which stories came ashore.",
  },
  guildhouse: {
    id: "guildhouse",
    interaction: "resident",
    label: "Guildhouse",
    mapLabel: "Guild",
    point: { x: 13, y: 6.1 },
    prompt: "Approach the Guildhouse",
    summary:
      "Greyhaven's ledgers, contracts, and ballot box all pass beneath Rhea Kest's roof.",
  },
  constable: {
    id: "constable",
    interaction: "resident",
    label: "Constable's post",
    mapLabel: "Post",
    point: { x: 21, y: 8.15 },
    prompt: "Visit the constable",
    summary:
      "A tidy post with an untidy archive. Elias hears every accusation twice.",
  },
  chapel: {
    id: "chapel",
    interaction: "resident",
    label: "Chapel",
    mapLabel: "Chapel",
    point: { x: 25, y: 7.05 },
    prompt: "Enter the chapel yard",
    summary:
      "Candles burn for the living and the dead. Father Orin keeps both kinds of confidence.",
  },
  alley: {
    id: "alley",
    interaction: "rumor",
    label: "Back alley",
    mapLabel: "Alley",
    point: { x: 9, y: 8 },
    prompt: "Listen at the corner",
    summary:
      "Laundry, barrels, and voices lowered just enough to make listening irresistible.",
  },
  inn: {
    id: "inn",
    interaction: "resident",
    label: "The Gull & Anchor",
    mapLabel: "Inn",
    point: { x: 7, y: 12.75 },
    prompt: "Step beneath the inn sign",
    summary:
      "Greyhaven's warmest room and busiest mouth. Marta knows who needs what before they ask.",
  },
  room: {
    id: "room",
    interaction: "room",
    label: "Your rented room",
    mapLabel: "Room",
    point: { x: 6.25, y: 12.75 },
    prompt: "Check your room",
    summary:
      "A narrow rented room above the inn. Your progress is already safe here.",
  },
  square: {
    id: "square",
    interaction: "resident",
    label: "Town square",
    mapLabel: "Square",
    point: { x: 15, y: 10.55 },
    prompt: "Enter the square",
    summary:
      "Every route crosses the fountain, and every version of a story eventually reaches Pip.",
  },
  notice_board: {
    id: "notice_board",
    interaction: "journal",
    label: "Notice board",
    mapLabel: "Board",
    point: { x: 17.35, y: 10.15 },
    prompt: "Read the notice board",
    summary:
      "Promises, public traits, and the town's current verdict, written where nobody can miss them.",
  },
  market: {
    id: "market",
    interaction: "resident",
    label: "Market Row",
    mapLabel: "Market",
    point: { x: 23, y: 11.65 },
    prompt: "Walk between the stalls",
    summary:
      "Three stalls, twelve prices, and Bram's firm belief that urgency should cost extra.",
  },
  midwife: {
    id: "midwife",
    interaction: "resident",
    label: "Midwife's cottage",
    mapLabel: "Midwife",
    point: { x: 25, y: 15.35 },
    prompt: "Visit the herb garden",
    summary:
      "Talia's flowers are cheerful; the drawn curtains are not.",
  },
  road: {
    id: "road",
    interaction: "status",
    label: "Road into town",
    mapLabel: "Road",
    point: { x: 15, y: 16.7 },
    prompt: "Read the milestone",
    summary:
      "The road still runs both ways. Greyhaven has not decided which direction you will take.",
  },
};

export const LOCATION_POINTS: Record<string, MapPoint> = Object.fromEntries(
  Object.values(LANDMARKS).map((landmark) => [landmark.id, landmark.point]),
);

export const PRESENTED_NPC_IDS = new Set([
  "bram",
  "elias",
  "marta",
  "nessa",
  "orin",
  "pip",
  "rhea",
  "talia",
]);

export const LANDMARK_RESIDENTS: Partial<Record<LandmarkId, string>> = {
  chapel: "orin",
  constable: "elias",
  docks: "nessa",
  guildhouse: "rhea",
  inn: "marta",
  market: "bram",
  midwife: "talia",
  square: "pip",
};

export const PATH_SEGMENTS: Array<{
  from: MapPoint;
  material: "dirt" | "stone" | "wood";
  to: MapPoint;
  width: number;
}> = [
  { from: { x: 15, y: 17 }, to: { x: 15, y: 11 }, material: "dirt", width: 1.6 },
  { from: { x: 15, y: 15.5 }, to: { x: 24.8, y: 15.5 }, material: "dirt", width: 1.45 },
  { from: { x: 24.8, y: 15.5 }, to: { x: 24.8, y: 11.5 }, material: "dirt", width: 1.45 },
  { from: { x: 12, y: 10.4 }, to: { x: 7.2, y: 12.5 }, material: "dirt", width: 1.6 },
  { from: { x: 7.5, y: 11.5 }, to: { x: 9, y: 8 }, material: "dirt", width: 1.35 },
  { from: { x: 9, y: 8 }, to: { x: 5, y: 5.3 }, material: "wood", width: 1.25 },
  { from: { x: 9, y: 8 }, to: { x: 13, y: 6.1 }, material: "stone", width: 1.3 },
  { from: { x: 14, y: 7.3 }, to: { x: 13, y: 6.1 }, material: "stone", width: 1.35 },
  { from: { x: 18, y: 9 }, to: { x: 21, y: 8.1 }, material: "stone", width: 1.4 },
  { from: { x: 21, y: 8.1 }, to: { x: 25, y: 7.05 }, material: "stone", width: 1.25 },
  { from: { x: 18, y: 10.3 }, to: { x: 23, y: 11.5 }, material: "dirt", width: 1.6 },
];

export const COLLISION_RECTS: MapRect[] = [
  { x: 0, y: 0, width: 8.65, height: 4.35 },
  { x: 9.45, y: 1.1, width: 7.1, height: 4.55 },
  { x: 23.35, y: 2.15, width: 3.3, height: 4.25 },
  { x: 19.45, y: 5.2, width: 3.2, height: 2.3 },
  { x: 4.65, y: 9.05, width: 4.75, height: 3.05 },
  { x: 23.35, y: 11.45, width: 3.3, height: 3.25 },
  { x: 14.35, y: 8.25, width: 1.3, height: 1.3 },
  { x: 20.35, y: 9.7, width: 1.85, height: 1.05 },
  { x: 22.25, y: 9.7, width: 1.85, height: 1.05 },
  { x: 24.15, y: 9.7, width: 1.85, height: 1.05 },
];

export const TREE_SCENERY: Array<
  MapPoint & {
    asset: "treeGreen" | "treeLime" | "treeTeal";
    scale?: number;
  }
> = [
  { asset: "treeGreen", x: 1.1, y: 6.7, scale: 1.9 },
  { asset: "treeTeal", x: 2.2, y: 9.6, scale: 1.75 },

  // Southwest woodland. Keep the inn's lawn and doorway entirely clear, then
  // compress three overlapping rows against the bottom edge like a forest wall.
  { asset: "treeTeal", x: 0.55, y: 15.25, scale: 1.85 },
  { asset: "treeGreen", x: 1.85, y: 15.25, scale: 1.75 },
  { asset: "treeLime", x: 3.15, y: 15.25, scale: 1.9 },
  { asset: "treeTeal", x: 4.45, y: 15.25, scale: 1.8 },
  { asset: "treeGreen", x: 5.75, y: 15.25, scale: 1.85 },
  { asset: "treeLime", x: 7.05, y: 15.25, scale: 1.75 },
  { asset: "treeTeal", x: 8.35, y: 15.25, scale: 1.9 },
  { asset: "treeGreen", x: 9.65, y: 15.25, scale: 1.8 },
  { asset: "treeLime", x: 10.95, y: 15.25, scale: 1.85 },
  { asset: "treeGreen", x: 0.1, y: 16.45, scale: 1.9 },
  { asset: "treeLime", x: 1.4, y: 16.45, scale: 1.8 },
  { asset: "treeTeal", x: 2.7, y: 16.45, scale: 1.85 },
  { asset: "treeGreen", x: 4, y: 16.45, scale: 1.75 },
  { asset: "treeLime", x: 5.3, y: 16.45, scale: 1.9 },
  { asset: "treeTeal", x: 6.6, y: 16.45, scale: 1.8 },
  { asset: "treeGreen", x: 7.9, y: 16.45, scale: 1.85 },
  { asset: "treeLime", x: 9.2, y: 16.45, scale: 1.75 },
  { asset: "treeTeal", x: 10.5, y: 16.45, scale: 1.9 },
  { asset: "treeGreen", x: 11.6, y: 16.45, scale: 1.8 },
  { asset: "treeLime", x: 0.65, y: 17.65, scale: 1.85 },
  { asset: "treeTeal", x: 2, y: 17.65, scale: 1.75 },
  { asset: "treeGreen", x: 3.35, y: 17.65, scale: 1.9 },
  { asset: "treeLime", x: 4.7, y: 17.65, scale: 1.8 },
  { asset: "treeTeal", x: 6.05, y: 17.65, scale: 1.85 },
  { asset: "treeGreen", x: 7.4, y: 17.65, scale: 1.75 },
  { asset: "treeLime", x: 8.75, y: 17.65, scale: 1.9 },
  { asset: "treeTeal", x: 10.1, y: 17.65, scale: 1.8 },
  { asset: "treeGreen", x: 11.35, y: 17.65, scale: 1.85 },

  { asset: "treeLime", x: 20.2, y: 17.4, scale: 1.65 },
  { asset: "treeGreen", x: 28.5, y: 16.4, scale: 1.85 },
  { asset: "treeTeal", x: 28.7, y: 12.4, scale: 1.8 },
  { asset: "treeLime", x: 28.5, y: 8.2, scale: 1.75 },
  { asset: "treeGreen", x: 28.2, y: 3.5, scale: 1.9 },
  { asset: "treeTeal", x: 19, y: 3.3, scale: 1.55 },
  { asset: "treeLime", x: 18, y: 6.3, scale: 1.45 },
  { asset: "treeGreen", x: 11.2, y: 8.2, scale: 1.35 },
  { asset: "treeLime", x: 3.5, y: 11.8, scale: 1.45 },
  { asset: "treeTeal", x: 20.2, y: 14.2, scale: 1.4 },
];

export function distanceToSegment(
  point: MapPoint,
  start: MapPoint,
  end: MapPoint,
) {
  const deltaX = end.x - start.x;
  const deltaY = end.y - start.y;
  const lengthSquared = deltaX * deltaX + deltaY * deltaY;
  if (lengthSquared === 0) {
    return Math.hypot(point.x - start.x, point.y - start.y);
  }
  const progress = Math.max(
    0,
    Math.min(
      1,
      ((point.x - start.x) * deltaX + (point.y - start.y) * deltaY) /
        lengthSquared,
    ),
  );
  return Math.hypot(
    point.x - (start.x + progress * deltaX),
    point.y - (start.y + progress * deltaY),
  );
}

export function terrainMaterialAt(x: number, y: number) {
  if (
    (y <= 2 && x <= 8) ||
    (y === 3 && x <= 7) ||
    (y === 4 && x <= 4)
  ) {
    return "water" as const;
  }
  if (x >= 12 && x <= 18 && y >= 7 && y <= 11) {
    return "stone" as const;
  }
  const center = { x: x + 0.5, y: y + 0.5 };
  const segment = PATH_SEGMENTS.find(
    (candidate) =>
      distanceToSegment(center, candidate.from, candidate.to) <=
      candidate.width / 2,
  );
  return segment?.material ?? ("grass" as const);
}
