# Slides 6 to 8: facts and sources

Every number and claim on slides 6 ("Impacts and Benefits"), 7 ("Business Impact & Scalability") and 8 ("Additional
links"), with where it comes from. Checked on 2026-10-17 against `main` at `ab05a85`. Deck:
`/home/Muaz/Downloads/DevHack-fixed-shots.pptx` (backup before these edits: `/home/Muaz/Documents/DevHack.backup-slides-6-8.pptx`).

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
| Held-out results | None: `eval/heldout.jsonl` has 0 cases | `wc -l eval/heldout.jsonl`; `eval/README.md` (written by teammates who haven't read `chaperone/`) | n/a |
| Speed | 3.3 s per message, the middle (p50) of 32 runs, AI reply included; p95 7.2 s and 15.2 s in two runs | timing script runs on 2026-10-17 (16 scenarios x 2, RTX 3050 Laptop GPU, 4 GB); README "Speed" | Yes (slide 4 footer: 3.3 s) |
| Tests | 108 pytest, 57 Playwright | `pytest --collect-only -q`; `npx playwright test --list` | Yes (slide 4 table) |

No number on slides 6 to 8 differs from slides 3 or 4.

## Claims on slide 6

| Claim | Source |
|---|---|
| English and Hinglish test messages | `eval/inference_dev.jsonl` (`lang`: 26 en, 6 hinglish); `eval/dev.jsonl` |
| Names go out as [PERSON_1] and come back filled in | `transform.py` `Vault.placeholder`, `restore_marked`; `test_gateway.py::test_first_name_alone_gets_the_full_names_placeholder` |
| Each message carries a purpose | `policy.Flow.purpose`; every `/api/chat` request needs `purpose` (`app.py` `ChatIn`) |
| A sealed log shows where data went | `gateway.py` `audit`, `_seal`, `verify_log`, `person_report`; `test_audit.py` |
| DPDP wants personal data used only for a stated purpose | PIB explainer, 17 Nov 2025 ("The notice must explain the specific purpose for which personal data is collected and used"): https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf |
| A diagnosis, salary or court case stays unless the flow allows it | `policies.yaml` rules on `HEALTH`, `COMPENSATION`, `LEGAL`; scenarios `1b`, `2b` |
| A drug name that gives away an illness is made vague | scenario `8a` ("tamoxifen" sent as `[HEALTH_1: health detail]`) |
| Aadhaar and PAN check digits | `detect.py` `_valid` (python-stdnum) |
| Reads Hinglish | `detect.py` `CONTEXT_PROMPT`; scenario `5` |
| 4 GB GPU, checks need no cloud account | `detect.py` `OLLAMA_URL` default `127.0.0.1`; GLiNER on CPU (`pyproject.toml`, `pytorch-cpu`); `nvidia-smi`: RTX 3050 Laptop GPU, 4096 MiB |

## Claims on slide 7, with the Built or Next tag

| Item | Tag | Source |
|---|---|---|
| Runs on one laptop with a 4 GB GPU, open models, no cloud bill for the checks | Built | as above; Qwen2.5 3B via Ollama, GLiNER `urchade/gliner_small-v2.1` (Apache-2.0) |
| Qwen2.5 3B's licence is research-only | footnote 1 | Qwen Research License Agreement, sections 1(i) and 2(a)-(b): https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE |
| The model is one setting | footnote 1 | `detect.py` `CONTEXT_MODEL = os.environ.get("CONTEXT_MODEL", "qwen2.5:3b")`; `.env.example` |
| Enterprise DLP is priced for banks | not a measured number | the team's own claim on slide 2 ("priced for banks"); no statistic used |
| Open source (MIT), one setup script | Built | `LICENSE` (MIT); `setup.sh`. The GitHub repo is private today (see slide 8) |
| Open-source core: gateway, rules, attacker, audit log | Built | `chaperone/` |
| Paid hosted dashboard for several offices | Next | not in the code; the app listens on `127.0.0.1` only (`__main__.py`) and has no login |
| Sector rule packs: HIPAA Safe Harbor ships today | Built part | `chaperone/policies_safe_harbor.yaml` |
| Finance, HR and education packs | Next | not in the code |
| DPDP Rules: 13 May 2027 deadline | fact, no tag | PIB, 17 Nov 2025: "an eighteen-month period for phased compliance" (link above). Bar & Bench, Nov 2025: Gazette notification dated 13 Nov 2025, transition "i.e., May 13, 2027": https://www.barandbench.com/amp/story/view-point/meity-notifies-final-digital-personal-data-protection-rules-2025. PIB itself gives the notification date as 14 Nov 2025 |
| Applies to every data fiduciary | fact, no tag | PIB: "Every Data Fiduciary must issue a separate consent notice". The brief said "regardless of size"; this was not written on the slide, because the PIB note does not say it in those words |
| Target segment: clinics, CA firms, college offices, SMEs | fact, no tag | README; slide 2 |
| One laptop, one person | Built | `__main__.py` binds `127.0.0.1` |
| One office server with a login; many offices, one dashboard | Next | not in the code |
| Aadhaar, PAN, GSTIN, UPI and Hinglish | Built | `detect.py` `RX`, `_valid`, `CONTEXT_PROMPT` |
| New rule sets as plain YAML files | Built | `policy.py` `_pack_files` (`policies_*.yaml` become rule sets) |
| ID and language packs per country or region | Next | not in the code |
| AI agents through MCP | Built | `chaperone/mcp_server.py` (`chaperone_check`, `chaperone_send`) |
| A proxy for any OpenAI-compatible chat app | Next | not in the code: `app.py` has 14 routes, `/` and `/api/*` only; `gateway.send` is a client of OpenAI-style endpoints, not a proxy |
| A browser extension for ChatGPT and Claude | Next | not in the code |

Left out: a count of MSMEs in India. Reports from 2026 disagree (7.83 crore and 8.84 crore Udyam registrations),
and the official parliament answers could not be opened from here, so no number is on the slide. No prices and no
revenue projections are on the slide.

## Claims on slide 8

| Claim | Source |
|---|---|
| GitHub repo URL | `git remote -v`: `https://github.com/MuazTPM-YT/devhack2026-round1.git`. **The repo is private**: the page and the API return 404 without a login (checked 2026-10-17) |
| Code, tests, eval scripts with saved results, a README that shows how to check every number | `tests/`, `web/e2e/`, `eval/`, `eval/results/`, `README.md` ("Evaluation") |
| No hosted version; setup is a few commands | `README.md` "Quick start"; `setup.sh`; `__main__.py` |
| git clone, ./setup.sh, uv run --frozen python -m chaperone, open 127.0.0.1:8000 | `README.md` steps 3 and 4; checked on a fresh clone on 2026-10-17 |
| Drive link | placeholder "[Drive link: to add]" for the team to fill |
