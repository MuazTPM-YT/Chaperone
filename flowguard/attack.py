import json
import os
import re
import time
from dataclasses import asdict, dataclass, field

from .detect import CONTEXT_MODEL, Span, _ask, _has_content, _is_pay, _locate
from .policy import Flow, decide

MAX_ROUNDS = int(os.environ.get("ATTACK_MAX_ROUNDS", "2"))  # tightening rounds; passes = rounds + 1
# pay/HR/legal proxy questions cost ~1 s a round and caused most false alarms; explicit mentions are already
# caught by the context layer, so they are opt-in
CATEGORIES = set(os.environ.get("ATTACK_CATEGORIES", "IDENTITY,HEALTH").split(","))
MIN_CONFIDENCE = float(os.environ.get("ATTACK_MIN_CONFIDENCE", "0.7"))
HISTORY_TURNS = 6
TOKEN = re.compile(r"\[[A-Z]+_\d+(?::[^\]\n]*)?\]")
CATEGORY_LABEL = {"IDENTITY": "PERSON", "HEALTH": "HEALTH", "COMPENSATION": "COMPENSATION", "HR": "HR", "LEGAL": "LEGAL"}
COARSE = {"IDENTITY": "a colleague", "HEALTH": "a health matter", "COMPENSATION": "a pay matter", "HR": "an HR matter",
          "LEGAL": "a legal matter"}


@dataclass
class Inference:
    category: str
    guess: str
    confidence: float
    evidence: list[str]
    description: str = ""
    safer: str = ""
    forbidden: bool = False
    disclosed: bool = False  # evidence only in earlier messages: already sent, cannot be pulled back
    rule: str = ""


# ---------- the three focused questions ----------

def _findings(schema_item: dict) -> dict:
    return {"type": "object", "required": ["findings"],
            "properties": {"findings": {"type": "array", "items": {"type": "object", "properties": schema_item,
                                                                   "required": list(schema_item)}}}}


QUOTES = {"type": "array", "items": {"type": "string"}}
HEALTH_PROMPT = ("You read a workplace message the way a medically trained reader would. List every health condition a "
                 "reader could infer about a person, including conditions only implied by a medicine name, a procedure, "
                 "a test, a device, a benefit or a leave pattern. Give the guessed condition, confidence 0-1, and the "
                 "exact words that reveal it. Placeholders like [PERSON_1] hide names; bracketed phrases are already "
                 "vague. Return {\"findings\": []} if nothing about anyone's health can be inferred.")
HEALTH_SHOTS = [
    ("[PERSON_1] will join late on Tuesdays because of his methotrexate injections.",
     [{"guess": "rheumatoid arthritis or another autoimmune disease", "confidence": 0.8, "evidence": ["methotrexate injections"]}]),
    ("[PERSON_1] needs a desk near the restroom while she is on her insulin pump trial.",
     [{"guess": "diabetes", "confidence": 0.9, "evidence": ["insulin pump"]}]),
    ("[PERSON_1] is on leave next week for a family wedding.", []),
    ("[PERSON_1] ki biopsy ke baad radiation shuru hogi.",
     [{"guess": "cancer", "confidence": 0.9, "evidence": ["biopsy", "radiation"]}]),
    ("[PERSON_1] is away for [HEALTH_1: a health matter] this week.", []),
]
IDENTITY_PROMPT = ("You check whether a workplace message points to one specific person even without a name. A reader "
                   "inside the organisation can often tell who is meant from a combination of role, rank, location, "
                   "team, gender, language, tenure or a rare trait (for example 'our only', 'the new', 'the senior-most'). "
                   "For each such description give: the exact phrase that describes the person, who you think it is, "
                   "confidence 0-1, the exact words that narrow it down, and a safer rewrite of the phrase that fits many "
                   "people while keeping the job family. Placeholders like [PERSON_1] do not count. Return "
                   "{\"findings\": []} if no one can be singled out.")
IDENTITY_SHOTS = [
    ("The only Tamil-speaking pharmacist at our Hassan clinic has resigned; draft the vacancy notice.",
     [{"description": "The only Tamil-speaking pharmacist at our Hassan clinic", "guess": "the one Tamil-speaking pharmacist in Hassan",
       "confidence": 0.9, "evidence": ["only Tamil-speaking pharmacist", "Hassan clinic"], "safer": "A pharmacist at one of our clinics"}]),
    ("Our new head of accounts in the Pune office asked for a standing desk.",
     [{"description": "Our new head of accounts in the Pune office", "guess": "the newly hired head of accounts in Pune",
       "confidence": 0.8, "evidence": ["new head of accounts", "Pune office"], "safer": "A senior finance colleague"}]),
    ("Several nurses asked for more night-shift allowance; draft a reply.", []),
    ("[PERSON_1] asked for a standing desk.", []),
]
OTHER_PROMPT = ("You read a workplace message and list what a reader could infer about a specific person's pay, job "
                "standing or legal trouble, even when it is only implied. Categories: COMPENSATION (pay, raise, "
                "debt, income), HR (performance, discipline, suspension, firing), LEGAL (court case, police, "
                "lawsuit). Give the category, the guess, confidence 0-1, and the exact words that reveal it. "
                "Return {\"findings\": []} if nothing can be inferred.")
OTHER_SHOTS = [
    ("[PERSON_1] got the smallest increment in the team this year; draft a kind note.",
     [{"category": "COMPENSATION", "guess": "received a below-average raise", "confidence": 0.8, "evidence": ["smallest increment in the team"]}]),
    ("[PERSON_1] has been asked not to come to office until the inquiry ends.",
     [{"category": "HR", "guess": "suspended pending a disciplinary inquiry", "confidence": 0.8, "evidence": ["not to come to office until the inquiry ends"]}]),
    ("[PERSON_1] ko Friday ko family court jaana hai, cover arrange karo.",
     [{"category": "LEGAL", "guess": "has a family court case, likely divorce or custody", "confidence": 0.8, "evidence": ["family court"]}]),
    ("Lunch for the team is at 1 pm on Friday.", []),
]
HEALTH_SCHEMA = _findings({"guess": {"type": "string"}, "confidence": {"type": "number"}, "evidence": QUOTES})
IDENTITY_SCHEMA = _findings({"description": {"type": "string"}, "guess": {"type": "string"}, "confidence": {"type": "number"},
                             "evidence": QUOTES, "safer": {"type": "string"}})
OTHER_SCHEMA = _findings({"category": {"type": "string", "enum": ["COMPENSATION", "HR", "LEGAL"]}, "guess": {"type": "string"},
                          "confidence": {"type": "number"}, "evidence": QUOTES})


def _call(model: str, prompt: str, shots: list, text: str, schema: dict) -> list[dict]:
    messages = [{"role": "system", "content": prompt}]
    for q, a in shots:
        messages += [{"role": "user", "content": q}, {"role": "assistant", "content": json.dumps({"findings": a})}]
    messages.append({"role": "user", "content": text})
    return _ask(model, messages, schema).get("findings", [])


def _choice(model: str, question: str, options: list[str]) -> str:
    schema = {"type": "object", "properties": {"answer": {"type": "string", "enum": options}}, "required": ["answer"]}
    return _ask(model, [{"role": "user", "content": f"{question} Pick one: {'; '.join(options)}."}], schema).get("answer", "")


COUNTS = ["exactly one", "two to five", "more than five"]
SPECIFIC = ["specific", "vague"]
SPECIFIC_Q = ("Health words like cancer, diabetes, pregnancy, disability or kidney failure are specific. Words like illness, "
              "injury, unwell, a health issue or medical leave are vague. Is \"{guess}\" specific or vague?")
HEALTHY = [("health-related: a medicine, procedure, test, medical device, pregnancy or maternity, disability, or a "
            "medical condition"), "not health-related: a verb, a request, a date, a return, or ordinary leave or time off"]
LEGALY = ["legal: a court, case, hearing, lawsuit, police, legal notice or inquiry", "not legal: ordinary work or personal words"]
HR_KINDS = ["performance rating or review", "warning, discipline or suspension", "improvement plan or firing",
            "schedule, meeting or leave", "ordinary work", "other"]


def _any_word(model: str, text: str, inf: Inference, options: list[str], what: str) -> bool:
    return any(_choice(model, f'Message: {text}\n\nIs "{q}" {what} in this message?', options) == options[0]
               for q in inf.evidence)


# second checks: a 3B model over-reports, a narrow question about one finding is more reliable.
# Asking "do these words prove X?" failed (it said no to tamoxifen -> breast cancer); asking what each
# evidence word is works: 11 of 12 test words right, three runs in a row.
def _confirmed(model: str, text: str, inf: Inference) -> bool:
    if inf.category == "IDENTITY":
        q = (f'Message: {text}\n\nIn an Indian organisation with several branches and a few hundred staff, how many people '
             f'could "{inf.description or inf.guess}" describe?')
        return _choice(model, q, COUNTS) in COUNTS[:2]
    if inf.category == "HEALTH":
        # "illness" or "a health matter" is what our own vague tokens are meant to allow
        # wording picked from three tried: 11 of 12 test guesses right, and its one miss errs towards caution
        specific = _choice(model, SPECIFIC_Q.format(guess=inf.guess), SPECIFIC) == SPECIFIC[0]
        return specific and _any_word(model, text, inf, HEALTHY, "health-related")
    if inf.category == "LEGAL":
        return _any_word(model, text, inf, LEGALY, "legal")
    if inf.category == "HR":
        quoted = "; ".join(f'"{q}"' for q in inf.evidence)
        return _choice(model, f"Message: {text}\n\nWhat do the words {quoted} describe about a person?", HR_KINDS) in HR_KINDS[:3]
    return all(_is_pay(model, text, e) for e in inf.evidence[:1])


NARROWING = re.compile(r"\b(?:only|sole|single|first|new|senior-most|junior-most|female|male|woman|man|lady)\b", re.IGNORECASE)
REWRITE_SCHEMA = {"type": "object", "properties": {"rewrite": {"type": "string"}}, "required": ["rewrite"]}


# a rewrite that keeps the place name, the gender or "only" still points at one person
def _too_specific(rewrite: str, description: str) -> bool:
    names = {w for w in re.findall(r"\b[A-Z][a-z]{2,}\b", description[1:])}
    return bool(NARROWING.search(rewrite)) or any(n in rewrite for n in names)


def safer_description(model: str, inf: Inference) -> str:
    if inf.safer and not _too_specific(inf.safer, inf.description):
        return inf.safer
    q = (f'Rewrite "{inf.description}" so it fits many people: keep only the general job (for example a doctor, a nurse, '
         "an accountant, a teacher) and say \"at one of our branches\". Remove place names, gender, rank, language, "
         "tenure and words like only or new.")
    rewrite = _ask(model, [{"role": "user", "content": q}], REWRITE_SCHEMA).get("rewrite", "").strip().rstrip(".")
    return rewrite if rewrite and not _too_specific(rewrite, inf.description) else "a colleague at one of our branches"


# ---------- attack one outbound message (plus what was already sent) ----------

# where a quote occurs outside our own tokens: words inside "[HEALTH_1: a health matter]" are ours, not evidence
def _outside_tokens(text: str, quote: str) -> bool:
    if not quote:
        return False
    tokens = [m.span() for m in TOKEN.finditer(text)]
    low, q = text.lower(), quote.lower()
    at = low.find(q)
    while at >= 0:
        if not any(a < at + len(q) and at < b for a, b in tokens):
            return True
        at = low.find(q, at + 1)
    return bool(not tokens and _locate(text, quote))  # small paraphrase, nothing of ours to confuse it with


# keep quotes (minus our tokens) that really are in the text; report whether any sits in the new message
def _verified(quotes: list[str], current: str, earlier: str) -> tuple[list[str], bool]:
    kept, in_current = [], False
    for q in quotes:
        bare = " ".join(TOKEN.sub(" ", q).split()).strip(" ,.;:'\"")
        if len(bare) < 3 or not _has_content(bare):
            continue  # a placeholder alone reveals nothing
        if _outside_tokens(current, bare):
            kept.append(bare)
            in_current = True
        elif earlier and _outside_tokens(earlier, bare):
            kept.append(bare)
    return kept, in_current


def attack(current: str, earlier: list[str], flow: Flow, model: str | None = None) -> list[Inference]:
    model = model or CONTEXT_MODEL
    past = "\n\n".join(earlier[-HISTORY_TURNS:])
    text = f"Earlier messages in this conversation:\n{past}\n\nNew message:\n{current}" if past else current
    raw: list[Inference] = []
    if "HEALTH" in CATEGORIES:
        for f in _call(model, HEALTH_PROMPT, HEALTH_SHOTS, text, HEALTH_SCHEMA):
            raw.append(Inference("HEALTH", f["guess"], float(f["confidence"]), f["evidence"]))
    if "IDENTITY" in CATEGORIES:
        for f in _call(model, IDENTITY_PROMPT, IDENTITY_SHOTS, text, IDENTITY_SCHEMA):
            raw.append(Inference("IDENTITY", f["guess"], float(f["confidence"]), [f["description"], *f["evidence"]],
                                 description=f["description"], safer=f.get("safer", "")))
    if CATEGORIES & {"COMPENSATION", "HR", "LEGAL"}:
        for f in _call(model, OTHER_PROMPT, OTHER_SHOTS, text, OTHER_SCHEMA):
            if f["category"] in CATEGORIES:
                raw.append(Inference(f["category"], f["guess"], float(f["confidence"]), f["evidence"]))
    out = []
    for inf in raw:
        inf.evidence, in_current = _verified(inf.evidence, current, past)
        if not inf.evidence or inf.confidence < MIN_CONFIDENCE:
            continue  # cited words not in the text: a made-up inference, dropped
        if not _confirmed(model, text, inf):
            continue
        d = decide(CATEGORY_LABEL[inf.category], "individual", flow)
        inf.forbidden, inf.rule = d.action != "pass", d.rule
        inf.disclosed = inf.forbidden and not in_current
        out.append(inf)
    return out


def forbidden_categories(flow: Flow) -> list[str]:
    return [c for c, label in CATEGORY_LABEL.items() if c in CATEGORIES and decide(label, "individual", flow).action != "pass"]


# ---------- tightening: replace only the words the attacker relied on ----------

def evidence_spans(text: str, inf: Inference, taken: list[Span], block: bool, model: str | None = None) -> list[Span]:
    pieces = [inf.description] if inf.category == "IDENTITY" and inf.description else inf.evidence
    if inf.category == "IDENTITY" and inf.description and not block:
        inf.safer = safer_description(model or CONTEXT_MODEL, inf)
    out: list[Span] = []
    for q in pieces:
        for part in [p.strip(" ,.;") for p in TOKEN.split(q) if len(p.strip(" ,.;")) >= 3]:
            loc = _locate(text, part)
            if not loc or any(loc[0] < t.end and t.start < loc[1] for t in out):
                continue  # overlaps with earlier rounds are handled by the caller: vague first, then blocked
            s, e = loc
            coarse = "" if block else (inf.safer if inf.category == "IDENTITY" and inf.safer else COARSE[inf.category])
            out.append(Span(s, e, text[s:e], inf.category if inf.category != "IDENTITY" else "IDENTITY", "individual",
                            "attacker", inf.confidence, f"a local attacker inferred: {inf.guess}", coarse=coarse))
    return out


@dataclass
class Round:
    index: int
    ms: float
    inferences: list[dict] = field(default_factory=list)
    tightened: list[str] = field(default_factory=list)


def as_dict(r: Round) -> dict:
    return asdict(r)


def timed_attack(current: str, earlier: list[str], flow: Flow, index: int, model: str | None = None) -> tuple[Round, list[Inference]]:
    t0 = time.perf_counter()
    infs = attack(current, earlier, flow, model)
    return Round(index, round((time.perf_counter() - t0) * 1000, 1), [asdict(i) for i in infs]), infs
