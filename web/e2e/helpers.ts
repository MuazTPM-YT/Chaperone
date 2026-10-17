import { expect, type Page, type Route } from "@playwright/test";

export const NORMAL = "http://127.0.0.1:8101", ADMIN = "http://127.0.0.1:8102", OFFLINE = "http://127.0.0.1:8103";

// a turn is finished when its outcome bar is up and, for external attacker runs, the names-only comparison has loaded
export async function done(page: Page, n = 0) {
  const turn = page.locator(`#turn-${n}`);
  await expect(turn.locator(".outcome")).toBeVisible();
  await expect(turn.locator('[aria-label="Loading comparison"]')).toHaveCount(0);
  await expect(page.locator("#send")).toHaveAttribute("aria-busy", "false");
  return turn;
}

export async function scenario(page: Page, id: string, base = "") {
  await page.goto(`${base}/`);
  await expect(page.locator(`#scenarios [data-id="${id}"]`)).toBeVisible();
  await page.locator(`#scenarios [data-id="${id}"]`).click();
}

export async function type(page: Page, text: string) {
  await page.locator("#text").fill(text);
  await page.locator("#text").press("Enter");
}

// the text of a step in the middle lane, by its title
export function step(page: Page, title: string, n = 0) {
  return page.locator(`#turn-${n} .step`).filter({ has: page.locator(".step-h b", { hasText: title }) });
}

// answer /api/chat/stream with these events, one JSON object per line
export function ndjson(events: object[]) {
  return async (route: Route) => route.fulfill({ status: 200, contentType: "application/x-ndjson",
    body: events.map((e) => JSON.stringify(e)).join("\n") + "\n" });
}

// a real run's events, fetched from the gateway, so a canned answer starts from the real shape
export async function realEvents(page: Page, body: object): Promise<Record<string, unknown>[]> {
  const res = await page.request.post("/api/chat/stream", { data: { session_id: `e2e-${Date.now()}`, ...body } });
  return (await res.text()).split("\n").filter(Boolean).map((l) => JSON.parse(l));
}
