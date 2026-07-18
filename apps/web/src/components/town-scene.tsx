"use client";

import {
  Clone,
  Html,
  OrbitControls,
  useAnimations,
  useGLTF,
} from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import * as THREE from "three";

import type { NpcState, RunSnapshot } from "@/lib/api";

interface TownSceneProps {
  snapshot: RunSnapshot;
  selectedNpcId: string | null;
  movementDisabled: boolean;
  onMove: (locationId: string) => void;
  onNpcClick: (npc: NpcState) => void;
}

const ASSETS = {
  animation: "/assets/animations/character-actions.glb",
  barrel: "/assets/models/dock-barrel.glb",
  bram: "/assets/characters/bram.glb",
  dock: "/assets/models/greyhaven-dock.glb",
  fishBucket: "/assets/models/dock-fish-bucket.glb",
  house: "/assets/models/greyhaven-house.glb",
  inn: "/assets/models/greyhaven-inn.glb",
  marta: "/assets/characters/marta.glb",
  player: "/assets/characters/player.glb",
  rhea: "/assets/characters/rhea.glb",
  stall: "/assets/models/market-stall.glb",
  tree: "/assets/models/common-tree.glb",
  wagon: "/assets/models/village-wagon.glb",
} as const;

const NPC_ASSET: Record<string, string> = {
  bram: ASSETS.bram,
  elias: ASSETS.bram,
  marta: ASSETS.marta,
  nessa: ASSETS.marta,
  orin: ASSETS.bram,
  pip: ASSETS.player,
  rhea: ASSETS.rhea,
  talia: ASSETS.rhea,
};

interface SceneAssetProps {
  path: string;
  position: [number, number, number];
  rotation?: [number, number, number];
  scale: number | [number, number, number];
}

function SceneAsset({
  path,
  position,
  rotation = [0, 0, 0],
  scale,
}: SceneAssetProps) {
  const { scene } = useGLTF(path);
  return (
    <Clone
      object={scene}
      position={position}
      rotation={rotation}
      scale={scale}
      castShadow
      receiveShadow
    />
  );
}

function useCharacterAnimation(
  root: React.RefObject<THREE.Group | null>,
  animationName: string,
) {
  const { animations } = useGLTF(ASSETS.animation);
  const { actions } = useAnimations(animations, root);

  useEffect(() => {
    const action = actions[animationName] ?? actions.Idle_Loop;
    action?.reset().fadeIn(0.25).play();
    return () => {
      action?.fadeOut(0.2);
    };
  }, [actions, animationName]);
}

function AnimatedResident({
  npc,
  position,
  onClick,
}: {
  npc: NpcState;
  position: [number, number, number];
  onClick: () => void;
}) {
  const group = useRef<THREE.Group>(null);
  const [hovered, setHovered] = useState(false);
  const { scene } = useGLTF(NPC_ASSET[npc.id] ?? ASSETS.marta);
  useCharacterAnimation(
    group,
    npc.speech ? "Idle_Talking_Loop" : "Idle_Loop",
  );

  useEffect(() => {
    document.body.style.cursor = hovered ? "pointer" : "";
    return () => {
      document.body.style.cursor = "";
    };
  }, [hovered]);

  return (
    <group
      ref={group}
      position={[position[0], 0.86, position[2]]}
      scale={hovered ? 0.92 : 0.84}
      onClick={(event) => {
        event.stopPropagation();
        onClick();
      }}
      onPointerOver={(event) => {
        event.stopPropagation();
        setHovered(true);
      }}
      onPointerOut={() => setHovered(false)}
    >
      <Clone object={scene} castShadow receiveShadow />
      {npc.speech && hovered ? (
        <Html position={[0, 1.75, 0]} center distanceFactor={10}>
          <button className="speech-bubble" type="button" onClick={onClick}>
            {npc.speech}
          </button>
        </Html>
      ) : null}
      {hovered ? (
        <Html position={[0, 1.28, 0]} center distanceFactor={14}>
          <span className="resident-name">{npc.name}</span>
        </Html>
      ) : null}
    </group>
  );
}

function PlayerCharacter({
  target,
}: {
  target: [number, number, number];
}) {
  const group = useRef<THREE.Group>(null);
  const { scene } = useGLTF(ASSETS.player);
  const [initialPosition] = useState(
    () => new THREE.Vector3(target[0], 0.86, target[2] + 0.7),
  );
  const destination = useMemo(
    () => new THREE.Vector3(target[0], 0.86, target[2] + 0.7),
    [target],
  );
  const [walking, setWalking] = useState(false);
  useCharacterAnimation(group, walking ? "Walk_Loop" : "Idle_Loop");

  useFrame((_, delta) => {
    if (!group.current) return;
    const distance = group.current.position.distanceTo(destination);
    setWalking(distance > 0.08);
    group.current.position.lerp(
      destination,
      1 - Math.exp(-Math.min(delta, 0.1) * 4.5),
    );
  });

  return (
    <group ref={group} position={initialPosition} scale={0.86}>
      <Clone object={scene} castShadow receiveShadow />
      <pointLight
        position={[0, 1.4, 0]}
        color="#ffd28c"
        intensity={1.4}
        distance={2.5}
      />
    </group>
  );
}

function Rain() {
  const points = useRef<THREE.Points>(null);
  const positions = useMemo(() => {
    const values = new Float32Array(900 * 3);
    let seed = 1729;
    const random = () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed / 0xffffffff;
    };
    for (let index = 0; index < values.length; index += 3) {
      values[index] = random() * 36 - 18;
      values[index + 1] = random() * 16 + 2;
      values[index + 2] = random() * 36 - 18;
    }
    return values;
  }, []);

  useFrame((state, delta) => {
    const geometry = points.current?.geometry;
    const attribute = geometry?.getAttribute("position");
    if (!(attribute instanceof THREE.BufferAttribute)) return;
    const positionArray = attribute.array;
    for (let index = 1; index < positionArray.length; index += 3) {
      positionArray[index] -= delta * 13;
      if (positionArray[index] < 0.15) {
        positionArray[index] = 17;
      }
    }
    attribute.needsUpdate = true;
    if (points.current) {
      points.current.rotation.y = state.clock.elapsedTime * 0.008;
    }
  });

  return (
    <>
      <points ref={points}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        </bufferGeometry>
        <pointsMaterial
          color="#b9d7df"
          size={0.045}
          transparent
          opacity={0.72}
          depthWrite={false}
        />
      </points>
      <StormFlash />
    </>
  );
}

function StormFlash() {
  const light = useRef<THREE.PointLight>(null);
  useFrame((state) => {
    if (!light.current) return;
    const cycle = state.clock.elapsedTime % 9;
    light.current.intensity =
      cycle > 7.7 && cycle < 7.82 ? 32 : cycle > 7.9 && cycle < 7.96 ? 18 : 0;
  });
  return (
    <pointLight
      ref={light}
      position={[0, 13, -4]}
      color="#dcecff"
      distance={38}
      decay={1.2}
    />
  );
}

function ProxyTown() {
  return (
    <group>
      {[
        [-7, 1.4, 1],
        [6, 1.2, 1],
        [-5, 1.5, -5],
        [8, 1.7, -7],
      ].map((position, index) => (
        <mesh
          key={index}
          position={position as [number, number, number]}
          castShadow
        >
          <boxGeometry args={[2.8, 2.8, 2.6]} />
          <meshStandardMaterial color="#655b4b" roughness={1} />
        </mesh>
      ))}
    </group>
  );
}

function WorldAssets() {
  return (
    <>
      <SceneAsset
        path={ASSETS.inn}
        position={[-7, 0, 1]}
        rotation={[0, 0.22, 0]}
        scale={0.42}
      />
      {[
        { position: [-5, 0, -5], rotation: 0.5, scale: 0.58 },
        { position: [8, 0, -7], rotation: -0.7, scale: 0.52 },
        { position: [5, 0, -5], rotation: 0.2, scale: 0.4 },
        { position: [10, 0, 5], rotation: -1.1, scale: 0.42 },
      ].map((building, index) => (
        <SceneAsset
          key={index}
          path={ASSETS.house}
          position={building.position as [number, number, number]}
          rotation={[0, building.rotation, 0]}
          scale={building.scale}
        />
      ))}
      <SceneAsset
        path={ASSETS.stall}
        position={[6, 0, 1]}
        rotation={[0, -0.35, 0]}
        scale={0.54}
      />
      <SceneAsset
        path={ASSETS.wagon}
        position={[3.8, 0, 3.1]}
        rotation={[0, 0.8, 0]}
        scale={0.65}
      />
      <SceneAsset
        path={ASSETS.dock}
        position={[-9, 0.08, -8]}
        rotation={[0, Math.PI / 2, 0]}
        scale={1.35}
      />
      <SceneAsset
        path={ASSETS.barrel}
        position={[-7.7, 0.05, -7.1]}
        scale={0.8}
      />
      <SceneAsset
        path={ASSETS.fishBucket}
        position={[-9.7, 0.05, -7.2]}
        scale={0.8}
      />
      {[
        [-12, 0, 2],
        [-10, 0, 8],
        [12, 0, 9],
        [11, 0, -10],
        [-13, 0, -6],
      ].map((position, index) => (
        <SceneAsset
          key={index}
          path={ASSETS.tree}
          position={position as [number, number, number]}
          rotation={[0, index * 0.9, 0]}
          scale={0.62 + (index % 2) * 0.08}
        />
      ))}
    </>
  );
}

function CameraRig({
  controls,
  playerPosition,
  focusPosition,
}: {
  controls: React.RefObject<React.ComponentRef<typeof OrbitControls> | null>;
  playerPosition: [number, number, number];
  focusPosition: [number, number, number] | null;
}) {
  const { camera } = useThree();
  const target = useMemo(
    () =>
      new THREE.Vector3(
        ...(focusPosition ?? playerPosition),
      ).add(new THREE.Vector3(0, focusPosition ? 1.1 : 0.6, 0)),
    [focusPosition, playerPosition],
  );

  useFrame((_, delta) => {
    if (!controls.current) return;
    const strength = 1 - Math.exp(-Math.min(delta, 0.1) * 4);
    controls.current.target.lerp(target, strength);
    if (focusPosition) {
      const desired = target
        .clone()
        .add(new THREE.Vector3(4.2, 3.1, 4.8));
      camera.position.lerp(desired, strength * 0.7);
    }
    controls.current.update();
  });
  return null;
}

function Scene({
  snapshot,
  selectedNpcId,
  movementDisabled,
  onMove,
  onNpcClick,
}: TownSceneProps) {
  const controls = useRef<React.ComponentRef<typeof OrbitControls>>(null);
  const locations = useMemo(
    () => new Map(snapshot.locations.map((location) => [location.id, location])),
    [snapshot.locations],
  );
  const playerLocation = locations.get(snapshot.player.location_id);
  const evening = snapshot.phase === "evening" || snapshot.phase === "night";
  const raining = snapshot.weather === "rain";
  const selectedNpc = snapshot.npcs.find((npc) => npc.id === selectedNpcId);
  const focusLocation = selectedNpc
    ? locations.get(selectedNpc.location_id)
    : undefined;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (
        movementDisabled ||
        event.repeat ||
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      ) {
        return;
      }
      const directions: Record<string, [number, number]> = {
        ArrowDown: [0, 1],
        ArrowLeft: [-1, 0],
        ArrowRight: [1, 0],
        ArrowUp: [0, -1],
        a: [-1, 0],
        d: [1, 0],
        s: [0, 1],
        w: [0, -1],
      };
      const direction = directions[event.key];
      if (!direction || !playerLocation) return;
      const candidates = playerLocation.neighbors
        .map((id) => locations.get(id))
        .filter((location) => location !== undefined)
        .map((location) => {
          const dx = location.position[0] - playerLocation.position[0];
          const dz = location.position[2] - playerLocation.position[2];
          const length = Math.hypot(dx, dz) || 1;
          return {
            id: location.id,
            score: (dx / length) * direction[0] + (dz / length) * direction[1],
          };
        })
        .filter((candidate) => candidate.score > 0.15)
        .sort((left, right) => right.score - left.score);
      if (candidates[0]) {
        event.preventDefault();
        onMove(candidates[0].id);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [locations, movementDisabled, onMove, playerLocation]);

  if (!playerLocation) return null;

  return (
    <>
      <color
        attach="background"
        args={[raining ? "#35444b" : evening ? "#25313a" : "#9fc1bc"]}
      />
      <fog
        attach="fog"
        args={[raining ? "#536269" : evening ? "#25313a" : "#9fc1bc", 13, 38]}
      />
      <ambientLight intensity={raining ? 0.45 : evening ? 0.5 : 1.15} />
      <directionalLight
        castShadow
        intensity={raining ? 0.7 : evening ? 1.1 : 2.1}
        color={evening ? "#ffc886" : "#fff1c7"}
        position={[8, 13, 5]}
        shadow-mapSize={[1024, 1024]}
      />

      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[24, 64]} />
        <meshStandardMaterial
          color={raining ? "#4f6652" : "#667f56"}
          roughness={raining ? 0.74 : 1}
        />
      </mesh>
      <mesh
        position={[0, 0.03, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        receiveShadow
      >
        <circleGeometry args={[4.2, 32]} />
        <meshStandardMaterial color="#9b8b70" roughness={0.9} />
      </mesh>
      <mesh position={[0, 0.035, 7]} receiveShadow>
        <boxGeometry args={[2.5, 0.07, 14]} />
        <meshStandardMaterial color="#927e61" roughness={1} />
      </mesh>
      <mesh
        position={[-9, -0.18, -11]}
        rotation={[-Math.PI / 2, 0, 0]}
        receiveShadow
      >
        <planeGeometry args={[15, 9]} />
        <meshStandardMaterial
          color="#315c68"
          roughness={0.28}
          metalness={0.08}
        />
      </mesh>

      <Suspense fallback={<ProxyTown />}>
        <WorldAssets />
        {snapshot.npcs.map((npc) => {
          const location = locations.get(npc.location_id);
          if (!location) return null;
          const offset = npc.id.charCodeAt(0) % 3;
          return (
            <AnimatedResident
              key={npc.id}
              npc={npc}
              position={[
                location.position[0] + offset * 0.5,
                0,
                location.position[2] + offset * 0.34,
              ]}
              onClick={() => onNpcClick(npc)}
            />
          );
        })}
        <PlayerCharacter target={playerLocation.position} />
      </Suspense>

      {raining ? <Rain /> : null}
      <CameraRig
        controls={controls}
        playerPosition={playerLocation.position}
        focusPosition={focusLocation?.position ?? null}
      />
      <OrbitControls
        ref={controls}
        makeDefault
        target={[playerLocation.position[0], 0.6, playerLocation.position[2]]}
        minDistance={6}
        maxDistance={28}
        maxPolarAngle={Math.PI / 2.12}
        enableDamping
      />
    </>
  );
}

export function TownScene(props: TownSceneProps) {
  return (
    <Canvas
      shadows
      camera={{ position: [10, 9, 18], fov: 42 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true }}
    >
      <Scene {...props} />
    </Canvas>
  );
}

Object.values(ASSETS).forEach((path) => {
  if (path.endsWith(".glb")) useGLTF.preload(path);
});
