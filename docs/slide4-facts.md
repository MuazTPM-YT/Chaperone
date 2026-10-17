# Slide 4 facts and sources

Every claim on slide 4 ("Technical Approach") and its speaker notes, with where it comes from. Slide layout updated 2026-10-17: the steps are two flow diagrams, the tools table has two columns, and the bottom strip moved to the speaker notes. Re-checked on 2026-10-17 against the
working tree on top of commit `06d86e5` (it includes uncommitted changes to `chaperone/gateway.py` and the tests).
Line numbers are for that working tree. The slide states defaults; `.env` can change them (see `.env.example`).

Both entry points run the same pipeline: the web app (`chaperone/app.py:chat`, `chat_stream`) and the MCP tool
`chaperone_send` (`chaperone/mcp_server.py:call`) both call `gateway.chat`; `chaperone_check` and `/api/compare`
call `gateway.analyze` only, so nothing is sent.

## Intro box

| Claim | Source |
|---|---|
| All of these steps run on the laptop (the AI the text is sent to is not) | Detection, policy, attacker, guard, restore, verify and audit are local code or the local Ollama model (`detect.py:198` `OLLAMA_URL` is 127.0.0.1 by default). Only `gateway.send` calls the chat model. |
| Six steps out, three back | `gateway.analyze` (detect, decide, transform, purpose, attack) then `gateway.send` (guard + send); `gateway.chat` then restores, verifies and audits. `tests/test_gateway.py::test_steps_are_reported_in_pipeline_order` (fails in the current working tree, see the bottom of this file) |
| Only checked text ever reaches the AI | `gateway.py:226-243` (`send`, the only function that calls a chat model; the guard runs first) |

## How one message is processed

| Step | Claim | Source |
|---|---|---|
| 1 Detect | Patterns catch IDs | `detect.py:48-76` (`RX`, `PRIORITY`), `detect.py:80-109` (`_valid`, python-stdnum checks) |
| 1 Detect | Local models spot names, health, pay and more | GLiNER for names, companies, places `detect.py:153-193`; qwen2.5:3b for health, pay, MNPI, HR, legal `detect.py:199-218` |
| 2 Policy | Who, where and why decide | Rules match on label, subject, role, destination, purpose: `policy.py:18` (`WHEN_KEYS`), `policy.py:254-261` (`decide`, first match wins) |
| 2 Policy | Rahul's salary to marketing is blocked | `policies.yaml` rule `salary-not-for-marketing` (scope request); scenario `2b` in `chaperone/scenarios.json`; live run on 2026-10-16 (Sales to external, marketing: Blocked) |
| 3 Transform | Names become `[PERSON_1]` | `transform.py:37-44` (`Vault.placeholder`); `test_gateway.py::test_placeholders_follow_reading_order` |
| 3 Transform | Exact ages become ranges, like "in their 50s" | `transform.py:80-82` (`coarse`, AGE), `transform.py:37-44` (placeholder `[AGE_1: in their 50s]`); `test_verify.py::test_generalized_value_goes_out_coarse_and_comes_back_exact`. Applies where a rule generalizes AGE: `clinical-quasi-ids` (external clinical summary); Safe Harbor groups only ages over 89 as "90 or older" |
| 4 Purpose | A clinical summary doesn't need the phone number, so it's left out | `policies.yaml` `clinical_summary` omits PHONE; `gateway.py:85-101`; `test_gateway.py::test_purpose_omits_what_the_task_does_not_need` |
| 4 Purpose | (slide 3: only IDs are dropped) | `policy.py:26` (`MINIMISABLE`); `test_policy.py::test_purposes_may_leave_out_identifiers_only` |
| 5 Attacker | It sees that "our only female cardiologist at Udupi" is one person, so it gets vaguer | `attack.py:210-239` (`attack`), `gateway.py:196-223` (`_tighten`). Live run on 2026-10-17 (Manager to external, general, scenario `8b`): round 0 inferred "the only female cardiologist at Udupi" (0.9); sent as `[IDENTITY_1: a doctor at one of our branches]`; round 1 found nothing |
| 6 Guard + send | A last scan looks for every masked value | `transform.py:144-157` (`value_pattern`, `guard`), `gateway.py:230-234` |
| 6 Guard + send | One hit and nothing is sent | `test_gateway.py::test_guard_stops_a_leak_before_any_network_call` |
| 7 Restore | Placeholders in the reply turn back into real names, only on your laptop | `transform.py:164-184` (`restore_marked`), called in `gateway.py:428` after the reply arrives |
| 8 Verify | Ages, dates, amounts and names the AI made up get flagged | `verify.py:41-91` (`check`); `test_verify.py::test_fabricated_age_is_flagged`, `test_invented_date_month_amount_and_number`, `test_invented_name_is_flagged` |
| 9 Audit | Logged as keyed hashes, never raw values | `gateway.py:301-325` (`audit`), `gateway.py:272-273` (`_tag`, HMAC-SHA256); `test_gateway.py::test_audit_log_holds_no_raw_values` |
| 9 Audit | Editing a line breaks the seal | `gateway.py:277-279` (`_seal`), `gateway.py:350-375` (`verify_log`); `test_audit.py::test_seal_finds_an_edited_or_removed_line` |

Not on the slide because the code does not do it: the tamoxifen example for step 5. In a live run on 2026-10-17
"tamoxifen" is caught at step 1 (context layer, HEALTH) and made vague by a rule; the attacker found nothing.

## What we used, and why

| Tool | Claim | Source |
|---|---|---|
| python-stdnum | Checks Aadhaar, PAN and GSTIN numbers | `detect.py:10`, `detect.py:80-96` |
| python-stdnum | Checks ID check digits, so an order number isn't mistaken for an Aadhaar | `detect.py:81-83`; `test_detect.py::test_aadhaar_needs_valid_verhoeff`; scenario `4b` ("Order number 797971147104", expected unchanged) |
| GLiNER small | Finds names, companies and places | `detect.py:153-157` (`urchade/gliner_small-v2.1`, labels person name, organization, location) |
| GLiNER small | Finds names and places on the CPU, leaving the 4 GB GPU for the local model | `pyproject.toml` (`torch` from the `pytorch-cpu` index); README "Choosing the local model" (only one model sits in 4 GB of VRAM) |
| Qwen2.5 3B on Ollama | Reads meaning and plays attacker | `detect.py:199`, `attack.py:211` |
| Qwen2.5 3B on Ollama | Fewest false alarms of the 3 small models we tested | `eval/results/models_dev.md`: precision 0.87 vs 0.67 (qwen3:1.7b) and 0.45 (gemma3:1b); README "best precision, so the fewest false request blocks" |
| Qwen2.5 3B on Ollama | Fits in 4 GB | Ollama `/api/tags`: 1,929,912,432 bytes; `nvidia-smi`: RTX 3050 Laptop GPU, 4096 MiB |
| YAML rule files | Hold the rules, roles and purposes | `policies.yaml` header and `roles:`, `purposes:`; `policy.py:225-239` |
| YAML rule files | An admin can change them without touching code (a broken edit is also refused) | `test_policy.py::test_an_edit_applies_without_restart_and_reset_restores_the_shipped_rules`, `test_a_broken_file_on_disk_keeps_the_last_good_rules_and_says_why`, `test_bad_rules_are_refused_with_a_reason` |
| HMAC | Tags log values (every detected value) | `gateway.py:318-321` (`value_hmac` for every span) |
| HMAC | Unlike a plain hash, trying every number won't undo it | Reasoning: an Indian mobile number is 10 digits starting 6 to 9, so about 4 billion values, each cheap to hash. The tag uses the secret `AUDIT_HMAC_KEY` (`gateway.py:265-273`); the example key is refused (`test_gateway.py::test_example_audit_key_is_rejected`) |
| MCP | Lets agents send through the same checks | `mcp_server.py:28-37` (`chaperone_check`, `chaperone_send`), `mcp_server.py:75-85`; `test_mcp.py::test_handshake_and_tool_list` |
| MCP | Lets any AI agent send through the same checks, with no custom code | `mcp_server.py:1-2` (stdio JSON-RPC, the standard MCP transport) |

## Full stack strip (added 2026-10-17)

Only what the project imports or runs directly. Checked against the working tree on 2026-10-17.

| Item on the slide | Source |
|---|---|
| Python 3.12 | `pyproject.toml` `requires-python = "~=3.12.0"`; `uv.lock` `requires-python = "==3.12.*"`; `.venv` runs Python 3.12.12 |
| FastAPI | `pyproject.toml`; `chaperone/app.py:8-12` (FastAPI, StaticFiles, StreamingResponse, Starlette TrustedHostMiddleware) |
| Uvicorn | `pyproject.toml`; `chaperone/__main__.py` (`uvicorn.run`, 127.0.0.1) |
| httpx | `pyproject.toml`; `detect.py:357` (Ollama), `gateway.py:239` (chat endpoint) |
| Qwen2.5 3B (GPU) | `detect.py:199` (`CONTEXT_MODEL` default `qwen2.5:3b`); `setup.sh:17` (`ollama pull qwen2.5:3b`); `ollama ps` on 2026-10-17: `qwen2.5:3b  2.2 GB  100% GPU` |
| GLiNER on PyTorch (CPU) | `detect.py:153` (`urchade/gliner_small-v2.1`), `detect.py:168` (`from gliner import GLiNER`); `pyproject.toml` `torch` from the `pytorch-cpu` index |
| YAML policies | `pyproject.toml` (`pyyaml`); `policy.py:12` (`import yaml`), `chaperone/policies.yaml`, `policies_safe_harbor.yaml` |
| python-stdnum | `pyproject.toml`; `detect.py:10` (`from stdnum.in_ import aadhaar, gstin, pan`) |
| Next.js + React (TypeScript), static files served by FastAPI, works offline | `web/package.json`: `next` 16.3.8, `react` 19.3.0, `react-dom` 19.3.0 (exact pins; dev: `typescript` 5.9.3, `@playwright/test` 1.63.0); no UI kit. `web/next.config.ts`: `output: "export"` for the build. `chaperone/app.py`: `WEB = ROOT / "web" / "out"`, `GET /` serves `web/out/index.html`, `app.mount("/", StaticFiles(directory=WEB))` serves the rest; no Node process at run time. The old `chaperone/static/index.html` was removed in `65b816f` (last in `24f3d64`); `chaperone/static/` now holds only `fonts/`. Offline: the full Playwright suite passed 57 of 57 in a network namespace with only loopback (`unshare -rn`, 2026-10-17). Same look: `web/e2e/parity.spec.ts` compares text and full-window pixels with the old page for the slide 2 and 3 messages |
| MCP over stdio (JSON-RPC) | `mcp_server.py:1-2` ("JSON-RPC 2.0, one message per line (MCP stdio transport). No SDK"), `mcp_server.py:113` (`for line in sys.stdin`), replies carry `"jsonrpc": "2.0"` (`mcp_server.py:107-108`) |
| pytest (108 tests) and Playwright (57 tests) | `uv run --frozen pytest --collect-only -q`: 108 tests collected (20 need Ollama; `-m "not ollama"` collects 88). `cd web && npx playwright test --list`: "Total: 57 tests in 5 files". Checked 2026-10-17 on `main` at `ef68dfc` |
| Llama 3.1 8B as grader | `eval/run_inference.py:71` (`--grader` default `llama3.1:8b`) |
| Presidio + spaCy as baseline | `pyproject.toml` `baseline` group (`presidio-analyzer`, `spacy`, `en-core-web-lg`); `eval/run_eval.py:87-97` (`AnalyzerEngine()`, default spaCy `en_core_web_lg`) |
| uv (locked installs) | `uv.lock`; `pyproject.toml` `[tool.uv]` (`exclude-newer`, pytorch-cpu index); `setup.sh` uses `uv run --frozen` |

Layout change (2026-10-17): the strip is now rows at the bottom of the tools table. The "Rules and IDs" row was dropped because YAML and python-stdnum already have their own rows above; spaCy is not named (it is Presidio's default NLP engine, `run_eval.py:97`).

Duplicates removed (2026-10-17): the "Models" and "Agents" rows were deleted, since Qwen2.5 3B, GLiNER and MCP have their own rows in the tools table; the block is now headed "Also in the stack". GPU/CPU placement stays sourced above (GLiNER row: CPU; `ollama ps`: GPU).

Found in the code but not on the slide: Pydantic request models (`app.py:11`, comes with FastAPI); ruff and mypy (`pyproject.toml` dev group and `[tool.ruff]`, `[tool.mypy]`); sentencepiece and protobuf (listed in `pyproject.toml` only because GLiNER's tokenizer needs them); qwen3:1.7b and gemma3:1b (only in the local-model benchmark, `eval/run_eval.py --models`); bundled Inter and JetBrains Mono fonts.

## Right column, re-checked 2026-10-17 on `main` at `ef68dfc` (after the Next.js switch)

| Row | Still true? | Source |
|---|---|---|
| python-stdnum | Yes, kept | `detect.py` `_valid` (`aadhaar.is_valid`, `pan`, `gstin`); `test_detect.py::test_aadhaar_needs_valid_verhoeff`; scenario `4b` |
| GLiNER small | Yes, kept | `detect.py` `NER_MODEL = urchade/gliner_small-v2.1`, labels person name, organization, location; `pyproject.toml` `torch` from the `pytorch-cpu` index. Since `271ab6a` it loads from disk first (`_gliner`, `local_files_only=True`) |
| Qwen2.5 3B on Ollama | Yes, kept | `detect.py` `CONTEXT_MODEL` default `qwen2.5:3b` (context layer), `attack.py` uses the same model; `eval/results/models_dev.md` precision 0.87 vs 0.67 (qwen3:1.7b) and 0.45 (gemma3:1b) |
| YAML rule files | Yes, kept | `policy.py` (`yaml`, live reload, `save_local` for admin edits); `policies.yaml`, `policies_safe_harbor.yaml` |
| HMAC (a keyed hash) | Yes, kept | `gateway.py` `_tag` and `_seal` (HMAC-SHA256 with `AUDIT_HMAC_KEY`) |
| MCP | Yes, kept | `mcp_server.py`: stdio JSON-RPC, no SDK, tools `chaperone_check` and `chaperone_send` |
| Backend | Yes, kept | `pyproject.toml` (`requires-python ~=3.12.0`, `fastapi`, `uvicorn`, `httpx`); `uv.lock` |
| Frontend | **Changed**: "Nextjs + Reactjs (TypeScript)" to "Next.js + React (TypeScript), static files served by FastAPI, works offline" | See the stack table above |
| Testing | Counts already right (108, 57); kept | See the stack table above |
| Evaluation | Yes, kept | `eval/run_inference.py` `--grader` default `llama3.1:8b`; `eval/run_eval.py` Presidio `AnalyzerEngine` |

Nothing new was added. There is no proxy endpoint: `app.py` has 14 routes, `/` and `/api/*` only; `gateway.send` is
a client of any OpenAI-style `/chat/completions` endpoint, which the Backend row's httpx already covers. The page
uses no UI kit, so no frontend library row is needed. Every tool appears once in the column.

Layout: font, size (11 pt), column widths and divider lines unchanged. The Frontend row now takes two lines; the six
two-line rows above gave back 28,487 EMU each, so the table keeps its total height (4,087,365 EMU) and its top and
bottom stay level with the cards. Every run in the table is marked no-proofing. Backup:
`/home/Muaz/Downloads/DevHack-fixed-shots.backup-slide4-right.pptx`.

## Footer line (added 2026-10-17)

| Claim | Source |
|---|---|
| If the local checks are offline, nothing goes to an external AI | `gateway.py:144-152` (in commit 06d86e5). Web and MCP both go through `gateway.chat` and `analyze` (`app.py:chat`, `chat_stream`; `mcp_server.py:call`). Tests: `test_gateway.py::test_external_is_refused_when_local_checks_are_offline`, `test_attacker_failing_mid_check_refuses_external`; internal still allowed: `test_internal_still_goes_out_with_the_offline_warning`. No MCP-specific offline test |
| About 3.3 s per message on an RTX 3050 laptop | Speed section below (p50, reply included, 32 runs) |
| The 3B attacker still misses some cases (7/23) | `eval/results/inference_dev.md`, written by `eval/run_inference.py` on 2026-10-15; not re-run |

## Guarantees (speaker notes only, removed from the slide on 2026-10-17)

The bottom strip was removed from the slide; these are kept in the speaker notes for questions. All of these ran and passed on 2026-10-17 (`uv run --frozen pytest -m "not ollama"`:
85 passed, 1 failed, 20 deselected; the failure is not one of these).

| Guarantee | Tests |
|---|---|
| Masked values never leave: the last scan checks every message, history too, before sending | `test_gateway.py::test_guard_stops_a_leak_before_any_network_call`, `test_session_history_is_guarded_too`, `test_guard_catches_respaced_and_cased_values` |
| Not cleared, not sent: still inferable after 2 rounds means blocked | `test_attack.py::test_message_that_cannot_be_cleared_is_not_sent`; `attack.py:10` (`MAX_ROUNDS` = 2), `gateway.py:153-158` |
| Checks down, nothing out: offline or switched-off local model means external sends are refused | `gateway.py:144-152`; `test_gateway.py::test_external_is_refused_when_local_checks_are_offline`, `test_attacker_failing_mid_check_refuses_external`, `test_external_is_refused_when_checks_are_turned_off`; internal still goes out: `test_internal_still_goes_out_with_the_offline_warning`, `test_internal_still_goes_out_when_checks_are_turned_off` |
| No raw data in the log: only keyed hashes, an edited line breaks the seal | `test_gateway.py::test_audit_log_holds_no_raw_values`; `test_audit.py::test_seal_finds_an_edited_or_removed_line` |

## Known limits (speaker notes only)

| Limit | Source |
|---|---|
| The 3B attacker still misses some cases: 7/23 leaked (names and IDs only: 23/23) | `eval/results/inference_dev.md` (working tree; the committed version said 8/23) |
| One request at a time | `app.py:21` (`LOCK` around every pipeline call) |
| Placeholder maps are lost on restart | `gateway.py:50-51` (`SESSIONS` in memory) |
| English and Hinglish only | `detect.py:202-203` (`CONTEXT_PROMPT`) |

## Speed (speaker notes only)

Measured 2026-10-17 on the build laptop (NVIDIA GeForce RTX 3050 Laptop GPU, 4096 MiB), Ollama live with qwen2.5:3b,
attacker on (defaults). 32 runs: the 16 messages in `chaperone/scenarios.json`, each with its own flow, twice.
Each run calls `gateway.chat`, the function behind `/api/chat` and `chaperone_send`, with a new session, and the
detection cache is cleared first so every run does full detection. Models were warmed up with one message that is
not counted. Audit lines went to a scratch file, not `data/audit.jsonl`.

| What | Runs | p50 | p95 |
|---|---|---|---|
| End to end, including the chat model's reply (on the slide) | 32 | 3.3 s | 7.0 s |
| End to end, sent messages only | 28 | 3.9 s | 7.1 s |
| Checks only (`timings.total_ms`, steps 1 to 5) | 32 | 1.6 s | 4.9 s |
| Chat model reply only | 28 | 1.7 s | 3.3 s |

All 32 runs had the local checks online; the attacker ran in 26 (skipped where the flow allows every category or
a rule had already blocked); 4 were blocked; no errors. The reply comes from the simulated external AI
(qwen2.5:3b on the same laptop, `.env`), so a hosted model's time would differ.

## Not on the slide

- Llama 3.1 8B as the leak-test grader (cut for space; source `eval/results/inference_dev.md`).
- FastAPI, Uvicorn and httpx (plumbing).

## Found while checking

- `tests/test_gateway.py::test_steps_are_reported_in_pipeline_order` fails in the current working tree: the
  attacker now runs under the `checks_up` fixture, and the test still expects "local AI unavailable".
- The README's "If the local LLM is down, detection falls back to patterns and names" paragraph describes the old
  behaviour; external sends are now refused.
