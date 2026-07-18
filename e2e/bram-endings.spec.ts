import { expect, test } from "@playwright/test";

test("threatening Bram becomes a remembered run-out-of-town ending", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();

  await page.getByRole("button", { name: /Find Bram/ }).click();
  await page.getByRole("button", { name: "Threaten him quietly" }).click();
  await expect(
    page.locator('[data-event-kind="bram_threatened"]'),
  ).toContainText("market goes still");
  await expect(
    page.getByText("Chalk says: Dangerous · Troublemaker"),
  ).toBeVisible();
  await expect(page.locator(".conversation blockquote")).toContainText(
    "threat is a debt",
  );

  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await expect(page.getByText("Day 2 · morning")).toBeVisible();
  await page.getByRole("button", { name: /Find Rhea/ }).click();
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await page.getByRole("button", { name: "Close conversation" }).click();

  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();

  await expect(
    page.getByRole("heading", { name: "The Road Remembers" }),
  ).toBeVisible();
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "threaten approach" })
      .first(),
  ).toBeVisible();
});
