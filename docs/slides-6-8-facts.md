# Slides 6 to 8: facts and sources

Every number and claim on slides 6 ("Impacts and Benefits"), 7 ("Business Impact & Scalability") and 8 ("Additional
links"), with where it comes from. Checked on 2026-10-17 against `main` at `2c1b51a` (redesign). Deck:
`/home/Muaz/Downloads/DevHack-fixed-shots.pptx`. Backups: `/home/Muaz/Documents/DevHack.backup-slides-6-8.pptx` (before the first
fill), `/home/Muaz/Documents/DevHack.backup-slides-6-8-redesign.pptx` (before this redesign). Styles: `docs/deck-style.md`.

## Numbers, compared with slides 3 and 4

| Number | Value | Source | Same as slides 3 and 4? |
|---|---|---|---|
| Hidden facts a reader could still guess, names and IDs only | 23 of 23 | `eval/results/inference_dev.md` (5 runs on 2026-10-17, all 23/23) | Yes (slide 3: 23/23) |
| Same, Chaperone full | 7 of 23, the middle of 5 runs; runs gave 8, 9, 7, 7, 7 | `eval/run_inference.py --split dev`, 5 runs on 2026-10-17; the committed result file is a 7/23 run (commit `008529a`) | Yes (slide 3 and the slide 4 footer: 7/23) |
| Test set for that | 32 messages, 28 forbidden facts, 23 that the grader could infer from the raw text | `eval/inference_dev.jsonl`; `eval/results/inference_dev.md` header | Slide 3 says "32-message test set" |
| Grader | Llama 3.1 8B, its own prompt; the in-loop attacker is Qwen2.5 3B | `eval/run_inference.py` (`--grader` default `llama3.1:8b`) | Yes (slide 4 table) |
| Sensitive details still sent, Chaperone full | 2.0% (2 of 102) | `eval/results/results_dev.md`, `eval/run_eval.py --split dev` on 2026-10-17 | Not on slides 3 or 4 |
| Same, Presidio with India recognizers | 37.3% (38 of 102) | same | Not on slides 3 or 4 |
| Same, Chaperone without the context layer | 38.2% (39 of 102) | same | Not used on the slides |
| Over-redaction (details that should pass but were changed) | Chaperone 3.0% (2 of 67), Presidio 70.1% (47 of 67) | same | Not on slides 3 or 4 |
| Detection F1, IDs and entities | Chaperone 0.98, Presidio 0.74 | same | Not used on the slides |
| Detection set | 86 messages, 169 labelled spans, hand-labelled by our team | `eval/dev.jsonl`; `eval/results/results_dev.md` header; `eval/README.md` | Not on slides 3 or 4 |
| Distinct messages in both test sets | 96 (86 detection cases use 64 distinct texts, some sent in two flows; plus 32 inference messages; no overlap) | `eval/dev.jsonl`, `eval/inference_dev.jsonl` (counted 2026-10-17) | Not on slides 3 or 4 |
| Details that should pass, and how many were changed | 67; Chaperone 2 (3.0%), Presidio 47 (70.1%) | `eval/results/results_dev.md` | Not on slides 3 or 4 |
| Detection set languages | 66 English, 20 Hinglish cases | `eval/dev.jsonl` `lang` | n/a |
| Held-out results | None: `eval/heldout.jsonl` has 0 cases | `wc -l eval/heldout.jsonl`; `eval/README.md` (written by teammates who haven't read `chaperone/`) | n/a |
| Speed | 3.3 s per message, the middle (p50) of 32 runs, AI reply included; p95 7.2 s and 15.2 s in two runs | timing script runs on 2026-10-17 (16 scenarios x 2, RTX 3050 Laptop GPU, 4 GB); README "Speed" | Yes (slide 4 footer: 3.3 s) |
| Tests | 108 pytest, 57 Playwright | `pytest --collect-only -q`; `npx playwright test --list` | Yes (slide 4 table) |

No number on slides 6 to 8 differs from slides 3 or 4.

## Claims on slide 6 (redesign)

| Claim | Source |
|---|---|
| English and Hinglish test messages | `lang` in both test sets (see above) |
| Graded by a separate model, Llama 3.1 8B | `eval/run_inference.py` `--grader` default |
| Checked against our own labels | `eval/run_eval.py` compares against the hand-labelled spans in `eval/dev.jsonl` |
| Presidio ran with its India recognizers | `eval/run_eval.py` (README "What Presidio already does") |
| Staff finish the notes without remembering what to delete | placeholders are swapped in and back automatically: `transform.py` `apply`, `restore_marked` |
| One search finds every request with a client's name; the log never stores it | `gateway.py` `person_report` (tags only, `_tag`); `test_audit.py::test_person_report_finds_every_request_that_carried_them`, `test_gateway.py::test_audit_log_holds_no_raw_values` |
| If a drug name gives the illness away, the AI gets the note, not the illness | scenario `8a`: "tamoxifen" leaves as `[HEALTH_1: health detail]`, the rest of the note is sent |
| A clinic or CA firm can use AI with a check in front of it, without an IT team | `setup.sh` (one script), runs on the office laptop (`__main__.py` binds `127.0.0.1`) |
| Speed about 3.3 s a message on a 4 GB laptop, middle of 32 runs | see the table above |

## Claims on slide 7 (redesign), with the Built or Next pill

| Item | Pill | Source |
|---|---|---|
| Runs on what they own: an office laptop, no cloud bill for the checks | Built | `detect.py` `OLLAMA_URL` default `127.0.0.1`; GLiNER on CPU |
| No per-seat licence: open source (MIT), one setup script | Built | `LICENSE`, `setup.sh`. The repo is private today |
| Paid hosted dashboard: shared rules and sealed logs across offices; the core stays free | Next | not in the code (no login, `127.0.0.1` only) |
| Sector rule packs: HIPAA Safe Harbor ships today; finance, HR, education next | Built | `chaperone/policies_safe_harbor.yaml`; the other packs are not in the code |
| Every data fiduciary, by 13 May 2027 | no pill (fact) | PIB 17 Nov 2025 and Bar & Bench (links below) |
| Who we start with: clinics, CA firms, college offices, SMEs | no pill (fact) | README, slide 2 |
| Users: one laptop, one person | Built | `__main__.py` (`host="127.0.0.1"`) |
| Users: office server with a login; many offices, one dashboard | Next | not in the code |
| Locations: India first, Indian IDs and Hinglish | Built | `detect.py` `RX`, `_valid`, `CONTEXT_PROMPT` |
| Locations: new rule sets as plain YAML files | Built | `policy.py` `_pack_files` (`policies_*.yaml`) |
| Locations: ID and language packs per country | Next | not in the code |
| Use cases: AI agents, through MCP | Built | `chaperone/mcp_server.py` |
| Use cases: a proxy for any OpenAI-style chat app | Next | not in the code (14 routes, `/` and `/api/*` only) |
| Use cases: browser extension for ChatGPT, Claude | Next | not in the code |
| Footnote 1: Qwen2.5 3B licence is research-only; the model is one setting | footnote | https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE; `detect.py` `CONTEXT_MODEL` |
| Footnote 2: DPDP dates | footnote | https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf ("an eighteen-month period for phased compliance"); https://www.barandbench.com/amp/story/view-point/meity-notifies-final-digital-personal-data-protection-rules-2025 (Gazette dated 13 Nov 2025, "May 13, 2027") |

Left out: a count of MSMEs in India (2026 reports disagree: 7.83 crore and 8.84 crore Udyam registrations; the
parliament answers could not be opened). No prices, no revenue projections.

## Claims on slide 8 (redesign)

| Claim | Source |
|---|---|
| GitHub repo link and QR code | `git remote -v`: `https://github.com/MuazTPM-YT/devhack2026-round1`. The link is a real hyperlink (also in the PDF export). The QR code was made with `qrcode` 8.2 (published 2025-05-01) and decoded with OpenCV 4.14.0.94 (2026-07-29), both from the image inside the deck and from the rendered slide: both give the exact URL. **The repo is private today** (404 without a login) |
| Code, tests, eval scripts with saved results, README | `chaperone/`, `tests/`, `web/e2e/`, `eval/`, `eval/results/`, `README.md` |
| Demo video | placeholder "[Drive link: to add]"; the QR slot is empty until the link exists |
| Commands: `git clone ….git`, `cd devhack2026-round1`, `./setup.sh`, `uv run --frozen python -m chaperone`, then open `http://127.0.0.1:8000` | `README.md` "Quick start" steps 3 and 4; run on a fresh clone on 2026-10-17 |
| Needs uv, Ollama and Node.js; the README lists the tested versions | `README.md` "What you need" |
| README walkthrough, from setup to every result | `README.md` (13 sections) |
| Eval scripts and results | `eval/run_eval.py`, `eval/run_inference.py`, `eval/results/` |
| 108 Python and 57 browser tests | `pytest --collect-only -q`; `npx playwright test --list` |
| Architecture diagram, in the README, steps 1 to 9 | `README.md` "How it works" (a text diagram with the nine numbered steps) |
