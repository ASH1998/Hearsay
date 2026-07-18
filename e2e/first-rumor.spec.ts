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
  await expect(
    page.getByText(
      "A price dispute became a claim about malicious intent.",
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close Town Historian" }).click();

  await page.reload();
  await expect(
    page.getByText("Release the inn's shipment from Bram before evening."),
  ).toBeVisible();
  await expect(page.getByText("Tick 1")).toBeVisible();
});
