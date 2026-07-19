"use client";

import { useCallback, useEffect, useState } from "react";

import { TownScene } from "@/components/town-scene";
import {
  clockLabel,
  createRun,
  loadRun,
  takeAction,
  traceRumorWithHistorian,
  type ActionVerb,
  type HistorianTrace,
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
  const [historian, setHistorian] = useState<HistorianTrace | null>(null);
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
        setSelectedNpc((current) =>
          current
            ? next.npcs.find((npc) => npc.id === current.id) ?? null
            : null,
        );
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
  const gameOver = snapshot.status === "completed";
  const activeTownEvent = snapshot.town_events.find(
    (event) => event.status === "active",
  );

  const move = (locationId: string) => {
    void act("move", locationId);
  };

  return (
    <main
      className="game"
      data-weather={snapshot.weather}
      data-town-event={activeTownEvent?.key ?? "none"}
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
            <strong className="storm-status">
              {activeTownEvent?.title ?? "Storm over Greyhaven"}
            </strong>
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
        {activeTownEvent ? (
          <article
            className="promise town-event"
            data-town-event-key={activeTownEvent.key}
          >
            <span className="promise__mark">
              {activeTownEvent.key === "storm" ? "☂" : "!"}
            </span>
            <div>
              <strong>{activeTownEvent.title}</strong>
              <p>
                {activeTownEvent.key === "storm"
                  ? "The docks are empty. Greyhaven has crowded into the inn."
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
        </section>
      ) : null}

      <section className="actions" aria-label="Available actions">
        <button type="button" disabled={busy || gameOver} onClick={() => act("observe")}>
          Eavesdrop
          <small>Free action</small>
        </button>
        <button type="button" disabled={busy || gameOver} onClick={() => setSelectedNpc(
          snapshot.npcs.find((npc) => npc.id === "marta") ?? null,
        )}>
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
        )}>
          Find Bram
          <small>
            {snapshot.locations.find(
              (location) =>
                location.id ===
                snapshot.npcs.find((npc) => npc.id === "bram")?.location_id,
            )?.name ?? "Greyhaven"}
          </small>
        </button>
        <button type="button" disabled={busy || gameOver} onClick={() => setSelectedNpc(
          snapshot.npcs.find((npc) => npc.id === "pip") ?? null,
        )}>
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
        )}>
          Find Rhea
          <small>
            {snapshot.locations.find(
              (location) =>
                location.id ===
                snapshot.npcs.find((npc) => npc.id === "rhea")?.location_id,
            )?.name ?? "Greyhaven"}
          </small>
        </button>
        <button type="button" disabled={busy || gameOver} onClick={() => setSelectedNpc(
          snapshot.npcs.find((npc) => npc.id === "nessa") ?? null,
        )}>
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
        )}>
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
        )}>
          Find Orin
          <small>
            {snapshot.locations.find(
              (location) =>
                location.id ===
                snapshot.npcs.find((npc) => npc.id === "orin")?.location_id,
            )?.name ?? "Greyhaven"}
          </small>
        </button>
        <button type="button" disabled={busy || gameOver} onClick={() => setSelectedNpc(
          snapshot.npcs.find((npc) => npc.id === "talia") ?? null,
        )}>
          Find Talia
          <small>
            {snapshot.locations.find(
              (location) =>
                location.id ===
                snapshot.npcs.find((npc) => npc.id === "talia")?.location_id,
            )?.name ?? "Greyhaven"}
          </small>
        </button>
        <button
          type="button"
          disabled={busy || gameOver}
          onClick={() => act("sleep")}
        >
          Sleep until morning
          <small>Advance to the next day</small>
        </button>
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
                <>
                  <button
                    disabled={busy}
                    type="button"
                    onClick={() => act("threaten_bram", "bram")}
                  >
                    Threaten him quietly
                  </button>
                  <button
                    disabled={busy}
                    type="button"
                    onClick={() => act("flatter_bram", "bram")}
                  >
                    Flatter his business sense
                  </button>
                  <button
                    disabled={busy}
                    type="button"
                    onClick={() => act("negotiate_bram", "bram")}
                  >
                    Negotiate a deal
                  </button>
                  <button
                    disabled={busy}
                    type="button"
                    onClick={() => act("lie_to_bram", "bram")}
                  >
                    Lie about a constable&apos;s order
                  </button>
                  {snapshot.promises.some(
                    (promise) =>
                      promise.promisee_id === "marta" &&
                      promise.status === "active",
                  ) ? (
                    <button
                      disabled={busy}
                      type="button"
                      onClick={() => act("settle_shipment", "bram")}
                    >
                      Pay to release Marta&apos;s shipment
                    </button>
                  ) : null}
                </>
              ) : null}
              {selectedNpc.id === "rhea" &&
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
              {selectedNpc.id === "nessa" &&
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
              {selectedNpc.id === "elias" &&
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
              {selectedNpc.id === "elias" &&
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
              {selectedNpc.id === "elias" &&
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
              {selectedNpc.id === "pip" &&
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
              {selectedNpc.id === "nessa" &&
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
              {selectedNpc.id === "orin" &&
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
              {selectedNpc.id === "orin" &&
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
            </div>
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

      <section className="event-strip" aria-live="polite">
        <span className="event-strip__icon">◉</span>
        <ol aria-label="Recent town events">
          {snapshot.recent_events.slice(0, 3).map((event) => (
            <li
              data-event-kind={event.kind}
              key={event.id}
            >
              {event.text}
            </li>
          ))}
        </ol>
      </section>

      {busy ? <div className="busy">The town is thinking…</div> : null}
      {error ? <div className="toast error">{error}</div> : null}
    </main>
  );
}
