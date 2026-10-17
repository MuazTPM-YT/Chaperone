// look, flow switchers, scenarios and the chat itself (checklist P, F, S, C)
import { expect, test } from "@playwright/test";
import { ADMIN, done, ndjson, realEvents, scenario, step, type } from "./helpers";

test("P1 page uses the local fonts and the same colour tokens", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => document.fonts.ready);
  const fonts = await page.evaluate(() => [...document.fonts].filter((f) => f.status === "loaded").map((f) => f.family));
  expect(fonts).toContain("Inter Variable");
  const tok = await page.evaluate(() => ["--paper", "--accent", "--pseudo", "--block"].map((v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim()));
  expect(tok).toEqual(["#fcfcfd", "#3b34d9", "#1f56c4", "#c01a2c"]);
  await expect(page.locator("body")).toHaveCSS("font-family", /Inter Variable/);
});

test("P2 top bar has the brand, the flow switchers, the local AI status and the theme button", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".brand b")).toHaveText("Chaperone");
  await expect(page.locator(".brand")).toHaveAttribute("href", "/");
  for (const id of ["#role", "#dest", "#purpose", "#pack", "#theme"]) await expect(page.locator(id)).toBeVisible();
  await expect(page.locator("#ctx-status")).toHaveText("Local AI check: qwen2.5:3b, on this laptop");
});

test("P4 start screen shows four featured scenarios and goes away once a message is sent", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".hero h1")).toHaveText("You see real names.The AI sees only what it needs.");
  await expect(page.locator("#picks .pick b")).toHaveText(["Leave for chemotherapy", "Medicine, no diagnosis", "Discharge summary", "External marketing copilot"]);
  await page.locator("#picks .pick").first().click();
  await expect(page.locator("#hero")).toBeHidden();
  await done(page);
});

test("P6 theme cycles automatic, light, dark and is remembered", async ({ page }) => {
  await page.goto("/");
  const html = page.locator("html");
  await expect(page.locator("#theme")).toHaveAttribute("aria-label", "Theme: automatic");
  await page.locator("#theme").click();
  await expect(html).toHaveAttribute("data-theme", "light");
  await page.locator("#theme").click();
  await expect(html).toHaveAttribute("data-theme", "dark");
  await expect(page.locator('meta[name="theme-color"]').first()).toHaveAttribute("content", "#0f1115");
  await page.reload();
  await expect(html).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("#theme")).toHaveAttribute("aria-label", "Theme: dark");
  await page.locator("#theme").click();
  await expect(html).not.toHaveAttribute("data-theme", /.*/);
});

test("P7 on a narrow screen the rail is a drawer that Escape and the scrim close", async ({ page }) => {
  await page.setViewportSize({ width: 1100, height: 900 });
  await page.goto("/");
  await expect(page.locator("#rail")).not.toBeInViewport();
  await page.locator("#rail-open").click();
  await expect(page.locator("#rail")).toHaveClass(/open/);
  await expect(page.locator("#rail-open")).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Escape");
  await expect(page.locator("#rail")).not.toHaveClass(/open/);
  await page.locator("#rail-open").click();
  await page.locator("#scrim").click({ position: { x: 1000, y: 400 } });
  await expect(page.locator("#rail")).not.toHaveClass(/open/);
  await page.setViewportSize({ width: 600, height: 900 });
  await expect(page.locator(".lane-heads")).toBeHidden();  // lanes stack under 860 px
});

test("F1 F3 role and purpose lists come from the rules, and the purpose line explains the purpose", async ({ page }) => {
  await page.goto("/");
  const meta = await (await page.request.get("/api/meta")).json();
  await expect(page.locator("#role option")).toHaveText(meta.roles);
  await expect(page.locator("#purpose option")).toHaveCount(meta.purposes.length);
  await page.locator("#purpose").selectOption("general");
  await expect(page.locator("#purpose-line")).toHaveText("No purpose stated, so nothing is left out for being unneeded.");
  await page.locator("#purpose").selectOption("clinical_summary");
  await expect(page.locator("#purpose-line")).toHaveText(/^Purpose: clinical summary\. Identifiers it does not need are left out\.$/i);
});

test("P3 F2 destination switch moves the thumb and renames the AI lane", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#ai-name")).toHaveText("External AI");
  await expect(page.locator("#ai-where")).toHaveText("qwen2.5:3b, simulated on this laptop");
  const thumb = page.locator("#dest .thumb");
  const before = await thumb.evaluate((e) => e.style.transform);
  await page.locator('#dest button[data-v="internal"]').click();
  await expect(page.locator('#dest button[data-v="internal"]')).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#ai-name")).toHaveText("Internal model");
  await expect(page.locator("#ai-where")).toHaveText("qwen2.5:3b, inside the organisation");
  expect(await thumb.evaluate((e) => e.style.transform)).not.toBe(before);
});

test("F4 F5 the rule pack switch and every switch reach the request", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#pack button")).toHaveText(["Standard rules", "Safe Harbor"]);
  await page.locator("#role").selectOption("Doctor");
  await page.locator('#dest button[data-v="internal"]').click();
  await page.locator("#purpose").selectOption("clinical_summary");
  await page.locator('#pack button[data-v="safe_harbor"]').click();
  await page.locator("#use-ctx").uncheck();
  const req = page.waitForRequest("/api/chat/stream");
  await type(page, "Hello there.");
  const body = (await req).postDataJSON();
  expect(body).toMatchObject({ text: "Hello there.", role: "Doctor", destination: "internal", purpose: "clinical_summary", pack: "safe_harbor", use_context: false, include: [] });
  await done(page);
});

test("S1 the rail lists every scenario, grouped, with its flow", async ({ page }) => {
  await page.goto("/");
  const meta = await (await page.request.get("/api/meta")).json();
  await expect(page.locator("#scenarios button[data-id]")).toHaveCount(meta.scenarios.length);
  await expect(page.locator('#scenarios [data-id="2b"]')).toHaveText("External marketing copilotSales to external AI, marketing");
  await expect(page.locator('#scenarios [data-id="9"] small')).toHaveText("Doctor to external AI, clinical summary, Safe Harbor");
  await expect(page.locator('#scenarios [data-id="10"] small')).toHaveText("three flows side by side");
  await expect(page.locator(".sc-group > p").first()).toHaveText("Leave note");
});

test("S2 a scenario sets the flow and the text, marks itself, and runs", async ({ page }) => {
  await scenario(page, "7");
  await expect(page.locator('#scenarios [data-id="7"]')).toHaveAttribute("aria-current", "true");
  await expect(page.locator("#role")).toHaveValue("Doctor");
  await expect(page.locator("#purpose")).toHaveValue("clinical_summary");
  await expect(page.locator('#dest button[data-v="external"]')).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#turn-0 .flowline")).toHaveText("Doctor to external AI, for clinical summary");
  await done(page);
});

test("S3 a scenario id in the address runs it", async ({ page }) => {
  await page.goto("/#1a");
  const turn = await done(page);
  await expect(turn.locator(".row.out .cell.you .bubble")).toContainText("is on leave next week");
  await expect(page.locator('#scenarios [data-id="1a"]')).toHaveAttribute("aria-current", "true");
});

test("S4 dev mode has the demo / worst case switch", async ({ page }) => {
  await page.goto(`${ADMIN}/`);
  await expect(page.locator(".devdata a")).toHaveText(["Demo data", "Worst case"]);
  await expect(page.locator('.devdata a[aria-current="true"]')).toHaveText("Demo data");
  const worst = await (await page.request.get(`${ADMIN}/api/meta?data=worst`)).json();
  await page.locator(".devdata a", { hasText: "Worst case" }).click();
  await expect(page.locator('.devdata a[aria-current="true"]')).toHaveText("Worst case");
  await expect(page.locator("#scenarios button[data-id]")).toHaveCount(worst.scenarios.length);
});

test("C1 composer: Enter sends, Shift+Enter adds a line, send is off when empty or busy", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#send")).toBeDisabled();
  await page.locator("#text").fill("Line one");
  await page.locator("#text").press("Shift+Enter");
  await page.locator("#text").pressSequentially("Line two");
  await expect(page.locator("#text")).toHaveValue("Line one\nLine two");
  await expect(page.locator("#send")).toBeEnabled();
  await page.locator("#text").press("Enter");
  await expect(page.locator("#send")).toHaveAttribute("aria-busy", "true");
  await expect(page.locator("#send")).toHaveAttribute("aria-label", "Checking");
  await expect(page.locator("#text")).toHaveValue("");
  await done(page);
  await expect(page.locator("#send")).toHaveAttribute("aria-label", "Check and send");
});

test("C2 the character counter appears near the limit", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#count")).toBeHidden();
  await page.locator("#text").fill("a".repeat(3500));
  await expect(page.locator("#count")).toHaveText("3,500 / 4,000 characters");
  await expect(page.locator("#text")).toHaveAttribute("maxlength", "4000");
});

test("C3 C6 a second turn keeps the session and comes into view", async ({ page }) => {
  const sessions: string[] = [];
  page.on("request", (r) => { if (r.url().endsWith("/api/chat/stream")) sessions.push(r.postDataJSON().session_id); });
  await scenario(page, "7");
  await done(page);
  await type(page, "Make it shorter.");
  await done(page, 1);
  expect(sessions).toHaveLength(2);
  expect(sessions[1]).toBe(sessions[0]);
  await expect(page.locator("#turn-1")).toBeInViewport();
});

test("C4 new chat resets the session on the server and clears the turns", async ({ page }) => {
  await scenario(page, "1a");
  await done(page);
  const reset = page.waitForRequest((r) => /\/api\/reset\/[a-z0-9]+$/.test(r.url()) && r.method() === "POST");
  await page.locator("#reset").click();
  await reset;
  await expect(page.locator(".turn")).toHaveCount(0);
  await expect(page.locator("#hero")).toBeVisible();
  await expect(page.locator('#scenarios [aria-current="true"]')).toHaveCount(0);
});

test("C5 R4 a stream error is shown and the text comes back in the box", async ({ page }) => {
  await page.goto("/");
  await page.route("/api/chat/stream", ndjson([{ step: "detect", items: [], context_ok: true, ms: 3 }, { step: "error", error: "RuntimeError" }]));
  await type(page, "Hello there.");
  await expect(page.locator("#turn-0 .outcome.stop")).toHaveText("The gateway failed (RuntimeError). Its terminal shows the details.");
  await expect(step(page, "Apply the rules for this flow")).toHaveClass(/pending/);
  await expect(page.locator("#text")).toHaveValue("Hello there.");
  await expect(page.locator("#turn-0 .ghost")).toHaveText("Not sent. External AI never saw this message.");
});

test("C5 a connection that drops mid-stream says so", async ({ page }) => {
  await page.goto("/");
  await page.route("/api/chat/stream", ndjson([{ step: "detect", items: [], context_ok: true, ms: 3 }]));
  await type(page, "Hello there.");
  await expect(page.locator("#turn-0 .outcome.stop")).toHaveText("The gateway stopped before the checks finished. Its terminal shows the details.");
});

test("R4 the AI not answering shows No reply and keeps what was sent", async ({ page }) => {
  await page.goto("/");
  const ev = await realEvents(page, { text: "Hello there.", role: "Manager", destination: "internal", purpose: "general" });
  const result = ev.find((e) => e.step === "result")!.result as Record<string, unknown>;
  const canned = [...ev.filter((e) => ["detect", "decide", "attack", "ready", "guard"].includes(e.step as string)),
    { step: "result", result: { ...result, sent: false, reply: null, restored: null, error: "LLM call failed: ConnectError" } }];
  await page.route("/api/chat/stream", ndjson(canned));
  await type(page, "Hello there.");
  await expect(page.locator("#turn-0 .row.back .ghost")).toHaveText("No reply. LLM call failed: ConnectError");
  await expect(page.locator("#turn-0 .outcome.note")).toContainText("The AI did not answer.");
  await expect(step(page, "Put the real values back")).toHaveText(/Nothing came back to restore\./);
});

test("C7 C8 steps are announced and the restored reply can be copied", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await scenario(page, "3b");
  await done(page);
  await expect(page.locator("#live")).toHaveText("Reply ready with real values.");
  await page.locator("#turn-0 .copy").click();
  await expect(page.locator("#turn-0 .copy")).toHaveText("Copied");
  const clip = await page.evaluate(() => navigator.clipboard.readText());
  await expect(page.locator("#turn-0 .bubble.mine.back")).toContainText(clip.split("\n")[0].replace(/\*\*/g, "").slice(0, 20));
  await expect(page.locator("#turn-0 .copy")).toHaveText("Copy", { timeout: 5000 });
});
