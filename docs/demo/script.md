# Demo video script

Target length 3:48 (hard limit 4:00). Voiceover: 475 words, about 3:24 at 140 words a minute. The spoken lines
alone are in `voiceover.txt`, and the subtitles are in `captions.srt`, with the same timing as this file.

Every scene was run on the live app on 2026-10-19 (Ollama on, qwen2.5:3b, RTX 3050 laptop, 4 GB). The
**Verified** line under each table says what was seen. **Real wait** is the measured time from the click to the
result. Cut or speed up those waits in editing; the times in the tables are after editing.

Before recording, do everything in `setup-checklist.md`. If a scene goes wrong, see `fallbacks.md`.

Fixed texts (all fictional, copy them exactly):

| Name | Text |
|---|---|
| Salary | `Summarise for the file: Vikram Nair's revised salary is ₹14.2 lakh per annum from April.` (the text of preset "Internal HR summarizer") |
| Hinglish | `Rakesh ka HbA1c 9.1 aaya, doctor ne metformin shuru kiya. Next week ki review meeting reschedule karo.` |
| Offline | `Draft a note to the team: Anil is off for two weeks after his knee surgery, his calls move to Meena.` Send this **only** in scene 6, with Ollama stopped (see the checklist). |

## Scene 1. Hook (0:00 to 0:21, running total 0:21)

| Time | On screen | Voiceover | Caption |
|---|---|---|---|
| 0:00–0:15 | A plain text editor, full screen, large font. Paste the discharge note of preset "Discharge summary" (Ramesh Rao, 54, chest pain). Slow push-in on "type 2 diabetes". No chatbot brand on screen. | It's late at a small clinic. The receptionist wants to go home, so they paste the discharge notes into an AI chatbot. They didn't do anything wrong. But the diagnosis has left the building. | Fictional clinic. Fictional patient. |
| 0:15–0:21 | Cut to the Chaperone start screen: "You see real names. The AI sees only what it needs." | The problem isn't people. Nobody gave them a safe way to use AI. | |

**Verified:** the start screen headline, at 125% zoom (screenshot).

## Scene 2. Same words, three flows (0:21 to 0:53, running total 0:53)

| Time | On screen | Voiceover | Caption |
|---|---|---|---|
| 0:21–0:29 | Start screen. Cursor on the three lane heads: You, Chaperone ("Checks on this laptop"), External AI. | This is Chaperone. It runs on the office laptop and checks every message before it reaches an AI. | |
| 0:29–0:37 | Side rail, Salary: click **Internal HR summarizer** (HR, Internal model, HR summary). Real wait 2.9 s: cut to 1 s. Zoom on the green bar "Sent as typed." and the right lane, "Internal model received": the sentence as typed. | One sentence about Vikram's salary. HR sends it to the internal assistant. It goes as typed. | HR to internal assistant: sent as typed |
| 0:37–0:43 | Click **External marketing copilot** (Sales, External AI, Marketing). Real wait 0.1 s. Zoom on the red bar "Blocked. Nothing left this laptop." and the rule line `salary-not-for-marketing`: "Pay data has no place in an external marketing tool." Right lane: "Nothing was sent." | Sales sends it to an outside marketing chatbot. Blocked. Nothing leaves. | Sales to outside marketing chatbot: blocked |
| 0:43–0:53 | Click **New chat**. Top bar: role **Intern**, **External AI**, purpose **General**. Paste the Salary text, press Enter. Real wait 2.3 s to the result, 4.2 s with the reply: cut. Zoom on the right lane: `[PERSON_1]'s revised salary is [COMPENSATION withheld] from April.` | An intern sends it outside. The name and the salary are hidden. Same words. Different flow. Different answer. | Intern to outside AI: name and salary hidden |

**Verified:** each flow ran twice (API and browser), same result both times. HR internal: sent as typed, rule `internal-stays-internal` /
`pay-hr-finance-internal`. Sales marketing: blocked by `salary-not-for-marketing`. Intern: name masked
(`intern-ids-masked`), salary withheld (`intern-no-sensitive`).

## Scene 3. The attacker (0:53 to 1:41, running total 1:41)

| Time | On screen | Voiceover | Caption |
|---|---|---|---|
| 0:53–1:02 | **New chat**. Role **Manager**, **External AI**, **General**. Paste the Hinglish text, press Enter. Let the middle lane run live (2.8 s in total, no cut). | Hiding names isn't enough. This Hinglish note never says diabetes. Chaperone blurs the test result and the drug. | |
| 1:02–1:17 | Zoom on "Try to work out who and what" (amber "!"): "Inferred diabetes. Those words were made vaguer, then the attacker found nothing this flow forbids." Click its **Details**. Point at "Before tightening: Health, diabetes, 90% sure, from HbA1c" and "Words changed: HbA1c." | Then a local model plays attacker and tries to guess what's hidden. It still guesses diabetes, from the word HbA1c. So that word gets vaguer too, and the next try finds nothing. | The attacker is a small local model. It runs before anything leaves. |
| 1:17–1:28 | Point at the red box "Masking names and IDs alone would have let a reader infer diabetes." and at "If only names and IDs were masked: diabetes, from HbA1c 9.1, metformin". Then pan to the right lane, "External AI received": `[PERSON_1] ka [HEALTH_3: a health matter] [HEALTH_1: health detail] aaya, doctor ne [HEALTH_2: health detail] shuru kiya.` | Masking only names and IDs would have given diabetes away. And if it's still guessable after two rounds, nothing is sent. | Names-and-IDs-only masking: a reader guesses diabetes |
| 1:28–1:41 | Side rail, What an attacker infers: click **Our only female cardiologist** (HR, External AI, HR summary). Real wait 8.3 s to the result: speed up 4x. Open the attacker **Details**: "Identity: the only female cardiologist at Udupi, 90% sure". Then the right lane, **scroll up** to "External AI received": `[IDENTITY_1: a doctor at one of our branches] has requested [HEALTH_1: a health matter] from June; draft the cover rota.` Do not show the reply (see fallbacks). | No name here. But our only female cardiologist at Udupi is one person. So she leaves as a doctor at one of our branches. | No name, still one person |

**Verified:** Hinglish, 5 of 5 runs: the rules made `9.1` and `metformin` vague, the attacker guessed diabetes from
"HbA1c" (0.9), tightened it (rule `attacker-tighten`), and the second pass found nothing. The names-and-IDs-only
comparison guessed diabetes from "HbA1c 9.1" and "metformin" every time. Cardiologist, 3 of 3 API runs plus 1 browser run: the attacker
guessed pregnancy (from "maternity leave") and the identity, and the text left as shown.

## Scene 4. The answer comes back (1:41 to 2:13, running total 2:13)

| Time | On screen | Voiceover | Caption |
|---|---|---|---|
| 1:41–1:48 | Side rail, Patient note: click **Discharge summary** (Doctor, External AI, Clinical summary). Real wait 4.3 s to the result, 6.6 s with the reply: cut. Show the left lane "You wrote" with the coloured marks. | Back to the clinic. The discharge note goes to an outside AI. Names leave as placeholders. | |
| 1:48–1:55 | Zoom on the right lane, "External AI received": `[PERSON_1]`, `[AGE_1: in their 50s]`, `[DATE_1: March 2026]`, `[PERSON_2]`. Point at the side rail legend "Made vague: a vaguer version goes out; the exact value stays here". | The age and the date leave vaguer, and the exact values stay on the laptop. | Exact age and date never leave the laptop |
| 1:55–2:01 | Click **Details** under "Apply the rules for this flow". Point at "Left out, Phone, 98450 12345, sent as [PHONE omitted]", rule `purpose-minimisation`: "Not needed to write a clinical summary of a patient's care, so it is left out". | IDs the summary doesn't need, like the wife's phone number, are left out. | Purpose: clinical summary. Phone number left out. |
| 2:01–2:13 | Scroll to "You get back": "Ramesh Rao" and "Sunita Rao" marked. Use a take where "50-year-old" has the wavy underline. Open **Details** under "Put the real values back": "Age 50 is not from your message. Your message says 54." | The reply gets the real names back, only on this laptop. And when the AI writes an age the doctor never gave, Chaperone flags it. | Invented detail flagged |

**Verified:** 12 of 12 API runs and 2 browser runs: names masked, age and date made vague, phone left out by `purpose-minimisation`, names
restored in "You get back". The flag on an invented age appeared in **3 of 12** runs; record takes until one has it
(see fallbacks). The exact age (54) and date (12 March) are **not** put back in the reply: the AI writes "in his
50s" or "March 2026", so the reply keeps the vague form. That's why the voiceover says the exact values "stay on the
laptop", not "come back".

## Scene 5. Proof (2:13 to 2:46, running total 2:46)

| Time | On screen | Voiceover | Caption |
|---|---|---|---|
| 2:13–2:25 | Side rail, Records: click **Person report**. Type `Ramesh Rao`, click **Find**. Real wait under 0.1 s. Zoom on the first row: time, "Doctor to external AI, clinical summary", the recipient, "Name: sent as placeholder [PERSON_1]". | Now the owner's question. Where did this patient's data go? One search finds every request that carried his name, where it went, and how it was sent. | The log stores keyed hashes, never the name |
| 2:25–2:32 | Close the dialog. Click **Check the audit log seal**. Toast: "Audit log seal intact. Seal intact over N lines." | The log never stores the name. Only keyed hashes: tags that can't be turned back. | |
| 2:32–2:46 | Cut to the terminal (see the checklist for the font and the `sealcheck` helper). Type the three commands below. The last one prints `Seal broken at line 3. This line was changed, or a line before it was removed, added or moved.` Real wait under 0.2 s. | Every line is sealed to the one before it. I change one line in a copy of the log, to say nothing was sent. The check names the broken line. | Edited copy: seal broken at line 3. The real log is untouched. |

Terminal commands for 2:32 (use the line number you picked in the checklist; 3 is an example):

```fish
cp data/audit.jsonl /tmp/chaperone-demo/copy.jsonl
sed -i '3s/"sent": true/"sent": false/' /tmp/chaperone-demo/copy.jsonl
sealcheck /tmp/chaperone-demo/copy.jsonl
```

**Verified:** person report for "Ramesh Rao" found every discharge request (0.01 s). The seal button said intact. On
a copy of the log, changing `"sent": true` to `"sent": false` on one line made the check report that exact line.
The real `data/audit.jsonl` stayed intact (checked with `/api/audit/verify` after the test).

## Scene 6. Fails closed (2:46 to 3:02, running total 3:02)

| Time | On screen | Voiceover | Caption |
|---|---|---|---|
| 2:46–2:50 | Terminal: `sudo systemctl stop ollama`. Cut the password prompt. | What if the local checks go down? | Local model stopped |
| 2:50–3:02 | Browser: **New chat**. Role **Manager**, **External AI**, **General**. Paste the Offline text, press Enter. Real wait 0.1 s. Zoom on the top right: red dot, "Local AI check: offline". Then the find step's red note "Local checks are offline, so nothing goes to an external AI.", the red bar "Blocked. Nothing left this laptop." (rule `local-checks-offline`) and the right lane "Nothing was sent. External AI never saw this message." | I stop the local model and send a new message. Nothing goes to the external AI. No checks, no send. | Fails closed: nothing sent |

After this scene, start Ollama again off camera: `sudo systemctl start ollama`.

**Verified:** 5 of 5 external sends with Ollama stopped (3 API, 2 browser): blocked by `local-checks-offline` in under 0.1 s. The
red "offline" dot shows only for a message that wasn't checked earlier with Ollama on (see the checklist).

## Scene 7. Agents too (3:02 to 3:17, running total 3:17)

| Time | On screen | Voiceover | Caption |
|---|---|---|---|
| 3:02–3:17 | Terminal with Claude Code (started as in the checklist). Paste the agent prompt from the checklist. Show the tool call `chaperone_check` and its result: `"outbound": "[PERSON_1] ka [HEALTH_3: a health matter] [HEALTH_1: health detail] aaya, ..."`. Real wait about 21 s: speed up or cut. Stop before the agent's own summary. | AI agents get the same checks through MCP, the way AI agents call tools. Here Claude Code checks the Hinglish note with Chaperone first. The agent only gets the masked text. | MCP tool: chaperone_check |

**Verified:** `claude -p` (Claude Code 2.1.303) with the checklist's MCP config called `chaperone_check` and got
the same masked text as scene 3, with "rounds": 2. **Not verified:** how the interactive Claude Code screen shows
the tool call. Rehearse it once.

## Scene 8. Numbers and close (3:17 to 3:48, running total 3:48)

| Time | On screen | Voiceover | Caption |
|---|---|---|---|
| 3:17–3:31 | Slide 6 ("Impacts and Benefits"), full screen. Highlight each tile as it's said: 7 vs 23, then 2% vs 37%. Leave the third tile (3% vs 70%) on screen. | On our own test messages, masking only names and IDs left 23 hidden facts a reader could guess. Chaperone left 7. Sensitive details sent: 2%, against 37% for Presidio, an open-source masking tool. | Our own test messages; best-case numbers until the held-out set is ready |
| 3:31–3:36 | Slide 5 (architecture diagram), 5 seconds. | It adds about 2 seconds a message. | |
| 3:36–3:48 | End card: Chaperone start screen, dimmed. Large text: `github.com/MuazTPM-YT/Chaperone`. | From 13 May 2027, India's data protection law, the DPDP Act, keeps every office responsible for client data it sends out. Chaperone gives small offices a safe way to use AI. | github.com/MuazTPM-YT/Chaperone |

**Verified against the deck** (`~/Downloads/DevHack-fixed-shots.pptx`, saved 2026-10-19): slide 6 has 7 vs 23,
2% vs 37%, 3% vs 70%, "about 2 seconds"; slide 7 has 13 May 2027 and "keeps every office responsible"; slide 8 has
`github.com/MuazTPM-YT/Chaperone`. The speed fits the live runs: the checks took 1.4 s to 2.9 s on scenes 2 to 4.
