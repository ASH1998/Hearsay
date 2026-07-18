import type { components } from "./api-schema";

type Schemas = components["schemas"];
type GeneratedSnapshot = Schemas["RunSnapshot"];

export type ActionVerb = Schemas["ActionVerb"];
export type Phase = GeneratedSnapshot["phase"];
export type LocationState = Schemas["LocationState"];
export type PromiseState = Schemas["PromiseState"];
export type MemoryLineage = Schemas["MemoryLineageResponse"];
export type HistorianTrace = Schemas["HistorianTraceResponse"];
export type NpcState = Omit<Schemas["NpcState"], "speech"> & {
  speech: string | null;
};
export type RunSnapshot = Omit<
  GeneratedSnapshot,
  "player" | "npcs" | "promises" | "dialogue" | "town_events" | "recent_events"
> & {
  player: Schemas["PlayerState"] & { traits: string[] };
  npcs: NpcState[];
  promises: PromiseState[];
  dialogue: Schemas["DialogueState"] | null;
  town_events: Schemas["TownEventState"][];
  recent_events: Schemas["WorldEvent"][];
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(error?.detail ?? `Hearsay API returned ${response.status}.`);
  }
  return (await response.json()) as T;
}

export async function createRun(displayName: string): Promise<RunSnapshot> {
  const body = await request<{ snapshot: RunSnapshot }>("/v1/runs", {
    method: "POST",
    body: JSON.stringify({ display_name: displayName, seed: 1729 }),
  });
  return body.snapshot;
}

export async function loadRun(runId: string): Promise<RunSnapshot> {
  return request<RunSnapshot>(`/v1/runs/${runId}/snapshot`);
}

export async function takeAction(
  runId: string,
  verb: ActionVerb,
  targetId?: string,
  content?: string,
): Promise<RunSnapshot> {
  const body = await request<{ snapshot: RunSnapshot }>(
    `/v1/runs/${runId}/actions`,
    {
      method: "POST",
      body: JSON.stringify({
        idempotency_key: crypto.randomUUID(),
        verb,
        target_id: targetId,
        content,
      }),
    },
  );
  return body.snapshot;
}

export async function loadMemoryLineage(
  runId: string,
  propositionKey?: string,
): Promise<MemoryLineage> {
  const query = propositionKey
    ? `?proposition_key=${encodeURIComponent(propositionKey)}`
    : "";
  return request<MemoryLineage>(`/v1/runs/${runId}/memories${query}`);
}

export async function traceRumorWithHistorian(
  runId: string,
  propositionKey: string,
): Promise<HistorianTrace> {
  return request<HistorianTrace>(`/v1/runs/${runId}/historian/trace`, {
    method: "POST",
    body: JSON.stringify({ proposition_key: propositionKey }),
  });
}

export function clockLabel(snapshot: RunSnapshot): string {
  return `Day ${snapshot.day} · ${snapshot.phase}`;
}
