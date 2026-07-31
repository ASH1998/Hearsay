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
  await page.getByLabel("Tell Marta anything").fill("hello!");
  await page.getByRole("button", { name: "Say it" }).click();
  await expect(
    page
      .getByLabel("Chat with Marta Vale")
      .getByText("Hello. Come in—what can I do for you?"),
  ).toBeVisible();
  await expect(page.getByText(/I will remember you said/i)).toHaveCount(0);
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

test("the focused release completes an eighteen-action memory campaign", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();

  await expect(page.getByLabel("Playable town of Greyhaven")).toBeVisible();
  await expect(page.getByText("Story step 1 of 18")).toBeVisible();
  await expect(
    page
      .getByLabel("Current objective")
      .getByText(/Marta has stopped you on the road/),
  ).toBeVisible();
  const portraitBox = await page.locator(".conversation .portrait").boundingBox();
  expect(portraitBox).not.toBeNull();
  expect(
    Math.abs((portraitBox?.width ?? 0) - (portraitBox?.height ?? 0)),
  ).toBeLessThan(2);
  const openingChatInput = page.getByLabel("Tell Marta anything");
  await openingChatInput.click();
  await page.keyboard.type("wasd t space");
  await expect(openingChatInput).toHaveValue("wasd t space");
  await expect(
    page.getByLabel("Share this message with the town"),
  ).not.toBeChecked();
  await expect(
    page.getByLabel("Share this message with the town"),
  ).toBeEnabled();
  await openingChatInput.fill("");

  await page
    .getByRole("button", { name: "Promise to fix the shipment" })
    .click();
  await expect(page.getByText("Story step 2 of 18")).toBeVisible();

  await walkFor(page, "ArrowUp", 1_950);
  await walkFor(page, "ArrowRight", 3_050);
  await talkTo(page, "Bram Coyle");
  await page.getByRole("button", { name: "Negotiate a deal" }).click();
  await expect(page.getByText("Story step 3 of 18")).toBeVisible();
  await expect(page.getByLabel("Visible gossip")).toBeVisible();
  await expect(
    page.getByLabel("Visible gossip").getByText("Agent memory"),
  ).toBeVisible();
  await expect(
    page.getByLabel("Visible gossip").getByText(/committed to CockroachDB/),
  ).toBeVisible();
  await expect(page.getByLabel("Autonomous agent turn")).toBeVisible();
  await expect(
    page
      .getByLabel("Autonomous agent turn")
      .getByText("Recall", { exact: true }),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Autonomous agent turn")
      .getByText("Decide", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Autonomous agent turn").getByText("Act", { exact: true }),
  ).toBeVisible();

  await page
    .getByRole("button", { name: "Pay to release Marta's shipment" })
    .click();
  await expect(page.getByText("Story step 4 of 18")).toBeVisible();

  await walkFor(page, "ArrowDown", 500);
  await walkFor(page, "ArrowLeft", 6_100);
  await talkTo(page, "Marta Vale");
  await page
    .getByLabel("Tell Marta anything")
    .fill("Please remember that I kept my promise and released your shipment.");
  await page.getByRole("button", { name: "Say it" }).click();
  await expect(page.getByText("Story step 5 of 18")).toBeVisible();
  await expect(
    page
      .getByLabel("Chat with Marta Vale")
      .getByText("Please remember that I kept my promise and released your shipment."),
  ).toBeVisible();
  await expect(
    page.getByLabel("Chat with Marta Vale").locator(".chat-message--npc").last(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close conversation" }).click();

  await walkFor(page, "ArrowRight", 800);
  await walkFor(page, "ArrowDown", 480);
  await talkTo(page, "Talia Fen");
  await page
    .getByRole("button", { name: "Ask about Oswin's sick room" })
    .click();
  await expect(page.getByText("Story step 6 of 18")).toBeVisible();
  await page.getByRole("button", { name: "Help Oswin quietly" }).click();
  await expect(page.getByText("Day 2 · morning")).toBeVisible();
  await expect(page.getByText("Story step 7 of 18")).toBeVisible();

  await walkFor(page, "ArrowRight", 1_500);
  await walkFor(page, "ArrowUp", 3_100);
  await talkTo(page, "Rhea Kest");
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await expect(page.getByText("Story step 8 of 18")).toBeVisible();
  await page
    .getByRole("button", { name: "Question Rhea's ballot custody" })
    .click();
  await expect(page.getByText("Story step 9 of 18")).toBeVisible();
  await page.getByRole("button", { name: "Demand a public count" }).click();
  await expect(page.getByText("Story step 10 of 18")).toBeVisible();

  const campaignMessages = [
    "Remember that Pip saw the replacement tally sheets.",
    "What did I tell you about Pip and the tally sheets?",
    "Elias says a public count is fair.",
    "Rhea rigged the last election and that was unfair.",
    "What does the town remember about Rhea?",
    "I helped Talia and protected Oswin's privacy.",
    "Bram cares more about leverage than fairness.",
    "Which of my promises will voters remember?",
    "Tell me what memory will decide your vote.",
  ];
  for (const [index, message] of campaignMessages.entries()) {
    const input = page.getByLabel("Tell Rhea anything");
    await input.fill(message);
    await page.getByRole("button", { name: "Say it" }).click();
    if (index === 1) {
      await expect(page.getByLabel("Long-term memories recalled")).toBeVisible();
      await expect(
        page
          .getByLabel("Long-term memories recalled")
          .getByText("individual memory")
          .first(),
      ).toBeVisible();
      await expect(
        page
          .getByLabel("Long-term memories recalled")
          .getByText(/replacement tally sheets/),
      ).toBeVisible();
    }
  }

  await expect(page.getByText("Day 3 · night")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "The Town Turns" }),
  ).toBeVisible();
  await expect(page.getByText("Newcomer 15–5 Rhea")).toBeVisible();
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
  await expect(page.getByText("Newcomer 15–5 Rhea")).toBeVisible();
});
