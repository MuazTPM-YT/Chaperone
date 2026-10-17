// nothing from outside, the local model offline or turned off, and the gateway itself down (checklist P5, O)
import { expect, test } from "@playwright/test";
import { NORMAL, OFFLINE, done, scenario, step, type } from "./helpers";

test("P5 the page loads nothing from outside this laptop", async ({ page }) => {
  const urls: string[] = [];
  page.on("request", (r) => urls.push(r.url()));
  await scenario(page, "8a");
  await done(page);
  await page.locator("#rules-open").click();
  await expect(page.locator("#rules-dlg .rule-card").first()).toBeVisible();
  expect(urls.length).toBeGreaterThan(5);
  expect(urls.filter((u) => !u.startsWith(`${NORMAL}/`))).toEqual([]);
});

test("O1 O3 local model offline: status says so and an external send is refused", async ({ page }) => {
  await scenario(page, "8a", OFFLINE);
  const turn = await done(page);
  await expect(page.locator("#ctx-status")).toHaveText("Local AI check: offline");
  await expect(page.locator("#ctx-status .dot")).toHaveClass(/off/);
  const find = step(page, "Find what is sensitive");
  await expect(find).toHaveClass(/warn/);
  await expect(find.locator(".callout")).toHaveText("Local checks are offline, so nothing goes to an external AI.");
  await expect(step(page, "Try to work out who and what").locator(".step-s")).toHaveText("The local AI is not available, so no attack ran.");
  await expect(turn.locator(".outcome.stop")).toContainText("Blocked. Nothing left this laptop.");
  await expect(turn.locator(".outcome + .note-s")).toHaveText("Rule local-checks-offline: Local checks are offline, so nothing goes to an external AI.");
  await expect(turn.locator(".cell.ai .ghost")).toHaveText("Nothing was sent. External AI never saw this message.");
});

test("O2 local model offline: internal still goes out, long warning first, short one after", async ({ page }) => {
  await page.goto(`${OFFLINE}/`);
  await page.locator('#dest button[data-v="internal"]').click();
  await type(page, "Priya is on leave next week, please cover her calls.");
  await done(page);
  await expect(step(page, "Find what is sensitive").locator(".callout")).toHaveText(
    "Local AI checks are offline. Only IDs and names were checked; health, pay, HR, legal details and inferences can go through unnoticed.");
  await expect(page.locator("#turn-0 .outcome")).not.toHaveClass(/stop/);
  await type(page, "Thanks, make it shorter.");
  await done(page, 1);
  await expect(step(page, "Find what is sensitive", 1).locator(".callout")).toHaveText("Local AI checks offline: only IDs and names checked.");
});

test("O3 local checks turned off: external refused with the turned-off wording", async ({ page }) => {
  await page.goto("/");
  await page.locator("#use-ctx").uncheck();
  await type(page, "Priya is on leave, she has started tamoxifen.");
  const turn = await done(page);
  await expect(page.locator("#ctx-status")).toHaveText("Local AI check: turned off");
  await expect(step(page, "Find what is sensitive").locator(".callout")).toHaveText("Local checks are turned off, so nothing goes to an external AI.");
  await expect(step(page, "Try to work out who and what").locator(".step-s")).toHaveText("Local AI checks are turned off.");
  await expect(turn.locator(".outcome + .note-s")).toHaveText("Rule local-checks-turned-off: Local checks are turned off, so nothing goes to an external AI.");
});

test("O4 gateway down: the start screen says how to start it", async ({ page }) => {
  await page.route("/api/meta*", (r) => r.abort());
  await page.goto("/");
  await expect(page.locator("#hero > p").first()).toHaveText("The gateway is not running. Start it with uv run --frozen python -m chaperone and reload this page.");
});

test("O4 gateway gone mid-session: a send says it could not reach it", async ({ page }) => {
  await page.goto("/");
  await page.route("/api/chat/stream", (r) => r.abort());
  await type(page, "Hello there.");
  await expect(page.locator("#turn-0 .outcome.stop")).toHaveText("Could not reach the gateway. Start it with uv run --frozen python -m chaperone, then try again.");
  await expect(page.locator("#text")).toHaveValue("Hello there.");
});
