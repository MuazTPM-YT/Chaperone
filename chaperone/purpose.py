from functools import lru_cache
from pathlib import Path

import yaml

from .policy import DEFAULT_PATH

# only identifiers are candidates: dropping a name or a clinical fact would make the answer wrong
MINIMISABLE = ("PHONE", "EMAIL", "UPI", "AADHAAR", "PAN", "GSTIN", "IFSC", "VEHICLE")
TASKS = {"scheduling": "schedule meetings, leave or shifts", "hr_summary": "write an HR summary or letter",
         "marketing": "write marketing or public copy", "clinical_summary": "write a clinical summary of a patient's care",
         "invoicing": "prepare an invoice, bill or payment request", "general": "do what the message asks"}


@lru_cache(maxsize=4)
def _declared(path: Path = DEFAULT_PATH) -> dict[str, set[str]]:
    raw = yaml.safe_load(path.read_text()).get("purposes", {})
    return {p: set(v.get("omit", [])) for p, v in raw.items()}


# does this purpose need this kind of identifier? undeclared purposes need everything
def omits(purpose: str, label: str, path: Path = DEFAULT_PATH) -> bool:
    return label in MINIMISABLE and label in _declared(path).get(purpose, set())
