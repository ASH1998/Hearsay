import { expect, test } from "@playwright/test";

async function declare(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: /Find Rhea/ }).click();
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await page.getByRole("button", { name: "Close conversation" }).click();
}

test("an unsupported candidacy ends in humiliation", async ({ page }) => {
  await declare(page);
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();

  await expect(
    page.getByRole("heading", { name: "No Seconding Voice" }),
  ).toBeVisible();
});

test("one square speech reaches an audited ten-ten narrow loss", async ({
  page,
}) => {
  await declare(page);
  await page.getByRole("button", { name: "Address the square" }).click();
  await expect(
    page.locator('[data-event-kind="square_speech"]'),
  ).toContainText("not every listener");
  await expect(page.getByText("Chalk says: Influential")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Address the square" }),
  ).toHaveCount(0);

  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();

  await expect(page.getByRole("heading", { name: "The Tied Bell" })).toBeVisible();
  await expect(page.getByText("Newcomer 10–10 Rhea")).toBeVisible();
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "square speech" })
      .first(),
  ).toBeVisible();
});
