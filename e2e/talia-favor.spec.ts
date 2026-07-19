import { expect, test } from "@playwright/test";

async function acceptFavor(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();
  await page.getByRole("button", { name: /Find Talia/ }).click();
  await page
    .getByRole("button", { name: "Ask about Oswin's sick room" })
    .click();
  await expect(page.getByText("Talia's sick-house request")).toBeVisible();
}

async function finishElection(
  page: import("@playwright/test").Page,
  tally: string,
  ending: string,
) {
  await page.reload();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: /Find Rhea/ }).click();
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await expect(page.getByRole("heading", { name: ending })).toBeVisible();
  await expect(page.getByText(tally)).toBeVisible();
}

test("quietly helping Oswin earns Talia's durable family backing", async ({
  page,
}) => {
  await acceptFavor(page);
  await page.getByRole("button", { name: "Help Oswin quietly" }).click();

  await expect(
    page.locator('[data-event-kind="talia_sick_house_helped"]'),
  ).toContainText("willow draught");
  await expect(
    page.getByText("Helped quietly · Talia's family backing earned"),
  ).toBeVisible();
  await expect(
    page.getByText("Chalk says: Generous · Reliable"),
  ).toBeVisible();

  await finishElection(page, "Newcomer 12–8 Rhea", "By One Voice");
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "quietly brought Oswin care" })
      .first(),
  ).toBeVisible();
});

test("warning through Pip visibly breaks sick-house confidence", async ({
  page,
}) => {
  await acceptFavor(page);
  await page
    .getByRole("button", { name: "Warn Greyhaven through Pip" })
    .click();

  await expect(
    page.locator('[data-event-kind="talia_sick_house_gossiped"]'),
  ).toContainText("breaking the sick room's privacy");
  await expect(
    page.getByText("Warned publicly · family confidence broken"),
  ).toBeVisible();
  await expect(page.getByText("Chalk says: Influential")).toBeVisible();

  await finishElection(page, "Newcomer 9–11 Rhea", "The Tied Bell");
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "private warning" })
      .first(),
  ).toBeVisible();
});
