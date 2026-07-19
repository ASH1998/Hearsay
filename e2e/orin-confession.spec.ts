import { expect, test } from "@playwright/test";

async function acceptConfession(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();
  await page.getByRole("button", { name: /Find Orin/ }).click();
  await page
    .getByRole("button", { name: "Accept the sealed confession" })
    .click();
  await expect(page.getByText("Orin's sealed confession")).toBeVisible();
}

async function finishElection(
  page: import("@playwright/test").Page,
  ending = "By One Voice",
  margin = "13–7",
) {
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: /Find Rhea/ }).click();
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await expect(page.getByRole("heading", { name: ending })).toBeVisible();
  await expect(page.getByText(`Newcomer ${margin} Rhea`)).toBeVisible();
}

test("revealing Orin's confession becomes visible election evidence", async ({
  page,
}) => {
  await acceptConfession(page);
  await page.getByRole("button", { name: "Reveal the confession" }).click();

  await expect(
    page.locator('[data-event-kind="orin_confession_revealed"]'),
  ).toContainText("Rhea changed two marks");
  await expect(
    page.getByText("Revealed publicly · Orin's confidence broken"),
  ).toBeVisible();
  await expect(page.getByText("Chalk says: Reliable")).toBeVisible();

  await page.reload();
  await expect(
    page.getByText("Revealed publicly · Orin's confidence broken"),
  ).toBeVisible();
  await finishElection(page);
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "revealed Orin's account" })
      .first(),
  ).toBeVisible();
});

test("concealing Orin's confession earns his durable elder blessing", async ({
  page,
}) => {
  await acceptConfession(page);
  await page
    .getByRole("button", { name: "Keep the confession sealed" })
    .click();

  await expect(
    page.locator('[data-event-kind="orin_confession_concealed"]'),
  ).toContainText("publicly blesses");
  await expect(
    page.getByText("Kept sealed · Orin's blessing earned"),
  ).toBeVisible();
  await expect(page.getByText("Chalk says: Influential")).toBeVisible();

  await page.reload();
  await expect(
    page.getByText("Kept sealed · Orin's blessing earned"),
  ).toBeVisible();
  await finishElection(page, "The Town Turns", "14–6");
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "blessed the player's decision" })
      .first(),
  ).toBeVisible();
});
