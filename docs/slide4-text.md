# Slide 4 text

Everything on slide 4, top to bottom, left to right. **Bold** marks the bold words on the slide.

## Header

Technical Approach

How **Chaperone** works, step by step.

## Intro box

**All of these steps** run on the laptop. A message takes six steps out and three back, and only the **checked** text reaches the AI.

## How one message is processed

Two flow diagrams. Each box has a number, a short name and one or two lines of text. Arrows join the boxes in order.

*When the user is sending the message to the AI* (1 to 3 on the top row, 4 to 6 below, step 5 in amber)

1. **Detect**
   Patterns catch IDs. Local models spot names, health and pay.
2. **Policy**
   Who, where and why pick the rule. Ex: Rahul's salary to marketing is **blocked**.
3. **Transform**
   Names become [PERSON_1]. Exact ages become ranges, like "in their 50s".
4. **Purpose**
   IDs the task doesn't need are **left out**, like a phone number in a clinical summary.
5. **Attacker**
   It sees "our only female cardiologist at Udupi" is one person, so that gets **vaguer**.
6. **Guard + send**
   A last scan looks for every masked value. **One hit** and nothing is sent.

*When the user gets a reply from the AI*

7. **Restore**
   Placeholders in the reply turn back into real names, **only** on your laptop.
8. **Verify**
   Ages, dates, amounts and names the AI **made up** get flagged.
9. **Audit**
   Logged as keyed hashes, never raw values. An edited line **breaks** the seal.

*Footer under the cards:* If the local checks are offline, nothing goes to an external AI. About 3.3 s per message on an RTX 3050 laptop. The 3B attacker can still miss some cases (7/23).

## What we used, and why

| Tools | What it does, and why |
|---|---|
| python-stdnum | Checks ID check digits, so an order number isn't mistaken for an Aadhaar. |
| GLiNER small | Finds names and places on the CPU, leaving the 4 GB GPU for the local model. |
| Qwen2.5 3B on Ollama | Reads meaning and plays attacker. Fewest false alarms of the 3 we tested. |
| YAML rule files | Hold the rules, so an admin can change them without touching code. |
| HMAC (a keyed hash) | Tags log values. Unlike a plain hash, trying every number won't undo it. |
| MCP (how AI agents call tools) | Lets any AI agent send through the same checks, with no custom code. |

## Also in the stack (bottom rows of the same table)

| Also in the stack | |
|---|---|
| Backend | Python 3.12 (uv), FastAPI, Uvicorn, httpx |
| Frontend | Next.js + React (TypeScript), static files served by FastAPI, works offline |
| Testing | pytest (108 tests) and Playwright (57 tests) |
| Evaluation | Llama 3.1 8B grader, Presidio baseline |

## Speaker notes

If asked what it guarantees (tests in tests/):
1. Masked values never leave: test_gateway.py::test_guard_stops_a_leak_before_any_network_call, test_session_history_is_guarded_too, test_guard_catches_respaced_and_cased_values
2. Not cleared, not sent (still guessable after 2 rounds means blocked): test_attack.py::test_message_that_cannot_be_cleared_is_not_sent
3. Local checks down or switched off, nothing goes to an external AI: test_gateway.py::test_external_is_refused_when_local_checks_are_offline, test_attacker_failing_mid_check_refuses_external, test_external_is_refused_when_checks_are_turned_off
4. No raw data in the log, and an edited line breaks the seal: test_gateway.py::test_audit_log_holds_no_raw_values; test_audit.py::test_seal_finds_an_edited_or_removed_line

Known limits: the small 3B attacker still misses some cases (7/23 leaked in our test); one request at a time; placeholder maps are lost on restart; English and Hinglish only.

Speed on an RTX 3050 laptop: about 3.3 s per message with the reply (p50), 7.0 s (p95), 32 runs. Checks alone: 1.6 s (p50), 4.9 s (p95). In the demo the external AI is simulated on the same laptop.
