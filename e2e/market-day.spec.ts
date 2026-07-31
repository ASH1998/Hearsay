import { expect, test } from "@playwright/test";

test("Market Day visibly crowds the row and makes Bram harder to reach", async ({
  page,
}) => {
  await page.goto("/?release_profile=full");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();

  await expect(
    page.locator('[data-town-event-key="market_day"]'),
  ).toContainText("Market Day at the row");
  await expect(
    page.locator('[data-scene-event="market_day"]'),
  ).toContainText("Three stalls · half the coast");
  await expect(
    page.locator('[data-scene-event="market_day"]'),
  ).toHaveAttribute("data-market-stalls", "3");
  await expect(
    page.locator('[data-scene-event="market_day"]'),
  ).toHaveAttribute("data-market-crowd", "8");
  await expect(page.locator("main.game")).toHaveAttribute(
    "data-market-audio",
    "active",
  );
  await expect(
    page.locator('[data-event-kind="market_day_begins"]'),
  ).toContainText("half the coast");

  const findBram = page.getByRole("button", { name: /Find Bram/ });
  await expect(findBram).toContainText("Busy at Market row");
  await findBram.click();
  await expect(page.getByText("Market Day has Bram buried")).toBeVisible();
  const talk = page
    .locator(".conversation")
    .getByRole("button", { name: "Talk", exact: true });
  await expect(talk).toBeDisabled();
  await expect(page.locator(".conversation blockquote")).toContainText(
    "Half the coast",
  );

  await page
    .getByRole("navigation", { name: "Walk through Greyhaven" })
    .getByRole("button", { name: "Town square" })
    .click();
  await page
    .getByRole("navigation", { name: "Walk through Greyhaven" })
    .getByRole("button", { name: "Market row" })
    .click();
  await expect(talk).toBeEnabled();

  await page.reload();
  await expect(
    page.locator('[data-town-event-key="market_day"]'),
  ).toBeVisible();
  await expect(
    page.locator('[data-scene-event="market_day"]'),
  ).toHaveAttribute("data-market-stalls", "3");
  await page.getByRole("button", { name: /Find Bram/ }).click();

  const restoredTalk = page
    .locator(".conversation")
    .getByRole("button", { name: "Talk", exact: true });
  await expect(restoredTalk).toBeEnabled();
  await restoredTalk.click();
  await restoredTalk.click();

  await expect(
    page.locator('[data-scene-event="market_day"]'),
  ).toHaveCount(0);
  await expect(
    page.locator('[data-scene-event="public_argument"]'),
  ).toBeVisible();
  await expect(
    page.locator('[data-event-kind="public_argument_begins"]'),
  ).toContainText("forms a ring");
});
