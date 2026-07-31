import { expect, test } from "@playwright/test";

test("calming Bram and Nessa becomes durable election evidence", async ({
  page,
}) => {
  await page.goto("/?release_profile=full");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();

  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: /Find Rhea/ }).click();
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: /Find Pip/ }).click();
  await page.getByRole("button", { name: "Talk", exact: true }).click();

  await expect(
    page
      .getByRole("region", { name: "Town ledger" })
      .getByText("Bram and Nessa in the square"),
  ).toBeVisible();
  await expect(
    page.locator('[data-scene-event="public_argument"]'),
  ).toContainText("The square is choosing sides");
  await expect(
    page.getByRole("button", { name: /Find Bram/ }),
  ).toContainText("Town square");

  await page.getByRole("button", { name: "Calm the crowd" }).click();
  await expect(
    page.locator('[data-event-kind="argument_calmed"]'),
  ).toContainText("quiet");
  await expect(page.getByText("Chalk says: Influential")).toBeVisible();
  await expect(page.locator(".conversation blockquote")).toContainText(
    "peace sound almost interesting",
  );

  await page.reload();
  await expect(
    page.locator('[data-scene-event="public_argument"]'),
  ).toBeVisible();
  await expect(page.getByText("Chalk says: Influential")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Calm the crowd" }),
  ).toHaveCount(0);

  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await expect(page.getByText("Day 3 · morning")).toBeVisible();
  await expect(
    page.locator('[data-scene-event="public_argument"]'),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Sleep until morning" }).click();

  await expect(page.getByRole("heading", { name: "By One Voice" })).toBeVisible();
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "calm argument" })
      .first(),
  ).toBeVisible();
});
