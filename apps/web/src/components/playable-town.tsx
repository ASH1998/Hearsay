"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
} from "react";

import {
  COLLISION_RECTS,
  LANDMARKS,
  LANDMARK_RESIDENTS,
  LOCATION_POINTS,
  PATH_SEGMENTS,
  PRESENTED_NPC_IDS,
  TILE_SIZE,
  TREE_SCENERY,
  WORLD_COLUMNS,
  WORLD_HEIGHT,
  WORLD_ROWS,
  WORLD_WIDTH,
  terrainMaterialAt,
  type LandmarkId,
  type MapPoint,
  type MapRect,
} from "@/components/greyhaven-map";
import type { NpcState, RunSnapshot } from "@/lib/api";

interface PlayableTownProps {
  snapshot: RunSnapshot;
  guidedNpcId: string | null;
  movementDisabled: boolean;
  onLandmarkInteract: (landmarkId: LandmarkId) => void;
  onMove: (locationId: string) => void;
  onNpcClick: (npc: NpcState) => void;
  selectedLandmarkId: LandmarkId | null;
  selectedNpcId: string | null;
}

type AssetKey =
  | "barrels"
  | "bench"
  | "boat"
  | "bridge"
  | "buildingChapel"
  | "buildingConstable"
  | "buildingGuildhouse"
  | "buildingInn"
  | "buildingMidwife"
  | "flowers"
  | "fountain"
  | "graves"
  | "marketBlue"
  | "marketCream"
  | "marketRed"
  | "noticeBoard"
  | "paths"
  | "signpost"
  | "terrain"
  | "terrainWater"
  | "treeGreen"
  | "treeLime"
  | "treeTeal"
  | "water"
  | "well"
  | CharacterAssetKey;

type CharacterAssetKey =
  | "bramIdle"
  | "bramWalk"
  | "eliasIdle"
  | "eliasWalk"
  | "martaIdle"
  | "martaWalk"
  | "nessaIdle"
  | "nessaWalk"
  | "orinIdle"
  | "orinWalk"
  | "pipIdle"
  | "pipWalk"
  | "playerIdle"
  | "playerWalk"
  | "rheaIdle"
  | "rheaWalk"
  | "taliaIdle"
  | "taliaWalk";

type LoadedAssets = Partial<Record<AssetKey, HTMLImageElement>>;

type Facing = "down" | "left" | "right" | "up";

interface CharacterConfig {
  idle: CharacterAssetKey;
  idleFrames: number;
  layout: "horizontal4" | "rows3" | "rows4";
  walk: CharacterAssetKey;
  walkFrames: number;
}

interface InteractionTarget {
  id: string;
  label: string;
  point: MapPoint;
  type: "landmark" | "npc";
}

interface Renderable {
  draw: () => void;
  sortY: number;
}

const ASSET_ROOT = "/world/farm-rpg";
const INTERACTION_DISTANCE = 1.35;
const LOCATION_ACTIVATION_DISTANCE = 0.68;
const PLAYER_SPEED_TILES_PER_SECOND = 165 / TILE_SIZE;

const ASSET_URLS: Record<AssetKey, string> = {
  barrels: `${ASSET_ROOT}/prop-barrels.png`,
  bench: `${ASSET_ROOT}/prop-bench.png`,
  boat: `${ASSET_ROOT}/prop-boat.png`,
  bramIdle: `${ASSET_ROOT}/characters/bram-blacksmith-idle.png`,
  bramWalk: `${ASSET_ROOT}/characters/bram-blacksmith-walk.png`,
  bridge: `${ASSET_ROOT}/prop-bridge.png`,
  buildingChapel: `${ASSET_ROOT}/building-chapel.png`,
  buildingConstable: `${ASSET_ROOT}/building-constable.png`,
  buildingGuildhouse: `${ASSET_ROOT}/building-guildhouse.png`,
  buildingInn: `${ASSET_ROOT}/building-inn.png`,
  buildingMidwife: `${ASSET_ROOT}/building-midwife.png`,
  eliasIdle: `${ASSET_ROOT}/characters/elias-banker-idle.png`,
  eliasWalk: `${ASSET_ROOT}/characters/elias-banker-walk.png`,
  flowers: `${ASSET_ROOT}/prop-flowers.png`,
  fountain: `${ASSET_ROOT}/prop-fountain.png`,
  graves: `${ASSET_ROOT}/prop-graves.png`,
  marketBlue: `${ASSET_ROOT}/market-stall-blue.png`,
  marketCream: `${ASSET_ROOT}/market-stall-cream.png`,
  marketRed: `${ASSET_ROOT}/market-stall-red.png`,
  martaIdle: `${ASSET_ROOT}/characters/marta-lyria-idle.png`,
  martaWalk: `${ASSET_ROOT}/characters/marta-lyria-walk.png`,
  nessaIdle: `${ASSET_ROOT}/characters/nessa-pirate-idle.png`,
  nessaWalk: `${ASSET_ROOT}/characters/nessa-pirate-walk.png`,
  noticeBoard: `${ASSET_ROOT}/prop-notice-board.png`,
  orinIdle: `${ASSET_ROOT}/characters/orin-idle.png`,
  orinWalk: `${ASSET_ROOT}/characters/orin-walk.png`,
  paths: `${ASSET_ROOT}/paths.png`,
  pipIdle: `${ASSET_ROOT}/characters/pip-josh-idle.png`,
  pipWalk: `${ASSET_ROOT}/characters/pip-josh-walk.png`,
  playerIdle: `${ASSET_ROOT}/characters/player-alex-idle.png`,
  playerWalk: `${ASSET_ROOT}/characters/player-alex-walk.png`,
  rheaIdle: `${ASSET_ROOT}/characters/rhea-manu-idle.png`,
  rheaWalk: `${ASSET_ROOT}/characters/rhea-manu-walk.png`,
  signpost: `${ASSET_ROOT}/prop-signpost.png`,
  taliaIdle: `${ASSET_ROOT}/characters/talia-tori-idle.png`,
  taliaWalk: `${ASSET_ROOT}/characters/talia-tori-walk.png`,
  terrain: `${ASSET_ROOT}/terrain-spring.png`,
  terrainWater: `${ASSET_ROOT}/terrain-water-spring.png`,
  treeGreen: `${ASSET_ROOT}/tree-green.png`,
  treeLime: `${ASSET_ROOT}/tree-lime.png`,
  treeTeal: `${ASSET_ROOT}/tree-teal.png`,
  water: `${ASSET_ROOT}/water.png`,
  well: `${ASSET_ROOT}/prop-well.png`,
};

const CHARACTER_CONFIGS: Record<string, CharacterConfig> = {
  bram: {
    idle: "bramIdle",
    idleFrames: 4,
    layout: "rows4",
    walk: "bramWalk",
    walkFrames: 6,
  },
  elias: {
    idle: "eliasIdle",
    idleFrames: 4,
    layout: "horizontal4",
    walk: "eliasWalk",
    walkFrames: 6,
  },
  marta: {
    idle: "martaIdle",
    idleFrames: 4,
    layout: "rows3",
    walk: "martaWalk",
    walkFrames: 6,
  },
  nessa: {
    idle: "nessaIdle",
    idleFrames: 4,
    layout: "rows4",
    walk: "nessaWalk",
    walkFrames: 6,
  },
  orin: {
    idle: "orinIdle",
    idleFrames: 4,
    layout: "horizontal4",
    walk: "orinWalk",
    walkFrames: 6,
  },
  pip: {
    idle: "pipIdle",
    idleFrames: 4,
    layout: "rows3",
    walk: "pipWalk",
    walkFrames: 6,
  },
  player: {
    idle: "playerIdle",
    idleFrames: 4,
    layout: "rows3",
    walk: "playerWalk",
    walkFrames: 6,
  },
  rhea: {
    idle: "rheaIdle",
    idleFrames: 4,
    layout: "rows3",
    walk: "rheaWalk",
    walkFrames: 6,
  },
  talia: {
    idle: "taliaIdle",
    idleFrames: 4,
    layout: "rows3",
    walk: "taliaWalk",
    walkFrames: 6,
  },
};

const BUILDINGS: Array<{
  asset: AssetKey;
  bottomY: number;
  label: string;
  landmarkId: LandmarkId;
  scale: number;
  x: number;
}> = [
  {
    asset: "buildingGuildhouse",
    bottomY: 5.75,
    label: "Guildhouse",
    landmarkId: "guildhouse",
    scale: 2,
    x: 13,
  },
  {
    asset: "buildingChapel",
    bottomY: 6.55,
    label: "Chapel",
    landmarkId: "chapel",
    scale: 1.45,
    x: 25,
  },
  {
    asset: "buildingConstable",
    bottomY: 7.6,
    label: "Constable's post",
    landmarkId: "constable",
    scale: 1.6,
    x: 21,
  },
  {
    asset: "buildingInn",
    bottomY: 12.2,
    label: "The Gull & Anchor",
    landmarkId: "inn",
    scale: 1.55,
    x: 7,
  },
  {
    asset: "buildingMidwife",
    bottomY: 14.75,
    label: "Midwife's cottage",
    landmarkId: "midwife",
    scale: 1.5,
    x: 25,
  },
];

const PROP_SCENERY: Array<{
  asset: AssetKey;
  bottomY: number;
  scale: number;
  x: number;
}> = [
  { asset: "boat", bottomY: 3.45, scale: 1.15, x: 4.1 },
  { asset: "bridge", bottomY: 5.0, scale: 1.65, x: 5.3 },
  { asset: "barrels", bottomY: 5.75, scale: 1.4, x: 7.1 },
  { asset: "well", bottomY: 8.35, scale: 1.45, x: 9.7 },
  { asset: "graves", bottomY: 7.15, scale: 1.5, x: 27.25 },
  { asset: "graves", bottomY: 7.55, scale: 1.35, x: 27.8 },
  { asset: "bench", bottomY: 10.85, scale: 2, x: 12.8 },
  { asset: "bench", bottomY: 10.85, scale: 2, x: 17.15 },
  { asset: "fountain", bottomY: 9.6, scale: 1.6, x: 15 },
  { asset: "noticeBoard", bottomY: 10.15, scale: 1.65, x: 17.35 },
  { asset: "signpost", bottomY: 12.0, scale: 1.35, x: 18.5 },
  { asset: "flowers", bottomY: 11.7, scale: 1.2, x: 13.4 },
  { asset: "flowers", bottomY: 16.1, scale: 1.25, x: 26.3 },
  { asset: "flowers", bottomY: 15.8, scale: 1.05, x: 22.7 },
];

const MARKET_STALLS: Array<{
  asset: AssetKey;
  bottomY: number;
  label: string;
  x: number;
}> = [
  { asset: "marketBlue", bottomY: 10.75, label: "Fish", x: 21.3 },
  { asset: "marketRed", bottomY: 10.75, label: "Produce", x: 23.2 },
  { asset: "marketCream", bottomY: 10.75, label: "Goods", x: 25.1 },
];

const NPC_OFFSETS: MapPoint[] = [
  { x: 0, y: 0 },
  { x: -0.85, y: 0.5 },
  { x: 0.85, y: 0.5 },
  { x: -1.55, y: 0.95 },
  { x: 1.55, y: 0.95 },
  { x: 0, y: 1.05 },
  { x: -2.1, y: 1.25 },
  { x: 2.1, y: 1.25 },
];

function clamp(value: number, minimum: number, maximum: number) {
  return Math.max(minimum, Math.min(maximum, value));
}

function distance(left: MapPoint, right: MapPoint) {
  return Math.hypot(left.x - right.x, left.y - right.y);
}

function roundedRect(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
) {
  context.beginPath();
  context.roundRect(x, y, width, height, radius);
}

function pointInsideRect(point: MapPoint, rectangle: MapRect) {
  const halfWidth = 0.18;
  const top = point.y - 0.3;
  const bottom = point.y + 0.02;
  return (
    point.x + halfWidth > rectangle.x &&
    point.x - halfWidth < rectangle.x + rectangle.width &&
    bottom > rectangle.y &&
    top < rectangle.y + rectangle.height
  );
}

function movementBlocked(point: MapPoint) {
  if (
    point.x < 0.42 ||
    point.x > WORLD_COLUMNS - 0.42 ||
    point.y < 0.45 ||
    point.y > WORLD_ROWS - 0.35
  ) {
    return true;
  }
  return COLLISION_RECTS.some((rectangle) =>
    pointInsideRect(point, rectangle),
  );
}

function npcPoints(snapshot: RunSnapshot) {
  const byLocation = new Map<string, NpcState[]>();
  snapshot.npcs
    .filter(
      (npc) => PRESENTED_NPC_IDS.has(npc.id) || npc.recent_echoes.length > 0,
    )
    .forEach((npc) => {
      const residents = byLocation.get(npc.location_id) ?? [];
      residents.push(npc);
      byLocation.set(npc.location_id, residents);
    });

  const result = new Map<string, MapPoint>();
  byLocation.forEach((residents, locationId) => {
    const anchor = LOCATION_POINTS[locationId];
    if (!anchor) return;
    residents
      .sort((left, right) => {
        const leftPrincipal = PRESENTED_NPC_IDS.has(left.id) ? 0 : 1;
        const rightPrincipal = PRESENTED_NPC_IDS.has(right.id) ? 0 : 1;
        return leftPrincipal - rightPrincipal || left.name.localeCompare(right.name);
      })
      .forEach((npc, index) => {
        const offset = NPC_OFFSETS[index % NPC_OFFSETS.length];
        const ring = Math.floor(index / NPC_OFFSETS.length);
        result.set(npc.id, {
          x: clamp(anchor.x + offset.x, 0.5, WORLD_COLUMNS - 0.5),
          y: clamp(
            anchor.y + offset.y + ring * 0.8,
            0.6,
            WORLD_ROWS - 0.4,
          ),
        });
      });
  });
  if (
    snapshot.action_count === 0 &&
    !snapshot.promises.some((promise) => promise.promisee_id === "marta")
  ) {
    result.set("marta", { x: 14, y: 16.25 });
  }
  return result;
}

function frameSource(
  config: CharacterConfig,
  facing: Facing,
  frame: number,
  walking: boolean,
) {
  const frames = walking ? config.walkFrames : config.idleFrames;
  if (config.layout === "horizontal4") {
    const groups: Record<Facing, number> = {
      down: 0,
      up: 1,
      right: 2,
      left: 3,
    };
    return {
      flip: false,
      sourceX: (groups[facing] * frames + frame) * 32,
      sourceY: 0,
    };
  }
  if (config.layout === "rows4") {
    const rows: Record<Facing, number> = {
      down: 0,
      left: 1,
      right: 2,
      up: 3,
    };
    return { flip: false, sourceX: frame * 32, sourceY: rows[facing] * 32 };
  }
  const rows: Record<Exclude<Facing, "left">, number> = {
    down: 0,
    right: 1,
    up: 2,
  };
  return {
    flip: facing === "left",
    sourceX: frame * 32,
    sourceY: rows[facing === "left" ? "right" : facing] * 32,
  };
}

function nearestTarget(
  player: MapPoint,
  snapshot: RunSnapshot,
  positions: Map<string, MapPoint>,
  guidedNpcId: string | null,
) {
  const npcTargets: InteractionTarget[] = snapshot.npcs
    .filter((npc) => positions.has(npc.id))
    .map((npc) => ({
      id: npc.id,
      label: npc.name,
      point: positions.get(npc.id) ?? player,
      type: "npc" as const,
    }));
  const landmarkTargets: InteractionTarget[] = Object.values(LANDMARKS).map(
    (landmark) => ({
      id: landmark.id,
      label: landmark.label,
      point: landmark.point,
      type: "landmark" as const,
    }),
  );
  const targets = [...npcTargets, ...landmarkTargets].sort(
    (left, right) => distance(player, left.point) - distance(player, right.point),
  );
  const guided = guidedNpcId
    ? npcTargets.find((target) => target.id === guidedNpcId)
    : null;
  if (guided && distance(player, guided.point) <= INTERACTION_DISTANCE) {
    return guided;
  }
  return targets[0] ?? null;
}

export function PlayableTown({
  snapshot,
  guidedNpcId,
  movementDisabled,
  onLandmarkInteract,
  onMove,
  onNpcClick,
  selectedLandmarkId,
  selectedNpcId,
}: PlayableTownProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const assetsRef = useRef<LoadedAssets>({});
  const cameraRef = useRef({ x: 0, y: 0 });
  const facingRef = useRef<Facing>("up");
  const guidedNpcIdRef = useRef(guidedNpcId);
  const keysRef = useRef(new Set<Facing>());
  const keyOrderRef = useRef<Facing[]>([]);
  const movementDisabledRef = useRef(movementDisabled);
  const onLandmarkInteractRef = useRef(onLandmarkInteract);
  const onMoveRef = useRef(onMove);
  const onNpcClickRef = useRef(onNpcClick);
  const pendingLocationRef = useRef<string | null>(null);
  const selectedTargetRef = useRef<InteractionTarget | null>(null);
  const selectedNpcIdRef = useRef(selectedNpcId);
  const snapshotRef = useRef(snapshot);
  const startingPoint =
    LOCATION_POINTS[snapshot.player.location_id] ?? LANDMARKS.road.point;
  const playerRef = useRef<MapPoint>({ ...startingPoint });
  const previousTimestampRef = useRef<number | null>(null);
  const walkingRef = useRef(false);
  const [assetProgress, setAssetProgress] = useState(0);
  const [nearbyTarget, setNearbyTarget] = useState<InteractionTarget | null>(
    null,
  );
  const [selectedTarget, setSelectedTarget] =
    useState<InteractionTarget | null>(null);
  const [selectedTargetIsNear, setSelectedTargetIsNear] = useState(false);

  useEffect(() => {
    const previousSnapshot = snapshotRef.current;
    snapshotRef.current = snapshot;
    guidedNpcIdRef.current = guidedNpcId;
    movementDisabledRef.current = movementDisabled;
    onLandmarkInteractRef.current = onLandmarkInteract;
    onMoveRef.current = onMove;
    onNpcClickRef.current = onNpcClick;
    selectedNpcIdRef.current = selectedNpcId;
    if (
      pendingLocationRef.current === snapshot.player.location_id ||
      previousSnapshot.run_id !== snapshot.run_id
    ) {
      pendingLocationRef.current = null;
    }
    if (previousSnapshot.run_id !== snapshot.run_id) {
      const point =
        LOCATION_POINTS[snapshot.player.location_id] ?? LANDMARKS.road.point;
      playerRef.current = { ...point };
      previousTimestampRef.current = null;
    }
  }, [
    guidedNpcId,
    movementDisabled,
    onLandmarkInteract,
    onMove,
    onNpcClick,
    selectedNpcId,
    snapshot,
  ]);

  useEffect(() => {
    selectedTargetRef.current = selectedTarget;
  }, [selectedTarget]);

  const activateTarget = useCallback((target: InteractionTarget) => {
    selectedTargetRef.current = null;
    setSelectedTarget(null);
    setSelectedTargetIsNear(false);
    if (target.type === "npc") {
      const npc = snapshotRef.current.npcs.find(
        (candidate) => candidate.id === target.id,
      );
      if (npc) onNpcClickRef.current(npc);
      return;
    }
    onLandmarkInteractRef.current(target.id as LandmarkId);
  }, []);

  const refreshNearbyTarget = useCallback(() => {
    if (canvasRef.current) {
      canvasRef.current.dataset.playerX = playerRef.current.x.toFixed(3);
      canvasRef.current.dataset.playerY = playerRef.current.y.toFixed(3);
    }
    const positions = npcPoints(snapshotRef.current);
    const candidate = nearestTarget(
      playerRef.current,
      snapshotRef.current,
      positions,
      guidedNpcIdRef.current,
    );
    const next =
      candidate &&
      distance(playerRef.current, candidate.point) <= INTERACTION_DISTANCE
        ? candidate
        : null;
    const selected = selectedTargetRef.current;
    setSelectedTargetIsNear(
      selected !== null &&
        distance(playerRef.current, selected.point) <= INTERACTION_DISTANCE,
    );
    setNearbyTarget((current) =>
      current?.id === next?.id && current?.type === next?.type ? current : next,
    );
  }, []);

  const interact = useCallback(() => {
    const selected = selectedTargetRef.current;
    if (
      selected &&
      distance(playerRef.current, selected.point) <= INTERACTION_DISTANCE
    ) {
      activateTarget(selected);
      return;
    }
    const positions = npcPoints(snapshotRef.current);
    const candidate = nearestTarget(
      playerRef.current,
      snapshotRef.current,
      positions,
      guidedNpcIdRef.current,
    );
    if (
      candidate &&
      distance(playerRef.current, candidate.point) <= INTERACTION_DISTANCE
    ) {
      activateTarget(candidate);
    }
  }, [activateTarget]);

  const updateAuthoritativeLocation = useCallback(() => {
    if (pendingLocationRef.current) return;
    const currentLocationId = snapshotRef.current.player.location_id;
    const nearest = Object.values(LANDMARKS)
      .filter((landmark) => landmark.id !== currentLocationId)
      .map((landmark) => ({
        distance: distance(playerRef.current, landmark.point),
        id: landmark.id,
      }))
      .sort((left, right) => left.distance - right.distance)[0];
    if (!nearest || nearest.distance > LOCATION_ACTIVATION_DISTANCE) return;
    pendingLocationRef.current = nearest.id;
    onMoveRef.current(nearest.id);
    window.setTimeout(() => {
      if (pendingLocationRef.current === nearest.id) {
        pendingLocationRef.current = null;
      }
    }, 800);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let loaded = 0;
    const assets: LoadedAssets = {};
    const entries = Object.entries(ASSET_URLS) as [AssetKey, string][];
    entries.forEach(([key, source]) => {
      const image = new Image();
      image.onload = () => {
        loaded += 1;
        if (!cancelled) setAssetProgress(loaded / entries.length);
      };
      image.onerror = () => {
        loaded += 1;
        if (!cancelled) setAssetProgress(loaded / entries.length);
      };
      image.src = source;
      assets[key] = image;
    });
    assetsRef.current = assets;
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    let frameId = 0;

    const resize = () => {
      const ratio = window.devicePixelRatio || 1;
      const bounds = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.round(bounds.width * ratio));
      canvas.height = Math.max(1, Math.round(bounds.height * ratio));
    };

    const drawSourceTile = (
      image: HTMLImageElement | undefined,
      sourceX: number,
      sourceY: number,
      destinationX: number,
      destinationY: number,
    ) => {
      if (!image?.complete || image.naturalWidth === 0) return;
      context.drawImage(
        image,
        sourceX,
        sourceY,
        16,
        16,
        destinationX,
        destinationY,
        TILE_SIZE,
        TILE_SIZE,
      );
    };

    const drawImageBottomCenter = (
      image: HTMLImageElement | undefined,
      worldX: number,
      bottomY: number,
      scale: number,
      cameraX: number,
      cameraY: number,
    ) => {
      if (!image?.complete || image.naturalWidth === 0) return;
      const width = image.naturalWidth * scale;
      const height = image.naturalHeight * scale;
      context.drawImage(
        image,
        worldX * TILE_SIZE - cameraX - width / 2,
        bottomY * TILE_SIZE - cameraY - height,
        width,
        height,
      );
    };

    const drawCharacter = (
      image: HTMLImageElement | undefined,
      config: CharacterConfig,
      point: MapPoint,
      facing: Facing,
      frame: number,
      walking: boolean,
      cameraX: number,
      cameraY: number,
      scale = 2,
    ) => {
      if (!image?.complete || image.naturalWidth === 0) return;
      const source = frameSource(config, facing, frame, walking);
      const width = 32 * scale;
      const height = 32 * scale;
      const destinationX = point.x * TILE_SIZE - cameraX - width / 2;
      const destinationY = point.y * TILE_SIZE - cameraY - height;
      context.save();
      if (source.flip) {
        context.translate(destinationX + width / 2, 0);
        context.scale(-1, 1);
        context.translate(-(destinationX + width / 2), 0);
      }
      context.drawImage(
        image,
        source.sourceX,
        source.sourceY,
        32,
        32,
        destinationX,
        destinationY,
        width,
        height,
      );
      context.restore();
    };

    const drawLabel = (
      label: string,
      point: MapPoint,
      cameraX: number,
      cameraY: number,
      accented: boolean,
    ) => {
      context.font = "700 12px ui-monospace, Consolas, monospace";
      const width = context.measureText(label).width + 18;
      const x = point.x * TILE_SIZE - cameraX - width / 2;
      const y = point.y * TILE_SIZE - cameraY;
      roundedRect(context, x, y, width, 24, 5);
      context.fillStyle = accented
        ? "rgba(91, 55, 25, 0.96)"
        : "rgba(252, 234, 177, 0.93)";
      context.fill();
      context.strokeStyle = accented ? "#ffd66b" : "#7b4b2d";
      context.lineWidth = 2;
      context.stroke();
      context.fillStyle = accented ? "#fff4cf" : "#3d2a20";
      context.textAlign = "center";
      context.fillText(label, point.x * TILE_SIZE - cameraX, y + 16);
    };

    const drawMarker = (
      point: MapPoint,
      cameraX: number,
      cameraY: number,
      now: number,
      color: string,
      arrow: boolean,
    ) => {
      const centerX = point.x * TILE_SIZE - cameraX;
      const footY = point.y * TILE_SIZE - cameraY;
      const pulse = Math.sin(now / 180) * 4;
      context.strokeStyle = color;
      context.lineWidth = 3;
      context.beginPath();
      context.ellipse(
        centerX,
        footY - 5,
        25 + pulse,
        11 + pulse * 0.35,
        0,
        0,
        Math.PI * 2,
      );
      context.stroke();
      if (!arrow) return;
      const arrowY = footY - 74 + Math.sin(now / 150) * 6;
      context.fillStyle = color;
      context.beginPath();
      context.moveTo(centerX, arrowY + 13);
      context.lineTo(centerX - 10, arrowY);
      context.lineTo(centerX + 10, arrowY);
      context.closePath();
      context.fill();
    };

    const drawMinimap = (
      viewWidth: number,
      viewHeight: number,
      guidePoint: MapPoint | null,
    ) => {
      const compact = viewWidth < 760;
      const width = compact ? 112 : 160;
      const height = compact ? 78 : 112;
      const x = viewWidth - width - (compact ? 10 : 18);
      const y = compact ? 64 : 98;
      roundedRect(context, x, y, width, height, 8);
      context.fillStyle = "rgba(255, 235, 180, 0.94)";
      context.fill();
      context.strokeStyle = "#6d4327";
      context.lineWidth = 4;
      context.stroke();
      const inset = compact ? 8 : 10;
      const plot = (point: MapPoint) => ({
        x: x + inset + (point.x / WORLD_COLUMNS) * (width - inset * 2),
        y: y + inset + (point.y / WORLD_ROWS) * (height - inset * 2),
      });
      context.strokeStyle = "rgba(120, 83, 48, 0.55)";
      context.lineWidth = compact ? 1.4 : 2;
      PATH_SEGMENTS.forEach((segment) => {
        const start = plot(segment.from);
        const end = plot(segment.to);
        context.beginPath();
        context.moveTo(start.x, start.y);
        context.lineTo(end.x, end.y);
        context.stroke();
      });
      Object.values(LANDMARKS).forEach((landmark) => {
        const position = plot(landmark.point);
        context.fillStyle = "#76543b";
        context.fillRect(position.x - 1.8, position.y - 1.8, 3.6, 3.6);
      });
      if (guidePoint) {
        const goal = plot(guidePoint);
        context.fillStyle = "#d79922";
        context.beginPath();
        context.arc(goal.x, goal.y, compact ? 4 : 5, 0, Math.PI * 2);
        context.fill();
      }
      const player = plot(playerRef.current);
      context.fillStyle = "#147d79";
      context.beginPath();
      context.arc(player.x, player.y, compact ? 3 : 4, 0, Math.PI * 2);
      context.fill();
      context.fillStyle = "#5d3a26";
      context.font = `800 ${compact ? 7 : 9}px ui-monospace, Consolas, monospace`;
      context.textAlign = "left";
      context.fillText("GREYHAVEN", x + 8, y + height - 6);
    };

    const renderFrame = (timestamp: number) => {
      const ratio = window.devicePixelRatio || 1;
      const viewWidth = canvas.width / ratio;
      const viewHeight = canvas.height / ratio;
      const assets = assetsRef.current;
      const currentSnapshot = snapshotRef.current;
      const now = timestamp;
      const firstFrame = previousTimestampRef.current === null;
      const previous = previousTimestampRef.current ?? timestamp;
      const deltaSeconds = Math.min(0.033, Math.max(0, (timestamp - previous) / 1000));
      previousTimestampRef.current = timestamp;

      const heldDirection = [...keyOrderRef.current]
        .reverse()
        .find((direction) => keysRef.current.has(direction));
      walkingRef.current =
        Boolean(heldDirection) &&
        !movementDisabledRef.current &&
        selectedNpcIdRef.current === null;
      if (walkingRef.current && heldDirection) {
        facingRef.current = heldDirection;
        const amount = PLAYER_SPEED_TILES_PER_SECOND * deltaSeconds;
        const vector: Record<Facing, MapPoint> = {
          down: { x: 0, y: amount },
          left: { x: -amount, y: 0 },
          right: { x: amount, y: 0 },
          up: { x: 0, y: -amount },
        };
        const movement = vector[heldDirection];
        const horizontal = {
          x: playerRef.current.x + movement.x,
          y: playerRef.current.y,
        };
        if (!movementBlocked(horizontal)) playerRef.current.x = horizontal.x;
        const vertical = {
          x: playerRef.current.x,
          y: playerRef.current.y + movement.y,
        };
        if (!movementBlocked(vertical)) playerRef.current.y = vertical.y;
        updateAuthoritativeLocation();
      }

      const targetCameraX = clamp(
        playerRef.current.x * TILE_SIZE - viewWidth / 2,
        0,
        Math.max(0, WORLD_WIDTH - viewWidth),
      );
      const targetCameraY = clamp(
        playerRef.current.y * TILE_SIZE - viewHeight / 2,
        0,
        Math.max(0, WORLD_HEIGHT - viewHeight),
      );
      if (firstFrame) {
        cameraRef.current = { x: targetCameraX, y: targetCameraY };
      } else {
        const cameraEase = 1 - Math.pow(0.001, deltaSeconds);
        cameraRef.current.x +=
          (targetCameraX - cameraRef.current.x) * cameraEase;
        cameraRef.current.y +=
          (targetCameraY - cameraRef.current.y) * cameraEase;
      }
      const cameraX = cameraRef.current.x;
      const cameraY = cameraRef.current.y;
      const screenX = (tileX: number) => tileX * TILE_SIZE - cameraX;
      const screenY = (tileY: number) => tileY * TILE_SIZE - cameraY;

      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.clearRect(0, 0, viewWidth, viewHeight);
      context.imageSmoothingEnabled = false;
      context.fillStyle = "#6ebf58";
      context.fillRect(0, 0, viewWidth, viewHeight);

      const firstColumn = clamp(
        Math.floor(cameraX / TILE_SIZE),
        0,
        WORLD_COLUMNS - 1,
      );
      const lastColumn = clamp(
        Math.ceil((cameraX + viewWidth) / TILE_SIZE),
        0,
        WORLD_COLUMNS - 1,
      );
      const firstRow = clamp(
        Math.floor(cameraY / TILE_SIZE),
        0,
        WORLD_ROWS - 1,
      );
      const lastRow = clamp(
        Math.ceil((cameraY + viewHeight) / TILE_SIZE),
        0,
        WORLD_ROWS - 1,
      );

      for (let y = firstRow; y <= lastRow; y += 1) {
        for (let x = firstColumn; x <= lastColumn; x += 1) {
          const material = terrainMaterialAt(x, y);
          if (material === "water") {
            drawSourceTile(assets.water, 0, 0, screenX(x), screenY(y));
            context.strokeStyle = "rgba(194, 238, 240, 0.38)";
            context.lineWidth = 2;
            const wave = ((now / 40 + x * 11 + y * 7) % 36) - 8;
            context.beginPath();
            context.moveTo(screenX(x) + wave, screenY(y) + 20);
            context.lineTo(screenX(x) + wave + 16, screenY(y) + 20);
            context.stroke();
            continue;
          }
          if (material === "stone") {
            const variant = (x + y) % 3;
            drawSourceTile(
              assets.paths,
              (2 + variant) * 16,
              variant === 1 ? 16 : 0,
              screenX(x),
              screenY(y),
            );
            continue;
          }
          if (material === "wood") {
            drawSourceTile(
              assets.paths,
              ((x + y) % 3 + 2) * 16,
              8 * 16,
              screenX(x),
              screenY(y),
            );
            continue;
          }
          if (material === "dirt") {
            drawSourceTile(
              assets.terrain,
              (5 + ((x + y) % 2)) * 16,
              (9 + ((x * 3 + y) % 2)) * 16,
              screenX(x),
              screenY(y),
            );
          } else {
            drawSourceTile(
              assets.terrain,
              (5 + ((x * 7 + y) % 2)) * 16,
              (1 + ((x + y * 3) % 2)) * 16,
              screenX(x),
              screenY(y),
            );
          }
        }
      }

      // Pixel-art shoreline seam over the irregular northwest harbor.
      context.strokeStyle = "#d9b35c";
      context.lineWidth = 4;
      context.beginPath();
      context.moveTo(screenX(8.65), screenY(0));
      context.lineTo(screenX(8.65), screenY(3));
      context.lineTo(screenX(7.65), screenY(3));
      context.lineTo(screenX(7.65), screenY(4));
      context.lineTo(screenX(4.65), screenY(4));
      context.lineTo(screenX(4.65), screenY(4.45));
      context.stroke();
      context.strokeStyle = "#2f8f69";
      context.lineWidth = 3;
      context.stroke();

      const positions = npcPoints(currentSnapshot);
      const guidePoint = guidedNpcIdRef.current
        ? positions.get(guidedNpcIdRef.current) ?? null
        : null;
      if (guidePoint) {
        drawMarker(guidePoint, cameraX, cameraY, now, "#ffd457", true);
      }
      const selected = selectedTargetRef.current;
      if (
        selected &&
        !(selected.type === "npc" && selected.id === guidedNpcIdRef.current)
      ) {
        drawMarker(selected.point, cameraX, cameraY, now, "#51d6c7", false);
      }

      const renderables: Renderable[] = [];
      BUILDINGS.forEach((building) => {
        renderables.push({
          sortY: building.bottomY * TILE_SIZE,
          draw: () => {
            const image = assets[building.asset];
            if (image?.naturalWidth) {
              const width = image.naturalWidth * building.scale;
              context.fillStyle = "rgba(68, 47, 31, 0.22)";
              context.beginPath();
              context.ellipse(
                building.x * TILE_SIZE - cameraX,
                building.bottomY * TILE_SIZE - cameraY - 5,
                width * 0.42,
                15,
                0,
                0,
                Math.PI * 2,
              );
              context.fill();
            }
            drawImageBottomCenter(
              image,
              building.x,
              building.bottomY,
              building.scale,
              cameraX,
              cameraY,
            );
          },
        });
      });
      MARKET_STALLS.forEach((stall) => {
        renderables.push({
          sortY: stall.bottomY * TILE_SIZE,
          draw: () =>
            drawImageBottomCenter(
              assets[stall.asset],
              stall.x,
              stall.bottomY,
              2.2,
              cameraX,
              cameraY,
            ),
        });
      });
      TREE_SCENERY.forEach((tree) => {
        renderables.push({
          sortY: tree.y * TILE_SIZE,
          draw: () =>
            drawImageBottomCenter(
              assets[tree.asset],
              tree.x,
              tree.y,
              tree.scale ?? 1.7,
              cameraX,
              cameraY,
            ),
        });
      });
      PROP_SCENERY.forEach((prop) => {
        renderables.push({
          sortY: prop.bottomY * TILE_SIZE,
          draw: () =>
            drawImageBottomCenter(
              assets[prop.asset],
              prop.x,
              prop.bottomY,
              prop.scale,
              cameraX,
              cameraY,
            ),
        });
      });

      const idleFrame = Math.floor(now / 190) % 4;
      currentSnapshot.npcs
        .filter((npc) => positions.has(npc.id))
        .forEach((npc) => {
          const point = positions.get(npc.id);
          if (!point) return;
          const config =
            CHARACTER_CONFIGS[npc.id] ??
            (npc.id.charCodeAt(0) % 2 === 0
              ? CHARACTER_CONFIGS.pip
              : CHARACTER_CONFIGS.rhea);
          renderables.push({
            sortY: point.y * TILE_SIZE,
            draw: () => {
              drawCharacter(
                assets[config.idle],
                config,
                point,
                "down",
                idleFrame % config.idleFrames,
                false,
                cameraX,
                cameraY,
                PRESENTED_NPC_IDS.has(npc.id) ? 2 : 1.8,
              );
              const guided = npc.id === guidedNpcIdRef.current;
              const nearby =
                distance(playerRef.current, point) <= INTERACTION_DISTANCE;
              if (guided || nearby) {
                drawLabel(
                  guided ? `${npc.name} · current lead` : npc.name,
                  { x: point.x, y: point.y - 1.36 },
                  cameraX,
                  cameraY,
                  guided,
                );
              }
            },
          });
        });

      const playerConfig = CHARACTER_CONFIGS.player;
      const playerFrame = walkingRef.current
        ? Math.floor(now / 120) % playerConfig.walkFrames
        : Math.floor(now / 190) % playerConfig.idleFrames;
      renderables.push({
        sortY: playerRef.current.y * TILE_SIZE,
        draw: () =>
          drawCharacter(
            assets[walkingRef.current ? playerConfig.walk : playerConfig.idle],
            playerConfig,
            playerRef.current,
            facingRef.current,
            playerFrame,
            walkingRef.current,
            cameraX,
            cameraY,
            2.15,
          ),
      });
      renderables.sort((left, right) => left.sortY - right.sortY);
      renderables.forEach((item) => item.draw());

      // The constable crop has a real chimney at source x=14, y=16. Anchor the
      // effect to that cap; the broad inn crop has a roof vent, not a chimney.
      const constableChimney = { x: 19.75, y: 5.6 };
      for (let index = 0; index < 3; index += 1) {
        const life = ((now / 24 + index * 31) % 96) / 96;
        context.fillStyle = `rgba(244, 239, 210, ${0.36 * (1 - life)})`;
        context.fillRect(
          screenX(constableChimney.x + Math.sin(life * Math.PI * 2) * 0.12),
          screenY(constableChimney.y - life * 1.25),
          5 + index,
          5 + index,
        );
      }
      Object.values(LANDMARKS).forEach((landmark) => {
        const isGuideLocation =
          guidedNpcIdRef.current != null &&
          LANDMARK_RESIDENTS[landmark.id] === guidedNpcIdRef.current;
        const near = distance(playerRef.current, landmark.point) < 4.4;
        if (near || isGuideLocation || landmark.id === "square") {
          drawLabel(
            landmark.mapLabel,
            { x: landmark.point.x, y: landmark.point.y + 0.2 },
            cameraX,
            cameraY,
            isGuideLocation,
          );
        }
      });

      drawMinimap(viewWidth, viewHeight, guidePoint);

      if (currentSnapshot.weather === "rain") {
        context.fillStyle = "rgba(38, 72, 86, 0.19)";
        context.fillRect(0, 0, viewWidth, viewHeight);
        context.strokeStyle = "rgba(224, 244, 246, 0.34)";
        context.lineWidth = 1.2;
        const offset = (now / 14) % 46;
        for (let x = -viewHeight; x < viewWidth + viewHeight; x += 42) {
          context.beginPath();
          context.moveTo(x + offset, 0);
          context.lineTo(x - viewHeight * 0.32 + offset, viewHeight);
          context.stroke();
        }
      }
      if (
        currentSnapshot.phase === "evening" ||
        currentSnapshot.phase === "night"
      ) {
        context.fillStyle =
          currentSnapshot.phase === "night"
            ? "rgba(23, 32, 77, 0.34)"
            : "rgba(103, 65, 91, 0.15)";
        context.fillRect(0, 0, viewWidth, viewHeight);
      }

      frameId = window.requestAnimationFrame(renderFrame);
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    frameId = window.requestAnimationFrame(renderFrame);
    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frameId);
      previousTimestampRef.current = null;
    };
  }, [updateAuthoritativeLocation]);

  useEffect(() => {
    const keyDirection = (key: string): Facing | null => {
      const normalized = key.toLowerCase();
      if (normalized === "arrowup" || normalized === "w") return "up";
      if (normalized === "arrowdown" || normalized === "s") return "down";
      if (normalized === "arrowleft" || normalized === "a") return "left";
      if (normalized === "arrowright" || normalized === "d") return "right";
      return null;
    };
    const onKeyDown = (event: KeyboardEvent) => {
      const normalized = event.key.toLowerCase();
      if (normalized === "t" || normalized === "enter" || normalized === " ") {
        interact();
        event.preventDefault();
        return;
      }
      const direction = keyDirection(event.key);
      if (!direction) return;
      keysRef.current.add(direction);
      keyOrderRef.current = [
        ...keyOrderRef.current.filter((item) => item !== direction),
        direction,
      ];
      facingRef.current = direction;
      event.preventDefault();
    };
    const onKeyUp = (event: KeyboardEvent) => {
      const direction = keyDirection(event.key);
      if (!direction) return;
      keysRef.current.delete(direction);
      event.preventDefault();
    };
    const clearKeys = () => {
      keysRef.current.clear();
      keyOrderRef.current = [];
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    window.addEventListener("blur", clearKeys);
    canvasRef.current?.focus();
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("blur", clearKeys);
    };
  }, [interact]);

  useEffect(() => {
    const interval = window.setInterval(refreshNearbyTarget, 120);
    refreshNearbyTarget();
    return () => window.clearInterval(interval);
  }, [refreshNearbyTarget, snapshot]);

  useEffect(() => {
    if (!selectedNpcId && !selectedLandmarkId) canvasRef.current?.focus();
  }, [selectedLandmarkId, selectedNpcId]);

  const onCanvasClick = (event: ReactMouseEvent<HTMLCanvasElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const point = {
      x:
        (event.clientX - bounds.left + cameraRef.current.x) /
        TILE_SIZE,
      y:
        (event.clientY - bounds.top + cameraRef.current.y) /
        TILE_SIZE,
    };
    const positions = npcPoints(snapshotRef.current);
    const npcCandidate = snapshotRef.current.npcs
      .filter((npc) => positions.has(npc.id))
      .map((npc) => ({
        id: npc.id,
        label: npc.name,
        point: positions.get(npc.id) ?? point,
        type: "npc" as const,
      }))
      .sort(
        (left, right) => distance(point, left.point) - distance(point, right.point),
      )[0];
    const landmarkCandidate = Object.values(LANDMARKS)
      .map((landmark) => ({
        id: landmark.id,
        label: landmark.label,
        point: landmark.point,
        type: "landmark" as const,
      }))
      .sort(
        (left, right) => distance(point, left.point) - distance(point, right.point),
      )[0];
    const clicked =
      npcCandidate && distance(point, npcCandidate.point) <= 0.85
        ? npcCandidate
        : landmarkCandidate && distance(point, landmarkCandidate.point) <= 3.15
          ? landmarkCandidate
          : null;
    if (!clicked) {
      selectedTargetRef.current = null;
      setSelectedTarget(null);
      setSelectedTargetIsNear(false);
      return;
    }
    selectedTargetRef.current = clicked;
    setSelectedTarget(clicked);
    const clickedIsNear =
      distance(playerRef.current, clicked.point) <= INTERACTION_DISTANCE;
    setSelectedTargetIsNear(clickedIsNear);
    if (clickedIsNear) {
      activateTarget(clicked);
    }
  };

  const promptTarget = nearbyTarget ?? selectedTarget;
  const promptIsNear = nearbyTarget !== null || selectedTargetIsNear;
  const latestEcho = snapshot.npcs
    .flatMap((listener) =>
      listener.recent_echoes.map((echo) => ({ echo, listener })),
    )
    .sort((left, right) => right.echo.hop - left.echo.hop)[0];

  return (
    <div className="playable-town">
      <canvas
        ref={canvasRef}
        className="playable-town__canvas"
        aria-label="Playable town of Greyhaven"
        onClick={onCanvasClick}
        tabIndex={0}
      />
      {assetProgress < 1 ? (
        <div className="world-loading" role="status">
          Painting Greyhaven… {Math.round(assetProgress * 100)}%
        </div>
      ) : null}
      {latestEcho ? (
        <aside className="world-bark" aria-label="Visible gossip">
          <small>
            {latestEcho.echo.speaker_name ?? latestEcho.echo.speaker_id} →{" "}
            {latestEcho.listener.name} · hop {latestEcho.echo.hop}
          </small>
          <p>{latestEcho.echo.text}</p>
        </aside>
      ) : null}
      {snapshot.status === "completed" ? null : promptTarget ? (
        <button
          className="world-interact"
          disabled={movementDisabled || !promptIsNear}
          onClick={interact}
          type="button"
        >
          <kbd>{promptIsNear ? "T" : "WASD"}</kbd>
          {promptIsNear
            ? promptTarget.type === "npc"
              ? `Talk to ${promptTarget.label}`
              : LANDMARKS[promptTarget.id as LandmarkId].prompt
            : `Walk closer to ${promptTarget.label}`}
        </button>
      ) : (
        <div className="world-interact world-interact--hint">
          <kbd>WASD</kbd>
          Explore Greyhaven · click or press T nearby
        </div>
      )}
      <nav className="landmark-access" aria-label="Greyhaven landmarks">
        {Object.values(LANDMARKS).map((landmark) => (
          <button
            key={landmark.id}
            onClick={() => {
              const target: InteractionTarget = {
                id: landmark.id,
                label: landmark.label,
                point: landmark.point,
                type: "landmark",
              };
              selectedTargetRef.current = target;
              setSelectedTarget(target);
              setSelectedTargetIsNear(
                distance(playerRef.current, target.point) <=
                  INTERACTION_DISTANCE,
              );
            }}
            type="button"
          >
            Locate {landmark.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
