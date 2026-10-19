# Chaperone

[![CI](https://github.com/MuazTPM-YT/Chaperone/actions/workflows/ci.yml/badge.svg)](https://github.com/MuazTPM-YT/Chaperone/actions/workflows/ci.yml)

Chaperone is a privacy gateway that runs on the office laptop. It sits between staff and an AI chatbot. It checks
every message before it leaves, and decides what may go out based on the flow: what the data is, whose it is, who
sends it, where it goes, and why.

**The problem.** Small clinics, CA firms, college offices and small companies paste client data into AI chatbots to
get work done. Names and ID numbers are only part of the risk. "Priya has started tamoxifen" names no illness, but a
reader can still guess breast cancer. "Our only female cardiologist at Udupi" has no name, but it points to one
person. Enterprise DLP (data loss prevention) tools that could catch this cost too much for these offices, and the
Indian DPDP Act (Digital Personal Data Protection Act, 2023) still applies to them.

Built for DevHack 2026, problem statement 2.2 (context-aware data privacy).

![Patient note: names masked, age and date sent vague and restored exact, the family phone left out](docs/screenshots/s7.png)

## Contents

1. [What Chaperone is](#chaperone)
2. [How it works](#how-it-works)
3. [Quick start](#quick-start)
4. [Try it](#try-it)
5. [Using it from an AI agent (MCP)](#using-it-from-an-ai-agent-mcp)
6. [Configuration](#configuration)
7. [API](#api)
8. [Evaluation](#evaluation)
9. [Tests](#tests)
10. [Guarantees and known limits](#guarantees-and-known-limits)
11. [About DPDP and HIPAA](#about-dpdp-and-hipaa)
12. [Prior art and what's different](#prior-art-and-whats-different)
13. [Project layout](#project-layout)
14. [License](#license)

## How it works

A message takes six steps on the way out and three on the way back. All nine run on the laptop. Only the checked
text goes to the AI. There is no architecture image in `docs/` yet, so here is the same picture as text:

```text
  You type a message and pick the flow (role, destination, purpose)
        |
  THIS LAPTOP ----------------------------------------------------------------
  | 1 Detect -> 2 Policy -> 3 Transform -> 4 Purpose -> 5 Attacker -> 6 Guard |
  |                                                                     |      |
  | 9 Audit  <- 8 Verify  <- 7 Restore  <-----------------------+       |      |
  -------------------------------------------------------------|-------|------
                                                               |       v
                                              reply comes back |   only checked text
                                                               +---- the AI (internal or external)
```

1. **Detect.** Text patterns find 14 kinds of ID. An Aadhaar number must pass its Verhoeff checksum (a check digit),
   so an order number is not mistaken for one. GLiNER (a small NER model: named entity recognition) finds names,
   organisations and places on the CPU. A local model, Qwen2.5 3B run by Ollama (a local model runner), finds health,
   pay, MNPI (unpublished company results), HR and legal details. It sees IDs and names only as tags like `[PERSON]`.
2. **Policy.** Rules in YAML files decide each item by its type, its owner (a person or a business), the sender's
   role, the destination and the purpose. The first matching rule wins: pass, mask, make vague, or block. Some rules
   block the whole message, for example unpublished results to an external AI.
3. **Transform.** Masked values become numbered placeholders such as `[PERSON_1]`, the same for the whole
   conversation. Vague values keep a hint, such as `[AGE_1: in their 50s]` or a salary band.
4. **Purpose.** IDs the purpose does not need are left out, not masked. A clinical summary drops the phone number.
   Only IDs can be left out. "Include anyway" puts one back and needs a reason, which the audit log keeps.
5. **Attacker.** The local model reads the outgoing text, plus up to 6 earlier messages, and tries to work out a
   diagnosis or a person. If the flow forbids what it finds, those words are made vaguer, then blocked. After 2
   rounds that do not clear it, the message is not sent.
6. **Guard and send.** Before any network call, the payload and the history are searched for every masked value,
   ignoring spaces and case. One hit and nothing is sent. The send goes to any OpenAI-style chat service.
7. **Restore.** Placeholders in the reply become real values again, on the laptop only, even when the AI wrote them
   differently (`[person_1]`, `Person 1`).
8. **Verify.** Ages, dates, amounts, long numbers and names in the reply that you never wrote are flagged as
   invented.
9. **Audit.** One line per request: rule, action and a keyed hash (HMAC) of each value, never the value. Each line's
   seal covers the line before it, so an edited or removed line breaks the chain.

If the local checks are offline or turned off, nothing goes to an external AI. A message to the internal model still
goes out, with a warning that only IDs and names were checked.

### Techniques

The exact method in each step. Rules, file locations and limits are in [docs/methods/techniques.md](docs/methods/techniques.md);
full citations are in [docs/methods/references.md](docs/methods/references.md). A reference marked "inspired by" is an idea we built
on, not a paper we reproduced.

| Step | Technique | Key parameters | Reference |
|---|---|---|---|
| 1 Detect | Regular expressions with check digits (Verhoeff for Aadhaar; PAN holder-type letter; Luhn mod 36 for GSTIN, via python-stdnum). GLiNER span-based zero-shot NER. Local LLM extraction with JSON-schema-constrained output, IDs and names hidden as tags; a second narrow question for pay, HR and MNPI | 14 ID patterns; GLiNER `gliner_small-v2.1`, thresholds 0.5 (person) and 0.6; `qwen2.5:3b`, temperature 0, 10 few-shot examples, sentence windows of about 250 characters | Verhoeff 1969; Zaratiana et al. 2024 |
| 2 Policy | Ordered first-match rule list in YAML | Conditions: label, subject, role, destination, purpose; last rule is a catch-all | Inspired by Nissenbaum 2004 (contextual integrity) |
| 3 Transform | Consistent pseudonymization with a per-conversation map; generalization; suppression | `[LABEL_n]` per (label, canonical value); age to decade; pay to 4 yearly bands; date to month and year | Terms as in Sweeney 2002 (no k-anonymity guarantee); HIPAA Safe Harbor pack |
| 4 Purpose | Purpose-based data minimisation | Per-purpose omit list, identifiers only (8 types) | |
| 5 Attacker | Adversarial inference with a local LLM, then iterative tightening | Act if: evidence outside placeholders, confidence ≥ 0.7, confirmed by a second question, policy forbids it, evidence in the new message. At most 2 tightening rounds, then refuse | Inspired by Staab et al. 2024 and 2025 |
| 6 Guard + send | Pattern scan of the payload for every protected value; one hit and nothing is sent | IDs match with up to 3 separator characters between characters; case ignored | |
| 7 Restore | Tolerant placeholder matching with one regular expression | Accepts `[person_1]`, `PERSON_1`, `Person 1`, `[AGE_1: hint]`; only placeholders that were sent | |
| 8 Verify | Set difference: values in the reply minus values you wrote | Ages, dates, rupee amounts, numbers of 6+ digits, names (GLiNER) | |
| 9 Audit | `tag(v) = HMAC-SHA256(k, canon(v))`, first 16 hex characters; seal chain `mac_i = HMAC-SHA256(k, mac_{i−1} ‖ JSON(line_i))` | Key from `AUDIT_HMAC_KEY`; one fixed key, so no forward security | RFC 2104; inspired by Haber & Stornetta 1991, Schneier & Kelsey 1999 |

Tags are cut to 16 hex characters (64 bits) because they are only lookup keys: the person report matches them by equality, and a session tag names a conversation. Tamper detection uses the seal chain, which keeps the full 256-bit HMAC.

## Quick start

### What you need

| Need | Tested with |
|---|---|
| Linux or macOS. Windows is not supported (the audit log uses `fcntl`). | Arch Linux, kernel 7.2.9 |
| [uv](https://docs.astral.sh/uv/) (installs Python 3.12 and every package from the lockfile) | uv 0.13.1, Python 3.12.12 |
| [Ollama](https://ollama.com) | Ollama 0.40.4 |
| [Node.js](https://nodejs.org) 20.9 or newer, with npm (only to build the page once) | Node 26.11.1, npm 12.2.0 |
| A GPU with 4 GB is enough. Without one, the checks run on the CPU and are slower. | NVIDIA RTX 3050 Laptop, 4 GB |
| About 2 GB of free RAM and 5 GB of disk. Measured: the app used 1.2 GB of RAM (1.6 GB peak while loading); Python packages 1.7 GB, page build tools 0.4 GB, local model 1.9 GB, name model 0.6 GB | 15 GiB RAM |

### Steps

The commands work in bash, zsh and fish.

1. Install uv, Ollama and Node.js if you do not have them:

   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   curl -fsSL https://ollama.com/install.sh | sh        # Linux; on macOS use the app from ollama.com
   ```

   Install Node.js from [nodejs.org](https://nodejs.org) or your package manager (Arch: `sudo pacman -S nodejs npm`).

2. Start Ollama and check that it answers:

   ```sh
   sudo systemctl start ollama     # Linux with the service; without it, run `ollama serve` in its own terminal
   ollama list                     # must print a table, not "could not connect"
   ```

3. Get the code and run the setup once:

   ```sh
   git clone https://github.com/MuazTPM-YT/Chaperone.git
   cd Chaperone
   ./setup.sh
   ```

   `setup.sh` installs the Python packages, pulls the local model (`ollama pull qwen2.5:3b`), downloads the name
   model, builds the page (`npm ci && npm run build` in `web/`), and writes `.env` with a new random audit key. It
   stops with a clear message if something is missing.

4. Start Chaperone:

   ```sh
   uv run --frozen python -m chaperone
   ```

   Wait for `context layer ok`, then open <http://127.0.0.1:8000>. Startup took 5.0 s on the test laptop (3 runs).

After setup, nothing needs the internet. We checked this by running the full browser test suite in a sandbox with no
network (only `127.0.0.1`): 57 of 57 passed.

To update later: `git pull`, then `uv sync --frozen`, then `(cd web && npm ci && npm run build)`, then start again.
Your `.env`, the audit log (`data/audit.jsonl`) and rule edits (`data/policies.local.yaml`) are not touched.

### If something goes wrong

| What you see | What to do |
|---|---|
| `context layer OFFLINE`, or the page says "Local AI check: offline" | Start Ollama (step 2) and run `ollama pull qwen2.5:3b`. |
| The page says "The page is not built yet" | Run `cd web && npm ci && npm run build`. |
| `missing required env var ...` | Run `./setup.sh`, or copy `.env.example` to `.env`. |
| `AUDIT_HMAC_KEY still has the example value` | Run `./setup.sh`, or put a random value in `.env`. |
| `address already in use` | `PORT=8001 uv run --frozen python -m chaperone` |
| `ollama list` is empty after a pull | `ollama serve` as your user looks in `~/.ollama`; the service uses `/var/lib/ollama`. Use the service. |

## Try it

The page has three lanes: **You** (what you wrote, with each finding marked), **Chaperone** (each check as it runs)
and **External AI** (exactly what the AI received and replied). Pick a scenario in the side rail, or type a message.
The top bar sets the flow: sender role, internal model or external AI, purpose, and rule set. Open **Details** under
a step to see each decision with its rule and reason.

`http://127.0.0.1:8000/#7` runs scenario 7 at once. `/#rules` opens the rules.

| Id | Scenario | Flow | What it shows |
|---|---|---|---|
| 1a, 1b | Leave note, with and without "chemotherapy" | Manager to external AI, scheduling | The name passes; the medical detail is made vague |
| 2a, 2b | "Vikram Nair's revised salary is ₹14.2 lakh" | HR to internal / Sales to external marketing | Exact inside the organisation; the whole request blocked outside |
| 3a, 3b | Invoice with a PAN | Accountant to external AI, invoicing | A company's PAN passes; a person's PAN and name are masked |
| 4a, 4b | Twelve digits | Accountant to external AI | A valid Aadhaar is masked; an order number that fails the checksum passes |
| 5 | "Rahul ka salary 14 lakh hai" | Manager to external AI | Hinglish: the name and the pay are caught |
| 6a, 6b | Apple's Q3 revenue / our Q3 revenue before the announcement | Manager to external AI | Public results pass; unpublished results never leave |
| 7 | Discharge summary | Doctor to external AI, clinical summary | Names masked, age and date vague, the family phone left out |
| 8a | "She has started tamoxifen" | Manager to external AI | No diagnosis written, but names-only masking would let a reader infer breast cancer |
| 8b | "Our only female cardiologist at the Udupi branch" | HR to external AI | No name, but one person; the attacker makes it vaguer |
| 9 | Discharge note under HIPAA Safe Harbor | Doctor to external AI | Dates go to the year only |
| 10 | Medicine note, three flows | Compare view | The same note decided three ways, side by side, nothing sent |

The side rail also has the exposure ledger (what the external AI could know about people in this chat), **View the
rules**, **Person report** (every logged request that carried one person's name or ID), **Check the audit log seal**
and **Download processing record (CSV)**.

Rules live in `chaperone/policies.yaml` and `chaperone/policies_safe_harbor.yaml`. A changed file applies to the next
message, without a restart. A bad edit is refused and the last good rules stay in use. To edit rules in the page, start
with `CHAPERONE_ADMIN=1`; edits go to `data/policies.local.yaml` and every change is sealed in the audit log.

## Using it from an AI agent (MCP)

MCP (Model Context Protocol) is how AI agents call tools. `uv run --frozen python -m chaperone.mcp_server` starts a
stdio MCP server with two tools:

| Tool | What it does |
|---|---|
| `chaperone_check` | Dry run. Returns what would leave for this flow and what the local attacker could still infer. Nothing is sent. |
| `chaperone_send` | Sends through the same nine steps. Returns the reply with real values restored, and any invented-detail flags. |

Both take `text`, `role`, `destination`, `purpose`, and optionally `pack` and `session_id`. The allowed values come
from the rule files. Example client config:

```json
{"mcpServers": {"chaperone": {"command": "uv", "args": ["run", "--frozen", "python", "-m", "chaperone.mcp_server"],
                              "cwd": "/path/to/Chaperone"}}}
```

## Configuration

Settings live in `.env`. `setup.sh` writes it from `.env.example`. It is not committed. A value already set in the
environment wins over `.env`. A missing required value stops the app at start and names the variable.

| Key | Default | Meaning |
|---|---|---|
| `INTERNAL_LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | Required. OpenAI-style endpoint of the organisation's own model |
| `INTERNAL_LLM_MODEL` | `qwen2.5:3b` | Required. Model name at that endpoint |
| `INTERNAL_LLM_API_KEY` | empty | Bearer key, if that endpoint needs one |
| `EXTERNAL_LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | Required. The "external AI". The default is local Ollama standing in for a third party |
| `EXTERNAL_LLM_MODEL` | `qwen2.5:3b` | Required. Model name at that endpoint |
| `EXTERNAL_LLM_API_KEY` | empty | Bearer key for a real hosted API |
| `AUDIT_HMAC_KEY` | `change-me` (refused) | Required. Secret for the audit log hashes and seals. `setup.sh` writes a random one |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Where the local checks reach Ollama |
| `CONTEXT_MODEL` | `qwen2.5:3b` | Local model for meaning and for the attacker |
| `CONTEXT_TIMEOUT` | `20` | Seconds before a local model call gives up |
| `CONTEXT_CHUNK` | `250` | Characters per window when long text is read |
| `NER_MODEL` | `urchade/gliner_small-v2.1` | Name, organisation and place model |
| `ATTACK_CATEGORIES` | `IDENTITY,HEALTH` | What the attacker looks for. Add `COMPENSATION,HR,LEGAL` to widen it |
| `ATTACK_MAX_ROUNDS` | `2` | Tightening rounds before a message is refused |
| `ATTACK_MIN_CONFIDENCE` | `0.7` | Lowest attacker confidence that counts |
| `PORT` | `8000` | Port of the web app. It always listens on `127.0.0.1` only |
| `CHAPERONE_ADMIN` | empty | `1` lets the page edit the rules. Leave it empty for staff |
| `CHAPERONE_DEV` | empty | `1` shows a "Demo data / Worst case" switch with stress-test messages |

**A real hosted AI as the external destination.** Set three lines in `.env` and restart. No code change:

```sh
EXTERNAL_LLM_BASE_URL=https://api.openai.com/v1
EXTERNAL_LLM_MODEL=gpt-4o-mini
EXTERNAL_LLM_API_KEY=<your key>
```

Any service with an OpenAI-style `/chat/completions` endpoint works. The page then shows the host name instead of
"simulated on this laptop", and the audit log records which host and model received each request.

## API

All endpoints are on `http://127.0.0.1:8000`. Bodies are JSON. Requests whose `Host` header is not `127.0.0.1` or
`localhost` are refused.

| Method and path | What it does |
|---|---|
| `GET /` | The page (built from `web/`) |
| `GET /api/meta` | Roles, purposes, rule sets, scenarios, configured models |
| `POST /api/chat` | Check, send, restore. Answers once with the full result |
| `POST /api/chat/stream` | Same as `/api/chat`, as one JSON line per step, then the full result |
| `POST /api/compare` | Dry run of one message in up to 4 flows. Nothing is sent |
| `POST /api/baseline` | What masking names and IDs alone would send, and what the attacker infers from it |
| `POST /api/reset/{session_id}` | Forget one conversation's placeholders |
| `POST /api/person-report` | `{"value": "Ramesh Rao"}`: every logged request that carried this name or ID |
| `GET /api/audit/verify` | Check the audit log's seal chain |
| `GET /api/records.csv` | One row per request: purpose, destination, categories, actions. No personal values |
| `GET /api/policies` | The rule sets, purposes and allowed values |
| `PUT /api/policies/{pack}` | Admin mode only: save edited rules (checked first; `422` with the reason if invalid) |
| `DELETE /api/policies/{pack}` | Admin mode only: drop the local edits of one rule set |
| `POST /api/policies/preview` | Admin mode only: one message under the saved rules and under the edit. Nothing is sent or saved |

A chat request:

```sh
curl -s http://127.0.0.1:8000/api/chat -H 'Content-Type: application/json' -d '{
  "session_id": "demo-1",
  "text": "Draft an invoice to Suresh Kumar, PAN ABKPS7312M, for ₹45,000 of printing work.",
  "role": "Accountant", "destination": "external", "purpose": "invoicing", "pack": "default", "use_context": true}'
```

`text` is 1 to 4,000 characters. `use_context: false` turns the local model checks off (then external sends are
refused). `include: [{"label": "PHONE", "text": "...", "reason": "..."}]` is "Include anyway".

## Evaluation

Every number below comes from runs on 2026-10-17 on the test laptop (RTX 3050 Laptop, 4 GB). These are our own dev
sets: we tuned on them, so the numbers are optimistic. The held-out set (`eval/heldout.jsonl`) is still empty.

### What a reader can still infer

```sh
uv run --frozen python eval/run_inference.py --split dev     # needs llama3.1:8b in Ollama as the grader
```

It measures whether the text that leaves still lets a reader conclude a forbidden fact (a diagnosis, or who a person
is). Data: `eval/inference_dev.jsonl`, 32 messages (15 health hints, 9 descriptions of one person, 2 with both, 6
controls with nothing to infer; 6 in Hinglish), with 28 forbidden facts. A different, larger model (Llama 3.1 8B,
with its own prompt) grades each outgoing text. On the raw text it could infer 23 of the 28 facts; those 23 are the
denominator.

Results over 5 runs with the same code. The middle value (median) is shown, with the lowest and highest:

| System | Facts a reader can still infer (median) | Lowest to highest | Usefulness (median) | Refused | False alarms on the 6 controls |
|---|---|---|---|---|---|
| Names and IDs masked only (our own ablation, not any product) | 23 of 23 (100%) | 23 to 23 | 94% | 0 of 32 | 0 |
| Chaperone, attacker and purpose steps off | 16 of 23 (70%) | 15 to 17 | 89% | 0 of 32 | 0 |
| **Chaperone, full** | **7 of 23 (30%)** | **7 to 9** | 84% | 2 of 32 | 0 |

Usefulness is the share of the task's key words (names, days, amounts) found in the restored reply from the
simulated external AI. It is a keyword check, not a quality score. Vaguer text means fewer of those words come back.

The local model is not fully deterministic: the same text can get a different answer depending on what it read just
before. The same message run 6 times gave 2 different answers. So the numbers move from run to run, and we report the
range.

### Detection and policy per written span

```sh
uv run --frozen python eval/run_eval.py --split dev
```

It measures whether each labelled span (a name, an ID, a health detail) reached the outgoing text, and whether spans
that should pass were changed. Data: `eval/dev.jsonl`, 86 hand-labelled messages with 169 labelled spans.

| System | Leak rate | Over-redaction | Whole-request blocks (right / wrong / missed) |
|---|---|---|---|
| Chaperone, full | 2.0% (2 of 102) | 3.0% (2 of 67) | 5 / 0 / 0 |
| Chaperone, local model off | 38.2% (39 of 102) | 0.0% (0 of 67) | 0 / 0 / 5 |
| Presidio with its India recognizers | 37.3% (38 of 102) | 70.1% (47 of 67) | 0 / 0 / 5 |

Detection F1 (a score from 0 to 1 that combines precision and recall): IDs and named entities 0.98 for Chaperone
against 0.74 for Presidio; health, pay, MNPI, HR and legal 0.88 for Chaperone, which Presidio does not detect. These
numbers were the same in two runs, one with and one without the startup change in this release. Full tables:
`eval/results/results_dev.md` and `eval/results/inference_dev.md`.

### Speed

Measured with the 16 demo scenarios, each sent twice (32 messages), each in a new conversation, with the detection
cache cleared and the models already loaded. The reply comes from the simulated external AI (Qwen2.5 3B on the same
laptop), so a hosted AI would take a different time. Two runs:

| What | Run 1: p50 / p95 | Run 2: p50 / p95 |
|---|---|---|
| End to end, reply included | 3.4 s / 7.2 s | 3.3 s / 15.2 s |
| Checks only (steps 1 to 5) | 1.4 s / 4.9 s | 1.4 s / 11.6 s |
| AI reply only | 1.6 s / 3.3 s | 1.7 s / 6.4 s |

p50 is the middle message; p95 is the slowest 1 in 20. The slow tail moves a lot: in run 2 one reply ran to 25 s
because the AI wrote a long answer, and the GPU got hotter during the second pass. Both runs produced the same
masked text for every message.

Where the time goes (run 1, mean per message): AI reply 1.5 s, attacker 1.3 s, local model reading 0.6 s, its
second questions 0.1 s, name model 56 ms, the invented-detail check 114 ms. Everything else (patterns, rules,
placeholders, guard, restore, audit) takes under 1 ms. So about 95% of the time is the local model writing.

Startup to the first answered request: 5.0 s (3 runs). It was 8.1 s before the name model was loaded from disk
first; the online check for a newer copy cost 2.6 s.

## Tests

```sh
uv run --frozen pytest                    # Python: 108 tests (20 need Ollama)
uv run --frozen pytest -m "not ollama"    # the ones that run without Ollama (what CI runs)
cd web && npm run e2e                     # browser: builds the page, starts 3 gateways, runs 57 Playwright tests
```

The browser tests need Ollama and a Chromium for Playwright (`cd web && npx playwright install chromium`, once). They
cover every item in [docs/ui-parity.md](docs/ui-parity.md), the list of everything the page does. The audit log and
rule edits of the test gateways go to a temporary folder, not `data/`.

Lint and type checks: `uv run --frozen ruff check chaperone tests eval`, `uv run --frozen mypy chaperone`, and
`cd web && npx tsc --noEmit`.

## Guarantees and known limits

Each guarantee has a test in `tests/`:

- **Raw values cannot leave.** The payload and the history are checked for every masked value before any network
  call (`test_guard_stops_a_leak_before_any_network_call`, `test_session_history_is_guarded_too`).
- **Not cleared, not sent.** If the attacker still sees through it after 2 rounds, nothing is sent
  (`test_message_that_cannot_be_cleared_is_not_sent`).
- **Checks down, nothing out.** If the local checks are offline or turned off, nothing goes to an external AI
  (`test_external_is_refused_when_local_checks_are_offline`, `test_external_is_refused_when_checks_are_turned_off`).
- **The log keeps hashes, not values,** and an edited line breaks the seal (`test_audit_log_holds_no_raw_values`,
  `test_seal_finds_an_edited_or_removed_line`).

Known limits:

- The 3B attacker still misses some cases (7 of 23 leaked in our test, median of 5 runs, range 7 to 9; names and IDs only: 23 of 23).
- The attacker can also over-tighten harmless phrases: it guessed pregnancy from "shifts move to mornings" and made that phrase vague.
- One request at a time: a global lock serialises the pipeline.
- Placeholder maps live in memory and are lost on restart.
- English and Hinglish only.
- "Nothing found" by the local attacker is weak evidence, never a guarantee. A larger model or a person who knows
  the patient may infer more.
- No login. Admin mode is on or off for the whole server.
- HIPAA Safe Harbor mode removes identifiers in text. It does not make anyone meet HIPAA.

## About DPDP and HIPAA

Chaperone helps an office with some of its duties under India's DPDP Act:

- sending only what a purpose needs,
- keeping data safe when it goes to outside services,
- being able to tell a person where their data went.

Using Chaperone does not, on its own, mean an office meets the DPDP Act. The office also needs consent notices,
contracts with the outside services that process data on its behalf, and a process for data breaches.

The clinic pack is modelled on the US HIPAA Safe Harbor list, because it is a well-defined way to remove identifiers.
HIPAA itself applies to US organisations.

This is not legal advice.

## Prior art and what's different

From each project's own documentation. We ran Presidio. We did not run the others.

| Project | What it does |
|---|---|
| [Presidio](https://github.com/microsoft/presidio) | Finds and masks PII (personally identifiable information) with patterns, checksums and NER. Our detection baseline above. |
| [LLM Guard](https://github.com/protectai/llm-guard) | Input and output scanners for LLM apps, including a reversible anonymiser. |
| CloakLLM ([PyPI](https://pypi.org/project/cloakllm/)) | Masks PII before an LLM call and restores it in the reply. |
| [CloakPipe](https://github.com/rohansx/cloakpipe) | A privacy proxy in front of LLM APIs that masks and restores. |
| AgentCloak | Masking for agents, including making meaning vaguer ("headache" to a vaguer condition). |
| Staab et al., *Beyond Memorization*, ICLR 2024 ([arXiv 2310.07298](https://arxiv.org/abs/2310.07298)) | Shows that LLMs infer personal facts (place, age, health) from text with no explicit PII. This is the threat our attacker tests for. |
| Staab et al., *Language Models are Advanced Anonymizers*, ICLR 2025 ([arXiv 2402.13846](https://arxiv.org/abs/2402.13846)) | An LLM attacker and an LLM anonymiser take turns until the attacker fails. The closest idea to our attack-and-tighten loop. We did not invent it. |

What Chaperone adds:

1. **The flow decides what counts as a leak.** Cancer inferred from "tamoxifen" is forbidden for a manager writing to
   an external chatbot, and allowed in a doctor's clinical summary. Staab et al. remove every inferable fact.
2. **Small, local and bounded.** The attacker is a 3B model on a 4 GB laptop GPU, at most 2 rounds, then refuse. Its
   evidence must be words in the outgoing text, or the finding is dropped.
3. **Reversible.** Vague text leaves; the exact value comes back in the reply, on the laptop.
4. **Conversation memory.** The attacker reads earlier messages to the same destination, and the exposure ledger shows
   what the external AI could already know.
5. **Purpose minimisation** with a logged "Include anyway" reason.
6. **Where did this person's data go?** A person report finds every request that carried one person's name or ID,
   from a sealed log that holds no personal values.

## Project layout

| Path | What |
|---|---|
| `chaperone/detect.py` | Step 1: patterns, GLiNER, the local model |
| `chaperone/policy.py`, `policies.yaml`, `policies_safe_harbor.yaml` | Step 2: rules, roles, purposes; live reload and admin edits |
| `chaperone/transform.py` | Steps 3, 6 and 7: placeholders, the outbound guard, restore |
| `chaperone/purpose.py` | Step 4: purpose minimisation |
| `chaperone/attack.py` | Step 5: the local attacker |
| `chaperone/verify.py` | Step 8: flags invented details in replies |
| `chaperone/gateway.py` | The pipeline, the only call to an LLM, step 9 (audit log, person report, processing record) |
| `chaperone/app.py` | The HTTP API; serves the built page |
| `chaperone/mcp_server.py` | The MCP tools for agents |
| `chaperone/scenarios.json` | Demo scenarios, used by the page and the tests |
| `chaperone/static/fonts/` | Inter and JetBrains Mono, so the page works offline |
| `web/` | The page: Next.js and React in TypeScript, built to static files in `web/out` |
| `web/e2e/` | Playwright browser tests and the test gateway |
| `eval/` | Datasets, evaluation scripts and results |
| `tests/` | Python tests |
| `docs/` | Demo runbook, plans, screenshots, the UI parity checklist |
| `data/` | Made at run time, not committed: `audit.jsonl`, `policies.local.yaml` |
| `setup.sh`, `.env.example` | One-time setup, and every setting with a safe default |

## License

MIT. Uses FastAPI, GLiNER (`urchade/gliner_small-v2.1`, Apache-2.0), python-stdnum, Ollama with Qwen2.5 3B, Next.js
and React, Llama 3.1 8B (evaluation grader only) and Presidio (baseline only). The Inter and JetBrains Mono fonts are
under the SIL Open Font License; the licence texts are in `chaperone/static/fonts/`.

Qwen2.5 3B is under the [Qwen Research License](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE),
which covers research use, not commercial use. A paid version would ship a local model licensed for business. The
model is one setting (`CONTEXT_MODEL`), so no code changes.
