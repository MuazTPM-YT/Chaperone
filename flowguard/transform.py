import re
from dataclasses import dataclass, field

from .detect import Span, rupees
from .policy import Decision

SEVERITY = {"pass": 0, "pseudonymize": 1, "generalize": 2, "block": 3}
NUMERIC = ("AADHAAR", "PHONE")
CODES = ("PAN", "GSTIN", "IFSC", "VEHICLE")


class OutboundLeak(Exception):
    pass


# same value written two ways ("7260 1815 9082" / "726018159082") gets one placeholder
def canonical(label: str, text: str) -> str:
    if label in NUMERIC:
        digits = re.sub(r"\D", "", text)
        return digits[-10:] if label == "PHONE" else digits
    if label in CODES:
        return re.sub(r"[^A-Z0-9]", "", text.upper())
    return " ".join(text.casefold().split())


# placeholder <-> raw map for one conversation with one destination
@dataclass
class Vault:
    by_key: dict[tuple[str, str], str] = field(default_factory=dict)  # (label, value) -> token as sent
    raw: dict[str, str] = field(default_factory=dict)  # "[AGE_1]" -> first raw form seen
    counts: dict[str, int] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)  # outbound chat turns, already transformed
    sources: list[str] = field(default_factory=list)  # what the user actually typed, for the reply check
    exposure: list[dict] = field(default_factory=list)  # what the attacker could still infer from what was sent

    # coarse given: the token carries it outbound ("[AGE_1: in their 50s]") and still restores to the exact value
    def placeholder(self, label: str, text: str, coarse: str | None = None) -> str:
        key = (label, canonical(label, text))
        if key not in self.by_key:
            self.counts[label] = self.counts.get(label, 0) + 1
            ph = f"[{label}_{self.counts[label]}]"
            self.by_key[key] = f"{ph[:-1]}: {coarse}]" if coarse else ph
            self.raw[ph] = text
        return self.by_key[key]

    def holds(self, label: str, text: str) -> bool:
        return (label, canonical(label, text)) in self.by_key


# ---------- generalize: coarse outbound, exact value kept on this laptop ----------

BANDS = [(3e5, "entry-level salary band (under ₹3 lakh/yr)"), (10e5, "mid-level salary band (₹3–10 lakh/yr)"),
         (30e5, "senior salary band (₹10–30 lakh/yr)"), (float("inf"), "executive salary band (over ₹30 lakh/yr)")]
WORDS = {"HEALTH": "health detail", "HR": "HR matter", "LEGAL": "legal matter",
         "MNPI": "confidential company financials", "LOCATION": "a location", "PERSON": "a person",
         "ORG": "an organisation", "IDENTITY": "a colleague"}


def money_band(span_text: str, context: str) -> str:
    amount = rupees(span_text)
    if amount is None:
        return "an undisclosed amount"
    if re.search(r"month|mahin|\bpm\b|/m\b", context, re.IGNORECASE):
        amount *= 12
    return next(label for cap, label in BANDS if amount < cap)


# the coarse words that stand in for a span outbound
def coarse(span: Span, text: str, style: str = "") -> str:
    if span.coarse:
        return span.coarse
    if style == "year":
        yr = re.search(r"(?:19|20)\d{2}", span.text)
        return yr.group() if yr else "a year"
    if style == "age90":
        return "90 or older"
    if span.label == "COMPENSATION":
        window = text[max(0, span.start - 40): span.end + 20]
        return money_band(span.text, window) if re.search(r"\d", span.text) else "pay detail"
    if span.label == "AGE":
        m = re.search(r"\d+", span.text)
        return f"in their {int(m.group()) // 10 * 10}s" if m else "an adult"
    if span.label == "DATE":
        mon = re.search(r"[A-Za-z]{3,9}", span.text)
        yr = re.search(r"(?:19|20)\d{2}", span.text)
        if mon and yr:
            return f"{mon.group()} {yr.group()}"
        nums = re.findall(r"\d+", span.text)
        return f"month {nums[1]}/{nums[2]}" if len(nums) == 3 else "a date"
    return WORDS.get(span.label, span.label.lower())


# ---------- apply decisions ----------

@dataclass
class Applied:
    span: Span
    decision: Decision
    replacement: str | None  # None = left as is (pass or covered by a wider span)
    covered: bool = False


# outbound text (None if whole request blocked) plus what happened to each span
def apply(text: str, spans: list[Span], decisions: list[Decision], vault: Vault) -> tuple[str | None, list[Applied]]:
    pairs = list(zip(spans, decisions))
    request_block = any(d.action == "block" and d.scope == "request" for _, d in pairs)
    # strictest, widest span wins an overlap; the loser is covered and needs no own replacement
    order = sorted(range(len(pairs)), key=lambda i: (-SEVERITY[pairs[i][1].action],
                                                    -(pairs[i][0].end - pairs[i][0].start)))
    chosen: list[int] = []
    records: dict[int, Applied] = {}
    for i in order:
        s, d = pairs[i]
        if d.action == "pass":
            records[i] = Applied(s, d, None)
            continue
        if any(s.start < pairs[j][0].end and pairs[j][0].start < s.end for j in chosen):
            records[i] = Applied(s, d, None, covered=True)
            continue
        chosen.append(i)
    # number placeholders in reading order, so [PERSON_1] is the first name in the message
    for i in sorted(chosen, key=lambda i: pairs[i][0].start):
        s, d = pairs[i]
        if d.action == "pseudonymize":
            rep = vault.placeholder(s.label, s.alias or s.text)
        elif d.action == "generalize":
            rep = vault.placeholder(s.label, s.alias or s.text, coarse(s, text, d.coarse))
        else:
            rep = f"[{s.label} omitted]" if d.rule == "purpose-minimisation" else f"[{s.label} withheld]"
        records[i] = Applied(s, d, rep)
    applied = [records[i] for i in range(len(pairs))]
    if request_block:
        return None, applied
    out = text
    for i in sorted(chosen, key=lambda i: -pairs[i][0].start):
        s = pairs[i][0]
        out = out[: s.start] + (records[i].replacement or "") + out[s.end:]
    return out, applied


# ---------- outbound guard ----------

# ids and amounts match however they are spaced: "7260 1815 9082" == "726018159082"
def value_pattern(value: str) -> re.Pattern:
    alnum = re.sub(r"[^A-Za-z0-9]", "", value)
    if re.search(r"\d", value) and len(alnum) >= 4:
        body = r"[^A-Za-z0-9]{0,3}".join(re.escape(c) for c in alnum)
        return re.compile(r"(?<![A-Za-z0-9])" + body + r"(?![A-Za-z0-9])", re.IGNORECASE)
    words = [re.escape(w) for w in value.split()]
    return re.compile(r"(?<!\w)" + r"\s+".join(words) + r"(?!\w)", re.IGNORECASE)


# last line of defence: refuse to send if any protected raw value survived
def guard(payload: str, protected: list[str]) -> None:
    for value in protected:
        if len(value.strip()) >= 2 and value_pattern(value).search(payload):
            raise OutboundLeak("outbound payload still contains a protected value; request not sent")


# ---------- restore ----------

# swap placeholders back; tolerate [person_1], PERSON_1, Person 1, PERSON-1's, [AGE_1: in their 50s]
# returns the restored text, counts, and where each restored value now sits (for highlighting)
def restore_marked(reply: str, vault: Vault) -> tuple[str, dict, list[dict]]:
    stats = {"exact": 0, "fuzzy": 0}
    if not vault.raw:
        return reply, stats, []
    labels = "|".join(sorted({ph[1:-1].rsplit("_", 1)[0] for ph in vault.raw}, key=len, reverse=True))
    rx = re.compile(rf"\[\s*({labels})[_ -]?(\d+)(?:\s*:[^\]\n]{{0,80}})?\s*\]"
                    rf"|(?<![A-Za-z])({labels})[_ -]?(\d+)(?!\d)", re.IGNORECASE)
    tokens = set(vault.by_key.values()) | set(vault.raw)
    out, marks, pos = [], [], 0
    for m in rx.finditer(reply):
        ph = f"[{(m.group(1) or m.group(3)).upper()}_{m.group(2) or m.group(4)}]"
        if ph not in vault.raw:
            continue  # a placeholder we never sent: leave it visible
        out.append(reply[pos:m.start()])
        start = sum(len(x) for x in out)
        out.append(vault.raw[ph])
        marks.append({"start": start, "end": start + len(vault.raw[ph]), "placeholder": ph, "seen": m.group()})
        stats["exact" if m.group() in tokens else "fuzzy"] += 1
        pos = m.end()
    out.append(reply[pos:])
    return "".join(out), stats, marks


def restore(reply: str, vault: Vault) -> tuple[str, dict]:
    text, stats, _ = restore_marked(reply, vault)
    return text, stats
