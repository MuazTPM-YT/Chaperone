# Slides 6 to 8: full text

Every line on slides 6 to 8 after the redesign, top to bottom, left to right, so it can be retyped by hand.
**Bold** marks bold words. Sources: `docs/slides-6-8-facts.md`. Styles: `docs/deck-style.md`.

## Slide 6: Impacts and Benefits

*Intro box (grey):* We tested **Chaperone** on 96 office messages we wrote and labelled ourselves, in English and
Hinglish. The question each time: from the text that actually leaves, what can a reader still find out?

**What we measured**

Three mint tiles. Each has two big numbers (Chaperone in green, the comparison in grey), a bold label and an italic
caption.

1. **7** Chaperone, **23** names and IDs only
   **Hidden facts a reader could still guess**
   *23 guessable facts in 32 messages, graded by a separate model (Llama 3.1 8B). Middle of 5 runs; range 7 to 9.*
2. **2%** Chaperone, **37%** Presidio
   **Sensitive details still sent**
   *102 sensitive details in 86 test cases, checked against our own labels. Presidio ran with its India recognizers.*
3. **3%** Chaperone, **70%** Presidio
   **Details changed that should pass**
   *67 details that should pass, in the same 86 cases. Over-blocking is what makes staff switch a tool off.*

**Who it helps** (two columns, green number circles)

1. **Staff keep using AI.**
   The receptionist still finishes the notes, **without** remembering what to delete.
2. **Owners can answer "where did my data go?"**
   One search finds every request with a client's name; the log never **stores** it.
3. **Patients and clients keep their secrets.**
   If a drug name gives the illness away, the AI gets the note, **not** the illness.
4. **Small offices get a safety net.**
   A clinic or CA firm can use AI with a check in front of it, **without** an IT team.

*Footnote (grey italic):* How we tested: 96 messages (86 detection cases and 32 inference cases), written and
hand-labelled by our team, who also tuned on them. The held-out set, written by teammates who haven't seen the code,
isn't ready yet. Speed: about 3.3 s a message on a 4 GB laptop (middle of 32 runs).

## Slide 7: Business Impact & Scalability

*Intro box (grey):* The checks run on a laptop the office already has. We charge only for **what grows** with the
office.

Three mint cards:

**Cost**

- [Built] **Runs on what they own.**
  An office laptop, and no cloud bill for the checks.¹
- [Built] **No per-seat licence.**
  Open source (MIT) and one setup script, unlike DLP (data loss prevention) suites.

**Revenue**

- [Next] **Paid hosted dashboard.**
  Shared rules and sealed logs across many offices. The core stays free.
- [Built] **Sector rule packs.**
  HIPAA Safe Harbor for clinics ships today. Finance, HR and education come next.

**Market**

- **Every data fiduciary, by 13 May 2027.**
  That's anyone deciding how personal data is used, under the DPDP Rules.²
- **Who we start with.**
  Clinics, CA firms, college offices and SMEs (small firms): client data, no IT team.

**How it scales** (three mint cards)

- **Users**: [Built] One laptop, one person / [Next] One office server, with a login / [Next] Many offices, one policy
  dashboard
- **Locations**: [Built] India first: Indian IDs and Hinglish / [Built] New rule sets as plain YAML files / [Next] ID
  and language packs per country
- **Use cases**: [Built] AI agents, through MCP / [Next] A proxy for any OpenAI-style chat app / [Next] Browser
  extension for ChatGPT, Claude

*Footnotes (grey italic):*

¹ Qwen2.5 3B's licence covers research use, so a paid version would ship a local model licensed for business. It's one
setting (CONTEXT_MODEL).

² PIB, 17 Nov 2025: DPDP Rules notified, with an 18-month phase-in. Bar & Bench, Nov 2025: Gazette dated 13 Nov 2025,
deadline 13 May 2027.

## Slide 8: Additional links

Three mint cards with green number circles:

1. **GitHub repo**
   **https://github.com/MuazTPM-YT/devhack2026-round1** (a clickable link; a QR code on the right)
   The code, the tests, the eval scripts with their saved results, and the README.
2. **Demo video**
   **[Drive link: to add]** (a dashed empty square on the right: "QR goes here once the link is added")
   On Google Drive.
3. **Deployment (optional)**
   No hosted version on purpose: it runs on your own laptop.
   It needs uv, Ollama and Node.js; the README lists the versions we tested.
   Commands (monospace block):
   `git clone https://github.com/MuazTPM-YT/devhack2026-round1.git`
   `cd devhack2026-round1`
   `./setup.sh`
   `uv run --frozen python -m chaperone`
   *then open http://127.0.0.1:8000*

**What's in the repo**

- **README walkthrough**: *From setup to every result*
- **Eval scripts and results**: *eval/, with the saved runs*
- **108 Python and 57 browser tests**: *pytest and Playwright*
- **Architecture diagram**: *In the README, steps 1 to 9*

*Template note (small, grey italic):* (Rename The file name to your team name while submitting)

## Lines on slides 3 and 4 that now repeat slide 6 (not edited)

| Slide | Line now | Suggested replacement |
|---|---|---|
| 3, point 2 body | "A local model plays attacker and tries to guess the hidden facts. If it can, Chaperone tightens the masking and checks again. Names-and-IDs-only masking leaked 23/23 in our test; Chaperone leaked 7/23." | "A local model plays attacker and tries to guess the hidden facts. If it can, Chaperone tightens the masking and checks again. (Results on slide 6.)" |
| 4, footer | "If the local checks are offline, nothing goes to an external AI. About 3.3 s per message on an RTX 3050 laptop. The 3B attacker can still miss some cases (7/23)." | "If the local checks are offline, nothing goes to an external AI." |

The speed and the 7/23 stay on slide 6 (tile 1 and the footnote), so nothing is lost from the deck.
