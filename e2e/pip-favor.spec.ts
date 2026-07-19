import { expect, test } from "@playwright/test";

async function acceptFavor(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();
  await page.getByRole("button", { name: /Find Pip/ }).click();
  await page
    .getByRole("button", { name: "Ask for Pip's ballot source" })
    .click();
  await expect(page.getByText("Pip's ballot source")).toBeVisible();
}

async function finishElection(page: import("@playwright/test").Page) {
  await page.reload();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: /Find Rhea/ }).click();
  await page
    .getByRole("button", { name: "Declare candidacy for mayor" })
    .click();
  await page.getByRole("button", { name: "Close conversation" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
  await page.getByRole("button", { name: "Sleep until morning" }).click();
}

test("tracing Kit's receipt visibly anchors Pip's rumor", async ({ page }) => {
  await acceptFavor(page);
  await page.getByRole("button", { name: "Trace Kit's receipt" }).click();

  await expect(
    page.locator('[data-event-kind="pip_source_verified"]'),
  ).toContainText("Edda verifies");
  await expect(
    page.getByText("Source verified · Kit's receipt anchors the story"),
  ).toBeVisible();
  await expect(
    page.getByText("Chalk says: Reliable · Influential"),
  ).toBeVisible();
  await expect(
    page.locator(".speech-bubble").filter({ hasText: "Pip" }).first(),
  ).toBeVisible();

  await finishElection(page);
  await expect(
    page.getByRole("heading", { name: "The Town Turns" }),
  ).toBeVisible();
  await expect(page.getByText("Newcomer 15–5 Rhea")).toBeVisible();
});

test("embellishing Pip's rumor visibly mutates into a narrow loss", async ({
  page,
}) => {
  await acceptFavor(page);
  await page
    .getByRole("button", { name: "Make it ballot stuffing" })
    .click();

  await expect(
    page.locator('[data-event-kind="pip_rumor_embellished"]'),
  ).toContainText("unsupported detail");
  await expect(
    page.getByText("Embellished publicly · unsupported detail spreading"),
  ).toBeVisible();
  await expect(
    page.getByText("Chalk says: Influential · Troublemaker"),
  ).toBeVisible();
  await expect(
    page.locator(".speech-bubble").filter({ hasText: "Pip" }).first(),
  ).toBeVisible();

  await finishElection(page);
  await expect(
    page.getByRole("heading", { name: "The Tied Bell" }),
  ).toBeVisible();
  await expect(page.getByText("Newcomer 8–12 Rhea")).toBeVisible();
  await expect(
    page
      .locator(".historian small")
      .filter({ hasText: "embellished Kit's tally-sheet" })
      .first(),
  ).toBeVisible();
});
