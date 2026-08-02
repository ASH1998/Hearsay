import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

type ReplayBundle = {
  id: string;
  outcome: {
    ending: string;
    player_votes: number;
    rhea_votes: number;
  };
  frames: Array<{
    action: string;
    duration_ms: number;
    snapshot: {
      action_count: number;
      election?: { ending: { key: string } } | null;
      run_id: string;
    };
  }>;
};

function loadReplay(id: string): ReplayBundle {
  const path = resolve(process.cwd(), "public", "replays", `${id}.json`);
  return JSON.parse(readFileSync(path, "utf8")) as ReplayBundle;
}

describe("recorded replay bundles", () => {
  it.each([
    ["trusted-win", "landslide", 15, 5],
    ["remembered-loss", "exposed", 10, 10],
  ])("keeps %s internally coherent", (id, ending, playerVotes, rheaVotes) => {
    const replay = loadReplay(id);

    expect(replay.id).toBe(id);
    expect(replay.frames).toHaveLength(19);
    expect(replay.frames[0].action).toBe("arrival");
    expect(replay.frames.every((frame) => frame.duration_ms >= 900)).toBe(true);
    expect(
      replay.frames.every(
        (frame, index) =>
          index === 0 ||
          frame.snapshot.action_count >= replay.frames[index - 1].snapshot.action_count,
      ),
    ).toBe(true);

    const finalSnapshot = replay.frames.at(-1)?.snapshot;
    expect(finalSnapshot?.election?.ending.key).toBe(ending);
    expect(replay.outcome).toMatchObject({
      ending,
      player_votes: playerVotes,
      rhea_votes: rheaVotes,
    });
  });

  it("contains no cloud credentials or database URLs", () => {
    for (const id of ["trusted-win", "remembered-loss"]) {
      const replay = JSON.stringify(loadReplay(id));
      expect(replay).not.toMatch(/DATABASE_URL|AWS_SECRET|COCKROACH_MCP_API_KEY/i);
      expect(replay).not.toMatch(/cockroachdb\+psycopg|postgresql:\/\//i);
    }
  });
});
