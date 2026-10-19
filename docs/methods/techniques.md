# Techniques, by pipeline step

The exact method behind each of the nine steps on slide 4 and the architecture diagram (slide 5). Every item names
the file and function it lives in. Defaults are as shipped; `.env` can change the ones marked "env". Checked on
2026-10-18 against `main` at `cc74bb4`.

Rule for this file: only what the code does. A paper is listed as the basis or inspiration for something we built, never
as something we implemented exactly. Full citations are in [references.md](references.md).

## 1 Detect

Three layers. Each later layer skips text an earlier layer already claimed.

| Layer | Technique | Parameters | Where |
|---|---|---|---|
| Patterns | Regular expressions for 14 identifier kinds (EMAIL, URL, UPI, GSTIN, PAN, IFSC, MRN, ACCOUNT, AADHAAR, IP, VEHICLE, PHONE, DATE, AGE). On an overlap the earlier label in `PRIORITY` wins (a GSTIN contains a PAN; a UPI handle can contain a phone number). | MRN and ACCOUNT count only next to a cue word (`MRN`, `UHID`, `A/c` ...). | `detect.py` `RX`, `PRIORITY`, `deterministic` |
| Check digits | Aadhaar: **Verhoeff** check digit (dihedral group D5). PAN: format `AAAAA9999A`, 4th letter must be a known holder type, digits not `0000`. GSTIN: state code, embedded PAN valid, 14th char `Z`, and a **Luhn mod 36** check character. All three come from python-stdnum 2.2 (`aadhaar.is_valid`, `pan.is_valid`, `gstin.is_valid`); we do not implement the algorithms ourselves. | PAN or GSTIN holder letter `P` (person) or `H` (Hindu undivided family) means an individual; any other letter means a business. Work emails are split by a list of role mailboxes (`info@`, `accounts@` ...). | `detect.py` `_valid` |
| Entities | **GLiNER**: span-based zero-shot NER (named entity recognition), model `urchade/gliner_small-v2.1`, on the CPU. | Labels `person name`, `organization`, `location`. Thresholds: PERSON 0.5, ORG 0.6, LOCATION 0.6. Stop-list of role nouns and acronyms. A found full name also masks its first name used alone later (exact, case-sensitive match). | `detect.py` `entities`, `NER_*`, `first_names` |
| Context | **Local LLM extraction with JSON-schema-constrained output** (Ollama `format` = JSON schema). Model `qwen2.5:3b`, temperature 0, seed 0, 10 few-shot examples. Before the model sees the text, every pattern hit and every name is replaced by a `[LABEL]` tag. | Categories HEALTH, COMPENSATION, MNPI, HR, LEGAL, plus PERSON for names GLiNER missed. Text read in **sentence-aligned windows of about 250 characters** (env `CONTEXT_CHUNK`). A quote the model paraphrased is located by the longest common substring (`difflib`), accepted if it is at least max(4, 0.6 × quote length) characters. | `detect.py` `context`, `windows`, `_mask`, `_locate`, `SCHEMA`, `FEW_SHOT` |
| Second question | A narrow follow-up question per finding, also schema-constrained. COMPENSATION: yes/no "is this pay, or a price/invoice/rent/fee?". MNPI: yes/no "price-sensitive and still secret?", asked about the phrase and, if that says no, about its sentence (a phrase of under 2 words is only asked as its sentence). HR: **not yes/no**; a 9-way choice (performance rating, warning, improvement plan, schedule change, leave, paperwork, facilities, payroll admin, other). The HR finding is dropped only for the 5 clearly non-HR answers. | Money is a regex candidate first; only an amount the model calls pay becomes COMPENSATION. | `detect.py` `_is_pay`, `_is_mnpi`, `_is_hr`, `money_candidates`, `_merge_money` |

Reference: GLiNER (Zaratiana et al. 2024). Verhoeff (1969) for the Aadhaar check digit.

## 2 Policy

**Ordered first-match rule list** in YAML. Each rule has a `when` over five attributes and one action.

- Attributes: `label` (information type), `subject` (individual, business, unknown), `role` (sender), `destination`
  (internal or external AI), `purpose`.
- Actions: `pass`, `pseudonymize`, `generalize`, `block`. `scope: request` makes a block stop the whole message.
- Rule: `decide(x) = action of the first rule r with every condition in r.when true for x`. The last rule must be a
  catch-all (no `when`), so every item gets a decision; this is checked when the file loads.
- Rule packs: HIPAA Safe Harbor mode runs its own rules first, then falls through to the standard rules (`extends`).
- Files reload on change; a broken edit is refused and the last good rules stay.

Where: `policy.py` `decide`, `WHEN_KEYS`, `_check_rules`, `_build`; `chaperone/policies.yaml`,
`chaperone/policies_safe_harbor.yaml`.

Reference: the five attributes map onto the parameters of **contextual integrity** (Nissenbaum 2004): sender,
recipient, subject, information type, and the norm of the flow. This is the framing we built on. We do not implement a
formal contextual-integrity logic.

## 3 Transform

| Technique | Rule | Where |
|---|---|---|
| **Consistent pseudonymization** with a per-conversation map (the `Vault`, one per conversation and destination) | `key = (label, canon(value))`; first new key of a label gets `[LABEL_n]` with n = count + 1. `canon`: digits only for Aadhaar and phone (last 10 for phone), upper-case alphanumerics for PAN, GSTIN, IFSC, vehicle, case-folded words otherwise. Placeholders are numbered in reading order. | `transform.py` `Vault.placeholder`, `canonical`, `apply` |
| **Generalization** (reversible: the vague form goes out, the exact value is restored locally) | Age: `in their ⌊a/10⌋·10s`. Salary: annualised (× 12 if "month" is near), then 4 bands: < ₹3 L, ₹3–10 L, ₹10–30 L, > ₹30 L per year. Date: month and year. Safe Harbor styles: `year` (year only), `age90` (ages over 89 become "90 or older"). Other labels: a fixed phrase ("a health matter", "a colleague"). Sent as `[AGE_1: in their 50s]`. | `transform.py` `coarse`, `money_band`, `BANDS` |
| **Suppression** | `block` replaces the value with `[LABEL withheld]`. | `transform.py` `apply` |
| Overlaps | The strictest action wins (pass < pseudonymize < generalize < block), then the widest span. | `transform.py` `apply`, `SEVERITY` |

Reference: "generalization" and "suppression" are used in the sense of Sweeney (2002). **No k-anonymity guarantee is
claimed**: we transform one message, not a table, and we never measure k. The `age90` and `year` styles follow HIPAA
Safe Harbor, 45 CFR 164.514(b)(2).

## 4 Purpose

**Purpose-based data minimisation.** Each purpose in `policies.yaml` lists the identifier types it does not need.

- Rule: `omit(x) ⇔ purpose declared ∧ label(x) ∈ MINIMISABLE ∧ label(x) ∈ omit(purpose)`, where
  `MINIMISABLE = {PHONE, EMAIL, UPI, AADHAAR, PAN, GSTIN, IFSC, VEHICLE}`. Names and clinical facts can never be omitted.
- An omitted item becomes `[LABEL omitted]` (rule `purpose-minimisation`). "Include anyway" puts it back and logs a
  masked reason.
- Example: `clinical_summary` omits PHONE, EMAIL, UPI, AADHAAR, PAN, GSTIN, IFSC, VEHICLE.

Where: `purpose.py` `omits`; `gateway.py` `analyze` (purpose block); `policy.py` `MINIMISABLE`, `_check_purposes`.

## 5 Attacker

**Adversarial inference check with a local LLM**, then **iterative tightening**. Same model as step 1
(`qwen2.5:3b`, JSON-schema output, few-shot). It reads the outbound text plus up to 6 earlier messages to the same
destination.

Questions asked (env `ATTACK_CATEGORIES`, default IDENTITY and HEALTH): HEALTH ("what condition could a medically
trained reader infer?"), IDENTITY ("does this point to one person without a name?"); COMPENSATION, HR and LEGAL are
opt-in.

**Acceptance rule** for one inference i with category c, confidence p and cited evidence Q (`attack.py` `attack`,
`gateway.py` `analyze`):

```
E(i)   = { q ∈ Q : q without placeholders has ≥ 3 chars and content,
                   and q occurs outside our placeholder tokens
                   in the new message or the earlier ones }
act(i) ⇔ E(i) ≠ ∅
       ∧ p ≥ 0.7                                   (env ATTACK_MIN_CONFIDENCE)
       ∧ confirm(i)                                (second question, below)
       ∧ decide(label(c), individual, flow) ≠ pass (policy forbids it)
       ∧ some q ∈ E(i) is in the new message        (else: already disclosed)
HEALTH also needs one word of E(i) that is not an ordinary schedule word.
```

`confirm(i)`: IDENTITY, "how many people could this describe?" ∈ {exactly one, two to five}. HEALTH, the guess has no
"no / leave / unknown" word and is called "specific", not "vague".

**Loop** (`gateway.py` `analyze`, `_tighten`; `attack.py` `evidence_spans`, `safer_description`): rounds r = 0, 1, 2
(env `ATTACK_MAX_ROUNDS` = 2). If any `act(i)` holds and r < 2: the evidence words are generalized (IDENTITY gets a
safer rewrite such as "a doctor at one of our branches"); words already generalized are blocked. Then attack again. If
something still holds after round 2, or tightening changed nothing, the request is refused (rule `attacker-not-cleared`).

Reference: the threat is from Staab et al. 2024 (*Beyond Memorization*). The attack-then-rewrite loop follows the idea
of Staab et al. 2025 (*Language Models are Advanced Anonymizers*). We did not reproduce either paper: our attacker is a
3B model, the policy decides what counts as a leak, and the loop is capped at 2 rounds and then refuses.

## 6 Guard + send

**Separator- and case-insensitive pattern scan** of the outbound payload for every protected value. Protected = every
raw value in the Vault plus every value this message masked, made vague, blocked or omitted.

Pattern per value v (`transform.py` `value_pattern`):

- v has a digit and ≥ 4 letters or digits: its letters and digits in order, with up to 3 other characters between
  each, case-insensitive, not touching another letter or digit. So `7260 1815 9082` matches `726018159082`.
- otherwise: the words of v separated by any whitespace, case-insensitive, whole words only.

Scanned three times before the network call: the JSON-encoded messages and the joined message text (values not
already sent as typed in an earlier turn), then the new message (all values). **Any hit raises `OutboundLeak` and
nothing is sent.** `send` is the only function that calls a chat model.

Where: `transform.py` `value_pattern`, `guard`; `gateway.py` `send`.

## 7 Restore

**Tolerant placeholder matching** with one regular expression built from the labels in the Vault. It accepts
`[PERSON_1]`, `[person_1]`, `PERSON_1`, `Person 1`, `PERSON-1's` and `[AGE_1: in their 50s]` (a bracketed hint of up
to 80 characters). Only placeholders that were actually sent are replaced; anything else is left visible. Each swap is
counted as exact or fuzzy. Runs on the laptop only.

Where: `transform.py` `restore_marked`.

## 8 Verify

**Set difference** between values in the restored reply and values in everything the user typed in the conversation:
`flag = V(reply) ∖ V(your messages)`, per type.

| Type | How a value is read |
|---|---|
| Age | the number in "52-year-old", "aged 52", "age: 52" |
| Date | parsed to a calendar date; month-year pairs too |
| Amount | rupee amounts normalised to a number (`₹14.2 lakh` = `₹14,20,000`); a range or salary band is skipped |
| Long number | 6 or more digits, not a substring of the digits you typed |
| Name | GLiNER PERSON in the reply with no word (over 2 letters) found in your text; template blanks like `[Your Name]` skipped |

Where: `verify.py` `check`.

## 9 Audit

One JSON line per request, never a raw value. Key k = env `AUDIT_HMAC_KEY` (the example value is refused).

```
tag(v)   = HMAC-SHA256(k, canon(label, v)), first 16 hex chars (64 bits)
mac_i    = HMAC-SHA256(k, mac_{i−1} ‖ JSON(line_i)),  mac_0 = ""   (full 64 hex chars)
           JSON = keys sorted, line_i without its own mac field
```

The previous seal comes first, then the line. `verify_log` recomputes the chain; the first line whose mac does not
match is reported. Known limit: lines cut off the end are only caught by comparing the last mac with a copy kept
elsewhere. Writes take an exclusive file lock (web app and MCP server can write at once).

Where: `gateway.py` `_tag`, `_seal`, `audit`, `_append`, `verify_log`, `person_report`.

Reference: HMAC, RFC 2104 (1997). Chaining each entry's value into the next is the hash-chain idea of Haber and
Stornetta (1991); MAC-chained audit logs appear in Schneier and Kelsey (1999). We use one fixed key, so unlike Schneier
and Kelsey there is no forward security: whoever holds the key can rewrite the whole chain.

## Checked but not claimed

- No embeddings, vector search, differential privacy, k-anonymity guarantee or encryption at rest are used anywhere.
- No self-implemented checksum: Verhoeff and Luhn mod 36 run inside python-stdnum.
- IFSC has no check digit; it is pattern only.
