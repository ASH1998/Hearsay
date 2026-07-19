import { expect, test } from "@playwright/test";

async function reachCompact(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: /Find Rhea/ }).click();
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await page
    .getByRole("button", { name: "Question Rhea's ballot custody" })
    .click();

  await expect(
    page.locator('[data-event-kind="rhea_compact_offered"]'),
  ).toContainText("sole ballot custody");
  await expect(page.getByText("Rhea's ballot compact")).toBeVisible();
  await expect(
    page.locator('[data-ballot-custody="unresolved"]'),
  ).toContainText("under negotiation");
}

async function finishElection(page: import("@playwright/test").Page) {
  await page.reload();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
}

test("challenging Rhea opens the count and wins by one voice", async ({
  page,
}) => {
  await reachCompact(page);
  await page.getByRole("button", { name: "Demand a public count" }).click();

  await expect(
    page.locator('[data-event-kind="rhea_ballot_challenged"]'),
  ).toContainText("independent witnesses");
  await expect(
    page.getByText("Public count demanded · independent witnesses posted"),
  ).toBeVisible();
  await expect(
    page.locator('[data-ballot-custody="challenged"]'),
  ).toContainText("Elias and Edda witnessing");
  await expect(
    page.getByText("Chalk says: Reliable · Troublemaker"),
  ).toBeVisible();

  await finishElection(page);
  await expect(
    page.getByRole("heading", { name: "By One Voice" }),
  ).toBeVisible();
  await expect(page.getByText("Newcomer 12–8 Rhea")).toBeVisible();
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "exposed the poll book's missing" })
      .first(),
  ).toBeVisible();
});

test("signing Rhea's compact preserves guild custody and wins the market", async ({
  page,
}) => {
  await reachCompact(page);
  await page.getByRole("button", { name: "Sign Rhea's compact" }).click();

  await expect(
    page.locator('[data-event-kind="rhea_compact_signed"]'),
  ).toContainText("sole ballot custody");
  await expect(
    page.getByText("Guild compact signed · sole custody preserved"),
  ).toBeVisible();
  await expect(
    page.locator('[data-ballot-custody="made_deal"]'),
  ).toContainText("compact posted");
  await expect(page.getByText("Chalk says: Influential")).toBeVisible();

  await finishElection(page);
  await expect(
    page.getByRole("heading", { name: "The Town Turns" }),
  ).toBeVisible();
  await expect(page.getByText("Newcomer 14–6 Rhea")).toBeVisible();
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "signed Rhea's compact" })
      .first(),
  ).toBeVisible();
});
