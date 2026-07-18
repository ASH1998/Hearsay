"use client";

import { useCallback, useEffect, useState } from "react";

import { TownScene } from "@/components/town-scene";
import {
  clockLabel,
  createRun,
  loadRun,
  takeAction,
  type ActionVerb,
  type NpcState,
  type RunSnapshot,
} from "@/lib/api";

const RUN_STORAGE_KEY = "hearsay.run-id";

export function GameShell() {
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null);
  const [selectedNpc, setSelectedNpc] = useState<NpcState | null>(null);
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
    async (verb: ActionVerb, targetId?: string) => {
      if (!snapshot) return;
      setBusy(true);
      setError(null);
      try {
        const next = await takeAction(snapshot.run_id, verb, targetId);
        setSnapshot(next);
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
    )?.name ?? "Greyhaven";

  return (
    <main className="game">
      <div className="scene" aria-label="A miniature view of Greyhaven">
        <TownScene snapshot={snapshot} onNpcClick={setSelectedNpc} />
      </div>

      <header className="topbar">
        <div>
          <p className="eyebrow">Greyhaven</p>
          <h1>Hearsay</h1>
        </div>
        <div className="clock" aria-label="Game clock">
          <span>{clockLabel(snapshot)}</span>
          <small>{18 - snapshot.action_count} consequential actions remain</small>
        </div>
      </header>

      <aside className="where">
        <span className="where__pin">◆</span>
        <div>
          <small>You are at</small>
          <strong>{currentLocation}</strong>
        </div>
      </aside>

      <nav className="waypoints" aria-label="Walk through Greyhaven">
        {[
          ["inn", "The inn"],
          ["square", "The square"],
          ["market", "Market row"],
          ["docks", "The docks"],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            disabled={busy || snapshot.player.location_id === id}
            onClick={() => act("move", id)}
          >
            {label}
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
            <h2>{selectedNpc.name}</h2>
            <blockquote>
              {snapshot.dialogue?.speaker_id === selectedNpc.id
                ? snapshot.dialogue.text
                : selectedNpc.speech ?? "They wait to hear what you have to say."}
            </blockquote>
            <div className="conversation__choices">
              <button disabled={busy} type="button" onClick={() => act("talk", selectedNpc.id)}>
                Talk
              </button>
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

      <section className="event-strip" aria-live="polite">
        <span className="event-strip__icon">◉</span>
        <p>{snapshot.recent_events[0]?.text}</p>
      </section>

      {busy ? <div className="busy">The town is thinking…</div> : null}
      {error ? <div className="toast error">{error}</div> : null}
    </main>
  );
}
