import difflib
import json
import os
import re
import time
from dataclasses import dataclass, field, replace
from functools import lru_cache

import httpx
from stdnum.in_ import aadhaar, gstin, pan

SEMANTIC = ("HEALTH", "COMPENSATION", "MNPI", "HR", "LEGAL")
ID_TAGS = re.compile(r"\[(?:AADHAAR|PAN|GSTIN|IFSC|UPI|PHONE|EMAIL|VEHICLE)\]")


@dataclass
class Span:
    start: int
    end: int
    text: str
    label: str
    subject: str = "individual"  # individual | business | unknown
    source: str = "regex"  # regex | ner | context
    score: float = 1.0
    note: str = ""
    alias: str = ""  # "Rohan" alone is the same person as "Rohan Deshpande": share one placeholder


@dataclass
class Detection:
    spans: list[Span]
    context_ok: bool
    timings: dict[str, float] = field(default_factory=dict)
    context_error: str = ""


# ---------- deterministic layer ----------

# PAN 4th char: P person, H Hindu undivided family are people; the rest are entities
INDIVIDUAL_HOLDERS = ("P", "H")
ROLE_MAILBOXES = {"info", "accounts", "account", "support", "sales", "admin", "contact", "hr", "billing",
                  "office", "hello", "careers", "jobs", "noreply", "no-reply", "enquiry", "help", "team"}
STATES = ["AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ", "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP", "MZ", "NL", "OD", "OR", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK", "UP", "WB"]
MONTHS = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|" \
         r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"

RX = {
    "EMAIL": re.compile(r"\b[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b"),
    "UPI": re.compile(r"\b[\w.-]{2,64}@[A-Za-z]{2,32}\b(?!\.\w)"),
    "GSTIN": re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"),
    "PAN": re.compile(r"\b[A-Z]{3}[ABCFGHJLPT][A-Z]\d{4}[A-Z]\b"),
    "IFSC": re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
    "AADHAAR": re.compile(r"(?<![\w-])[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?![\w-])"),
    "PHONE": re.compile(r"(?<![\w+])(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\w)"),
    "VEHICLE": re.compile(r"\b(" + "|".join(STATES) + r")[\s-]?\d{1,2}[\s-]?[A-Z]{1,3}[\s-]?\d{4}\b"
                          r"|\b\d{2}\s?BH\s?\d{4}\s?[A-Z]{1,2}\b"),
    "AGE": re.compile(r"\b\d{1,3}[- ](?:year|yr)s?[- ]old\b|\baged \d{1,3}\b|\bage:? ?\d{1,3}\b"
                      r"|\b\d{1,3} (?:years|yrs) old\b|\b\d{1,3} saal (?:ka|ki|ke)\b", re.IGNORECASE),
    "DATE": re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)? {MONTHS},? \d{{4}}\b|\b{MONTHS} \d{{1,2}}(?:st|nd|rd|th)?,? \d{{4}}\b"
                       r"|\b\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)\d{2}\b"),
}
# money is only a candidate: the context layer decides whether it is pay
MONEY = re.compile(
    r"(?:₹|\bRs\.?|\bINR)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:lakhs?|lacs?|L|LPA|crores?|cr|k|K|hazaa?r|thousand)\b)?"
    r"(?:\s(?:a|per)\s(?:month|year|annum))?"
    r"|\b\d[\d,]*(?:\.\d+)?\s?(?:lakhs?|lacs?|LPA|crores?|cr|k|K|hazaa?r|thousand)\b(?:\s(?:a|per)\s(?:month|year|annum))?"
    r"|\b\d{1,3}(?:,\d{2,3})+\b"
)
# deterministic labels win ties in this order (GSTIN contains a PAN, UPI can contain a phone)
PRIORITY = ["EMAIL", "UPI", "GSTIN", "PAN", "IFSC", "AADHAAR", "VEHICLE", "PHONE", "DATE", "AGE"]


# keep hit? plus whose data it is and why
def _valid(label: str, value: str) -> tuple[bool, str, str]:
    if label == "AADHAAR":
        ok = aadhaar.is_valid(re.sub(r"\D", "", value))
        return ok, "individual", "Verhoeff check digit valid" if ok else ""
    if label == "PAN":
        if not pan.is_valid(value):
            return False, "", ""
        holder = "individual" if value[3] in INDIVIDUAL_HOLDERS else "business"
        return True, holder, f"PAN holder '{value[3]}' = {pan.info(value)['holder_type']}"
    if label == "GSTIN":
        if not gstin.is_valid(value):
            return False, "", ""
        holder = "individual" if value[5] in INDIVIDUAL_HOLDERS else "business"
        note = f"GSTIN checksum valid; embedded PAN holder = {gstin.info(value)['holder_type']}"
        if holder == "individual":
            note += " (proprietorship: exposes a personal PAN)"
        return True, holder, note
    if label == "IFSC":
        return True, "business", "bank branch code"
    if label == "EMAIL":
        local = value.split("@")[0].lower()
        role = local in ROLE_MAILBOXES
        return True, "business" if role else "individual", "role mailbox" if role else "personal mailbox"
    if label == "UPI":
        return True, "individual", "UPI handle"
    if label in ("AGE", "DATE", "PHONE", "VEHICLE"):
        return True, "individual", ""
    return True, "unknown", ""


def deterministic(text: str) -> list[Span]:
    found: list[Span] = []
    taken: list[tuple[int, int]] = []
    for label in PRIORITY:
        for m in RX[label].finditer(text):
            s, e = m.span()
            if any(s < te and ts < e for ts, te in taken):
                continue
            keep, subject, note = _valid(label, m.group())
            if keep:
                found.append(Span(s, e, m.group(), label, subject, "regex", 1.0, note))
                taken.append((s, e))
    return found


UNITS = [(r"crores?|cr", 1e7), (r"lakhs?|lacs?|LPA|L", 1e5), (r"k|K|thousand|hazaa?r", 1e3)]


# "₹14.2 lakh" and "₹14,20,000" are the same 1420000.0
def rupees(text: str) -> float | None:
    m = re.search(r"\d[\d,]*(?:\.\d+)?", text)
    if not m:
        return None
    amount = float(m.group().replace(",", ""))
    for unit, mult in UNITS:
        if re.search(rf"\d\s?(?:{unit})\b", text):
            return amount * mult
    return amount


def money_candidates(text: str, taken: list[Span]) -> list[Span]:
    out = []
    for m in MONEY.finditer(text):
        s, e = m.span()
        if not any(s < t.end and t.start < e for t in taken):
            out.append(Span(s, e, m.group(), "MONEY", "unknown", "regex", 1.0))
    return out


# ---------- entity layer ----------

NER_MODEL = os.environ.get("NER_MODEL", "urchade/gliner_small-v2.1")
# "person name" beats "person": splits "Rahul and Deepak", skips "her manager"
NER_LABELS = {"person name": ("PERSON", "individual"), "organization": ("ORG", "business"),
              "location": ("LOCATION", "unknown")}
NER_THRESHOLD = {"PERSON": 0.5, "ORG": 0.6, "LOCATION": 0.6}
# acronyms and role nouns GLiNER likes to call entities
NOT_ENTITIES = {"aadhaar", "pan", "gstin", "gst", "upi", "ifsc", "kyc", "tds", "pf", "ctc", "pip", "ca", "hr", "lpa",
                "emi", "customer", "student", "patient", "client", "team", "company", "board", "manager", "doctor",
                "wife", "husband", "son", "daughter", "mother", "father", "sir", "madam", "boss"}


@lru_cache(maxsize=1)
def _gliner():
    from gliner import GLiNER  # heavy import, load once

    return GLiNER.from_pretrained(NER_MODEL)


def _noise(span_text: str) -> bool:
    words = span_text.lower().split()
    if span_text.islower() or not words:
        return True
    if words[0] in ("the", "our", "my", "your", "this"):
        words = words[1:]
    return " ".join(words) in NOT_ENTITIES


def entities(text: str) -> list[Span]:
    out = []
    for ent in _gliner().predict_entities(text, list(NER_LABELS), threshold=min(NER_THRESHOLD.values())):
        label, subject = NER_LABELS[ent["label"]]
        s, e = ent["start"], ent["end"]
        # trim possessive so "Suresh Kumar's" pseudonymizes as the name only
        if text[s:e].endswith(("'s", "’s")):
            e -= 2
        if ent["score"] < NER_THRESHOLD[label] or _noise(text[s:e]):
            continue
        out.append(Span(s, e, text[s:e], label, subject, "ner", round(float(ent["score"]), 3)))
    return out


# ---------- context layer ----------

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
CONTEXT_MODEL = os.environ.get("CONTEXT_MODEL", "qwen2.5:3b")
CONTEXT_TIMEOUT = float(os.environ.get("CONTEXT_TIMEOUT", "20"))

CONTEXT_PROMPT = """You find sensitive details in workplace messages written in English or Hinglish \
(Hindi in Latin script mixed with English). Names and ID numbers are already hidden as tags like [PERSON] or \
[AADHAAR]; never return a tag on its own. Return each sensitive phrase copied EXACTLY from the message, \
with one category. Quote only the sensitive words themselves (at most six words), with a separate finding \
for each separate detail. Categories:
- HEALTH: a specific person's medical condition, diagnosis, symptom, treatment, medicine, test result, \
surgery, pregnancy or disability.
- COMPENSATION: a specific person's salary, CTC, bonus, pay, deductions or income. Copy the amount itself.
- MNPI: our own company's results, revenue, profit, deals or plans before they are made public, including \
anything to be announced later.
- HR: a specific person's performance rating, warning, disciplinary action or improvement plan (PIP).
- LEGAL: a lawsuit, complaint, court case, or legal dispute involving a specific person or our company.
- PERSON: a person's first or full name that is still visible (not a tag). Not job titles like "customer".
Do NOT flag: general topics, public results of other companies, published statistics, market averages, \
invoices, rent or prices, leave or absence without a medical reason, or casual words like "sick of" or \
"depressed that the team lost".
Return {"findings": []} when nothing is sensitive."""

FEW_SHOT = [
    ("Tell the team [PERSON] will miss Friday's review because of his dialysis.",
     [{"quote": "dialysis", "category": "HEALTH"}]),
    ("[PERSON] ka in-hand 55,000 hai, loan form mein bharna hai.",
     [{"quote": "55,000", "category": "COMPENSATION"}]),
    ("Prepare slides on our H1 margins ahead of the earnings call on Tuesday.",
     [{"quote": "our H1 margins ahead of the earnings call", "category": "MNPI"}]),
    ("TCS posted strong Q1 results last month; summarise the press coverage.", []),
    ("Pay the vendor invoice of Rs 1,20,000 by Friday. Contact [PHONE].", []),
    ("[PERSON] ko last month do baar late aane pe show-cause notice mila tha.",
     [{"quote": "show-cause notice", "category": "HR"}]),
    ("[PERSON] is off tomorrow, please cover the client call.", []),
    ("Pooja kal office nahi aayegi, client call tum le lo.", [{"quote": "Pooja", "category": "PERSON"}]),
    ("Our supplier has filed a case against us in the commercial court over unpaid dues.",
     [{"quote": "filed a case against us in the commercial court", "category": "LEGAL"}]),
    ("I am so sick of these long meetings.", []),
]

SCHEMA = {
    "type": "object",
    "properties": {"findings": {"type": "array", "items": {
        "type": "object",
        "properties": {"quote": {"type": "string"}, "category": {"type": "string", "enum": [*SEMANTIC, "PERSON"]}},
        "required": ["quote", "category"]}}},
    "required": ["findings"],
}


def _locate(text: str, quote: str) -> tuple[int, int] | None:
    quote = quote.strip().strip(".,;")
    if not quote:
        return None
    i = text.lower().find(quote.lower())
    if i >= 0:
        return i, i + len(quote)
    # small models paraphrase a little; accept a long common run
    m = difflib.SequenceMatcher(None, text.lower(), quote.lower(), autojunk=False).find_longest_match()
    if m.size >= max(4, int(0.6 * len(quote))):
        return m.a, m.a + m.size
    return None


# hide ids and names behind [LABEL] tags: LLM judges meaning, cannot mistake a number for MNPI
def _mask(text: str, spans: list[Span]) -> tuple[str, list[tuple[int, int, int, int]]]:
    parts, segs, pos, out_len = [], [], 0, 0
    for sp in sorted(spans, key=lambda x: x.start):
        if sp.start < pos:
            continue
        tag = f"[{sp.label}]"
        parts += [text[pos:sp.start], tag]
        out_len += sp.start - pos
        segs.append((out_len, out_len + len(tag), sp.start, sp.end))
        out_len += len(tag)
        pos = sp.end
    parts.append(text[pos:])
    return "".join(parts), segs


def _to_orig(i: int, segs: list[tuple[int, int, int, int]], is_end: bool) -> int:
    delta = 0
    for ms, me, os_, oe in segs:
        if i <= ms:
            break
        if i < me:
            return oe if is_end else os_
        delta = oe - me
    return i + delta


TAG = re.compile(r"\[[A-Z]+\]")
EDGE_LEAD = re.compile(r"(?:\s+|[.,;:]|'s\b|(?:ka|ki|ke|ko|ne|is|was|the|a|an|his|her|their|of|for|with|due to)\b)*",
                       re.IGNORECASE)
EDGE_TAIL = re.compile(r"(?:\s+|[.,;:!?]|'s|\b(?:hai|tha|thi|ka|ki|ke|of|for|with|and))*$", re.IGNORECASE)


# quote must not swallow names or ids inside it: split on tags, trim filler; a piece that
# leads into or out of an id ("can be reached at [PHONE]") describes the id, not a secret
def _pieces(masked: str, a: int, b: int) -> list[tuple[int, int]]:
    tags = list(TAG.finditer(masked, a, b))
    bounds = [(a, None)] + [(t.end(), t) for t in tags]
    out = []
    for n, (pa, before) in enumerate(bounds):
        after = tags[n] if n < len(tags) else None
        pb = after.start() if after else b
        if any(t is not None and ID_TAGS.fullmatch(t.group()) for t in (before, after)):
            continue
        lead = EDGE_LEAD.match(masked, pa, pb)
        pa = lead.end() if lead else pa
        tail = EDGE_TAIL.search(masked, pa, pb)
        pb = tail.start() if tail else pb
        if pb > pa:
            out.append((pa, pb))
    return out


def context(text: str, model: str | None = None, hide: list[Span] | None = None,
            money: list[Span] | None = None) -> list[Span]:
    model = model or CONTEXT_MODEL
    masked, segs = _mask(text, hide or [])
    messages = [{"role": "system", "content": CONTEXT_PROMPT}]
    for question, answer in FEW_SHOT:
        messages += [{"role": "user", "content": question},
                     {"role": "assistant", "content": json.dumps({"findings": answer})}]
    messages.append({"role": "user", "content": masked})
    findings = _ask(model, messages, SCHEMA).get("findings", [])
    out = []
    for f in findings:
        cat = f.get("category")
        loc = _locate(masked, f.get("quote", "")) if cat in (*SEMANTIC, "PERSON") else None
        if not loc and cat == "COMPENSATION":
            # model rewrote the amount ("₹14.2 lakh" -> "₹14,20,000"): match it by value
            value = rupees(f.get("quote", ""))
            out += [Span(m.start, m.end, m.text, "COMPENSATION", "individual", "context", 0.8,
                         "amount flagged as pay by local LLM") for m in money or [] if value and rupees(m.text) == value]
        # MNPI blocks the whole request; one built around an id number is the model confusing ids with secrets
        if loc and cat == "MNPI" and ID_TAGS.search(masked, *loc):
            continue
        for pa, pb in _pieces(masked, *loc) if loc else []:
            s, e = _to_orig(pa, segs, False), _to_orig(pb, segs, True)
            if e <= s or not _has_content(masked[pa:pb]):
                continue
            if cat != "PERSON":
                out.append(Span(s, e, text[s:e], cat, "individual", "context", 0.9, "local LLM"))
            elif not _noise(text[s:e]) and text[s].isupper():
                out.append(Span(s, e, text[s:e], "PERSON", "individual", "context", 0.7, "name missed by NER"))
    # second look at pay and HR: extraction over-flags them (invoice totals, meeting moves); a narrow question
    # about one phrase gets it right more often
    check = {"COMPENSATION": _is_pay, "HR": _is_hr, "MNPI": _is_mnpi}
    verdict = {(o.label, o.text): check[o.label](model, masked, o.text) for o in out if o.label in check}
    return [o for o in out if verdict.get((o.label, o.text), True)]


def _ask(model: str, messages: list[dict], schema: dict) -> dict:
    body: dict = {"model": model, "messages": messages, "stream": False, "format": schema,
                  "keep_alive": "30m", "options": {"temperature": 0, "seed": 0}}
    if model.startswith("qwen3"):
        body["think"] = False
    r = httpx.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=CONTEXT_TIMEOUT)
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])


YES_NO = {"type": "object", "properties": {"answer": {"type": "string", "enum": ["yes", "no"]}},
          "required": ["answer"]}


HR_KINDS = ["performance rating", "warning or discipline", "improvement plan", "schedule or meeting change",
            "leave or absence", "paperwork or certificate", "office or facilities", "payroll or staff admin", "other"]


def _is_hr(model: str, masked: str, phrase: str) -> bool:
    schema = {"type": "object", "properties": {"answer": {"type": "string", "enum": HR_KINDS}}, "required": ["answer"]}
    question = f'Message: {masked}\n\nWhat does "{phrase}" refer to in this message? Pick one: {", ".join(HR_KINDS)}.'
    # drop only on a clear non-HR answer; "other" keeps the finding, a leak costs more than a vague word
    return _ask(model, [{"role": "user", "content": question}], schema).get("answer") not in HR_KINDS[3:8]


def _sentence(text: str, phrase: str) -> str:
    i = max(text.find(phrase), 0)
    start = max(text.rfind(".", 0, i), text.rfind(";", 0, i)) + 1
    ends = [x for x in (text.find(".", i + len(phrase)), text.find(";", i + len(phrase))) if x != -1]
    return text[start:min(ends or [len(text)])].strip()


# MNPI blocks the whole request, so a false alarm is expensive: ask about the phrase, and if that says no,
# about its whole sentence (a bare "30%" needs the sentence; a sentence can bury the phrase)
def _is_mnpi(model: str, masked: str, phrase: str) -> bool:
    def secret(part: str) -> bool:
        question = (f'In the message below, is "{part}" price-sensitive company information that is still secret '
                    "(results, revenue, profit, acquisition, before an announcement)? Answer yes or no.\n\n"
                    f"Message: {masked}")
        return _ask(model, [{"role": "user", "content": question}], YES_NO).get("answer") == "yes"

    short = len(re.findall(r"[A-Za-z]{2,}", phrase)) < 2
    return secret(_sentence(masked, phrase) if short else phrase) or (not short and secret(_sentence(masked, phrase)))


def _is_pay(model: str, masked: str, amount: str) -> bool:
    question = (f'In the message below, what is "{amount}"? Answer yes if it is someone\'s salary, earnings, '
                "bonus or pay deduction. Answer no if it is a price, invoice amount, rent or fee.\n\n"
                f"Message: {masked}")
    return _ask(model, [{"role": "user", "content": question}], YES_NO).get("answer") == "yes"


FILLER = frozenset({
    "aur", "ka", "ki", "ke", "ko", "ne", "pe", "par", "se", "hai", "hain", "tha", "thi", "is", "was", "the", "a",
    "an", "and", "or", "of", "to", "in", "on", "at", "for", "with", "by", "number", "id", "no", "tracking", "order",
    "invoice", "phone", "mobile", "email", "card", "account",
})


# a finding of only tags, ids and filler words ("Aadhaar number", "aur") is noise; short numbers
# ("30%", "42,000", "2/5") are content, long digit runs look like ids
def _has_content(masked_quote: str) -> bool:
    bare = re.sub(r"\[[A-Z]+\]", " ", masked_quote)
    if re.search(r"\d", bare) and not re.search(r"\d{6,}", re.sub(r"[\s-]", "", bare)):
        return True
    words = re.findall(r"[A-Za-z]{2,}", bare)
    return any(w.lower() not in FILLER and w.lower() not in NOT_ENTITIES and w.lower() != "aadhaar" for w in words)


# pay findings snap to exact amount, so generalize swaps only the number
def _merge_money(ctx: list[Span], money: list[Span]) -> list[Span]:
    out = []
    for c in ctx:
        if c.label != "COMPENSATION":
            out.append(c)
            continue
        hits = [m for m in money if m.start < c.end and c.start < m.end]
        if not hits:
            out.append(c)
        for m in hits:
            out.append(Span(m.start, m.end, m.text, "COMPENSATION", "individual", "context", c.score,
                            "amount flagged as pay by local LLM"))
    # dedupe identical spans
    seen, uniq = set(), []
    for s in out:
        key = (s.start, s.end, s.label)
        if key not in seen:
            seen.add(key)
            uniq.append(s)
    return uniq


# a found full name also covers its first name used alone later ("Rohan wants...", "Rohan's car")
# ponytail: exact, case-sensitive first-name match; a name that is also a common word ("Will") can over-mask
def first_names(text: str, spans: list[Span]) -> list[Span]:
    out: list[Span] = []
    for p in [s for s in spans if s.label == "PERSON" and len(s.text.split()) >= 2]:
        first = p.text.split()[0]
        if len(first) < 3 or first.lower() in NOT_ENTITIES:
            continue
        for m in re.finditer(rf"(?<![\w-]){re.escape(first)}(?![\w-])", text):
            if not any(m.start() < o.end and o.start < m.end() for o in spans + out):
                out.append(Span(m.start(), m.end(), first, "PERSON", "individual", "ner", p.score,
                                f"same person as {p.text}", alias=p.text))
    return out


CONTEXT_CHUNK = int(os.environ.get("CONTEXT_CHUNK", "250"))


# sentence-aligned windows: the 3B model returns nothing for long pasted text, so it reads it in pieces
def windows(text: str, size: int = CONTEXT_CHUNK) -> list[tuple[int, int]]:
    out, start, last = [], 0, 0
    for end in [m.end() for m in re.finditer(r"[.!?;\n](?=\s|$)", text)] + [len(text)]:
        if end - start > size and last > start:
            out.append((start, last))
            start = last
        last = end
    out.append((start, len(text)))
    return [(a, b) for a, b in out if text[a:b].strip()]


def _shift(spans: list[Span], by: int) -> list[Span]:
    return [replace(x, start=x.start + by, end=x.end + by) for x in spans]


def _context_windowed(text: str, model: str | None, hide: list[Span], money: list[Span]) -> list[Span]:
    found = []
    for a, b in windows(text):
        hide_w = _shift([x for x in hide if a <= x.start and x.end <= b], -a)
        money_w = _shift([x for x in money if a <= x.start and x.end <= b], -a)
        found += _shift(context(text[a:b], model, hide_w, money_w), a)
    return found


def detect(text: str, use_context: bool = True, model: str | None = None) -> Detection:
    t = {}
    t0 = time.perf_counter()
    det = deterministic(text)
    t["regex_ms"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    ner = [n for n in entities(text) if not any(n.start < d.end and d.start < n.end for d in det)]
    ner += first_names(text, det + ner)
    t["ner_ms"] = (time.perf_counter() - t0) * 1000

    ctx: list[Span] = []
    ok, err = False, "disabled"
    if use_context:
        t0 = time.perf_counter()
        try:
            hide = det + [n for n in ner if n.label == "PERSON"]
            money = money_candidates(text, det)
            ctx = _merge_money(_context_windowed(text, model, hide, money), money)
            ok, err = True, ""
        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as exc:
            err = f"{type(exc).__name__}: {exc}"[:200]
        t["context_ms"] = (time.perf_counter() - t0) * 1000
    spans = sorted(det + ner + ctx, key=lambda s: (s.start, -s.end))
    return Detection(spans, ok, t, err)
