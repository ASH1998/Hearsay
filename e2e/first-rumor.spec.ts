import { expect, test } from "@playwright/test";

test("a promise, confrontation, rumor, and refresh form one durable story", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();

  await expect(page.getByLabel("Town ledger")).toBeVisible();
  await expect(page.locator("canvas")).toBeVisible();

  await page.getByRole("button", { name: /Find Marta/ }).click();
  await page
    .getByRole("button", { name: "Promise to fix the shipment" })
    .click();
  await expect(
    page.getByText("Release the inn's shipment from Bram before evening."),
  ).toBeVisible();

  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: /Find Bram/ }).click();
  await page
    .getByRole("button", { name: "Negotiate a deal" })
    .click();
  await expect(
    page.locator('[data-event-kind="schedule_shift"]'),
  ).toContainText("Afternoon routines move");
  await expect(
    page.getByRole("button", { name: /Find Pip/ }),
  ).toContainText("Market row");

  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: /Find Pip/ }).click();
  await expect(
    page.locator(".conversation blockquote"),
  ).toHaveText(
    "The newcomer tried to ruin Bram in the middle of market row.",
  );
  await page.getByRole("button", { name: "Talk", exact: true }).click();
  await expect(page.getByText(/Memory-informed · 1 recalled/)).toBeVisible();
  await expect(page.getByText(/standing -10/)).toBeVisible();
  await expect(page.getByText(/Cold: the market-row rumor/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Set the record straight" }),
  ).toBeVisible();
  await expect(page.locator(".conversation blockquote")).toContainText(
    "ruin Bram",
  );

  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: "Trace Pip's rumor" }).click();
  await expect(page.getByRole("heading", { name: "Town Historian" })).toBeVisible();
  await expect(page.getByText("Development fallback · not MCP proof")).toBeVisible();
  await expect(page.getByText(/sponsor proof false/)).toBeVisible();
  await expect(
    page.getByText(
      "A price dispute became a claim about malicious intent.",
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close Town Historian" }).click();

  await page.getByRole("button", { name: /Find Bram/ }).click();
  await page
    .getByRole("button", { name: "Pay to release Marta's shipment" })
    .click();
  await expect(
    page.getByText("Kept · Marta's shipment was released"),
  ).toBeVisible();
  await expect(page.getByText("Chalk says: Reliable · Generous")).toBeVisible();
  await expect(
    page.getByLabel("Game clock").getByText("Storm over Greyhaven"),
  ).toBeVisible();
  await expect(
    page.locator('[data-event-kind="storm_begins"]'),
  ).toContainText("docks empty");

  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: /Find Marta/ }).click();
  await page.getByRole("button", { name: "Talk", exact: true }).click();
  await expect(page.getByText(/standing \+20/)).toBeVisible();
  await expect(page.getByText(/Grateful: they remember/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Ask for endorsement" }),
  ).toBeVisible();

  await page.reload();
  await expect(
    page.getByText("Release the inn's shipment from Bram before evening."),
  ).toBeVisible();
  await expect(
    page.getByText("Kept · Marta's shipment was released"),
  ).toBeVisible();
  await expect(page.getByText("Tick 2")).toBeVisible();
  await expect(
    page.getByLabel("Game clock").getByText("Storm over Greyhaven"),
  ).toBeVisible();

  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await expect(page.getByText("Day 2 · morning")).toBeVisible();
  await page.getByRole("button", { name: /Find Rhea/ }).click();
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await expect(
    page.getByText("Ballot: the newcomer is standing against Rhea"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close conversation" }).click();

  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await expect(page.getByText("Day 3 · morning")).toBeVisible();
  await page.getByRole("button", { name: "Sleep until morning" }).click();

  await expect(page.getByRole("heading", { name: "By One Voice" })).toBeVisible();
  await expect(page.getByText("Newcomer 11–9 Rhea")).toBeVisible();
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "shipment promise was kept" })
      .filter({ hasText: "v1" }),
  ).toBeVisible();
});
