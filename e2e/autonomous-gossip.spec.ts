import { expect, test } from "@playwright/test";

test("a resident carries Pip's rumor onward on a later tick", async ({
  page,
}) => {
  await page.goto("/?release_profile=full");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();

  await page.getByRole("button", { name: /Find Marta/ }).click();
  await page
    .getByRole("button", { name: "Promise to fix the shipment" })
    .click();
  await page.getByRole("button", { name: "Close conversation" }).click();

  await page.getByRole("button", { name: /Find Bram/ }).click();
  await page.getByRole("button", { name: "Negotiate a deal" }).click();
  await page
    .getByRole("button", { name: "Pay to release Marta's shipment" })
    .click();
  await page.getByRole("button", { name: "Close conversation" }).click();

  await page.getByRole("button", { name: /Find Elias/ }).click();
  await page.getByRole("button", { name: "Talk", exact: true }).click();

  await expect(
    page.locator('[data-event-kind="rumor_continues"]'),
  ).toContainText("Hettie Voss");
  await expect(
    page.locator(".speech-bubble small").filter({ hasText: "Hettie Voss →" }),
  ).toHaveCount(2);
  await expect(
    page.locator(".speech-bubble small").filter({ hasText: "hop 3" }),
  ).toHaveCount(2);

  await page.reload();
  await expect(
    page.locator(".speech-bubble small").filter({ hasText: "Hettie Voss →" }),
  ).toHaveCount(2);
  await expect(
    page.locator(".speech-bubble small").filter({ hasText: "hop 3" }),
  ).toHaveCount(2);

  await page.getByRole("button", { name: /Find Nessa/ }).click();
  await page.getByRole("button", { name: "Talk", exact: true }).click();
  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: /Find Orin/ }).click();
  await page.getByRole("button", { name: "Talk", exact: true }).click();
  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: /Find Rhea/ }).click();
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();

  await expect(
    page.getByRole("heading", { name: "By One Voice" }),
  ).toBeVisible();
  await expect(page.getByText("Newcomer 12–8 Rhea")).toBeVisible();
});
