"use client";

import { Html, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useMemo } from "react";

import type { NpcState, RunSnapshot } from "@/lib/api";

interface TownSceneProps {
  snapshot: RunSnapshot;
  onNpcClick: (npc: NpcState) => void;
}

const BUILDINGS: Array<{
  location: string;
  color: string;
  scale: [number, number, number];
}> = [
  { location: "inn", color: "#8d5f45", scale: [3.7, 2.8, 3] },
  { location: "market", color: "#a0784e", scale: [3.5, 1.6, 2.2] },
  { location: "guildhouse", color: "#76644f", scale: [3.2, 3.2, 2.8] },
  { location: "constable", color: "#53636a", scale: [2.4, 2.5, 2.4] },
  { location: "chapel", color: "#78746d", scale: [3, 4.2, 3] },
  { location: "midwife", color: "#7a634e", scale: [2.6, 2.2, 2.5] },
];

function Resident({
  npc,
  position,
  onClick,
}: {
  npc: NpcState;
  position: [number, number, number];
  onClick: () => void;
}) {
  return (
    <group position={[position[0], 0.9, position[2]]} onClick={onClick}>
      <mesh castShadow>
        <capsuleGeometry args={[0.28, 0.68, 6, 10]} />
        <meshStandardMaterial color={npc.color} roughness={0.78} />
      </mesh>
      <mesh position={[0, 0.74, 0]} castShadow>
        <sphereGeometry args={[0.27, 16, 16]} />
        <meshStandardMaterial color="#d6a77f" roughness={0.85} />
      </mesh>
      {npc.speech ? (
        <Html position={[0, 1.6, 0]} center distanceFactor={10}>
          <button className="speech-bubble" type="button" onClick={onClick}>
            {npc.speech}
          </button>
        </Html>
      ) : null}
    </group>
  );
}

function Scene({ snapshot, onNpcClick }: TownSceneProps) {
  const locations = useMemo(
    () => new Map(snapshot.locations.map((location) => [location.id, location])),
    [snapshot.locations],
  );
  const playerLocation = locations.get(snapshot.player.location_id);
  const evening = snapshot.phase === "evening" || snapshot.phase === "night";

  return (
    <>
      <color attach="background" args={[evening ? "#25313a" : "#9fc1bc"]} />
      <fog attach="fog" args={[evening ? "#25313a" : "#9fc1bc", 14, 36]} />
      <ambientLight intensity={evening ? 0.5 : 1.2} />
      <directionalLight
        castShadow
        intensity={evening ? 1.1 : 2.2}
        color={evening ? "#ffc886" : "#fff1c7"}
        position={[8, 13, 5]}
        shadow-mapSize={[1024, 1024]}
      />

      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[24, 64]} />
        <meshStandardMaterial color="#667f56" roughness={1} />
      </mesh>
      <mesh position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[4.2, 32]} />
        <meshStandardMaterial color="#9b8b70" roughness={1} />
      </mesh>

      {BUILDINGS.map((building) => {
        const location = locations.get(building.location);
        if (!location) return null;
        return (
          <mesh
            key={building.location}
            castShadow
            receiveShadow
            position={[
              location.position[0],
              building.scale[1] / 2,
              location.position[2],
            ]}
            scale={building.scale}
          >
            <boxGeometry />
            <meshStandardMaterial color={building.color} roughness={0.92} />
          </mesh>
        );
      })}

      <group position={[-9, 0.2, -8]}>
        <mesh receiveShadow>
          <boxGeometry args={[7, 0.35, 3.5]} />
          <meshStandardMaterial color="#6b4d35" roughness={1} />
        </mesh>
        <mesh position={[0, -0.3, -3]}>
          <boxGeometry args={[12, 0.25, 5]} />
          <meshStandardMaterial color="#325e69" roughness={0.4} />
        </mesh>
      </group>

      {snapshot.npcs.map((npc) => {
        const location = locations.get(npc.location_id);
        if (!location) return null;
        const offset = npc.id.charCodeAt(0) % 3;
        return (
          <Resident
            key={npc.id}
            npc={npc}
            position={[
              location.position[0] + offset * 0.45,
              0,
              location.position[2] + offset * 0.3,
            ]}
            onClick={() => onNpcClick(npc)}
          />
        );
      })}

      {playerLocation ? (
        <group
          position={[
            playerLocation.position[0],
            0.65,
            playerLocation.position[2] + 1,
          ]}
        >
          <mesh castShadow>
            <capsuleGeometry args={[0.32, 0.75, 6, 10]} />
            <meshStandardMaterial
              color="#e6d6a8"
              emissive="#94713c"
              emissiveIntensity={0.12}
            />
          </mesh>
          <pointLight color="#ffd28c" intensity={2} distance={3} />
        </group>
      ) : null}

      <OrbitControls
        makeDefault
        target={[0, 0, 0]}
        minDistance={9}
        maxDistance={28}
        maxPolarAngle={Math.PI / 2.12}
      />
    </>
  );
}

export function TownScene(props: TownSceneProps) {
  return (
    <Canvas
      shadows
      camera={{ position: [14, 15, 18], fov: 44 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true }}
    >
      <Scene {...props} />
    </Canvas>
  );
}
