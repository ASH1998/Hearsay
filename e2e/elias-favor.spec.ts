import { expect, test } from "@playwright/test";

async function acceptFavor(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();
  await page.getByRole("button", { name: /Find Elias/ }).click();
  await page
    .getByRole("button", { name: "Ask about Elias's old arrest" })
    .click();
  await expect(
    page.getByText("Elias's omitted arrest correction"),
  ).toBeVisible();
}

async function finishElection(page: import("@playwright/test").Page) {
  await page.reload();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: /Find Rhea/ }).click();
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
}

test("reopening Tob's arrest creates public legitimacy and multi-hop proof", async ({
  page,
}) => {
  await acceptFavor(page);
  await page.getByRole("button", { name: "Reopen Tob's arrest" }).click();

  await expect(
    page.locator('[data-event-kind="elias_arrest_investigated"]'),
  ).toContainText("public ledger");
  await expect(
    page.getByText("Record corrected · Tob publicly cleared"),
  ).toBeVisible();
  await expect(
    page.getByText("Chalk says: Reliable · Influential"),
  ).toBeVisible();

  await finishElection(page);
  await expect(
    page.getByRole("heading", { name: "The Town Turns" }),
  ).toBeVisible();
  await expect(page.getByText("Newcomer 16–4 Rhea")).toBeVisible();
});

test("covering Elias's arrest record becomes a witnessed Exposed ending", async ({
  page,
}) => {
  await acceptFavor(page);
  await page
    .getByRole("button", { name: "Keep the correction buried" })
    .click();

  await expect(
    page.locator('[data-event-kind="elias_arrest_covered"]'),
  ).toContainText("Tob witnesses");
  await expect(
    page.getByText("Correction destroyed · Tob witnessed it"),
  ).toBeVisible();
  await expect(page.getByText("Chalk says: Dishonest")).toBeVisible();

  await finishElection(page);
  await expect(
    page.getByRole("heading", { name: "The Story Unravels" }),
  ).toBeVisible();
  await expect(page.getByText("Newcomer 0–20 Rhea")).toBeVisible();
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "helped Elias destroy" })
      .first(),
  ).toBeVisible();
});
