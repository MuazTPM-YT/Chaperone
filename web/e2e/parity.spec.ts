// gate check: the slide 2 and 3 messages render the same in the new page as in the old one.
// The old page (chaperone/static/index.html, removed after the switch) is read from git history and runs live;
// its exact answers are then replayed into the new page, so both draw the same data.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const OLD = "/static/index.html";
const LAST_OLD = "24f3d64";  // the last commit that still had the old page
const OLD_PAGE = execFileSync("git", ["show", `${LAST_OLD}:chaperone/static/index.html`], { cwd: path.join(__dirname, "../.."), maxBuffer: 1 << 24 });
// tall enough that a whole turn fits without scrolling, so one picture holds the top bar, the rail and the turn
test.use({ viewport: { width: 1600, height: 2600 } });

async function shot(page: Page) {
  await page.locator("#stage").evaluate((e) => e.scrollTo(0, 0));
  return page.screenshot({ animations: "disabled" });
}
// slide 2: Q3 revenue (ours and Apple's), tamoxifen, Udupi cardiologist, Rahul's salary; slide 3: the same plus the Hinglish HbA1c run
const SCENARIOS = ["6a", "6b", "8a", "8b", "2a", "2b"];
const HINGLISH = "Rakesh ka HbA1c 9.1 aaya, doctor ne metformin shuru kiya. Next week ki review meeting reschedule karo.";

async function finished(page: Page) {
  await expect(page.locator("#turn-0 .outcome")).toBeVisible({ timeout: 120_000 });
  await expect(page.locator('#turn-0 [aria-label="Loading comparison"]')).toHaveCount(0, { timeout: 60_000 });
  await expect(page.locator("#send")).toHaveAttribute("aria-busy", "false");
}

// open every Details panel, then read the turn as a person would
async function read(page: Page) {
  const closed = page.locator("#turn-0 details.more:not([open]) > summary");
  for (let n = 0; n < 6 && await closed.count(); n++) await closed.first().click();
  await page.waitForTimeout(450);  // the crossing animations
  const text = await page.locator("#turn-0").innerText();
  return text.replace(/\s+/g, " ").trim();
}

async function run(page: Page, start: (p: Page) => Promise<void>) {
  await start(page);
  await finished(page);
  return read(page);
}

for (const id of [...SCENARIOS, "hinglish"]) {
  test(`gate 4: ${id} renders the same as the old page`, async ({ page }, info) => {
    const start = async (p: Page) => {
      if (id === "hinglish") { await p.locator("#text").fill(HINGLISH); await p.locator("#text").press("Enter"); }
      else await p.locator(`#scenarios [data-id="${id}"]`).click();
    };
    // the old page's real answers pass through here once, and are kept for the replay
    const bodies: Record<string, Buffer> = {};
    for (const path of ["/api/chat/stream", "/api/baseline"]) {
      await page.route(path, async (r) => {
        const res = await r.fetch();
        bodies[path] = await res.body();
        await r.fulfill({ response: res, body: bodies[path] });
      });
    }
    await page.route(OLD, (r) => r.fulfill({ status: 200, contentType: "text/html", body: OLD_PAGE }));
    await page.goto(OLD);
    await expect(page.locator("#scenarios button").first()).toBeVisible();
    const oldText = await run(page, start);
    const oldShot = await shot(page);

    await page.unrouteAll();
    await page.route("/api/chat/stream", (r) => r.fulfill({ status: 200, contentType: "application/x-ndjson", body: bodies["/api/chat/stream"] }));
    await page.route("/api/baseline", (r) => bodies["/api/baseline"] ? r.fulfill({ status: 200, contentType: "application/json", body: bodies["/api/baseline"] }) : r.continue());
    await page.goto("/");
    await expect(page.locator("#scenarios button").first()).toBeVisible();
    const newText = await run(page, start);
    expect(newText).toBe(oldText);

    // same pixels, within anti-aliasing noise: the old page's picture is the expected one
    const snap = info.snapshotPath(`${id}.png`);
    fs.mkdirSync(path.dirname(snap), { recursive: true });
    fs.writeFileSync(snap, oldShot);
    expect(await shot(page)).toMatchSnapshot(`${id}.png`, { maxDiffPixelRatio: 0.002 });
  });
}
