"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { PlayableTown } from "@/components/playable-town";
import { clockLabel, type RunSnapshot } from "@/lib/api";

type ReplayOutcome = {
  ending: string;
  headline: string;
  summary: string;
  player_votes: number;
  rhea_votes: number;
};

type ReplaySummary = {
  id: string;
  title: string;
  subtitle: string;
  accent: "gold" | "rust";
  recorded_runtime: string;
  outcome: ReplayOutcome;
};

type ReplayFrame = {
  duration_ms: number;
  title: string;
  detail: string;
  action: string;
  target_id: string | null;
  snapshot: RunSnapshot;
};

type ReplayBundle = ReplaySummary & {
  schema_version: number;
  frames: ReplayFrame[];
};

type ReplayManifest = {
  schema_version: number;
  replays: ReplaySummary[];
};

const SPEEDS = [0.75, 1, 1.5, 2] as const;

function scoreLabel(outcome: ReplayOutcome) {
  return `${outcome.player_votes}–${outcome.rhea_votes}`;
}

function outcomeLabel(outcome: ReplayOutcome) {
  return outcome.player_votes > outcome.rhea_votes
    ? "Newcomer elected"
    : "Rhea retains the mayoralty";
}

function actionLabel(action: string) {
  return action.replaceAll("_", " ");
}

export function ReplayExperience() {
  const [manifest, setManifest] = useState<ReplayManifest | null>(null);
  const [bundle, setBundle] = useState<ReplayBundle | null>(null);
  const [frameIndex, setFrameIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speedIndex, setSpeedIndex] = useState(1);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/replays/manifest.json")
      .then((response) => {
        if (!response.ok) throw new Error("The replay index could not be opened.");
        return response.json() as Promise<ReplayManifest>;
      })
      .then(setManifest)
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Greyhaven did not answer."),
      );
  }, []);

  const startReplay = useCallback(async (id: string) => {
    setLoadingId(id);
    setError(null);
    try {
      const response = await fetch(`/replays/${id}.json`);
      if (!response.ok) throw new Error("That recorded run could not be opened.");
      const nextBundle = (await response.json()) as ReplayBundle;
      setBundle(nextBundle);
      setFrameIndex(0);
      setPlaying(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Greyhaven did not answer.");
    } finally {
      setLoadingId(null);
    }
  }, []);

  const returnToRuns = useCallback(() => {
    setPlaying(false);
    setBundle(null);
    setFrameIndex(0);
  }, []);

  const advance = useCallback(() => {
    if (!bundle) return;
    setFrameIndex((current) => {
      if (current >= bundle.frames.length - 1) {
        setPlaying(false);
        return current;
      }
      return current + 1;
    });
  }, [bundle]);

  const retreat = useCallback(() => {
    setPlaying(false);
    setFrameIndex((current) => Math.max(0, current - 1));
  }, []);

  useEffect(() => {
    if (!bundle || !playing) return;
    const frame = bundle.frames[frameIndex];
    const timer = window.setTimeout(
      advance,
      Math.max(900, frame.duration_ms / SPEEDS[speedIndex]),
    );
    return () => window.clearTimeout(timer);
  }, [advance, bundle, frameIndex, playing, speedIndex]);

  useEffect(() => {
    if (!bundle) return;
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === " ") {
        setPlaying((current) => !current);
        event.preventDefault();
      } else if (event.key === "ArrowRight") {
        advance();
        event.preventDefault();
      } else if (event.key === "ArrowLeft") {
        retreat();
        event.preventDefault();
      } else if (event.key === "Escape") {
        returnToRuns();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [advance, bundle, retreat, returnToRuns]);

  const frame = bundle?.frames[frameIndex] ?? null;
  const snapshot = frame?.snapshot ?? null;
  const visibleEvents = useMemo(
    () => snapshot?.recent_events.filter((event) => event.visible).slice(0, 3) ?? [],
    [snapshot],
  );
  const activeTownEvent = snapshot?.town_events.find(
    (event) => event.status === "active",
  );
  const latestEcho = snapshot?.npcs
    .flatMap((npc) => npc.recent_echoes.map((echo) => ({ npc, echo })))
    .at(-1);

  if (!bundle || !frame || !snapshot) {
    return (
      <main className="replay-landing">
        <div className="replay-landing__sky" aria-hidden="true" />
        <div className="replay-landing__village" aria-hidden="true">
          <span className="replay-building replay-building--inn" />
          <span className="replay-building replay-building--guild" />
          <span className="replay-building replay-building--chapel" />
          <span className="replay-tree replay-tree--pine-left" />
          <span className="replay-tree replay-tree--maple-left" />
          <span className="replay-tree replay-tree--birch" />
          <span className="replay-tree replay-tree--pine-right" />
          <span className="replay-tree replay-tree--teal-right" />
          <span className="replay-villager replay-villager--marta" />
          <span className="replay-villager replay-villager--pip" />
          <span className="replay-villager replay-villager--talia" />
          <span className="replay-villager replay-villager--rhea" />
        </div>
        <section className="replay-hero">
          <p className="eyebrow">Two histories · one election</p>
          <h1>Hearsay</h1>
          <p className="replay-hero__tagline">The truth is what survives the telling.</p>
          <p className="replay-hero__copy">
            Choose a completed run and watch Greyhaven reconstruct it inside the
            real game world. The choices are fixed. The consequences are not hidden.
          </p>
        </section>

        <section className="replay-picker" aria-label="Choose a recorded run">
          {manifest?.replays.map((replay) => (
            <article
              className="replay-card"
              data-accent={replay.accent}
              key={replay.id}
            >
              <div className="replay-card__result">
                <span>{outcomeLabel(replay.outcome)}</span>
                <strong>{scoreLabel(replay.outcome)}</strong>
              </div>
              <div className="replay-card__portraits" aria-hidden="true">
                <span className="replay-card__newcomer" />
                <span className="replay-card__versus">vs</span>
                <span className="replay-card__rhea" />
              </div>
              <p className="eyebrow">Recorded history</p>
              <h2>{replay.title}</h2>
              <p>{replay.subtitle}</p>
              <button
                type="button"
                onClick={() => void startReplay(replay.id)}
                disabled={loadingId !== null}
              >
                {loadingId === replay.id ? "Opening the ledger…" : "Replay this run"}
                <span aria-hidden="true">→</span>
              </button>
            </article>
          ))}
          {!manifest && !error ? (
            <p className="replay-picker__loading">Opening Greyhaven’s ledger…</p>
          ) : null}
        </section>

        <aside className="replay-disclosure" aria-label="Recorded replay disclosure">
          <strong>Recorded Run Mode</strong>
          <p>
            This site replays saved world-state snapshots from deterministic local
            sessions. Choices and outcomes are fixed. No live CockroachDB or AWS
            services are contacted during playback.
          </p>
          <small>Greyhaven remembers—but live memory isn’t cheap.</small>
        </aside>
        {error ? <p className="replay-error">{error}</p> : null}
      </main>
    );
  }

  const finished = frameIndex === bundle.frames.length - 1;
  const election = snapshot.election;
  const speed = SPEEDS[speedIndex];

  return (
    <main
      className="replay-stage"
      data-weather={snapshot.weather}
      data-finished={finished}
    >
      <div className="replay-stage__world">
        <PlayableTown
          snapshot={snapshot}
          guidedNpcId={frame.target_id}
          movementDisabled
          onLandmarkInteract={() => undefined}
          onMove={() => undefined}
          onNpcClick={() => undefined}
          selectedLandmarkId={null}
          selectedNpcId={frame.target_id}
          syncPlayerPosition
        />
      </div>

      <header className="replay-topbar">
        <button type="button" onClick={returnToRuns} aria-label="Choose another run">
          ← Runs
        </button>
        <div>
          <p className="eyebrow">Recorded run · {bundle.title}</p>
          <h1>Hearsay</h1>
        </div>
        <div className="replay-topbar__clock">
          <strong>{clockLabel(snapshot)}</strong>
          <span>{activeTownEvent?.title ?? outcomeLabel(bundle.outcome)}</span>
        </div>
      </header>

      <section className="replay-scene" aria-live="polite">
        <div className="replay-scene__count">
          <span>{String(frameIndex + 1).padStart(2, "0")}</span>
          <small>of {bundle.frames.length}</small>
        </div>
        <div>
          <p className="eyebrow">{actionLabel(frame.action)}</p>
          <h2>{frame.title}</h2>
          <p>{frame.detail}</p>
        </div>
      </section>

      {snapshot.dialogue ? (
        <section className="replay-dialogue" aria-label="Recorded conversation">
          <div className="replay-dialogue__speaker">
            <span aria-hidden="true" />
            <div>
              <small>{snapshot.dialogue.treatment_cue ?? "Remembered response"}</small>
              <strong>{snapshot.dialogue.speaker_name}</strong>
            </div>
          </div>
          <blockquote>“{snapshot.dialogue.text}”</blockquote>
          {(snapshot.dialogue.recalled_memories ?? []).length ? (
            <p className="replay-memory-cue">
              <span>Memory recalled</span>
              {snapshot.dialogue.recalled_memories?.[0]?.summary}
            </p>
          ) : null}
        </section>
      ) : latestEcho ? (
        <section className="replay-dialogue replay-dialogue--rumor" aria-label="Rumor retelling">
          <div className="replay-dialogue__speaker">
            <span aria-hidden="true" />
            <div>
              <small>Rumor · hop {latestEcho.echo.hop}</small>
              <strong>{latestEcho.npc.name}</strong>
            </div>
          </div>
          <blockquote>“{latestEcho.echo.text}”</blockquote>
        </section>
      ) : null}

      {visibleEvents.length ? (
        <aside className="replay-events" aria-label="Latest recorded events">
          <p className="eyebrow">Town ledger</p>
          {visibleEvents.map((event) => (
            <p key={event.id}>{event.text}</p>
          ))}
        </aside>
      ) : null}

      {election ? (
        <section className="replay-election" data-outcome={bundle.accent}>
          <p className="eyebrow">The count is witnessed</p>
          <h2>{election.ending.title}</h2>
          <div className="replay-election__score">
            <span>
              <small>Newcomer</small>
              <strong>{election.player_votes}</strong>
            </span>
            <i>—</i>
            <span>
              <small>Rhea</small>
              <strong>{election.rhea_votes}</strong>
            </span>
          </div>
          <p>{election.ending.summary}</p>
        </section>
      ) : null}

      <footer className="replay-controls" aria-label="Replay controls">
        <div className="replay-controls__buttons">
          <button type="button" onClick={retreat} disabled={frameIndex === 0} aria-label="Previous scene">
            ‹
          </button>
          <button
            className="replay-controls__play"
            type="button"
            onClick={() => {
              if (finished) setFrameIndex(0);
              setPlaying((current) => (finished ? true : !current));
            }}
            aria-label={playing ? "Pause replay" : finished ? "Replay from beginning" : "Play replay"}
          >
            {playing ? "Ⅱ" : finished ? "↻" : "▶"}
          </button>
          <button type="button" onClick={advance} disabled={finished} aria-label="Next scene">
            ›
          </button>
        </div>
        <label>
          <span className="sr-only">Replay position</span>
          <input
            type="range"
            min={0}
            max={bundle.frames.length - 1}
            value={frameIndex}
            onChange={(event) => {
              setPlaying(false);
              setFrameIndex(Number(event.target.value));
            }}
          />
        </label>
        <button
          className="replay-controls__speed"
          type="button"
          onClick={() => setSpeedIndex((current) => (current + 1) % SPEEDS.length)}
          aria-label={`Playback speed ${speed} times`}
        >
          {speed}×
        </button>
        <p>
          <strong>Recorded snapshots</strong>
          <span>No live database or model calls</span>
        </p>
      </footer>
    </main>
  );
}
