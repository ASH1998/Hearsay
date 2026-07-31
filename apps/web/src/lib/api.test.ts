import { describe, expect, it } from "vitest";

import { normalizeSnapshot, type RunSnapshot } from "./api";

describe("normalizeSnapshot", () => {
  it("upgrades a saved snapshot created before chat history existed", () => {
    const legacySnapshot = {
      run_id: "legacy-run",
    } as unknown as RunSnapshot;

    expect(normalizeSnapshot(legacySnapshot).conversation_history).toEqual([]);
  });
});
