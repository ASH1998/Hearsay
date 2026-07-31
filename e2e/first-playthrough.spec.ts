import { expect, test } from "@playwright/test";

test("the default URL does not restore a legacy full-profile run", async ({
  page,
}) => {
  await page.goto("/?release_profile=full");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();
  await expect(page.getByLabel("Map of Greyhaven")).toBeVisible();

  const fullRunId = await page.evaluate(() =>
    window.localStorage.getItem("hearsay.run-id.full"),
  );
  expect(fullRunId).not.toBeNull();
  await page.evaluate((runId) => {
    window.localStorage.clear();
    window.localStorage.setItem("hearsay.run-id", runId);
  }, fullRunId as string);

  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Take the road to Greyhaven" }),
  ).toBeVisible();
  await expect(page.getByLabel("Map of Greyhaven")).toHaveCount(0);

  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();
  await expect(page.getByLabel("Playable town of Greyhaven")).toBeVisible();
});

async function walkFor(
  page: import("@playwright/test").Page,
  key: "ArrowDown" | "ArrowLeft" | "ArrowRight" | "ArrowUp",
  milliseconds: number,
) {
  const town = page.getByLabel("Playable town of Greyhaven");
  await town.focus();
  await page.keyboard.down(key);
  await page.waitForTimeout(milliseconds);
  await page.keyboard.up(key);
  await page.waitForTimeout(80);
}

async function talkTo(
  page: import("@playwright/test").Page,
  residentName: string,
) {
  await expect(
    page.getByRole("button", { name: `T Talk to ${residentName}` }),
  ).toBeVisible();
  await page.getByLabel("Playable town of Greyhaven").press("t");
}

test("the focused release completes its guided ten-action election", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();

  await expect(page.getByLabel("Playable town of Greyhaven")).toBeVisible();
  await expect(page.getByText("Story step 1 of 10")).toBeVisible();
  await expect(
    page
      .getByLabel("Current objective")
      .getByText(/Marta has stopped you on the road/),
  ).toBeVisible();

  await page
    .getByRole("button", { name: "Promise to fix the shipment" })
    .click();
  await expect(page.getByText("Story step 2 of 10")).toBeVisible();

  await walkFor(page, "ArrowUp", 1_950);
  await walkFor(page, "ArrowRight", 3_050);
  await talkTo(page, "Bram Coyle");
  await page.getByRole("button", { name: "Negotiate a deal" }).click();
  await expect(page.getByText("Story step 3 of 10")).toBeVisible();
  await expect(page.getByLabel("Visible gossip")).toBeVisible();

  await page
    .getByRole("button", { name: "Pay to release Marta's shipment" })
    .click();
  await expect(page.getByText("Story step 4 of 10")).toBeVisible();

  await walkFor(page, "ArrowDown", 500);
  await walkFor(page, "ArrowLeft", 6_100);
  await talkTo(page, "Marta Vale");
  await page.getByRole("button", { name: "Talk", exact: true }).click();
  await expect(page.getByText("Story step 5 of 10")).toBeVisible();

  await walkFor(page, "ArrowRight", 800);
  await walkFor(page, "ArrowDown", 480);
  await talkTo(page, "Talia Fen");
  await page
    .getByRole("button", { name: "Ask about Oswin's sick room" })
    .click();
  await expect(page.getByText("Story step 6 of 10")).toBeVisible();
  await page.getByRole("button", { name: "Help Oswin quietly" }).click();
  await expect(page.getByText("Day 2 · morning")).toBeVisible();
  await expect(page.getByText("Story step 7 of 10")).toBeVisible();

  await walkFor(page, "ArrowRight", 1_500);
  await walkFor(page, "ArrowUp", 3_100);
  await talkTo(page, "Rhea Kest");
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await expect(page.getByText("Story step 8 of 10")).toBeVisible();
  await page
    .getByRole("button", { name: "Question Rhea's ballot custody" })
    .click();
  await expect(page.getByText("Story step 9 of 10")).toBeVisible();
  await page.getByRole("button", { name: "Demand a public count" }).click();
  await expect(page.getByText("Story step 10 of 10")).toBeVisible();

  await page.getByRole("button", { name: "Talk", exact: true }).click();

  await expect(page.getByText("Day 3 · night")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "The Town Turns" }),
  ).toBeVisible();
  await expect(page.getByText("Newcomer 14–6 Rhea")).toBeVisible();
  await expect(
    page.getByLabel("Current objective").getByText(/Election resolved/),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Start a new story" }),
  ).toBeVisible();

  await page.reload();
  await expect(
    page.getByRole("heading", { name: "The Town Turns" }),
  ).toBeVisible();
  await expect(page.getByText("Newcomer 14–6 Rhea")).toBeVisible();
});
