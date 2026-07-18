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
    .getByRole("button", { name: "Confront him about the price" })
    .click();

  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: /Find Pip/ }).click();
  await expect(
    page.locator(".conversation blockquote"),
  ).toHaveText(
    "The newcomer tried to ruin Bram in the middle of market row.",
  );

  await page.reload();
  await expect(
    page.getByText("Release the inn's shipment from Bram before evening."),
  ).toBeVisible();
  await expect(page.getByText("Tick 1")).toBeVisible();
});
