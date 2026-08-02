"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  LANDMARKS,
  LANDMARK_RESIDENTS,
  PRESENTED_NPC_IDS,
  type LandmarkId,
} from "@/components/greyhaven-map";
import { PlayableTown } from "@/components/playable-town";
import { TownMap } from "@/components/town-map";
import {
  clockLabel,
  createRun,
  loadRun,
  takeAction,
  traceRumorWithHistorian,
  type ActionVerb,
  type HistorianTrace,
  type NpcState,
  type ReleaseProfile,
  type RunSnapshot,
} from "@/lib/api";
import {
  isAutonomousEvent,
  releaseTierForNpc,
} from "@/lib/release-profile";

const LEGACY_RUN_STORAGE_KEY = "hearsay.run-id";
const RUN_STORAGE_KEYS: Record<ReleaseProfile, string> = {
  full: "hearsay.run-id.full",
  hackathon_small: "hearsay.run-id.playable-town",
};
type GuidedStage =
  | "bram_approach"
  | "campaign"
  | "declare_candidacy"
  | "election_complete"
  | "final_talk"
  | "marta_promise"
  | "marta_recall"
  | "rhea_question"
  | "rhea_resolve"
  | "settle_shipment"
  | "talia_request"
  | "talia_resolve";

function firstPlaythroughStage(snapshot: RunSnapshot): GuidedStage {
  if (snapshot.election) return "election_complete";
  const martaPromise = snapshot.promises.find(
    (promise) => promise.promisee_id === "marta",
  );
  const taliaFavor = snapshot.favors.find(
    (favor) => favor.key === "talia_sick_house",
  );
  const rheaCompact = snapshot.favors.find(
    (favor) => favor.key === "rhea_ballot_compact",
  );

  if (!martaPromise) return "marta_promise";
  if (!snapshot.player.bram_approach) return "bram_approach";
  if (martaPromise.status === "active") return "settle_shipment";
  if (!taliaFavor) return "talia_request";
  if (taliaFavor.status === "active") return "talia_resolve";
  if (snapshot.day < 2) return "campaign";
  if (!snapshot.player.candidate) return "declare_candidacy";
  if (!rheaCompact) return "rhea_question";
  if (rheaCompact.status === "active") return "rhea_resolve";
  if (snapshot.action_count < snapshot.action_budget - 1) return "campaign";
  return "final_talk";
}

const GUIDED_OBJECTIVES: Record<GuidedStage, string> = {
  bram_approach:
    "Walk north-east to Market Row. Confront Bram under the gold marker.",
  campaign:
    "Build support. Talk to anyone, share claims, and learn what each resident remembers.",
  declare_candidacy:
    "Walk north-west to the Guildhouse. Tell Rhea you are standing for mayor.",
  election_complete: "Election resolved. Open the journal to see why each vote moved.",
  final_talk:
    "Speak to Rhea once more. Election night will resolve every remembered choice.",
  marta_promise:
    "Marta has stopped you on the road. Promise to free the inn's shipment.",
  marta_recall:
    "Return west to the Gull & Anchor. Let Marta tell you what she remembers.",
  rhea_question:
    "Stay with Rhea. Ask who controls the ballot box before election night.",
  rhea_resolve:
    "Choose: demand a witnessed public count, or accept Rhea's private compact.",
  settle_shipment:
    "Bram named his price. Pay now to keep your promise before evening.",
  talia_request:
    "Follow the gold marker to Talia. Ask who in Greyhaven needs help.",
  talia_resolve:
    "Choose whether to protect Oswin's privacy or turn his illness into public warning.",
};

const GUIDED_NPCS: Record<GuidedStage, string | null> = {
  bram_approach: "bram",
  campaign: null,
  declare_candidacy: "rhea",
  election_complete: null,
  final_talk: "rhea",
  marta_promise: "marta",
  marta_recall: "marta",
  rhea_question: "rhea",
  rhea_resolve: "rhea",
  settle_shipment: "bram",
  talia_request: "talia",
  talia_resolve: "talia",
};

function firstPlaythroughObjective(snapshot: RunSnapshot) {
  return GUIDED_OBJECTIVES[firstPlaythroughStage(snapshot)];
}

function requestedReleaseProfile(): ReleaseProfile {
  const requestedProfile = new URLSearchParams(window.location.search).get(
    "release_profile",
  );
  return requestedProfile === "full" ? "full" : "hackathon_small";
}

function remainingActionLabel(snapshot: RunSnapshot) {
  const remaining = snapshot.action_budget - snapshot.action_count;
  return `${remaining} consequential ${remaining === 1 ? "action remains" : "actions remain"}`;
}

function agentDecisionProvenance(
  event: RunSnapshot["recent_events"][number],
) {
  const payload = event.payload;
  if (
    event.kind !== "agent_decision" ||
    payload == null ||
    typeof payload.provider_id !== "string" ||
    typeof payload.model_id !== "string"
  ) {
    return null;
  }
  return `${payload.provider_id}/${payload.model_id}${
    payload.fallback_used === true ? " · safe fallback" : ""
  }`;
}

function createAudioContext() {
  const AudioContextClass =
    window.AudioContext ??
    (
      window as typeof window & {
        webkitAudioContext?: typeof AudioContext;
      }
    ).webkitAudioContext;
  return AudioContextClass ? new AudioContextClass() : null;
}

function playConfirmation() {
  const context = createAudioContext();
  if (!context) return;
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(620, context.currentTime);
  oscillator.frequency.exponentialRampToValueAtTime(860, context.currentTime + 0.1);
  gain.gain.setValueAtTime(0.05, context.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.14);
  oscillator.connect(gain).connect(context.destination);
  oscillator.start();
  oscillator.stop(context.currentTime + 0.14);
  oscillator.addEventListener("ended", () => void context.close(), { once: true });
}

function playThunder() {
  const context = createAudioContext();
  if (!context) return;
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = "sawtooth";
  oscillator.frequency.setValueAtTime(58, context.currentTime);
  oscillator.frequency.exponentialRampToValueAtTime(
    24,
    context.currentTime + 1.45,
  );
  gain.gain.setValueAtTime(0.0001, context.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.19, context.currentTime + 0.03);
  gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 1.55);
  oscillator.connect(gain).connect(context.destination);
  oscillator.start();
  oscillator.stop(context.currentTime + 1.6);
  oscillator.addEventListener("ended", () => void context.close(), {
    once: true,
  });
}

function playMarketAmbience() {
  const context = createAudioContext();
  if (!context) return;
  const duration = 3.2;
  const buffer = context.createBuffer(
    1,
    Math.floor(context.sampleRate * duration),
    context.sampleRate,
  );
  const samples = buffer.getChannelData(0);
  let seed = 1729;
  for (let index = 0; index < samples.length; index += 1) {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    samples[index] = (seed / 0xffffffff) * 2 - 1;
  }

  const murmur = context.createBufferSource();
  const filter = context.createBiquadFilter();
  const murmurGain = context.createGain();
  murmur.buffer = buffer;
  filter.type = "bandpass";
  filter.frequency.value = 360;
  filter.Q.value = 0.7;
  murmurGain.gain.setValueAtTime(0.0001, context.currentTime);
  murmurGain.gain.exponentialRampToValueAtTime(
    0.026,
    context.currentTime + 0.18,
  );
  murmurGain.gain.exponentialRampToValueAtTime(
    0.0001,
    context.currentTime + duration,
  );
  murmur.connect(filter).connect(murmurGain).connect(context.destination);

  const bell = context.createOscillator();
  const bellGain = context.createGain();
  bell.type = "triangle";
  bell.frequency.setValueAtTime(740, context.currentTime + 0.12);
  bell.frequency.exponentialRampToValueAtTime(
    510,
    context.currentTime + 0.8,
  );
  bellGain.gain.setValueAtTime(0.0001, context.currentTime);
  bellGain.gain.exponentialRampToValueAtTime(0.06, context.currentTime + 0.13);
  bellGain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 1.1);
  bell.connect(bellGain).connect(context.destination);

  void context.resume().catch(() => void context.close());
  murmur.start();
  bell.start(context.currentTime + 0.12);
  murmur.stop(context.currentTime + duration);
  bell.stop(context.currentTime + 1.1);
  murmur.addEventListener("ended", () => void context.close(), { once: true });
}

export function GameShell() {
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null);
  const [selectedNpc, setSelectedNpc] = useState<NpcState | null>(null);
  const [chatDraft, setChatDraft] = useState("");
  const [shareChatPublicly, setShareChatPublicly] = useState(false);
  const chatThreadRef = useRef<HTMLDivElement>(null);
  const [historian, setHistorian] = useState<HistorianTrace | null>(null);
  const [historianOpen, setHistorianOpen] = useState(false);
  const [journalOpen, setJournalOpen] = useState(false);
  const [selectedLandmarkId, setSelectedLandmarkId] =
    useState<LandmarkId | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const moveInFlightRef = useRef(false);
  const marketDayActive =
    snapshot?.town_events.some(
      (event) => event.key === "market_day" && event.status === "active",
    ) ?? false;

  useEffect(() => {
    const releaseProfile = requestedReleaseProfile();
    const storageKey = RUN_STORAGE_KEYS[releaseProfile];
    const profileRunId = window.localStorage.getItem(storageKey);
    const legacyRunId = window.localStorage.getItem(LEGACY_RUN_STORAGE_KEY);
    const runId = profileRunId ?? legacyRunId;
    if (!runId) {
      const ready = window.setTimeout(() => setBusy(false), 0);
      return () => window.clearTimeout(ready);
    }
    loadRun(runId)
      .then((next) => {
        if (next.release_profile !== releaseProfile) {
          window.localStorage.removeItem(storageKey);
          if (legacyRunId === runId) {
            window.localStorage.removeItem(LEGACY_RUN_STORAGE_KEY);
          }
          return;
        }
        window.localStorage.setItem(storageKey, next.run_id);
        if (legacyRunId === runId) {
          window.localStorage.removeItem(LEGACY_RUN_STORAGE_KEY);
        }
        setSnapshot(next);
      })
      .catch(() => {
        window.localStorage.removeItem(storageKey);
        if (legacyRunId === runId) {
          window.localStorage.removeItem(LEGACY_RUN_STORAGE_KEY);
        }
      })
      .finally(() => setBusy(false));
  }, []);

  useEffect(() => {
    if (!marketDayActive) return;
    const playOnce = () => playMarketAmbience();
    window.addEventListener("pointerdown", playOnce, { once: true });
    return () => window.removeEventListener("pointerdown", playOnce);
  }, [marketDayActive]);

  const begin = useCallback(async () => {
    setBusy(true);
    setError(null);
    setSelectedNpc(null);
    setHistorian(null);
    setHistorianOpen(false);
    setJournalOpen(false);
    setSelectedLandmarkId(null);
    try {
      const releaseProfile = requestedReleaseProfile();
      const next = await createRun("Newcomer", releaseProfile);
      window.localStorage.setItem(
        RUN_STORAGE_KEYS[releaseProfile],
        next.run_id,
      );
      window.localStorage.removeItem(LEGACY_RUN_STORAGE_KEY);
      setSnapshot(next);
      if (releaseProfile === "hackathon_small") {
        setSelectedNpc(next.npcs.find((npc) => npc.id === "marta") ?? null);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Greyhaven did not answer.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    const toggleJournal = (event: KeyboardEvent) => {
      if (
        event.key.toLowerCase() !== "j" ||
        selectedNpc ||
        selectedLandmarkId ||
        historianOpen
      ) {
        return;
      }
      setJournalOpen((open) => !open);
      event.preventDefault();
    };
    window.addEventListener("keydown", toggleJournal);
    return () => window.removeEventListener("keydown", toggleJournal);
  }, [historianOpen, selectedLandmarkId, selectedNpc]);

  const openNpc = useCallback((npc: NpcState) => {
    setJournalOpen(false);
    setSelectedLandmarkId(null);
    setChatDraft("");
    setShareChatPublicly(false);
    setSelectedNpc(npc);
  }, []);

  const interactWithLandmark = useCallback((landmarkId: LandmarkId) => {
    setSelectedNpc(null);
    if (landmarkId === "notice_board") {
      setSelectedLandmarkId(null);
      setJournalOpen(true);
      return;
    }
    setJournalOpen(false);
    setSelectedLandmarkId(landmarkId);
  }, []);

  const act = useCallback(
    async (
      verb: ActionVerb,
      targetId?: string,
      content?: string,
      publicStatement = false,
    ) => {
      if (!snapshot) return;
      setBusy(true);
      setError(null);
      try {
        const next = await takeAction(
          snapshot.run_id,
          verb,
          targetId,
          content,
          publicStatement,
        );
        setSnapshot(next);
        if (verb === "talk") setShareChatPublicly(false);
        playConfirmation();
        if (snapshot.weather !== "rain" && next.weather === "rain") {
          playThunder();
        }
        if (
          !snapshot.town_events.some(
            (event) => event.key === "market_day" && event.status === "active",
          ) &&
          next.town_events.some(
            (event) => event.key === "market_day" && event.status === "active",
          )
        ) {
          playMarketAmbience();
        }
        setSelectedNpc((current) => {
          if (!current) return null;
          if (next.release_profile === "hackathon_small") {
            const nextStage = firstPlaythroughStage(next);
            const nextGuide = GUIDED_NPCS[nextStage];
            if (
              verb !== "talk" &&
              nextStage !== "campaign" &&
              nextGuide !== current.id
            ) {
              return null;
            }
          }
          return next.npcs.find((npc) => npc.id === current.id) ?? null;
        });
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "The action failed.");
      } finally {
        setBusy(false);
      }
    },
    [snapshot],
  );

  const openHistorian = useCallback(async () => {
    if (!snapshot) return;
    setBusy(true);
    setError(null);
    try {
      const nextTrace = await traceRumorWithHistorian(
        snapshot.run_id,
        "bram-price-confrontation",
      );
      setHistorian(nextTrace);
      setSelectedNpc(null);
      setHistorianOpen(true);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "The Historian could not reconstruct that story.",
      );
    } finally {
      setBusy(false);
    }
  }, [snapshot]);

  const move = useCallback(
    async (locationId: string) => {
      if (!snapshot || moveInFlightRef.current) return;
      moveInFlightRef.current = true;
      setError(null);
      try {
        const next = await takeAction(snapshot.run_id, "move", locationId);
        setSnapshot(next);
      } catch (reason) {
        setError(
          reason instanceof Error
            ? reason.message
            : "Greyhaven's road did not answer.",
        );
      } finally {
        moveInFlightRef.current = false;
      }
    },
    [snapshot],
  );

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      const thread = chatThreadRef.current;
      if (thread) thread.scrollTop = thread.scrollHeight;
    });
    return () => window.cancelAnimationFrame(frame);
  }, [snapshot?.conversation_history?.length, selectedNpc?.id]);

  if (!snapshot) {
    return (
      <main className="arrival">
        <div className="arrival__mist" />
        <section className="arrival__card">
          <p className="eyebrow">A living town remembers</p>
          <span className="arrival__sprite" aria-hidden="true" />
          <h1>Hearsay</h1>
          <p className="tagline">The truth is what survives the telling.</p>
          <p className="arrival__copy">
            You arrive in Greyhaven three days before its mayoral election. Every
            promise has witnesses. Every rumor learns to walk.
          </p>
          <button className="primary" type="button" onClick={begin} disabled={busy}>
            {busy ? "Waking the town…" : "Take the road to Greyhaven"}
          </button>
          {error ? <p className="error">{error}</p> : null}
        </section>
      </main>
    );
  }

  const currentLocation =
    snapshot.locations.find(
      (location) => location.id === snapshot.player.location_id,
    );
  const waypointLocations =
    currentLocation?.neighbors
      .map((neighborId) =>
        snapshot.locations.find((location) => location.id === neighborId),
      )
      .filter((location) => location !== undefined) ?? [];
  const gameOver = snapshot.status === "completed";
  const activeTownEvent = snapshot.town_events.find(
    (event) => event.status === "active",
  );
  const selectedNpcOutOfReach =
    selectedNpc !== null &&
    activeTownEvent?.busy_resident_ids?.includes(selectedNpc.id) === true &&
    snapshot.player.location_id !== selectedNpc.location_id;
  const rheaCompact = snapshot.favors.find(
    (favor) => favor.key === "rhea_ballot_compact",
  );
  const smallRelease = snapshot.release_profile === "hackathon_small";
  const guidedStage = firstPlaythroughStage(snapshot);
  const guidedNpcId = smallRelease ? GUIDED_NPCS[guidedStage] : null;
  const guidedStep = Math.min(
    snapshot.action_count + 1,
    snapshot.action_budget,
  );
  const selectedLandmark =
    selectedLandmarkId === null ? null : LANDMARKS[selectedLandmarkId];
  const selectedLandmarkResidentId =
    selectedLandmarkId === null
      ? null
      : LANDMARK_RESIDENTS[selectedLandmarkId] ?? null;
  const selectedLandmarkResident =
    selectedLandmarkResidentId === null
      ? null
      : snapshot.npcs.find((npc) => npc.id === selectedLandmarkResidentId) ?? null;
  const latestEcho = snapshot.npcs
    .flatMap((listener) =>
      listener.recent_echoes.map((echo) => ({ echo, listener })),
    )
    .sort((left, right) => right.echo.hop - left.echo.hop)[0];
  const latestAgentTurn = snapshot.recent_events.find(
    (event) => event.kind === "agent_decision",
  );
  const agentTurnPayload = latestAgentTurn?.payload;
  const actingAgentId =
    agentTurnPayload && typeof agentTurnPayload.agent_id === "string"
      ? agentTurnPayload.agent_id
      : null;
  const actingAgent = snapshot.npcs.find((npc) => npc.id === actingAgentId);
  const agentTargetId =
    agentTurnPayload && typeof agentTurnPayload.target_id === "string"
      ? agentTurnPayload.target_id
      : null;
  const agentTarget = snapshot.npcs.find((npc) => npc.id === agentTargetId);
  const recalledAgentMemories =
    agentTurnPayload && Array.isArray(agentTurnPayload.recalled_memories)
      ? agentTurnPayload.recalled_memories.filter(
          (memory): memory is string => typeof memory === "string",
        )
      : [];
  const agentAction =
    agentTurnPayload && typeof agentTurnPayload.action === "string"
      ? agentTurnPayload.action
      : null;
  const agentRationale =
    agentTurnPayload && typeof agentTurnPayload.rationale === "string"
      ? agentTurnPayload.rationale
      : null;
  const agentProvider =
    agentTurnPayload && typeof agentTurnPayload.provider_id === "string"
      ? agentTurnPayload.provider_id
      : null;
  const agentModel =
    agentTurnPayload && typeof agentTurnPayload.model_id === "string"
      ? agentTurnPayload.model_id
      : null;
  const agentUsedFallback = agentTurnPayload?.fallback_used === true;
  const selectedConversationMessages = selectedNpc
    ? (snapshot.conversation_history ?? []).filter(
        (message) => message.npc_id === selectedNpc.id,
      )
    : [];
  const latestStoredNpcMessage = selectedConversationMessages.findLast(
    (message) => message.speaker === "npc",
  );

  return (
    <main
      className="game"
      data-release-profile={snapshot.release_profile}
      data-weather={snapshot.weather}
      data-town-event={activeTownEvent?.key ?? "none"}
      data-market-audio={marketDayActive ? "active" : "inactive"}
      data-conversation={selectedNpc ? "open" : "closed"}
      data-landmark={selectedLandmarkId ?? "closed"}
      data-historian={historianOpen ? "open" : "closed"}
      data-game-status={snapshot.status}
    >
      <div className="town-stage">
        {smallRelease ? (
          <PlayableTown
            snapshot={snapshot}
            guidedNpcId={guidedNpcId}
            selectedNpcId={selectedNpc?.id ?? null}
            selectedLandmarkId={selectedLandmarkId}
            movementDisabled={busy || gameOver || selectedLandmark !== null}
            onMove={(locationId) => void move(locationId)}
            onLandmarkInteract={interactWithLandmark}
            onNpcClick={openNpc}
          />
        ) : (
          <TownMap
            snapshot={snapshot}
            selectedNpcId={selectedNpc?.id ?? null}
            movementDisabled={busy}
            onMove={(locationId) => void move(locationId)}
            onNpcClick={openNpc}
          />
        )}
      </div>

      <header className="topbar">
        <div>
          <p className="eyebrow">
            {smallRelease
              ? "Greyhaven · three days to change twenty minds"
              : "Greyhaven · full simulation"}
          </p>
          <h1>Hearsay</h1>
        </div>
        <div className="clock" aria-label="Game clock">
          <span>{clockLabel(snapshot)}</span>
          {snapshot.weather === "rain" ? (
            <strong className="storm-status">
              {activeTownEvent?.title ?? "Storm over Greyhaven"}
            </strong>
          ) : activeTownEvent ? (
            <strong className="event-status">{activeTownEvent.title}</strong>
          ) : null}
          <small>
            {smallRelease
              ? gameOver
                ? "Election resolved"
                : `Story step ${guidedStep} of ${snapshot.action_budget}`
              : remainingActionLabel(snapshot)}
          </small>
        </div>
      </header>

      {smallRelease ? (
        <>
          <section className="quest-hud" aria-label="Current objective">
            <div className="quest-hud__step">
              <span>{gameOver ? "✓" : guidedStep}</span>
              <small>{gameOver ? "Complete" : "Current lead"}</small>
            </div>
            <div>
              <strong>{firstPlaythroughObjective(snapshot)}</strong>
              <small>
                {gameOver
                  ? "The town remembers every choice."
                  : "Follow the gold marker · WASD to move · T to talk"}
              </small>
            </div>
          </section>
          <button
            className="journal-toggle"
            aria-expanded={journalOpen}
            onClick={() => setJournalOpen((open) => !open)}
            type="button"
          >
            <kbd>J</kbd>
            Journal
          </button>
        </>
      ) : (
        <>
          <aside className="where">
            <span className="where__pin">◆</span>
            <div>
              <small>You are at</small>
              <strong>{currentLocation?.name ?? "Greyhaven"}</strong>
            </div>
          </aside>

          <nav className="waypoints" aria-label="Walk through Greyhaven">
            <small>Walk · WASD / arrows</small>
            {waypointLocations.map((location) => (
              <button
                key={location.id}
                type="button"
                disabled={busy}
                onClick={() => move(location.id)}
              >
                {location.name}
              </button>
            ))}
          </nav>
        </>
      )}

      {smallRelease && latestAgentTurn && actingAgent ? (
        <section className="agent-turn-card" aria-label="Autonomous agent turn">
          <header>
            <span className="agent-turn-card__pulse" aria-hidden="true" />
            <div>
              <small>Autonomous town turn</small>
              <strong>{actingAgent.name} acts without the player</strong>
            </div>
          </header>
          <ol>
            <li>
              <span>Recall</span>
              <p>
                {recalledAgentMemories[0]
                  ? `“${recalledAgentMemories[0]}”`
                  : "No salient public memory was selected."}
              </p>
            </li>
            <li>
              <span>Decide</span>
              <p>
                {agentAction === "share_rumor" && agentTarget
                  ? `Carry this version to ${agentTarget.name}.`
                  : "Hold the story for now."}
              </p>
              {agentRationale ? <small>{agentRationale}</small> : null}
            </li>
            <li>
              <span>Act</span>
              <p>
                {latestEcho && agentTarget
                  ? `${agentTarget.name} now carries a changed version at hop ${latestEcho.echo.hop}.`
                  : latestAgentTurn.text}
              </p>
            </li>
          </ol>
          <footer>
            {agentProvider && agentModel
              ? `${agentProvider}/${agentModel}`
              : "validated agent policy"}
            {agentUsedFallback ? " · safe local fallback" : ""}
            {" · memory committed to CockroachDB"}
          </footer>
        </section>
      ) : null}

      <section
        className={`ledger${smallRelease ? " ledger--journal" : ""}`}
        aria-label={smallRelease ? "Journal" : "Town ledger"}
        aria-hidden={smallRelease && !journalOpen}
        data-open={smallRelease && journalOpen}
      >
        <div className="panel-title">
          <p className="eyebrow">{smallRelease ? "Journal" : "Town ledger"}</p>
          <span>Tick {snapshot.world_tick}</span>
          {smallRelease ? (
            <button
              aria-label="Close journal"
              onClick={() => setJournalOpen(false)}
              type="button"
            >
              ×
            </button>
          ) : null}
        </div>
        {activeTownEvent ? (
          <article
            className="promise town-event"
            data-town-event-key={activeTownEvent.key}
          >
            <span className="promise__mark">
              {activeTownEvent.key === "storm"
                ? "☂"
                : activeTownEvent.key === "market_day"
                  ? "♜"
                  : "!"}
            </span>
            <div>
              <strong>{activeTownEvent.title}</strong>
              <p>
                {activeTownEvent.key === "storm"
                  ? "The docks are empty. Greyhaven has crowded into the inn."
                  : activeTownEvent.key === "market_day"
                    ? "Two visiting stalls are open. Ambients crowd Market Row, and Bram is hard to reach."
                    : "Bram and Nessa are shouting. Greyhaven has formed a ring in the square."}
              </p>
              <small>Active · behavior and routes changed</small>
              {activeTownEvent.key === "public_argument" &&
              !snapshot.player.argument_choice ? (
                <div
                  className="town-event__choices"
                  aria-label="Answer the public argument"
                >
                  <button
                    disabled={busy}
                    onClick={() => act("side_with_bram")}
                    type="button"
                  >
                    Back Bram&apos;s claim
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => act("side_with_nessa")}
                    type="button"
                  >
                    Defend Nessa&apos;s crews
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => act("calm_argument")}
                    type="button"
                  >
                    Calm the crowd
                  </button>
                </div>
              ) : null}
            </div>
          </article>
        ) : null}
        {snapshot.promises.length ? (
          snapshot.promises.map((promise) => (
            <article className="promise" key={promise.id}>
              <span className="promise__mark">✦</span>
              <div>
                <strong>Promise to Marta</strong>
                <p>{promise.content}</p>
                <small>
                  {promise.status === "active"
                    ? `Due day ${promise.deadline_day}, ${promise.deadline_phase}`
                    : promise.status === "kept"
                      ? "Kept · Marta's shipment was released"
                      : "Broken · evening arrived first"}
                </small>
              </div>
            </article>
          ))
        ) : (
          <p className="muted">Your word has not cost you anything—yet.</p>
        )}
        {snapshot.favors.map((favor) => (
          <article className="promise" key={favor.id}>
            <span className="promise__mark">
              {favor.key === "orin_election_confession"
                ? "✧"
                : favor.key === "talia_sick_house"
                  ? "✚"
                  : favor.key === "elias_wrongful_arrest"
                    ? "⚖"
                    : favor.key === "pip_ballot_source"
                      ? "☞"
                      : favor.key === "rhea_ballot_compact"
                        ? "⌘"
                        : "⚓"}
            </span>
            <div>
              <strong>
                {favor.key === "orin_election_confession"
                  ? "Orin's sealed confession"
                  : favor.key === "talia_sick_house"
                    ? "Talia's sick-house request"
                    : favor.key === "elias_wrongful_arrest"
                      ? "Elias's omitted arrest correction"
                      : favor.key === "pip_ballot_source"
                        ? "Pip's ballot source"
                        : favor.key === "rhea_ballot_compact"
                          ? "Rhea's ballot compact"
                          : "Nessa's harbor log"}
              </strong>
              <p>{favor.content}</p>
              <small>
                {favor.key === "orin_election_confession"
                  ? favor.resolution === "revealed"
                    ? "Revealed publicly · Orin's confidence broken"
                    : favor.resolution === "concealed"
                      ? "Kept sealed · Orin's blessing earned"
                      : "Unresolved · reveal it or keep it sealed"
                  : favor.key === "talia_sick_house"
                    ? favor.resolution === "helped_quietly"
                      ? "Helped quietly · Talia's family backing earned"
                      : favor.resolution === "gossiped_publicly"
                        ? "Warned publicly · family confidence broken"
                        : "Unresolved · help quietly or warn publicly"
                    : favor.key === "elias_wrongful_arrest"
                      ? favor.resolution === "investigated"
                        ? "Record corrected · Tob publicly cleared"
                        : favor.resolution === "covered_up"
                          ? "Correction destroyed · Tob witnessed it"
                          : "Unresolved · reopen or bury the old arrest"
                      : favor.key === "pip_ballot_source"
                        ? favor.resolution === "verified_source"
                          ? "Source verified · Kit's receipt anchors the story"
                          : favor.resolution === "embellished"
                            ? "Embellished publicly · unsupported detail spreading"
                            : "Unresolved · verify the source or sharpen the rumor"
                        : favor.key === "rhea_ballot_compact"
                          ? favor.resolution === "challenged"
                            ? "Public count demanded · independent witnesses posted"
                            : favor.resolution === "made_deal"
                              ? "Guild compact signed · sole custody preserved"
                              : "Unresolved · challenge Rhea or take her deal"
                          : favor.corrected_publicly
                            ? "Corrected publicly · endorsement available"
                            : favor.status === "completed"
                              ? "Delivered to Elias · correct Pip's story"
                              : "Active · carry the log to Elias"}
              </small>
            </div>
          </article>
        ))}
        {snapshot.player.traits.length ? (
          <p className="muted">
            Chalk says: {snapshot.player.traits.join(" · ")}
          </p>
        ) : null}
        <p className="muted">
          {snapshot.player.candidate
            ? "Ballot: the newcomer is standing against Rhea"
            : "Ballot: Rhea is currently unopposed"}
        </p>
        {rheaCompact ? (
          <p
            className="muted"
            data-ballot-custody={rheaCompact.resolution ?? "unresolved"}
          >
            {rheaCompact.resolution === "challenged"
              ? "Guildhouse: public count · Elias and Edda witnessing"
              : rheaCompact.resolution === "made_deal"
                ? "Guildhouse: sole guild custody · compact posted"
                : "Guildhouse: ballot custody under negotiation"}
          </p>
        ) : null}
        <button
          className="secondary"
          type="button"
          disabled={busy}
          onClick={() => act("read_notice_board")}
        >
          Read the notice board
        </button>
        {snapshot.world_tick > 0 ? (
          <button
            className="secondary"
            type="button"
            disabled={busy}
            onClick={openHistorian}
          >
            Trace Pip&apos;s rumor
          </button>
        ) : null}
        {smallRelease ? (
          <button
            className="secondary"
            disabled={busy}
            onClick={begin}
            type="button"
          >
            Restart first playthrough
          </button>
        ) : null}
      </section>

      {snapshot.election ? (
        <section className="historian" aria-label="Election result">
          <p className="eyebrow">Election night · auditable result</p>
          <h2>{snapshot.election.ending.title}</h2>
          <p className="historian__summary">
            Newcomer {snapshot.election.player_votes}–{snapshot.election.rhea_votes} Rhea
            {snapshot.election.tie_favors_rhea
              ? " · a tied ballot stays with Rhea"
              : ""}
          </p>
          <p>{snapshot.election.ending.summary}</p>
          <div className="historian__chain">
            {(snapshot.election.ending.decisive_voter_ids ?? []).map((voterId) => {
              const vote = snapshot.election?.votes.find(
                (item) => item.voter_id === voterId,
              );
              if (!vote) return null;
              const voter = snapshot.npcs.find((npc) => npc.id === voterId);
              return (
                <article key={vote.id}>
                  <span>
                    {voter?.name ?? voterId} voted {vote.choice === "player" ? "for you" : "for Rhea"}
                  </span>
                  {vote.inputs
                    .filter((input) => input.decisive_rank !== null)
                    .sort(
                      (left, right) =>
                        (left.decisive_rank ?? 4) - (right.decisive_rank ?? 4),
                    )
                    .map((input) => (
                      <small key={input.id}>
                        {input.contribution >= 0 ? "+" : ""}
                        {input.contribution.toFixed(2)} · {input.explanation}
                        {input.belief_id
                          ? ` · belief ${input.belief_id.slice(0, 8)} v${input.belief_version}`
                          : ""}
                      </small>
                    ))}
                </article>
              );
            })}
          </div>
          <button
            className="primary election-restart"
            disabled={busy}
            onClick={begin}
            type="button"
          >
            Start a new story
          </button>
        </section>
      ) : null}

      {!smallRelease ? (
      <section className="actions" aria-label="Available actions">
        <button type="button" disabled={busy || gameOver} onClick={() => act("observe")}>
          Eavesdrop
          <small>Free action</small>
        </button>
        <button type="button" disabled={busy || gameOver} onClick={() => setSelectedNpc(
          snapshot.npcs.find((npc) => npc.id === "marta") ?? null,
        )} data-release-tier={releaseTierForNpc("marta")}>
          Find Marta
          <small>
            {snapshot.locations.find(
              (location) =>
                location.id ===
                snapshot.npcs.find((npc) => npc.id === "marta")?.location_id,
            )?.name ?? "Greyhaven"}
          </small>
        </button>
        <button type="button" disabled={busy || gameOver} onClick={() => setSelectedNpc(
          snapshot.npcs.find((npc) => npc.id === "bram") ?? null,
        )} data-release-tier={releaseTierForNpc("bram")}>
          Find Bram
          <small>
            {activeTownEvent?.busy_resident_ids?.includes("bram") &&
            snapshot.player.location_id !==
              snapshot.npcs.find((npc) => npc.id === "bram")?.location_id
              ? "Busy at Market row · walk there"
              : (snapshot.locations.find(
                  (location) =>
                    location.id ===
                    snapshot.npcs.find((npc) => npc.id === "bram")?.location_id,
                )?.name ?? "Greyhaven")}
          </small>
        </button>
        <button type="button" disabled={busy || gameOver} onClick={() => setSelectedNpc(
          snapshot.npcs.find((npc) => npc.id === "pip") ?? null,
        )} data-release-tier={releaseTierForNpc("pip")}>
          Find Pip
          <small>
            {snapshot.locations.find(
              (location) =>
                location.id ===
                snapshot.npcs.find((npc) => npc.id === "pip")?.location_id,
            )?.name ?? "Greyhaven"}
          </small>
        </button>
        <button type="button" disabled={busy || gameOver} onClick={() => setSelectedNpc(
          snapshot.npcs.find((npc) => npc.id === "rhea") ?? null,
        )} data-release-tier={releaseTierForNpc("rhea")}>
          Find Rhea
          <small>
            {snapshot.locations.find(
              (location) =>
                location.id ===
                snapshot.npcs.find((npc) => npc.id === "rhea")?.location_id,
            )?.name ?? "Greyhaven"}
          </small>
        </button>
        {snapshot.release_profile === "full" ? (
          <>
            <button type="button" disabled={busy || gameOver} onClick={() => setSelectedNpc(
              snapshot.npcs.find((npc) => npc.id === "nessa") ?? null,
            )} data-release-tier={releaseTierForNpc("nessa")}>
              Find Nessa
              <small>
                {snapshot.locations.find(
                  (location) =>
                    location.id ===
                    snapshot.npcs.find((npc) => npc.id === "nessa")?.location_id,
                )?.name ?? "Greyhaven"}
              </small>
            </button>
            <button type="button" disabled={busy || gameOver} onClick={() => setSelectedNpc(
              snapshot.npcs.find((npc) => npc.id === "elias") ?? null,
            )} data-release-tier={releaseTierForNpc("elias")}>
              Find Elias
              <small>
                {snapshot.locations.find(
                  (location) =>
                    location.id ===
                    snapshot.npcs.find((npc) => npc.id === "elias")?.location_id,
                )?.name ?? "Greyhaven"}
              </small>
            </button>
            <button type="button" disabled={busy || gameOver} onClick={() => setSelectedNpc(
              snapshot.npcs.find((npc) => npc.id === "orin") ?? null,
            )} data-release-tier={releaseTierForNpc("orin")}>
              Find Orin
              <small>
                {snapshot.locations.find(
                  (location) =>
                    location.id ===
                    snapshot.npcs.find((npc) => npc.id === "orin")?.location_id,
                )?.name ?? "Greyhaven"}
              </small>
            </button>
          </>
        ) : null}
        <button type="button" disabled={busy || gameOver} onClick={() => setSelectedNpc(
          snapshot.npcs.find((npc) => npc.id === "talia") ?? null,
        )} data-release-tier={releaseTierForNpc("talia")}>
          Find Talia
          <small>
            {snapshot.locations.find(
              (location) =>
                location.id ===
                snapshot.npcs.find((npc) => npc.id === "talia")?.location_id,
            )?.name ?? "Greyhaven"}
          </small>
        </button>
        {snapshot.release_profile === "full" ? (
          <button
            type="button"
            disabled={busy || gameOver}
            onClick={() => act("sleep")}
          >
            Sleep until morning
            <small>Advance to the next day</small>
          </button>
        ) : null}
        {snapshot.player.candidate &&
        !snapshot.player.square_speech_days.includes(snapshot.day) ? (
          <button
            disabled={busy || gameOver}
            onClick={() => act("give_square_speech", "square")}
            type="button"
          >
            Address the square
            <small>Once today · consequential</small>
          </button>
        ) : null}
      </section>
      ) : null}

      {smallRelease && selectedLandmark ? (
        <section
          className="landmark-panel"
          aria-label={selectedLandmark.label}
          data-landmark-id={selectedLandmark.id}
        >
          <button
            className="landmark-panel__close"
            type="button"
            aria-label={`Close ${selectedLandmark.label}`}
            onClick={() => setSelectedLandmarkId(null)}
          >
            ×
          </button>
          <p className="eyebrow">Greyhaven landmark</p>
          <h2>{selectedLandmark.label}</h2>
          <p>{selectedLandmark.summary}</p>
          {selectedLandmark.id === "room" ? (
            <div className="landmark-panel__note">
              <strong>
                Day {snapshot.day} · {snapshot.phase}
              </strong>
              <span>
                Your story is saved after every choice. Rest becomes available
                when this guided day permits it.
              </span>
            </div>
          ) : selectedLandmark.id === "alley" ? (
            <div className="landmark-panel__note">
              <strong>{latestEcho ? "Newest whisper" : "Quiet—for now"}</strong>
              <span>
                {latestEcho
                  ? `${latestEcho.echo.speaker_name ?? latestEcho.echo.speaker_id} → ${latestEcho.listener.name}, hop ${latestEcho.echo.hop}: “${latestEcho.echo.text}”`
                  : "No story has travelled far enough to leave an echo here yet."}
              </span>
            </div>
          ) : selectedLandmark.id === "road" ? (
            <div className="landmark-panel__note">
              <strong>
                {snapshot.election
                  ? snapshot.election.ending.title
                  : `${snapshot.action_budget - snapshot.action_count} story choices remain`}
              </strong>
              <span>
                {snapshot.election
                  ? snapshot.election.ending.summary
                  : "You arrived as a stranger. Greyhaven is still deciding what name to give you."}
              </span>
            </div>
          ) : selectedLandmarkResident ? (
            <div className="landmark-panel__note">
              <strong>{selectedLandmarkResident.name}</strong>
              <span>
                {selectedLandmarkResident.location_id === selectedLandmark.id
                  ? `${selectedLandmarkResident.role} is nearby. Close this plaque and press T beside them to talk.`
                  : `${selectedLandmarkResident.name} is away at ${snapshot.locations.find((location) => location.id === selectedLandmarkResident.location_id)?.name ?? "another part of Greyhaven"}.`}
              </span>
            </div>
          ) : (
            <div className="landmark-panel__note">
              <strong>A place worth remembering</strong>
              <span>Nothing here spends a story action. Explore freely.</span>
            </div>
          )}
        </section>
      ) : null}

      {selectedNpc ? (
        <section className="conversation" aria-live="polite">
          <button
            className="conversation__close"
            type="button"
            aria-label="Close conversation"
            onClick={() => setSelectedNpc(null)}
          >
            ×
          </button>
          <div
            className="portrait"
            data-npc-id={selectedNpc.id}
            style={{ "--portrait-color": selectedNpc.color } as React.CSSProperties}
          >
            {PRESENTED_NPC_IDS.has(selectedNpc.id)
              ? null
              : selectedNpc.name
                  .split(" ")
                  .map((part) => part[0])
                  .join("")}
          </div>
          <div className="conversation__body">
            <p className="eyebrow">{selectedNpc.role}</p>
            <h2>
              {selectedNpc.name} · standing{" "}
              {selectedNpc.relationship >= 0 ? "+" : ""}
              {selectedNpc.relationship}
            </h2>
            <div
              className="chat-thread"
              ref={chatThreadRef}
              aria-label={`Chat with ${selectedNpc.name}`}
            >
              {selectedConversationMessages.length === 0 ? (
                <article className="chat-message chat-message--npc">
                  <span>{selectedNpc.name}</span>
                  <p>
                    {snapshot.dialogue?.speaker_id === selectedNpc.id
                      ? snapshot.dialogue.text
                      : selectedNpc.speech ??
                        "They wait to hear what you have to say."}
                  </p>
                </article>
              ) : (
                selectedConversationMessages.map((message) => (
                  <article
                    className={`chat-message chat-message--${message.speaker}`}
                    key={message.id}
                  >
                    <span>
                      {message.speaker === "player" ? "You" : selectedNpc.name}
                      {message.public_statement ? <em>Shared with town</em> : null}
                    </span>
                    <p>{message.text}</p>
                  </article>
                ))
              )}
              {selectedConversationMessages.length > 0 &&
              snapshot.dialogue?.speaker_id === selectedNpc.id &&
              snapshot.dialogue.text !== latestStoredNpcMessage?.text ? (
                <article className="chat-message chat-message--npc">
                  <span>{selectedNpc.name}</span>
                  <p>{snapshot.dialogue.text}</p>
                </article>
              ) : null}
            </div>
            {snapshot.dialogue?.speaker_id === selectedNpc.id &&
            (snapshot.dialogue.recalled_memories?.length ?? 0) > 0 ? (
              <div className="memory-proof" aria-label="Long-term memories recalled">
                <div className="memory-proof__heading">
                  <span>Long-term memory recalled</span>
                  <small>
                    {snapshot.dialogue.provider_id}/{snapshot.dialogue.model_id}
                    {snapshot.dialogue.fallback_used ? " · safe fallback" : ""}
                    {snapshot.dialogue.inference_input_tokens != null &&
                    snapshot.dialogue.inference_output_tokens != null
                      ? ` · ${snapshot.dialogue.inference_input_tokens} in / ${snapshot.dialogue.inference_output_tokens} out`
                      : ""}
                  </small>
                </div>
                <ul>
                  {snapshot.dialogue.recalled_memories?.map((memory) => (
                    <li key={`${memory.belief_id}-${memory.version}`}>
                      <strong>{memory.scope} memory</strong>
                      <span>{memory.summary}</span>
                      <code>
                        {memory.proposition_key.replaceAll("_", " ")} · belief{" "}
                        {memory.belief_id.slice(0, 8)} · v{memory.version}
                      </code>
                      {memory.contested ? <em>contested</em> : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {snapshot.dialogue?.speaker_id === selectedNpc.id &&
            snapshot.dialogue.treatment_cue ? (
              <p>{snapshot.dialogue.treatment_cue}</p>
            ) : null}
            {selectedNpcOutOfReach ? (
              <p className="conversation__busy">
                Market Day has Bram buried in customers. Walk to Market Row to
                get his attention.
              </p>
            ) : null}
            <form
              className="npc-chat"
              onSubmit={(event) => {
                event.preventDefault();
                const message = chatDraft.trim();
                if (!message) return;
                setChatDraft("");
                void act(
                  "talk",
                  selectedNpc.id,
                  message,
                  shareChatPublicly,
                );
              }}
            >
              <label htmlFor={`chat-${selectedNpc.id}`}>
                Tell {selectedNpc.name.split(" ")[0]} anything
              </label>
              <textarea
                id={`chat-${selectedNpc.id}`}
                disabled={busy || selectedNpcOutOfReach}
                maxLength={500}
                onChange={(event) => setChatDraft(event.target.value)}
                placeholder={`Ask what ${selectedNpc.name.split(" ")[0]} remembers, or tell them something about another resident…`}
                rows={2}
                value={chatDraft}
              />
              <div className="npc-chat__controls">
                <label>
                  <input
                    checked={shareChatPublicly}
                    disabled={busy || selectedNpcOutOfReach}
                    onChange={(event) =>
                      setShareChatPublicly(event.target.checked)
                    }
                    type="checkbox"
                  />
                  Share this message with the town
                </label>
                <button
                  disabled={busy || chatDraft.trim().length === 0}
                  type="submit"
                >
                  Say it
                </button>
              </div>
              <small>
                Private by default · Town sharing creates public memory and rumor hops
              </small>
            </form>
            <fieldset
              className="conversation__choices"
              disabled={busy || selectedNpcOutOfReach}
            >
              {!smallRelease &&
              snapshot.dialogue?.speaker_id === selectedNpc.id
                ? snapshot.dialogue.available_choices?.map((choice) => (
                    <button
                      disabled={busy}
                      key={choice.id}
                      type="button"
                      onClick={() =>
                        act("talk", selectedNpc.id, choice.prompt)
                      }
                    >
                      {choice.label}
                    </button>
                  ))
                : null}
              {selectedNpc.id === "marta" &&
              (!smallRelease || guidedStage === "marta_promise") &&
              !snapshot.promises.some((promise) => promise.promisee_id === "marta") ? (
                <button
                  disabled={busy}
                  type="button"
                  onClick={() => act("promise_help", "marta")}
                >
                  Promise to fix the shipment
                </button>
              ) : null}
              {selectedNpc.id === "bram" &&
              (!smallRelease || guidedStage === "bram_approach") ? (
                <>
                  <button
                    aria-label="Threaten him quietly"
                    className={smallRelease ? "choice-card choice-card--danger" : undefined}
                    disabled={busy}
                    type="button"
                    onClick={() => act("threaten_bram", "bram")}
                  >
                    <span>Threaten him quietly</span>
                    {smallRelease ? (
                      <small aria-hidden="true">Fast · the town may remember cruelty</small>
                    ) : null}
                  </button>
                  <button
                    aria-label="Flatter his business sense"
                    className={smallRelease ? "choice-card" : undefined}
                    disabled={busy}
                    type="button"
                    onClick={() => act("flatter_bram", "bram")}
                  >
                    <span>Flatter his business sense</span>
                    {smallRelease ? (
                      <small aria-hidden="true">Safe · costs pride, not coin</small>
                    ) : null}
                  </button>
                  <button
                    aria-label="Negotiate a deal"
                    className={
                      smallRelease
                        ? "choice-card choice-card--recommended"
                        : undefined
                    }
                    disabled={busy}
                    type="button"
                    onClick={() => act("negotiate_bram", "bram")}
                  >
                    <span>Negotiate a deal</span>
                    {smallRelease ? (
                      <small aria-hidden="true">Recommended · firm without making an enemy</small>
                    ) : null}
                  </button>
                  <button
                    aria-label="Lie about a constable's order"
                    className={smallRelease ? "choice-card choice-card--danger" : undefined}
                    disabled={busy}
                    type="button"
                    onClick={() => act("lie_to_bram", "bram")}
                  >
                    <span>Lie about a constable&apos;s order</span>
                    {smallRelease ? (
                      <small aria-hidden="true">Risky · devastating if exposed</small>
                    ) : null}
                  </button>
                </>
              ) : null}
              {selectedNpc.id === "bram" &&
              (!smallRelease || guidedStage === "settle_shipment") &&
              snapshot.promises.some(
                (promise) =>
                  promise.promisee_id === "marta" &&
                  promise.status === "active",
              ) ? (
                <button
                  className={smallRelease ? "choice-card choice-card--recommended" : undefined}
                  disabled={busy}
                  type="button"
                  onClick={() => act("settle_shipment", "bram")}
                >
                  Pay to release Marta&apos;s shipment
                </button>
              ) : null}
              {selectedNpc.id === "rhea" &&
              (!smallRelease || guidedStage === "declare_candidacy") &&
              snapshot.day >= 2 &&
              !snapshot.player.candidate ? (
                <button
                  disabled={busy}
                  type="button"
                  onClick={() => act("declare_candidacy", "rhea")}
                >
                  Declare candidacy for mayor
                </button>
              ) : null}
              {selectedNpc.id === "rhea" &&
              (!smallRelease || guidedStage === "rhea_question") &&
              snapshot.player.candidate &&
              !snapshot.favors.some(
                (favor) => favor.key === "rhea_ballot_compact",
              ) ? (
                <button
                  disabled={busy}
                  type="button"
                  onClick={() => act("accept_rhea_compact", "rhea")}
                >
                  Question Rhea&apos;s ballot custody
                </button>
              ) : null}
              {selectedNpc.id === "rhea" &&
              (!smallRelease || guidedStage === "rhea_resolve") &&
              snapshot.favors.some(
                (favor) =>
                  favor.key === "rhea_ballot_compact" &&
                  favor.status === "active",
              ) ? (
                <>
                  <button
                    disabled={busy}
                    type="button"
                    onClick={() => act("challenge_rhea_ballot", "rhea")}
                  >
                    Demand a public count
                  </button>
                  <button
                    disabled={busy}
                    type="button"
                    onClick={() => act("deal_with_rhea", "rhea")}
                  >
                    Sign Rhea&apos;s compact
                  </button>
                </>
              ) : null}
              {!smallRelease &&
              selectedNpc.id === "nessa" &&
              snapshot.day >= 2 &&
              !snapshot.favors.some(
                (favor) => favor.key === "nessa_harbor_log",
              ) ? (
                <button
                  disabled={busy}
                  onClick={() => act("accept_nessa_favor", "nessa")}
                  type="button"
                >
                  Offer to carry the harbor log
                </button>
              ) : null}
              {!smallRelease &&
              selectedNpc.id === "elias" &&
              snapshot.favors.some(
                (favor) =>
                  favor.key === "nessa_harbor_log" &&
                  favor.status === "active",
              ) ? (
                <button
                  disabled={busy}
                  onClick={() => act("deliver_harbor_log", "elias")}
                  type="button"
                >
                  Give Elias the harbor log
                </button>
              ) : null}
              {!smallRelease &&
              selectedNpc.id === "elias" &&
              !snapshot.favors.some(
                (favor) => favor.key === "elias_wrongful_arrest",
              ) ? (
                <button
                  disabled={busy}
                  onClick={() => act("accept_elias_favor", "elias")}
                  type="button"
                >
                  Ask about Elias&apos;s old arrest
                </button>
              ) : null}
              {!smallRelease &&
              selectedNpc.id === "elias" &&
              snapshot.favors.some(
                (favor) =>
                  favor.key === "elias_wrongful_arrest" &&
                  favor.status === "active",
              ) ? (
                <>
                  <button
                    disabled={busy}
                    onClick={() => act("investigate_elias_arrest", "elias")}
                    type="button"
                  >
                    Reopen Tob&apos;s arrest
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => act("cover_elias_arrest", "elias")}
                    type="button"
                  >
                    Keep the correction buried
                  </button>
                </>
              ) : null}
              {!smallRelease &&
              selectedNpc.id === "pip" &&
              snapshot.favors.some(
                (favor) =>
                  favor.key === "nessa_harbor_log" &&
                  favor.status === "completed" &&
                  !favor.corrected_publicly,
              ) ? (
                <button
                  disabled={busy}
                  onClick={() => act("correct_storm_rumor", "pip")}
                  type="button"
                >
                  Correct the storm rumor
                </button>
              ) : null}
              {!smallRelease &&
              selectedNpc.id === "pip" &&
              !snapshot.favors.some(
                (favor) => favor.key === "pip_ballot_source",
              ) ? (
                <button
                  disabled={busy}
                  onClick={() => act("accept_pip_favor", "pip")}
                  type="button"
                >
                  Ask for Pip&apos;s ballot source
                </button>
              ) : null}
              {!smallRelease &&
              selectedNpc.id === "pip" &&
              snapshot.favors.some(
                (favor) =>
                  favor.key === "pip_ballot_source" &&
                  favor.status === "active",
              ) ? (
                <>
                  <button
                    disabled={busy}
                    onClick={() => act("verify_pip_source", "pip")}
                    type="button"
                  >
                    Trace Kit&apos;s receipt
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => act("embellish_pip_rumor", "pip")}
                    type="button"
                  >
                    Make it ballot stuffing
                  </button>
                </>
              ) : null}
              {!smallRelease &&
              selectedNpc.id === "nessa" &&
              snapshot.favors.some(
                (favor) =>
                  favor.key === "nessa_harbor_log" &&
                  favor.corrected_publicly,
              ) &&
              !snapshot.player.endorsements.includes("nessa") ? (
                <button
                  disabled={busy}
                  onClick={() => act("ask_nessa_endorsement", "nessa")}
                  type="button"
                >
                  Ask for the harbor&apos;s endorsement
                </button>
              ) : null}
              {!smallRelease &&
              selectedNpc.id === "orin" &&
              !snapshot.favors.some(
                (favor) => favor.key === "orin_election_confession",
              ) ? (
                <button
                  disabled={busy}
                  onClick={() => act("accept_orin_confession", "orin")}
                  type="button"
                >
                  Accept the sealed confession
                </button>
              ) : null}
              {!smallRelease &&
              selectedNpc.id === "orin" &&
              snapshot.favors.some(
                (favor) =>
                  favor.key === "orin_election_confession" &&
                  favor.status === "active",
              ) ? (
                <>
                  <button
                    disabled={busy}
                    onClick={() => act("reveal_orin_confession", "orin")}
                    type="button"
                  >
                    Reveal the confession
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => act("conceal_orin_confession", "orin")}
                    type="button"
                  >
                    Keep the confession sealed
                  </button>
                </>
              ) : null}
              {selectedNpc.id === "talia" &&
              (!smallRelease || guidedStage === "talia_request") &&
              !snapshot.favors.some(
                (favor) => favor.key === "talia_sick_house",
              ) ? (
                <button
                  disabled={busy}
                  onClick={() => act("accept_talia_favor", "talia")}
                  type="button"
                >
                  Ask about Oswin&apos;s sick room
                </button>
              ) : null}
              {selectedNpc.id === "talia" &&
              (!smallRelease || guidedStage === "talia_resolve") &&
              snapshot.favors.some(
                (favor) =>
                  favor.key === "talia_sick_house" &&
                  favor.status === "active",
              ) ? (
                <>
                  <button
                    disabled={busy}
                    onClick={() => act("help_oswin_quietly", "talia")}
                    type="button"
                  >
                    Help Oswin quietly
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => act("gossip_oswin_illness", "talia")}
                    type="button"
                  >
                    Warn Greyhaven through Pip
                  </button>
                </>
              ) : null}
            </fieldset>
          </div>
        </section>
      ) : null}

      {historianOpen && historian ? (
        <section className="historian" aria-label="Town Historian">
          <button
            className="historian__close"
            type="button"
            aria-label="Close Town Historian"
            onClick={() => setHistorianOpen(false)}
          >
            ×
          </button>
          <p className="eyebrow">
            {historian.audit.sponsor_proof
              ? "Independent Managed MCP record"
              : "Development fallback · not MCP proof"}
          </p>
          <h2>Town Historian</h2>
          <p className="historian__summary">
            {historian.audit.sponsor_proof
              ? `Verified through ${historian.audit.tool_name ?? "Managed MCP"} · audit ${historian.audit.id.slice(0, 8)}`
              : `Direct ${historian.audit.provider_id} read · ${historian.audit.fallback_reason ?? "fallback"} · sponsor proof false`}
          </p>
          <p className="historian__summary">
            {historian.lineage.versions.length} immutable versions ·{" "}
            {historian.lineage.transmissions.length} recorded retelling ·{" "}
            {historian.lineage.inputs.length} evaluated claim
          </p>
          <div className="historian__chain">
            {historian.lineage.versions.map((version) => (
              <article key={`${version.belief_id}-${version.version}`}>
                <span>
                  {snapshot.npcs.find((npc) => npc.id === version.holder_id)
                    ?.name ?? version.holder_id}{" "}
                  · v{version.version}
                </span>
                <blockquote>{version.narrative_text}</blockquote>
                <small>
                  {Math.round(version.confidence * 100)}% confidence · source{" "}
                  {version.source_id ?? version.source_kind}
                </small>
              </article>
            ))}
          </div>
          {historian.lineage.transmissions.map((transmission) => (
            <p className="historian__mutation" key={transmission.id}>
              <strong>Mutation recorded:</strong> {transmission.mutation_note}
              <small>
                {" "}
                · {transmission.provider_id}/{transmission.model_id}
                {transmission.fallback_used
                  ? ` · deterministic fallback (${transmission.fallback_reason ?? "provider error"})`
                  : ""}
              </small>
            </p>
          ))}
          {historian.lineage.inputs.map((input) => (
            <p className="historian__mutation" key={input.id}>
              <strong>Claim {input.outcome}:</strong>{" "}
              {input.source_id ?? input.source_kind} → {input.holder_id} ·{" "}
              {input.classification} against v
              {input.evaluated_against_version ?? "none"}
              {input.recalculated_after_conflict
                ? ` · re-evaluated after serialization conflict (${input.transaction_attempts} attempts)`
                : ""}
            </p>
          ))}
        </section>
      ) : null}

      {!smallRelease ? (
      <section className="event-strip" aria-live="polite">
        <span className="event-strip__icon">◉</span>
        <div className="event-strip__label">
          <strong>Town activity</strong>
          <small>Autonomous actions persist in CockroachDB</small>
        </div>
        <ol aria-label="Recent town events">
          {snapshot.recent_events
            .filter((event) => event.visible)
            .slice(0, 3)
            .map((event) => {
              const provenance = agentDecisionProvenance(event);
              return (
                <li
                  data-autonomous={isAutonomousEvent(event.kind)}
                  data-event-kind={event.kind}
                  key={event.id}
                >
                  {isAutonomousEvent(event.kind) ? (
                    <span className="event-strip__agent-tag">Agent</span>
                  ) : null}
                  {event.text}
                  {provenance ? (
                    <small className="event-strip__provenance">
                      {provenance}
                    </small>
                  ) : null}
                </li>
              );
            })}
        </ol>
      </section>
      ) : null}

      {busy ? <div className="busy">The town is thinking…</div> : null}
      {error ? <div className="toast error">{error}</div> : null}
    </main>
  );
}
