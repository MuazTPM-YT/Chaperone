// compare view, person report, seal check, records CSV, and the rules panel (checklist K, PR, SC, RC, RU, D2)
import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { ADMIN, done, scenario, step } from "./helpers";

test("K1 compare runs one message through three flows without sending", async ({ page }) => {
  let sent = 0;
  page.on("request", (r) => { if (r.url().endsWith("/api/chat/stream")) sent += 1; });
  await scenario(page, "10");
  const dlg = page.locator("#compare-dlg");
  await expect(dlg).toBeVisible();
  await expect(dlg.locator(".cmp-col h3")).toHaveText(["Doctor to internal modelfor general", "Doctor to external AIfor general", "Intern to external AIfor general"]);
  await expect(dlg.locator(".cmp-col").first().locator(".pill")).toHaveText(/Would be sent|Blocked/);
  await expect(dlg.locator(".cmp-col h4").first()).toHaveText("What would leave");
  await expect(dlg.locator(".cmp-col .payload mark.diff").first()).toBeVisible();
  await expect(dlg.locator(".cmp-col").nth(1).locator("h4").nth(1)).toHaveText("What an attacker could infer");
  expect(sent).toBe(0);
  await page.mouse.click(5, 5);  // outside the dialog
  await expect(dlg).toBeHidden();
});

test("K1 the compare button uses the typed text and the shown rule pack", async ({ page }) => {
  await page.goto("/");
  await page.locator("#text").fill("Patient Ramesh Rao, 54-year-old male, needs a discharge note.");
  const req = page.waitForRequest("/api/compare");
  await page.locator("#compare").click();
  expect((await req).postDataJSON()).toEqual({ text: "Patient Ramesh Rao, 54-year-old male, needs a discharge note.", pack: "default", use_context: true });
  await expect(page.locator("#compare-dlg .cmp-col")).toHaveCount(3);
  await page.locator("#compare-dlg .icon-btn[aria-label=Close]").click();
  await expect(page.locator("#compare-dlg")).toBeHidden();
});

test("PR1 the person report finds every request that carried a name", async ({ page }) => {
  await scenario(page, "3b");
  await done(page);
  await page.locator("#person-open").click();
  const dlg = page.locator("#person-dlg");
  await expect(page.locator("#person-q")).toBeFocused();
  await page.locator("#person-q").fill("Nobody Atall");
  await page.locator("#person-go").click();
  await expect(dlg.locator(".empty")).toHaveText("No logged request carried this value. Type a name in full, as the message wrote it.");
  await page.locator("#person-q").fill("Suresh Kumar");
  await page.locator("#person-go").click();
  await expect(page.locator("#person-title")).toHaveText(/^Person report: \d+ requests?$/);
  const row = dlg.locator(".prow").last();
  await expect(row).toContainText("Accountant to external AI, invoicing");
  await expect(row).toContainText("Received by qwen2.5:3b, on this laptop");
  await expect(row).toContainText("Name: sent as placeholder [PERSON_1]");
  await expect(dlg.locator(".seal")).toHaveText(/^Seal intact over \d+ lines?\. Head [0-9a-f]{16}: keep a copy/);
});

test("SC1 the seal check shows a toast that can be dismissed", async ({ page }) => {
  await page.goto("/");
  await page.locator("#verify").click();
  const t = page.locator("#toast-slot .toast");
  await expect(t).toHaveText(/^(Audit log seal intact\. (Seal intact over \d+ lines?\. Head [0-9a-f]{16}: keep a copy, so lines cut from the end show up\.|No sealed lines yet\.))$/);
  await t.locator("button[aria-label=Dismiss]").click();
  await expect(t).toHaveCount(0);
});

test("RC1 the processing record downloads as CSV", async ({ page }) => {
  await scenario(page, "1a");
  await done(page);
  const dl = page.waitForEvent("download");
  await page.locator("a", { hasText: "Download processing record (CSV)" }).click();
  const file = await dl;
  expect(file.suggestedFilename()).toBe("chaperone-processing-record.csv");
  const csv = readFileSync(await file.path(), "utf8");
  expect(csv.split("\n")[0]).toMatch(/^time_utc,conversation,sender_role,destination,purpose/);
  expect(csv).toContain("Manager,external,scheduling");
});

test("RU1 RU3 the rules panel: numbered rules, packs, purposes, read-only note", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#rules-open-label")).toHaveText("View the rules");
  await page.locator("#rules-open").click();
  const dlg = page.locator("#rules-dlg");
  await expect(dlg.locator(".rule-card").first().locator(".n")).toHaveText("1");
  await expect(dlg.locator("#rule-salary-not-for-marketing .chip").first()).toHaveText("Blocked");
  await expect(dlg.locator("#rule-salary-not-for-marketing .chip.plain")).toHaveText("Whole message");
  await expect(dlg.locator("#rules-bar .note-s")).toHaveText("Read only. To edit, start the server with CHAPERONE_ADMIN=1.");
  await expect(dlg.locator(".rules-sec h3")).toHaveText("What each purpose leaves out");
  await dlg.locator('#rules-tabs button[data-v="safe_harbor"]').click();
  await expect(dlg.locator(".inherit")).toContainText("Items these rules do not decide go on to the");
  await dlg.locator(".inherit .link").click();
  await expect(dlg.locator('#rules-tabs button[data-v="default"]')).toHaveAttribute("aria-pressed", "true");
});

test("S3 #rules opens the rules panel", async ({ page }) => {
  await page.goto("/#rules");
  await expect(page.locator("#rules-dlg")).toBeVisible();
  await expect(page.locator("#rules-dlg .rule-card").first()).toBeVisible();
});

test("D2 a rule link in the decisions opens that rule, highlighted", async ({ page }) => {
  await scenario(page, "2b");
  await done(page);
  await page.locator("#turn-0 .outcome + .note-s .rule-link").click();
  const card = page.locator("#rule-salary-not-for-marketing");
  await expect(card).toBeInViewport();
  await expect(card).toHaveClass(/flash/);
});

test("RU2 admin mode: edit, try, save and reset the rules", async ({ page }) => {
  await page.goto(`${ADMIN}/`);
  await expect(page.locator("#rules-open-label")).toHaveText("View and edit the rules");
  await page.locator("#text").fill("Call Priya on 98450 12345 about the invoice.");
  await page.locator("#rules-open").click();
  const dlg = page.locator("#rules-dlg");
  await dlg.locator("#rules-edit").click();
  await expect(dlg.locator("#rules-save")).toBeVisible();
  await expect(dlg.locator('#rules-tabs button[data-v="safe_harbor"]')).toBeDisabled();
  const count = await dlg.locator(".rule-card.edit").count();
  await dlg.locator("#rules-add").click();
  await expect(dlg.locator(".rule-card.edit")).toHaveCount(count + 1);
  await expect(dlg.locator('#draft-0 input[data-f="id"]')).toBeFocused();
  await dlg.locator('#draft-0 input[data-f="id"]').fill("phones-blocked");
  await dlg.locator('#draft-0 select[data-f="action"]').selectOption("block");
  await dlg.locator('#draft-0 .tog[data-key="label"][data-val="PHONE"]').click();
  await expect(dlg.locator('#draft-0 .tog[data-key="label"][data-val="PHONE"]')).toHaveAttribute("aria-pressed", "true");
  await dlg.locator('#draft-0 textarea[data-f="why"]').fill("Phone numbers never leave in this test.");
  await dlg.locator('#draft-0 [aria-label="Move rule 1 down"]').click();
  await expect(dlg.locator('#draft-1 input[data-f="id"]')).toHaveValue("phones-blocked");
  await dlg.locator('#draft-1 [aria-label="Move rule 2 up"]').click();
  await expect(dlg.locator('#draft-0 input[data-f="id"]')).toHaveValue("phones-blocked");
  await expect(dlg.locator(".rule-card.edit").last().locator('[aria-label^="Delete"]')).toBeDisabled();
  await expect(dlg.locator("#try-text")).toHaveValue("Call Priya on 98450 12345 about the invoice.");
  await dlg.locator("#try-go").click();
  await expect(dlg.locator("#try-out .try-grid h4")).toHaveText(["Saved rules", "Your edit"]);
  await expect(dlg.locator("#try-out .changes li", { hasText: "98450 12345" })).toContainText("now Blocked by phones-blocked");
  await dlg.locator("#rules-save").click();
  await expect(page.locator("#toast-slot .toast")).toHaveText(/^Rules saved\. The next message uses them/);
  await expect(dlg.locator("#rule-phones-blocked")).toBeVisible();
  await expect(dlg.locator(".pill.edited")).toHaveText("Edited here");
  await dlg.locator("#rules-edit").click();
  await dlg.locator("#rules-reset").click();
  await expect(dlg.locator("#rules-reset")).toHaveText("Click again to reset");
  await dlg.locator("#rules-reset").click();
  await expect(page.locator("#toast-slot .toast")).toHaveText(/^Shipped rules restored\./);
  await expect(dlg.locator("#rule-phones-blocked")).toHaveCount(0);
});

test("RU2 a bad edit is refused with the server's reason", async ({ page }) => {
  await page.goto(`${ADMIN}/`);
  await page.locator("#rules-open").click();
  const dlg = page.locator("#rules-dlg");
  await dlg.locator("#rules-edit").click();
  await dlg.locator("#rules-add").click();
  await dlg.locator('#draft-0 input[data-f="id"]').fill("Bad Id!");
  await dlg.locator("#rules-save").click();
  await expect(dlg.locator("#rules-error")).toBeVisible();
  await expect(dlg.locator("#rules-error")).not.toHaveText("");
  await dlg.locator("#rules-cancel").click();
  await expect(dlg.locator("#rules-edit")).toBeVisible();
});

test("D2 gateway-only rules show as plain text, not a link", async ({ page }) => {
  await scenario(page, "7");
  await done(page);
  await step(page, "Apply the rules for this flow").locator("summary").click();
  await expect(page.locator("#turn-0 .dl .rule", { hasText: "purpose-minimisation" }).first()).toBeVisible();
});
