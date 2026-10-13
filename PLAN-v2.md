# PLAN v2: from "mask and restore" to "attack every message before it leaves"

Masking and restoring is the floor (AgentCloak, CloakPipe, CloakLLM, Presidio, LLM Guard all do it; AgentCloak even
generalizes meaning, e.g. "headache" to "minor neurological condition"). What we add: a local attacker reads each
outgoing message, and the conversation so far, and we tighten until it can no longer infer what this flow forbids.

## Changes

| Item | Change | Where |
|---|---|---|
| W0 | Generalized spans become restorable: `[AGE_1: in their 50s]` goes out, "54-year-old" comes back locally. A local check flags ages, dates, amounts, long numbers and names in the reply that the source never said. | `transform.py`, new `verify.py` |
| W1 | Attacker: three focused local calls (identity, health, pay/HR/legal) + second checks, evidence verified against the text, forbidden if the flow's policy would not pass that category raw. Tighten evidence spans (generalize, then block), re-run, cap the rounds, refuse to send if not cleared. | new `attack.py`, `gateway.py` |
| W2 | Purpose check: one short call decides which identifiers the stated purpose needs; unneeded ones are omitted. "Include anyway" needs a reason; logged as hashes and ids. | `gateway.py`, `app.py` |
| W3 | `/api/compare`: one message, several flows, side by side, differences highlighted. Context results cached per text. | `app.py`, UI |
| W4 | Inference dev set (proxies, quasi-identifiers, Hinglish), mask-only vs full, graded by a different, larger local model. | `eval/` |
| W5 | Policy packs: default and "HIPAA Safe Harbor mode". Purpose is first-class in UI copy (DPDP purpose limitation, data minimisation). | `policies_*.yaml` |
| W6 | Processing record CSV from the audit log, no raw values. | `app.py` |
| UI | Apple-style light theme with glass materials, dark mode, new panels: attacker, exposure ledger, compare, flags. | `static/index.html` |

## Extras proposed (agent privacy)

- **E1 Conversation mosaic check.** Each message can be harmless alone; together they identify someone. The attacker reads every message already sent to this destination plus the new one. Evidence in old messages cannot be pulled back, so the UI says "already disclosed earlier".
- **E2 Exposure ledger.** Per person, what the external AI could infer so far in this conversation. Updated every turn.
- **E3 Agent gateway over MCP.** A small stdio MCP server (no SDK dependency) exposing `flowguard_check` and `flowguard_send`, so any MCP agent sends outbound text through the same checks. Built only after W0 to W5.

## Decisions (section 6) with measured numbers

Measured on this laptop, qwen2.5:3b on the RTX 3050, GPU cool, 8 test messages:

- **Attacker calls:** one combined zero-shot call missed both headline cases (no tamoxifen to cancer, no "only female cardiologist" re-identification). Two focused few-shot calls caught both, plus dialysis and a disability claim: **0.8 s mean, 1.05 s max per pass**. Decision: focused calls, examples never taken from demo or eval text.
- **Round cap:** at most **2 tightening rounds** (3 attacker passes, about 3 s worst case when cool). Budget: 5 s for the attacker on a cool GPU. A hot GPU (seen today: clock down to ~440 MHz) can triple this. If CPU-only, run one pass without tightening and say so in the UI.
- **Attacker and purpose in one call?** Neither. A purpose model call was tried in three wordings: qwen2.5:3b answered "needed" for nearly every identifier (it kept the discharge note's family phone "to contact the wife"). Purpose needs are now **declared per purpose in `policies.yaml`** (0 ms, deterministic, auditable, matches DPDP "specified purpose"). "General" (no purpose stated) omits nothing. Cost: a mislabelled purpose can omit something the task needs; "Include anyway" (with a logged reason) is the way out.
- **Attacker scope:** identity and health by default. The pay/HR/legal proxy call caused most false alarms and ~1 s per round; it is opt-in (`ATTACK_CATEGORIES`). Explicit pay/HR/legal mentions are still caught by the context layer.
- **What is forbidden:** an inference of category C is forbidden in a flow if the existing policy would not `pass` C raw in that flow. Identity maps to PERSON. No new policy syntax; packs just swap the rule file.
- **Thresholds:** report an inference only at confidence >= 0.7 **and** after a second check (identity: "how many people could this describe?" must be "exactly one" or "two to five"; health: must be a specific condition, not "illness"). False alarm cost: a vaguer message. Miss cost: a leak. Both rates go in the W4 table.
- **Evaluator:** llama3.1:8b (different family, different prompt) once ~8 GB of disk is free. Slow is fine offline.

## Where the brief and the code disagree

1. Generalization was one-way on purpose. W0 makes it restorable; README and UI copy change from "made vague for good" to "vague outbound, exact on this laptop".
2. The machine has a 4 GB GPU, not CPU-only. Numbers above are GPU numbers.
3. Disk has 2.1 GB free. The evaluator cannot be pulled until space is freed. W4 waits for that.
4. Purpose minimisation drops only identifiers (phone, email, IDs, UPI, vehicle). It never drops names or clinical facts: a discharge summary without the patient would be wrong.
5. HIPAA Safe Harbor covers the patient and relatives, employers, household members. Text has no photos or biometrics. We cannot tell a state from a city without a gazetteer, so Safe Harbor mode removes every location. Indian items (Aadhaar for SSN, PIN codes, UHID) are labelled as our adaptation. We never claim that the software makes anyone meet HIPAA.
6. "Attacker found nothing" is shown as "No inference found by the local check", never "safe".

## Order

W0, W1 (+E1, E2), W2, UI theme and panels, W3, W5, W4 (after disk), W6, E3, README. Commit after each.
