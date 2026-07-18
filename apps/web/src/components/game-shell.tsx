"use client";

import { useCallback, useEffect, useState } from "react";

import { TownScene } from "@/components/town-scene";
import {
  clockLabel,
  createRun,
  loadMemoryLineage,
  loadRun,
  takeAction,
  type ActionVerb,
  type MemoryLineage,
  type NpcState,
  type RunSnapshot,
} from "@/lib/api";

const RUN_STORAGE_KEY = "hearsay.run-id";

function playConfirmation() {
  const audio = new Audio("/assets/audio/ui-confirm.ogg");
  audio.volume = 0.24;
  void audio.play().catch(() => undefined);
}

function playThunder() {
  const AudioContextClass =
    window.AudioContext ??
    (
      window as typeof window & {
        webkitAudioContext?: typeof AudioContext;
      }
    ).webkitAudioContext;
  if (!AudioContextClass) return;

  const context = new AudioContextClass();
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

export function GameShell() {
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null);
  const [selectedNpc, setSelectedNpc] = useState<NpcState | null>(null);
  const [lineage, setLineage] = useState<MemoryLineage | null>(null);
  const [historianOpen, setHistorianOpen] = useState(false);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const runId = window.localStorage.getItem(RUN_STORAGE_KEY);
    if (!runId) {
      const ready = window.setTimeout(() => setBusy(false), 0);
      return () => window.clearTimeout(ready);
    }
    loadRun(runId)
      .then(setSnapshot)
      .catch(() => window.localStorage.removeItem(RUN_STORAGE_KEY))
      .finally(() => setBusy(false));
  }, []);

  const begin = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const next = await createRun("Newcomer");
      window.localStorage.setItem(RUN_STORAGE_KEY, next.run_id);
      setSnapshot(next);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Greyhaven did not answer.");
    } finally {
      setBusy(false);
    }
  }, []);

  const act = useCallback(
    async (verb: ActionVerb, targetId?: string, content?: string) => {
      if (!snapshot) return;
      setBusy(true);
      setError(null);
      try {
        const next = await takeAction(snapshot.run_id, verb, targetId, content);
        setSnapshot(next);
        playConfirmation();
        if (snapshot.weather !== "rain" && next.weather === "rain") {
          playThunder();
        }
        if (selectedNpc) {
          setSelectedNpc(next.npcs.find((npc) => npc.id === selectedNpc.id) ?? null);
        }
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "The action failed.");
      } finally {
        setBusy(false);
      }
    },
    [selectedNpc, snapshot],
  );

  const openHistorian = useCallback(async () => {
    if (!snapshot) return;
    setBusy(true);
    setError(null);
    try {
      const nextLineage = await loadMemoryLineage(
        snapshot.run_id,
        "bram-price-confrontation",
      );
      setLineage(nextLineage);
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

  if (!snapshot) {
    return (
      <main className="arrival">
        <div className="arrival__mist" />
        <section className="arrival__card">
          <p className="eyebrow">A living town remembers</p>
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

  const move = (locationId: string) => {
    void act("move", locationId);
  };

  return (
    <main
      className="game"
      data-weather={snapshot.weather}
      data-conversation={selectedNpc ? "open" : "closed"}
      data-historian={historianOpen ? "open" : "closed"}
    >
      <div className="scene" aria-label="A miniature view of Greyhaven">
        <TownScene
          snapshot={snapshot}
          selectedNpcId={selectedNpc?.id ?? null}
          movementDisabled={busy}
          onMove={move}
          onNpcClick={setSelectedNpc}
        />
      </div>

      <header className="topbar">
        <div>
          <p className="eyebrow">Greyhaven</p>
          <h1>Hearsay</h1>
        </div>
        <div className="clock" aria-label="Game clock">
          <span>{clockLabel(snapshot)}</span>
          {snapshot.weather === "rain" ? (
            <strong className="storm-status">Storm over Greyhaven</strong>
          ) : null}
          <small>{18 - snapshot.action_count} consequential actions remain</small>
        </div>
      </header>

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

      <section className="ledger" aria-label="Town ledger">
        <div className="panel-title">
          <p className="eyebrow">Town ledger</p>
          <span>Tick {snapshot.world_tick}</span>
        </div>
        {snapshot.promises.length ? (
          snapshot.promises.map((promise) => (
            <article className="promise" key={promise.id}>
              <span className="promise__mark">✦</span>
              <div>
                <strong>Promise to Marta</strong>
                <p>{promise.content}</p>
                <small>
                  Due day {promise.deadline_day}, {promise.deadline_phase}
                </small>
              </div>
            </article>
          ))
        ) : (
          <p className="muted">Your word has not cost you anything—yet.</p>
        )}
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
      </section>

      <section className="actions" aria-label="Available actions">
        <button type="button" disabled={busy} onClick={() => act("observe")}>
          Eavesdrop
          <small>Free action</small>
        </button>
        <button type="button" disabled={busy} onClick={() => setSelectedNpc(
          snapshot.npcs.find((npc) => npc.id === "marta") ?? null,
        )}>
          Find Marta
          <small>The Gull & Anchor</small>
        </button>
        <button type="button" disabled={busy} onClick={() => setSelectedNpc(
          snapshot.npcs.find((npc) => npc.id === "bram") ?? null,
        )}>
          Find Bram
          <small>Market row</small>
        </button>
        <button type="button" disabled={busy} onClick={() => setSelectedNpc(
          snapshot.npcs.find((npc) => npc.id === "pip") ?? null,
        )}>
          Find Pip
          <small>Town square</small>
        </button>
      </section>

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
            style={{ "--portrait-color": selectedNpc.color } as React.CSSProperties}
          >
            {selectedNpc.name
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
            <blockquote>
              {snapshot.dialogue?.speaker_id === selectedNpc.id
                ? snapshot.dialogue.text
                : selectedNpc.speech ?? "They wait to hear what you have to say."}
            </blockquote>
            {snapshot.dialogue?.speaker_id === selectedNpc.id &&
            (snapshot.dialogue.recalled_memories?.length ?? 0) > 0 ? (
              <small>
                Memory-informed · {snapshot.dialogue.recalled_memories?.length ?? 0} recalled ·{" "}
                {snapshot.dialogue.provider_id}/{snapshot.dialogue.model_id}
                {snapshot.dialogue.fallback_used ? " · safe fallback" : ""}
              </small>
            ) : null}
            {snapshot.dialogue?.speaker_id === selectedNpc.id &&
            snapshot.dialogue.treatment_cue ? (
              <p>{snapshot.dialogue.treatment_cue}</p>
            ) : null}
            <div className="conversation__choices">
              <button
                disabled={busy}
                type="button"
                onClick={() =>
                  act(
                    "talk",
                    selectedNpc.id,
                    "What have you heard about me and the town?",
                  )
                }
              >
                Talk
              </button>
              {snapshot.dialogue?.speaker_id === selectedNpc.id
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
              !snapshot.promises.some((promise) => promise.promisee_id === "marta") ? (
                <button
                  disabled={busy}
                  type="button"
                  onClick={() => act("promise_help", "marta")}
                >
                  Promise to fix the shipment
                </button>
              ) : null}
              {selectedNpc.id === "bram" ? (
                <button
                  disabled={busy}
                  type="button"
                  onClick={() => act("confront", "bram")}
                >
                  Confront him about the price
                </button>
              ) : null}
            </div>
          </div>
        </section>
      ) : null}

      {historianOpen && lineage ? (
        <section className="historian" aria-label="Town Historian">
          <button
            className="historian__close"
            type="button"
            aria-label="Close Town Historian"
            onClick={() => setHistorianOpen(false)}
          >
            ×
          </button>
          <p className="eyebrow">Independent memory record</p>
          <h2>Town Historian</h2>
          <p className="historian__summary">
            {lineage.versions.length} immutable versions ·{" "}
            {lineage.transmissions.length} recorded retelling ·{" "}
            {lineage.inputs.length} evaluated claim
          </p>
          <div className="historian__chain">
            {lineage.versions.map((version) => (
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
          {lineage.transmissions.map((transmission) => (
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
          {lineage.inputs.map((input) => (
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

      <section className="event-strip" aria-live="polite">
        <span className="event-strip__icon">◉</span>
        <p>{snapshot.recent_events[0]?.text}</p>
      </section>

      {busy ? <div className="busy">The town is thinking…</div> : null}
      {error ? <div className="toast error">{error}</div> : null}
    </main>
  );
}
