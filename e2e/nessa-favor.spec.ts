import { expect, test } from "@playwright/test";

test("Nessa's harbor log becomes a public correction and endorsement", async ({
  page,
}) => {
  await page.goto("/?release_profile=full");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();

  await page.getByRole("button", { name: /Find Nessa/ }).click();
  await page
    .getByRole("button", { name: "Offer to carry the harbor log" })
    .click();
  await expect(page.getByText("Nessa's harbor log")).toBeVisible();
  await page.getByRole("button", { name: "Close conversation" }).click();

  await page.getByRole("button", { name: /Find Elias/ }).click();
  await page
    .getByRole("button", { name: "Give Elias the harbor log" })
    .click();
  await expect(
    page.getByText("Delivered to Elias · correct Pip's story"),
  ).toBeVisible();
  await expect(page.getByText("Chalk says: Reliable")).toBeVisible();
  await page.getByRole("button", { name: "Close conversation" }).click();

  await page.getByRole("button", { name: /Find Pip/ }).click();
  await page.getByRole("button", { name: "Correct the storm rumor" }).click();
  await expect(
    page.getByText("Corrected publicly · endorsement available"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close conversation" }).click();

  await page.getByRole("button", { name: /Find Nessa/ }).click();
  await page
    .getByRole("button", { name: "Ask for the harbor's endorsement" })
    .click();
  await expect(
    page.getByText("Chalk says: Reliable · Influential"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close conversation" }).click();

  await page.getByRole("button", { name: /Find Rhea/ }).click();
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();

  await page.reload();
  await expect(
    page.getByText("Corrected publicly · endorsement available"),
  ).toBeVisible();
  await expect(
    page.getByText("Chalk says: Reliable · Influential"),
  ).toBeVisible();

  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await expect(
    page.getByRole("heading", { name: "The Town Turns" }),
  ).toBeVisible();
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "harbor log proved" })
      .first(),
  ).toBeVisible();
});
