import re
from datetime import date

from .detect import MONEY, MONTHS, NOT_ENTITIES, RX, entities, rupees, windows

AGE = re.compile(r"\b(\d{1,3})[- ](?:year|yr)s?[- ]old\b|\baged (\d{1,3})\b|\b(\d{1,3}) (?:years|yrs) old\b"
                 r"|\bage:? ?(\d{1,3})\b", re.IGNORECASE)
MONTH_YEAR = re.compile(rf"\b({MONTHS})[a-z]*,? ((?:19|20)\d{{2}})\b", re.IGNORECASE)
LONG_NUMBER = re.compile(r"(?<![\w.])\d[\d\s-]{4,}\d(?!\w|\.\d)")
TEMPLATE_SLOT = re.compile(r"\[[^\]\n]{1,60}\]")
RANGE_NEAR = re.compile(r"\d\s*(?:–|-|to)\s*[₹\d]")
MONTH_NUM = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _ages(text: str) -> list[tuple[int, int, int]]:
    return [(int(next(g for g in m.groups() if g)), m.start(), m.end()) for m in AGE.finditer(text)]


# "12 March 2026", "March 12, 2026", "12/03/2026" -> a date; None if it does not parse
def _date(s: str) -> date | None:
    nums = [int(n) for n in re.findall(r"\d+", s)]
    mon = re.search(r"[A-Za-z]{3}", s)
    try:
        if mon and len(nums) == 2:
            day, year = (nums[0], nums[1]) if nums[1] > 31 else (nums[1], nums[0])
            return date(year, MONTH_NUM[mon.group().lower()], day)
        if len(nums) == 3:
            return date(nums[2], nums[1], nums[0])
    except (ValueError, KeyError):
        return None
    return None


def _month_years(text: str) -> set[tuple[int, int]]:
    out = {(int(m.group(2)), MONTH_NUM[m.group(1)[:3].lower()]) for m in MONTH_YEAR.finditer(text)}
    out |= {(d.year, d.month) for m in RX["DATE"].finditer(text) if (d := _date(m.group()))}
    return out


# specific values the reply states that the user never gave: the model filling vagueness with false precision
def check(reply: str, sources: list[str], names: bool = True) -> list[dict]:
    src = "\n".join(sources)
    flags: list[dict] = []

    def flag(start: int, end: int, kind: str, reason: str) -> None:
        if not any(start < f["end"] and f["start"] < end for f in flags):
            flags.append({"start": start, "end": end, "text": reply[start:end], "kind": kind, "reason": reason})

    src_ages = {a for a, _, _ in _ages(src)}
    for age, s, e in _ages(reply):
        if age not in src_ages:
            said = f"Your message says {', '.join(str(a) for a in sorted(src_ages))}." if src_ages else "Your message gives no age."
            flag(s, e, "age", f"Age {age} is not from your message. {said}")

    src_dates = {d for m in RX["DATE"].finditer(src) if (d := _date(m.group()))}
    src_months = _month_years(src)
    for m in RX["DATE"].finditer(reply):
        d = _date(m.group())
        if d and d not in src_dates:
            flag(m.start(), m.end(), "date", "This date is not in your message.")
    for m in MONTH_YEAR.finditer(reply):
        key = (int(m.group(2)), MONTH_NUM[m.group(1)[:3].lower()])
        if src_months and key not in src_months:
            flag(m.start(), m.end(), "date", "This month does not match any date in your message.")

    src_amounts = {v for m in MONEY.finditer(src) if (v := rupees(m.group())) is not None}
    for m in MONEY.finditer(reply):
        v = rupees(m.group())
        around = reply[max(0, m.start() - 4): m.end() + 4]
        if v is None or v in src_amounts or RANGE_NEAR.search(around) or "lakh/yr" in around:
            continue  # a range or band is the vague version we sent, not a new claim
        flag(m.start(), m.end(), "amount", "This amount is not in your message.")

    src_digits = re.sub(r"\D", "", src)
    for m in LONG_NUMBER.finditer(reply):
        digits = re.sub(r"\D", "", m.group())
        if len(digits) >= 6 and digits not in src_digits:
            flag(m.start(), m.end(), "number", "This number is not in your message.")

    if names:
        low = src.casefold()
        slots = [m.span() for m in TEMPLATE_SLOT.finditer(reply)]  # "[Your Name]" is a blank to fill, not a claim
        for a, b in windows(reply, 600):
            for p in entities(reply[a:b]):
                if p.label != "PERSON" or p.text.casefold() in NOT_ENTITIES:
                    continue
                if any(s <= a + p.start and a + p.end <= e for s, e in slots):
                    continue
                if not any(w.casefold() in low for w in p.text.split() if len(w) > 2):
                    flag(a + p.start, a + p.end, "name", "This name is not in your message.")
    return sorted(flags, key=lambda f: f["start"])
