# UI parity checklist

Everything `chaperone/static/index.html` does, as read on 2026-10-17 (commit `96ba3f3`). The Next.js app in `web/`
must do all of it. Each item names the Playwright tests that cover it (`web/e2e/`); every test title starts with the
item ids it covers.

Status: `[ ]` not done, `[x]` done and covered by a passing test. Last full run: 57 of 57 passed on 2026-10-17.

Gate check 4 (the slide 2 and 3 messages look the same as in the old page) is `parity.spec.ts`: the old page runs live,
its answers are replayed into the new page, and the text and the full-window picture must match.

## Layout and look

- [x] P1. Same colours, spacing, fonts and layout: the CSS is carried over unchanged (light and dark tokens, Inter and
  JetBrains Mono from local files). Covered by the `P1` tests in `ui.spec.ts`.
- [x] P2. Top bar: menu button (narrow screens), brand mark "Chaperone" (link to `/`), flow switchers, local AI
  status, theme button. Covered by the `P2` tests in `ui.spec.ts`.
- [x] P3. Three lanes with sticky heads: You, Chaperone, External AI / Internal model (name and "where" line follow
  the destination and `/api/meta` endpoints, "simulated on this laptop"). Covered by the `P3` tests in `ui.spec.ts`.
- [x] P4. Start screen: headline, intro text, four featured scenario cards (1b, 8a, 7, 2b), how-to line; hidden once a
  message is sent. Covered by the `P4` tests in `ui.spec.ts`.
- [x] P5. No external requests: no CDN, no remote fonts or scripts; works with only `127.0.0.1` reachable. Covered by
  the `P5` tests in `offline.spec.ts`.
- [x] P6. Theme button cycles automatic, light, dark; remembered in `localStorage` (`fg-theme`); `theme-color` metas
  follow. Covered by the `P6` tests in `ui.spec.ts`.
- [x] P7. Narrow screens (under 1360 px): the side rail becomes a drawer with a scrim; Escape and the scrim close it;
  it is inert when closed. Under 860 px the lanes stack. Covered by the `P7` tests in `ui.spec.ts`.

## Flow switchers

- [x] F1. Sender role select, filled from `/api/meta` roles. Covered by the `F1` tests in `ui.spec.ts`.
- [x] F2. Destination segmented control (Internal model / External AI), sliding thumb. Covered by the `F2` tests in
  `ui.spec.ts`.
- [x] F3. Purpose select with labels from `/api/meta`; the hint line under the box explains it ("No purpose stated..."
  or "Purpose: X. Identifiers it does not need are left out."). Covered by the `F3` tests in `ui.spec.ts`.
- [x] F4. Rule pack segmented control from `/api/meta` packs (Default / Safe Harbor), titles from the descriptions.
  Covered by the `F4` tests in `ui.spec.ts`.
- [x] F5. The flow sent with each message is the one shown: role, destination, purpose, pack, local checks on/off.
  Covered by the `F5` tests in `ui.spec.ts`.

## Scenarios and presets

- [x] S1. Side rail lists every scenario from `/api/meta`, grouped, with "role to destination, purpose, pack" or
  "three flows side by side" under each title. Covered by the `S1` tests in `ui.spec.ts`.
- [x] S2. Clicking a scenario (rail or start card) starts a new chat, sets the flow and text, marks it current, and
  sends it (or opens the compare view for a compare scenario). Covered by the `S2` tests in `ui.spec.ts`.
- [x] S3. `#<id>` in the URL runs that scenario on load; `#rules` opens the rules panel. Covered by the `S3` tests in
  `ui.spec.ts`, `dialogs.spec.ts`.
- [x] S4. Dev only (`CHAPERONE_DEV=1`): "Demo data / Worst case" switch, `?data=worst` loads the worst-case set.
  Covered by the `S4` tests in `ui.spec.ts`.

## Chat and sessions

- [x] C1. Composer: auto-growing textarea, Enter sends, Shift+Enter adds a line, send button disabled when empty or
  busy, busy spinner and label "Checking". Covered by the `C1` tests in `ui.spec.ts`.
- [x] C2. Character counter appears at 85% of `max_text` (4000). Covered by the `C2` tests in `ui.spec.ts`.
- [x] C3. Each message is a turn with a session id; later turns reuse the session (placeholders stay the same).
  Covered by the `C3` tests in `ui.spec.ts`.
- [x] C4. "New chat" resets the session on the server (`POST /api/reset/<id>`), clears the turns and the scenario
  mark. Covered by the `C4` tests in `ui.spec.ts`.
- [x] C5. Streaming: steps render live from `/api/chat/stream` NDJSON, then the full result. Errors in the stream and
  dropped connections show a clear message, and the text is put back in the box. Covered by the `C5` tests in
  `ui.spec.ts`, `pipeline.spec.ts`.
- [x] C6. Follow mode: the live turn scrolls into view until the reader scrolls. Covered by the `C6` tests in
  `ui.spec.ts`.
- [x] C7. Screen reader announcements (`aria-live`) per step and at the end. Covered by the `C7` tests in
  `ui.spec.ts`.
- [x] C8. Copy button on the restored reply. Covered by the `C8` tests in `ui.spec.ts`.

## Step-by-step processing view

- [x] V1. "Find what is sensitive": item count, chips per kind and outcome with ×n, time. Covered by the `V1` tests in
  `pipeline.spec.ts`.
- [x] V2. "Apply the rules for this flow": counts text ("1 masked and 2 made vague."), or "A rule stops the whole
  request.", time. Covered by the `V2` tests in `pipeline.spec.ts`.
- [x] V3. "Try to work out who and what": live round text while running, then the summary, time; skipped reasons.
  Covered by the `V3` tests in `pipeline.spec.ts`.
- [x] V4. "Final check": "No masked value is left in what goes out. Sent to external AI." or "Nothing to send."
  Covered by the `V4` tests in `pipeline.spec.ts`.
- [x] V5. "Put the real values back" on the way back, with count and flags. Covered by the `V5` tests in
  `pipeline.spec.ts`.
- [x] V6. Outcome bar: "Sent with N changes.", "Sent as typed.", "Blocked. Nothing left this laptop." plus the rule
  link and reason, "Not sent. The final check stopped it.", "The AI did not answer." Covered by the `V6` tests in
  `pipeline.spec.ts`, `ui.spec.ts`.
- [x] V7. Flow line above the steps ("Manager to external AI, for general"). Covered by the `V7` tests in
  `pipeline.spec.ts`.
- [x] V8. Details panels stay open across live re-renders. Covered by the `V8` tests in `pipeline.spec.ts`.

## Decisions with reasons

- [x] D1. Details list every item: action chip, label chip, ×n for repeats, value, "sent as ...", whose data, found by
  which layer, note, rule link and reason; covered items dimmed. Covered by the `D1` tests in `pipeline.spec.ts`.
- [x] D2. Rule ids link to the rules panel at that rule (flash highlight); gateway-only rules show plain. Covered by
  the `D2` tests in `dialogs.spec.ts`.
- [x] D3. Highlights in "You wrote": each item marked by its outcome colour with a label superscript. Covered by the
  `D3` tests in `pipeline.spec.ts`.

## What was sent

- [x] W1. "External AI received" bubble with masked and vague tokens marked; falls back to plain server text if the
  rebuild does not match. Covered by the `W1` tests in `pipeline.spec.ts`.
- [x] W2. Blocked or not sent: dashed ghost "Nothing was sent. External AI never saw this message." Covered by the
  `W2` tests in `pipeline.spec.ts`.

## Attacker panel

- [x] A1. "Before tightening": each inference with category, guess, confidence, evidence words, and "Those words were
  made vaguer before sending."; "Words changed: ...". Covered by the `A1` tests in `pipeline.spec.ts`.
- [x] A2. "Still inferable" when not cleared (request blocked). Covered by the `A2` tests in `pipeline.spec.ts`.
- [x] A3. "Already disclosed earlier" and "Allowed for this flow" groups. Covered by the `A3` tests in
  `pipeline.spec.ts`.
- [x] A4. Names-and-IDs-only comparison: loads from `/api/baseline` after the result (shimmer meanwhile), the red
  callout "Masking names and IDs alone would have let a reader infer ...", and the "If only names and IDs were masked"
  list. Covered by the `A4` tests in `pipeline.spec.ts`.
- [x] A5. Pass count and the "weak evidence" note. Covered by the `A5` tests in `pipeline.spec.ts`.

## Include anyway

- [x] I1. A left-out item has "Include anyway"; it opens a reason box (8 to 200 characters); "Include and send again"
  resends the same message with `include` and shows "Included anyway: Phone. Your reason is in the audit log, with
  names removed." Covered by the `I1` tests in `pipeline.spec.ts`.

## Compare view

- [x] K1. "Compare three flows" button and compare scenarios open a dialog with one column per flow: flow title, Would
  be sent / Blocked, what would leave (differences outlined), what an attacker could infer. Loading shimmer; errors
  shown in the dialog; closes on outside click. Covered by the `K1` tests in `dialogs.spec.ts`.

## Restored reply

- [x] R1. "External AI replied" bubble shows placeholders as the AI wrote them, marked; markdown (paragraphs, lists,
  headings, rules, bold, code). Covered by the `R1` tests in `pipeline.spec.ts`.
- [x] R2. "You get back" bubble: real values restored and marked (title "The AI saw [PERSON_1]"), omitted and withheld
  markers kept visible. Covered by the `R2` tests in `pipeline.spec.ts`.
- [x] R3. Invented details flagged with a wavy underline and reason, and a "N details in the reply are not from your
  message." box in the restore step. Covered by the `R3` tests in `pipeline.spec.ts`.
- [x] R4. Typing indicator while the AI writes; "No reply." with the error when the call fails. Covered by the `R4`
  tests in `ui.spec.ts`.

## Exposure ledger

- [x] L1. "What the external AI could know" in the rail for external chats: category, guess, status, message number;
  "Nothing inferred about anyone yet in this chat." Covered by the `L1` tests in `pipeline.spec.ts`.

## Person report

- [x] PR1. Dialog with a search box; rows with time, flow, recipient, and what happened to each item; seal line; "may
  be incomplete" when the seal is broken; empty-state text. Covered by the `PR1` tests in `dialogs.spec.ts`.

## Seal check

- [x] SC1. "Check the audit log seal" shows a toast: "Audit log seal intact. Seal intact over N lines. Head ..." (or
  broken, with the line and reason); toast closes on its button and after 9 s. Covered by the `SC1` tests in
  `dialogs.spec.ts`.

## Records CSV

- [x] RC1. "Download processing record (CSV)" downloads `chaperone-processing-record.csv` from `/api/records.csv`.
  Covered by the `RC1` tests in `dialogs.spec.ts`.

## Rules panel

- [x] RU1. "View the rules": dialog with a pack switch, numbered rule cards (id, action, whole-message and how-vague
  chips, conditions, reason), "Items these rules do not decide go on to ..." link, purposes table, broken-file
  warning. Covered by the `RU1` tests in `dialogs.spec.ts`.
- [x] RU2. Admin mode (`CHAPERONE_ADMIN=1`): "Edit", toggles per condition, action/scope/how-vague fields, move up and
  down, delete, add at the top, catch-all locked last, purposes toggles, Save (toast, sealed), Cancel, two-click
  Reset, server errors shown, "Try your edit" preview with saved vs edited and what changed. Covered by the `RU2`
  tests in `dialogs.spec.ts`.
- [x] RU3. Read-only note when admin mode is off. Covered by the `RU3` tests in `dialogs.spec.ts`.

## Offline

- [x] O1. Local AI status in the top bar: "qwen2.5:3b, on this laptop", "offline" or "turned off" (red dot). Covered
  by the `O1` tests in `offline.spec.ts`.
- [x] O2. Offline warning in the find step, long form first, short form in later turns; internal sends still go out.
  Covered by the `O2` tests in `offline.spec.ts`.
- [x] O3. Offline refusal for external sends: "Local checks are offline, so nothing goes to an external AI." and the
  blocked outcome with rule `local-checks-offline`; "turned off" wording when the switch is off. Covered by the `O3`
  tests in `offline.spec.ts`.
- [x] O4. Gateway not running: start screen says how to start it; a send says "Could not reach the gateway...".
  Covered by the `O4` tests in `offline.spec.ts`.

## Timings

- [x] T1. Per step time (`<1 ms`, `N ms`, `N.N s`) and the outcome time "checks + AI N s". Covered by the `T1` tests
  in `pipeline.spec.ts`.
