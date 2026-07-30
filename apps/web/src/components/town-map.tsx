"use client";

import { useEffect, useMemo, type CSSProperties } from "react";

import type { NpcState, RunSnapshot } from "@/lib/api";
import { releaseTierForNpc } from "@/lib/release-profile";

interface TownMapProps {
  snapshot: RunSnapshot;
  selectedNpcId: string | null;
  movementDisabled: boolean;
  onMove: (locationId: string) => void;
  onNpcClick: (npc: NpcState) => void;
}

interface MapPoint {
  x: number;
  y: number;
}

const MAP_BOUNDS = {
  minX: -12,
  maxX: 12,
  minZ: -10,
  maxZ: 14,
} as const;

const MOVEMENT_KEYS: Record<string, MapPoint> = {
  ArrowDown: { x: 0, y: 1 },
  ArrowLeft: { x: -1, y: 0 },
  ArrowRight: { x: 1, y: 0 },
  ArrowUp: { x: 0, y: -1 },
  a: { x: -1, y: 0 },
  d: { x: 1, y: 0 },
  s: { x: 0, y: 1 },
  w: { x: 0, y: -1 },
} as const;

function mapPoint(location: RunSnapshot["locations"][number]): MapPoint {
  const [x, , z] = location.position;
  return {
    x: ((x - MAP_BOUNDS.minX) / (MAP_BOUNDS.maxX - MAP_BOUNDS.minX)) * 100,
    y: ((z - MAP_BOUNDS.minZ) / (MAP_BOUNDS.maxZ - MAP_BOUNDS.minZ)) * 100,
  };
}

function residentInitials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function directionalNeighbor(
  current: RunSnapshot["locations"][number],
  locations: Map<string, RunSnapshot["locations"][number]>,
  direction: MapPoint,
) {
  const [currentX, , currentZ] = current.position;

  return current.neighbors
    .map((id) => locations.get(id))
    .filter((location) => location !== undefined)
    .map((location) => {
      const [x, , z] = location.position;
      const deltaX = x - currentX;
      const deltaZ = z - currentZ;
      const distance = Math.hypot(deltaX, deltaZ) || 1;
      return {
        location,
        score: (deltaX / distance) * direction.x + (deltaZ / distance) * direction.y,
      };
    })
    .filter(({ score }) => score > 0.25)
    .sort((left, right) => right.score - left.score)[0]?.location;
}

function eventLabel(snapshot: RunSnapshot, locationId: string) {
  const event = snapshot.town_events.find((item) => item.status === "active");
  if (!event) return null;
  if (event.key === "storm" && locationId === "inn") return "Storm shelter";
  if (event.key === "market_day" && locationId === "market") return "Market Day";
  if (event.key === "public_argument" && locationId === "square") {
    return "Public argument";
  }
  return null;
}

export function TownMap({
  snapshot,
  selectedNpcId,
  movementDisabled,
  onMove,
  onNpcClick,
}: TownMapProps) {
  const locations = useMemo(
    () => new Map(snapshot.locations.map((location) => [location.id, location])),
    [snapshot.locations],
  );
  const currentLocation = locations.get(snapshot.player.location_id);
  const reachableLocations = useMemo(
    () => new Set(currentLocation?.neighbors ?? []),
    [currentLocation],
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
      const direction = MOVEMENT_KEYS[key];
      const target = event.target;
      if (
        !direction ||
        !currentLocation ||
        movementDisabled ||
        target instanceof HTMLButtonElement ||
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement
      ) {
        return;
      }

      const destination = directionalNeighbor(currentLocation, locations, direction);
      if (!destination) return;
      event.preventDefault();
      onMove(destination.id);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [currentLocation, locations, movementDisabled, onMove]);

  if (!currentLocation) return null;

  const currentPoint = mapPoint(currentLocation);

  return (
    <div
      className="town-map"
      data-weather={snapshot.weather}
      aria-label="Map of Greyhaven"
    >
      <div className="town-map__water" aria-hidden="true" />
      <div className="town-map__shore" aria-hidden="true" />

      <svg
        className="town-map__routes"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {snapshot.locations.flatMap((location) => {
          const start = mapPoint(location);
          return location.neighbors
            .filter((neighborId) => location.id < neighborId)
            .map((neighborId) => {
              const neighbor = locations.get(neighborId);
              if (!neighbor) return null;
              const end = mapPoint(neighbor);
              return (
                <line
                  key={`${location.id}-${neighborId}`}
                  x1={start.x}
                  y1={start.y}
                  x2={end.x}
                  y2={end.y}
                />
              );
            });
        })}
      </svg>

      {snapshot.locations.map((location) => {
        const point = mapPoint(location);
        const current = location.id === currentLocation.id;
        const reachable = reachableLocations.has(location.id);
        const label = eventLabel(snapshot, location.id);

        return (
          <button
            className="town-map__location"
            data-current={current}
            data-reachable={reachable}
            disabled={movementDisabled || current || !reachable}
            key={location.id}
            onClick={() => onMove(location.id)}
            style={{ left: `${point.x}%`, top: `${point.y}%` }}
            type="button"
          >
            <span className="town-map__location-mark" aria-hidden="true" />
            <strong>{location.name}</strong>
            {label ? <small>{label}</small> : null}
          </button>
        );
      })}

      {snapshot.npcs.map((npc) => {
        const location = locations.get(npc.location_id);
        if (!location) return null;
        const releaseTier = releaseTierForNpc(npc.id);
        const point = mapPoint(location);
        const peers = snapshot.npcs.filter(
          (resident) => resident.location_id === npc.location_id,
        );
        const peerIndex = peers.findIndex((resident) => resident.id === npc.id);
        const column = (peerIndex % 3) - 1;
        const row = Math.floor(peerIndex / 3) % 3;
        const style = {
          "--npc-color": npc.color,
          left: `${point.x}%`,
          top: `${point.y}%`,
          transform: `translate(calc(-50% + ${column * 26}px), calc(-50% + ${36 + row * 24}px))`,
        } as CSSProperties;

        return (
          <button
            aria-label={`${npc.name}, ${npc.role}`}
            className="town-map__resident"
            data-npc-id={npc.id}
            data-release-tier={releaseTier}
            data-selected={npc.id === selectedNpcId}
            data-speaking={Boolean(npc.speech)}
            disabled={movementDisabled}
            key={npc.id}
            onClick={() => onNpcClick(npc)}
            style={style}
            title={npc.speech ?? `${npc.name} — ${npc.role}`}
            type="button"
          >
            {npc.id === "talia" ? null : residentInitials(npc.name)}
          </button>
        );
      })}

      <span
        className="town-map__player"
        style={{ left: `${currentPoint.x}%`, top: `${currentPoint.y}%` }}
        aria-label={`The Newcomer at ${currentLocation.name}`}
        role="img"
      />

      {snapshot.weather === "rain" ? (
        <div className="town-map__rain" aria-hidden="true" />
      ) : null}
    </div>
  );
}
