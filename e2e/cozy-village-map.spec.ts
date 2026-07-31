import { expect, test, type Page } from "@playwright/test";

type Direction = "ArrowDown" | "ArrowLeft" | "ArrowRight" | "ArrowUp";

async function walkFor(page: Page, key: Direction, milliseconds: number) {
  const town = page.getByLabel("Playable town of Greyhaven");
  await town.focus();
  await page.keyboard.down(key);
  await page.waitForTimeout(milliseconds);
  await page.keyboard.up(key);
  await page.waitForTimeout(80);
}

async function playerPoint(page: Page) {
  return page.getByLabel("Playable town of Greyhaven").evaluate((canvas) => ({
    x: Number((canvas as HTMLCanvasElement).dataset.playerX),
    y: Number((canvas as HTMLCanvasElement).dataset.playerY),
  }));
}

async function walkAxisTo(
  page: Page,
  axis: "x" | "y",
  target: number,
) {
  for (let attempt = 0; attempt < 6; attempt += 1) {
    const point = await playerPoint(page);
    const delta = target - point[axis];
    if (Math.abs(delta) <= 0.42) return;
    const key: Direction =
      axis === "x"
        ? delta > 0
          ? "ArrowRight"
          : "ArrowLeft"
        : delta > 0
          ? "ArrowDown"
          : "ArrowUp";
    await walkFor(
      page,
      key,
      Math.min(2_800, Math.max(140, Math.round(Math.abs(delta) * 400))),
    );
  }
  const point = await playerPoint(page);
  expect(Math.abs(target - point[axis])).toBeLessThanOrEqual(0.7);
}

async function walkTo(
  page: Page,
  x: number,
  y: number,
  order: "xy" | "yx" = "xy",
) {
  if (order === "xy") {
    await walkAxisTo(page, "x", x);
    await walkAxisTo(page, "y", y);
  } else {
    await walkAxisTo(page, "y", y);
    await walkAxisTo(page, "x", x);
  }
}

async function inspectLandmark(
  page: Page,
  label: string,
  panelHeading = label,
) {
  await page
    .locator(".landmark-access button")
    .filter({ hasText: `Locate ${label}` })
    .evaluate((button: HTMLButtonElement) => button.click());
  await page.getByLabel("Playable town of Greyhaven").press("t");

  if (label === "Notice board") {
    await expect(
      page.getByRole("region", { name: "Journal" }),
    ).toHaveAttribute("data-open", "true");
    await page.getByRole("button", { name: "Close journal" }).click();
    return;
  }

  const panel = page.getByLabel(label);
  await expect(
    panel.getByRole("heading", { name: panelHeading, exact: true }),
  ).toBeVisible();
  await panel.getByRole("button", { name: `Close ${label}` }).click();
}

async function talkToResident(
  page: Page,
  residentId: string,
  residentName: string,
) {
  await expect(
    page.getByRole("button", { name: `T Talk to ${residentName}` }),
  ).toBeVisible();
  await page.getByLabel("Playable town of Greyhaven").press("t");
  await expect(
    page.locator(`.portrait[data-npc-id="${residentId}"]`),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close conversation" }).click();
}

test("all twelve cozy-village landmarks are reachable and action-free", async ({
  page,
}) => {
  test.setTimeout(90_000);
  const failedAssets: string[] = [];
  const legacyRequests: string[] = [];

  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/world/greyhaven")) legacyRequests.push(url);
    if (
      url.includes("/world/farm-rpg/") &&
      response.status() >= 400
    ) {
      failedAssets.push(`${response.status()} ${url}`);
    }
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.getByRole("button", { name: "Take the road to Greyhaven" }).click();
  await expect(page.getByLabel("Playable town of Greyhaven")).toBeVisible();
  await page.getByRole("button", { name: "Close conversation" }).click();
  await expect(page.getByText(/Painting Greyhaven/)).toHaveCount(0);
  await expect(page.getByText("Story step 1 of 10")).toBeVisible();
  await page.screenshot({ path: ".qa/greyhaven-1440x900.png" });

  await page.setViewportSize({ width: 1280, height: 720 });
  await page.reload();
  await expect(page.getByLabel("Playable town of Greyhaven")).toBeVisible();
  await expect(page.getByText(/Painting Greyhaven/)).toHaveCount(0);
  await page.screenshot({ path: ".qa/greyhaven-1280x720.png" });
  await page.setViewportSize({ width: 760, height: 900 });
  await page.reload();
  await expect(page.getByLabel("Playable town of Greyhaven")).toBeVisible();
  await expect(page.getByText(/Painting Greyhaven/)).toHaveCount(0);
  await page.screenshot({ path: ".qa/greyhaven-760x900.png" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.reload();
  await expect(page.getByLabel("Playable town of Greyhaven")).toBeVisible();
  await expect(page.getByText(/Painting Greyhaven/)).toHaveCount(0);

  await inspectLandmark(page, "Road into town");
  await talkToResident(page, "marta", "Marta Vale");

  await walkTo(page, 25, 16.7);
  await walkTo(page, 25, 15.35);
  await page.screenshot({ path: ".qa/greyhaven-east-1440x900.png" });
  await inspectLandmark(page, "Midwife's cottage");
  await talkToResident(page, "talia", "Talia Fen");

  await walkTo(page, 22, 15.35);
  await walkTo(page, 22, 11.65);
  await walkTo(page, 23, 11.65);
  await inspectLandmark(page, "Market Row");
  await talkToResident(page, "bram", "Bram Coyle");

  await walkTo(page, 19, 11.65);
  await walkTo(page, 19, 8.15);
  await walkTo(page, 21, 8.15);
  await inspectLandmark(page, "Constable's post");
  await talkToResident(page, "elias", "Elias Ward");

  await walkTo(page, 21, 8.3);
  await walkTo(page, 25, 8.3);
  await walkTo(page, 25, 7.05);
  await page.screenshot({ path: ".qa/greyhaven-northeast-1440x900.png" });
  await inspectLandmark(page, "Chapel");
  await talkToResident(page, "orin", "Father Orin");

  await walkTo(page, 25, 8.15);
  await walkTo(page, 13, 8.15);
  await walkTo(page, 13, 6.1);
  await inspectLandmark(page, "Guildhouse");
  await talkToResident(page, "rhea", "Rhea Kest");

  await walkTo(page, 5, 6.1);
  await walkTo(page, 5, 5.25);
  await inspectLandmark(page, "Docks & harbor");
  await talkToResident(page, "nessa", "Nessa Reed");

  await walkTo(page, 5, 8);
  await walkTo(page, 9, 8);
  await inspectLandmark(page, "Back alley");

  await walkTo(page, 10, 8);
  await walkTo(page, 10, 12.75);
  await walkTo(page, 7, 12.75);
  await inspectLandmark(page, "The Gull & Anchor");
  await inspectLandmark(page, "Your rented room");

  await walkTo(page, 15, 12.75);
  await walkTo(page, 15, 10.55);
  await inspectLandmark(page, "Town square");
  await talkToResident(page, "pip", "Pip Marr");

  await walkTo(page, 17.35, 10.15);
  await inspectLandmark(page, "Notice board");

  await expect(page.getByText("Story step 1 of 10")).toBeVisible();
  expect(failedAssets).toEqual([]);
  expect(legacyRequests).toEqual([]);
});
