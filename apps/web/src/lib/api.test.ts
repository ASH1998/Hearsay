import { describe, expect, it } from "vitest";

import { clockLabel, type RunSnapshot } from "./api";

describe("clockLabel", () => {
  it("makes the action clock legible", () => {
    const snapshot = {
      day: 2,
      phase: "evening",
    } as RunSnapshot;

    expect(clockLabel(snapshot)).toBe("Day 2 · evening");
  });
});
