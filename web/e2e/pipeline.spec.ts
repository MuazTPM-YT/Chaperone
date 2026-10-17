// the processing view: steps, decisions, what was sent, the attacker, include anyway, the reply, the ledger
// (checklist V, D, W, A, I, R, L, T)
import { expect, test } from "@playwright/test";
import { done, ndjson, realEvents, scenario, step, type } from "./helpers";

test("V1 V2 V4 V7 T1 steps of a discharge note: find, rules, final check, times", async ({ page }) => {
  await scenario(page, "7");
  const turn = await done(page);
  await expect(turn.locator(".flowline")).toHaveText("Doctor to external AI, for clinical summary");
  await expect(step(page, "Find what is sensitive").locator(".step-s")).toHaveText(/^\d+ items found\.$/);
  await expect(step(page, "Find what is sensitive").locator(".found .chip.pseudonymize").first()).toHaveText(/^Name( ×\d+)?$/);
  await expect(step(page, "Find what is sensitive").locator(".ms")).toHaveText(/^(<1 ms|\d+ ms|\d+\.\d s)$/);
  await expect(step(page, "Apply the rules for this flow").locator(".step-s")).toHaveText(/masked.*left out.*\.$|left out.*\.$/);
  await expect(step(page, "Final check").locator(".step-s")).toHaveText("No masked value is left in what goes out. Sent to external AI.");
  await expect(turn.locator(".outcome.ok")).toHaveText(/^Sent with \d+ changes\.\d+(\.\d)? s \+ AI \d+(\.\d)? s$|^Sent with \d+ changes\.\d+ ms \+ AI \d+(\.\d)? s$/);
});

test("V2 V6 W2 a rule that stops the whole request: blocked, nothing sent, rule and reason shown", async ({ page }) => {
  await scenario(page, "2b");
  const turn = await done(page);
  await expect(step(page, "Apply the rules for this flow").locator(".step-s")).toHaveText("A rule stops the whole request.");
  await expect(step(page, "Final check").locator(".step-s")).toHaveText("Nothing to send.");
  await expect(turn.locator(".outcome.stop")).toContainText("Blocked. Nothing left this laptop.");
  await expect(turn.locator(".outcome + .note-s")).toHaveText(/^Rule salary-not-for-marketing: .+/);
  await expect(turn.locator(".cell.ai .ghost")).toHaveText("Nothing was sent. External AI never saw this message.");
  await expect(step(page, "Try to work out who and what").locator(".step-s")).toHaveText("Not needed: a rule already stopped the request.");
});

test("V6 the final check stopping a send says so", async ({ page }) => {
  await page.goto("/");
  const ev = await realEvents(page, { text: "Customer Aadhaar 7260 1815 9082 needs a KYC update.", role: "Manager", destination: "internal", purpose: "general" });
  const result = ev.find((e) => e.step === "result")!.result as Record<string, unknown>;
  await page.route("/api/chat/stream", ndjson([...ev.filter((e) => ["detect", "decide", "attack", "ready"].includes(e.step as string)),
    { step: "result", result: { ...result, sent: false, reply: null, restored: null, error: "Outbound guard refused to send: a masked value is still in the payload" } }]));
  await type(page, "Customer Aadhaar 7260 1815 9082 needs a KYC update.");
  await expect(page.locator("#turn-0 .outcome.stop")).toContainText("Not sent. The final check stopped it.");
  await expect(step(page, "Final check")).toHaveClass(/fail/);
  await expect(step(page, "Final check").locator(".step-s")).toHaveText(/^Outbound guard refused to send/);
});

test("D1 D3 W1 decisions list every item with its reason; you wrote and what was sent are marked", async ({ page }) => {
  await scenario(page, "3b");
  const turn = await done(page);
  await expect(turn.locator(".row.out .cell.you mark.pseudonymize", { hasText: "Suresh Kumar" })).toHaveAttribute("title", "Name: Masked");
  await expect(turn.locator(".row.out .cell.you mark sup").first()).toBeVisible();
  const sent = turn.locator(".row.out .cell.ai .bubble.theirs");
  await expect(sent).toContainText("[PERSON_1]");
  await expect(sent).not.toContainText("Suresh");
  const res = await page.evaluate(() => document.querySelector("#turn-0 .row.out .cell.ai .bubble")!.textContent);
  expect(res).toContain("PAN");  // the PAN goes as a placeholder too
  await step(page, "Apply the rules for this flow").locator("summary").click();
  const pan = step(page, "Apply the rules for this flow").locator(".dl li").filter({ hasText: "ABKPS7312M" });
  await expect(pan.locator(".chip").first()).toHaveText("Masked");
  await expect(pan.locator(".chip.plain")).toHaveText("PAN");
  await expect(pan.locator(".as")).toHaveText("sent as [PAN_1]");
  await expect(pan.locator(".why")).toHaveText(/^Personal data, found by pattern \(PAN holder 'P' = .+\)\. Rule [\w-]+: .+/);
});

test("V8 details stay open while the next step arrives", async ({ page }) => {
  await scenario(page, "8b");
  await done(page);
  await step(page, "Apply the rules for this flow").locator("summary").click();
  await expect(step(page, "Apply the rules for this flow").locator("details")).toHaveAttribute("open", "");
  // the names-only comparison re-renders the turn when it lands; the panel must survive that
  await page.locator("#turn-0 .flowline").click();
  await expect(step(page, "Apply the rules for this flow").locator("details")).toHaveAttribute("open", "");
});

test("V3 A1 A4 A5 the attacker panel: before and after tightening, and the names-and-IDs-only comparison", async ({ page }) => {
  await scenario(page, "8b");
  const turn = await done(page);
  const atk = step(page, "Try to work out who and what");
  await expect(atk).toHaveClass(/warn/);
  await expect(atk.locator(".step-s")).toHaveText(/^Inferred .+\. Those words were made vaguer, then the attacker found nothing this flow forbids\.$/);
  await atk.locator("summary").click();
  const before = atk.locator(".detail > div").filter({ has: page.locator("h4", { hasText: "Before tightening" }) });
  await expect(before.locator(".inf li .chip.cat", { hasText: "Identity" })).toHaveCount(1);
  await expect(before.locator(".inf li").first().locator(".conf")).toHaveText(/^\d+% sure$/);
  await expect(before.locator(".then").first()).toHaveText("Those words were made vaguer before sending.");
  await expect(before.locator(".note-s")).toHaveText(/^Words changed: .+\.$/);
  await expect(atk.locator(".detail > .note-s").last()).toHaveText(/^\d attack passes\. A small local model can miss what a large one would infer/);
  await expect(atk.locator(".detail h4", { hasText: "If only names and IDs were masked" })).toBeVisible();
  await expect(turn.locator(".cell.ai .bubble.theirs mark.generalize").first()).toHaveText(/^\[IDENTITY_\d: .+\]$/);
});

test("A4 the names-only comparison shows its red callout when masking names alone leaks", async ({ page }) => {
  await scenario(page, "8a");
  await done(page);
  const atk = step(page, "Try to work out who and what");
  await expect(atk.locator(".callout")).toHaveText(/^Masking names and IDs alone would have let a reader infer .+\.$/);
});

test("A2 A3 still inferable, already disclosed and allowed groups", async ({ page }) => {
  await page.goto("/");
  const text = "Draft a note to the team: Priya is on leave for three weeks, she has started tamoxifen and will be back in November.";
  const ev = await realEvents(page, { text, role: "Manager", destination: "external", purpose: "general" });
  const result = ev.find((e) => e.step === "result")!.result as Record<string, any>;
  const inf = (o: object) => ({ category: "HEALTH", guess: "breast cancer", confidence: 0.9, evidence: ["tamoxifen"], description: "", safer: "", forbidden: true, disclosed: false, rule: "health-external", ...o });
  const rounds = [{ index: 0, ms: 900, inferences: [inf({}), inf({ category: "IDENTITY", guess: "the team lead", forbidden: false, evidence: ["the team"] }), inf({ guess: "pregnancy", disclosed: true })], tightened: ["tamoxifen"] },
    { index: 1, ms: 800, inferences: [inf({})], tightened: [] }, { index: 2, ms: 700, inferences: [inf({}), inf({ category: "IDENTITY", guess: "the team lead", forbidden: false })], tightened: [] }];
  const blocked = { ...result, outbound: null, blocked: true, sent: false, reply: null, restored: null,
    block_reason: { action: "block", rule: "attacker-not-cleared", why: "After 2 tightening rounds a local attacker could still infer: breast cancer. Edit the message and try again.", scope: "request", coarse: "" },
    attack: { ran: true, skipped: "", max_rounds: 2, rounds, unresolved: [inf({})] } };
  await page.route("/api/chat/stream", ndjson([...ev.filter((e) => ["detect", "decide"].includes(e.step as string)),
    ...rounds.map((r) => ({ step: "attack", round: r.index, ms: r.ms, found: ["breast cancer"], skipped: "" })),
    { step: "ready", outbound: null, blocked: true, ms: 3000 }, { step: "result", result: blocked }]));
  await type(page, text);
  const atk = step(page, "Try to work out who and what");
  await expect(atk).toHaveClass(/fail/);
  await expect(atk.locator(".step-s")).toHaveText("Could still infer breast cancer after 2 rounds of tightening.");
  await atk.locator("summary").click();
  await expect(atk.locator(".detail h4")).toHaveText(["Still inferable", "Before tightening", "Already disclosed earlier", "Allowed for this flow", "If only names and IDs were masked"]);
  await expect(atk.locator("li", { hasText: "pregnancy" }).locator(".then")).toHaveText("Sent in an earlier message; it cannot be pulled back.");
  await expect(atk.locator("li.muted", { hasText: "the team lead" })).toHaveCount(1);
  await expect(page.locator("#turn-0 .outcome + .note-s")).toHaveText(/^Rule attacker-not-cleared: After 2 tightening rounds/);
});

test("I1 include anyway asks for a reason and sends the message again with it", async ({ page }) => {
  await scenario(page, "7");
  await done(page);
  await step(page, "Apply the rules for this flow").locator("summary").click();
  const phone = page.locator("#turn-0 .dl li").filter({ has: page.locator(".chip.omit") }).first();
  await expect(phone.locator(".chip").first()).toHaveText("Left out");
  await phone.locator(".chip-btn", { hasText: "Include anyway" }).click();
  const input = phone.locator(".include-form input");
  await expect(input).toBeFocused();
  await input.fill("short");
  await phone.locator(".include-form button").click();
  await expect(page.locator("#turn-1")).toHaveCount(0);  // under 8 characters: refused by the form
  const req = page.waitForRequest("/api/chat/stream");
  await input.fill("Ward clerk needs the contact on the note");
  await phone.locator(".include-form button").click();
  const body = (await req).postDataJSON();
  expect(body.include).toEqual([expect.objectContaining({ label: "PHONE", reason: "Ward clerk needs the contact on the note" })]);
  await done(page, 1);
  await expect(step(page, "Apply the rules for this flow", 1).locator(".callout.info")).toHaveText("Included anyway: Phone. Your reason is in the audit log, with names removed.");
});

test("R1 R2 V5 the reply as the AI wrote it, and back with the real values marked", async ({ page }) => {
  await scenario(page, "3b");
  const turn = await done(page);
  const raw = turn.locator(".row.back .cell.ai .bubble.theirs .md");
  await expect(raw).toContainText("[PERSON_1]");
  await expect(raw.locator("mark.pseudonymize").first()).toHaveText(/^\[PERSON_1\]$/);
  const mine = turn.locator(".row.back .cell.you .bubble.mine .md");
  await expect(mine).toContainText("Suresh Kumar");
  await expect(mine.locator("mark.pseudonymize").first()).toHaveAttribute("title", /^The AI saw \[?PERSON_1\]?/i);
  await expect(step(page, "Put the real values back").locator(".step-s")).toHaveText(/^\d+ placeholders? replaced with the real value\./);
  await step(page, "Put the real values back").locator("summary").click();
  await expect(step(page, "Put the real values back").locator(".dl li").first().locator(".as")).toHaveText(/^\[[A-Z]+_1\]$/);
});

test("R1 R3 markdown in the reply, and invented details flagged", async ({ page }) => {
  await page.goto("/");
  const text = "Patient Ramesh Rao, 54-year-old male, admitted with chest pain.";
  const ev = await realEvents(page, { text, role: "Doctor", destination: "internal", purpose: "general" });
  const result = ev.find((e) => e.step === "result")!.result as Record<string, any>;
  const reply = "## Summary\n\n**Ramesh Rao**, aged 61, was admitted.\n\n- chest pain\n- `ECG` done\n\n---\n\n1. rest";
  const restored = reply;
  const at = restored.indexOf("aged 61");
  const canned = { ...result, reply, restored, restore_stats: { exact: 0, fuzzy: 0 }, restore_marks: [],
    flags: [{ start: at, end: at + 7, text: "aged 61", kind: "age", reason: "Age 61 is not from your message. Your message says 54." }] };
  await page.route("/api/chat/stream", ndjson([...ev.filter((e) => ["detect", "decide", "attack", "ready", "guard"].includes(e.step as string)),
    { step: "reply", reply, ms: 900 }, { step: "restore", restored, stats: { exact: 0, fuzzy: 0 }, flags: 1 }, { step: "result", result: canned }]));
  await type(page, text);
  const mine = page.locator("#turn-0 .row.back .cell.you .md");
  await expect(mine.locator("h4")).toHaveText("Summary");
  await expect(mine.locator("strong")).toHaveText("Ramesh Rao");
  await expect(mine.locator("ul li")).toHaveText(["chest pain", "ECG done"]);
  await expect(mine.locator("code")).toHaveText("ECG");
  await expect(mine.locator("hr")).toHaveCount(1);
  await expect(mine.locator("ol li")).toHaveText(["rest"]);
  await expect(mine.locator("mark.flag")).toHaveText("aged 61");
  await expect(mine.locator("mark.flag")).toHaveAttribute("title", "Age 61 is not from your message. Your message says 54.");
  const restore = step(page, "Put the real values back");
  await expect(restore).toHaveClass(/warn/);
  await expect(restore.locator(".step-s")).toHaveText("No placeholders to replace. 1 detail in the reply is not from your message.");
  await restore.locator("summary").click();
  await expect(restore.locator(".flags")).toHaveText(/^1 detail in the reply is not from your message\.\s*aged 61: Age 61 is not from your message\. Your message says 54\.$/);
});

test("L1 the exposure ledger lists what the external AI could know", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#ledger-block")).toBeHidden();
  const text = "Draft a two-line note to the team: Priya is on leave next week, so her Monday 1:1s move to Thursday.";
  const ev = await realEvents(page, { text, role: "Manager", destination: "external", purpose: "scheduling" });
  const result = ev.find((e) => e.step === "result")!.result as Record<string, any>;
  await page.route("/api/chat/stream", ndjson([...ev.filter((e) => e.step !== "result"),
    { step: "result", result: { ...result, exposure: [{ turn: 1, category: "HEALTH", guess: "a long illness", status: "allowed for this flow" }] } }]));
  await type(page, text);
  await done(page);
  await expect(page.locator("#ledger-block")).toBeVisible();
  await expect(page.locator("#ledger li")).toHaveText(["Health: a long illnessAllowed for this flow, message 1"]);
  await page.unroute("/api/chat/stream");
  await page.locator("#reset").click();
  await page.locator('#dest button[data-v="external"]').click();
  await type(page, "Hello there.");
  await done(page);
  await expect(page.locator("#ledger li")).toHaveText(["Nothing inferred about anyone yet in this chat."]);
});

test("V3 C5 live states while the stream is still open: attacker rounds, final check, the AI writing", async ({ page }) => {
  // the page's own fetch gets a stream we feed by hand, so each half-finished state can be checked
  await page.addInitScript(() => {
    const real = window.fetch;
    const w = window as unknown as { push: (e: object | null) => void };
    window.fetch = (input, init) => {
      if (String(input).endsWith("/api/chat/stream")) {
        let ctl!: ReadableStreamDefaultController<Uint8Array>;
        const body = new ReadableStream<Uint8Array>({ start: (c) => { ctl = c; } });
        w.push = (e) => e ? ctl.enqueue(new TextEncoder().encode(JSON.stringify(e) + "\n")) : ctl.close();
        return Promise.resolve(new Response(body, { status: 200 }));
      }
      return real(input, init);
    };
  });
  await page.goto("/");
  const push = (e: object | null) => page.evaluate((x) => (window as unknown as { push: (e: object | null) => void }).push(x), e);
  await type(page, "Priya has started tamoxifen.");
  await expect(step(page, "Find what is sensitive")).toHaveClass(/active/);
  await expect(step(page, "Find what is sensitive").locator(".step-s")).toHaveText("Reading for names, IDs, health, pay and more…");
  await push({ step: "detect", items: [{ label: "PERSON", text: "Priya", source: "ner" }], context_ok: true, ms: 400 });
  await expect(step(page, "Apply the rules for this flow").locator(".step-s")).toHaveText("Deciding what may leave…");
  await push({ step: "decide", counts: { pseudonymize: 1 }, blocked: false, ms: 1 });
  await expect(step(page, "Try to work out who and what").locator(".step-s")).toHaveText("A local attacker reads the protected version…");
  await push({ step: "attack", round: 0, ms: 900, found: ["breast cancer"], skipped: "" });
  await expect(step(page, "Try to work out who and what").locator(".step-s")).toHaveText("Round 1: inferred breast cancer. Making those words vaguer, then reading again…");
  await expect(step(page, "Try to work out who and what").locator(".ms")).toHaveText("900 ms");
  await push({ step: "attack", round: 1, ms: 800, found: [], skipped: "" });
  await push({ step: "ready", outbound: "[PERSON_1] has started [HEALTH_1: a health matter].", blocked: false, ms: 2100 });
  await expect(step(page, "Final check").locator(".step-s")).toHaveText("Checking the payload for every masked value…");
  await push({ step: "guard", checked: 2 });
  await expect(page.locator("#turn-0 .row.out .cell.ai .bubble.theirs mark.generalize")).toHaveText("[HEALTH_1: a health matter]");
  await expect(page.locator("#turn-0 .row.back .cap")).toHaveText("External AI is writing");
  await expect(page.locator("#live")).toHaveText("Final check passed. Sent.");
  await push({ step: "reply", reply: "Noted for [PERSON_1].", ms: 700 });
  await expect(step(page, "Put the real values back").locator(".step-s")).toHaveText("Swapping placeholders for real values…");
  await push(null);
  await expect(page.locator("#turn-0 .outcome.stop")).toHaveText("The gateway stopped before the checks finished. Its terminal shows the details.");
});
