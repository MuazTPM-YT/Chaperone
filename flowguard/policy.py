from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

ACTIONS = ("pass", "pseudonymize", "generalize", "block")
WHEN_KEYS = ("label", "subject", "role", "destination", "purpose")
DEFAULT_PATH = Path(__file__).with_name("policies.yaml")
PACKS = {"default": DEFAULT_PATH, "safe_harbor": DEFAULT_PATH.with_name("policies_safe_harbor.yaml")}
COARSE_STYLES = ("", "year", "age90")


@dataclass(frozen=True)
class Flow:
    role: str
    destination: str
    purpose: str
    pack: str = "default"


@dataclass(frozen=True)
class Decision:
    action: str
    rule: str
    why: str
    scope: str = "span"
    coarse: str = ""  # how vague a generalize must be: "" default, "year" (dates), "age90" (ages over 89)


# load rules, fail loud on typos so a bad policy never silently passes data
@lru_cache(maxsize=4)
def load(path: Path = DEFAULT_PATH) -> tuple[dict, ...]:
    data = yaml.safe_load(path.read_text())
    rules = list(data["rules"])
    if data.get("extends"):  # a pack: its rules run first, the base file covers the rest
        rules += list(load(path.with_name(data["extends"])))
    for r in rules:
        bad = set(r.get("when", {})) - set(WHEN_KEYS)
        if (bad or r["action"] not in ACTIONS or r.get("scope", "span") not in ("span", "request")
                or r.get("coarse", "") not in COARSE_STYLES):
            raise ValueError(f"bad policy rule {r.get('id')}: keys {bad}, action {r['action']}")
    if rules[-1].get("when"):
        raise ValueError("last policy rule must be a catch-all (no 'when')")
    return tuple(rules)


def decide(label: str, subject: str, flow: Flow, path: Path | None = None) -> Decision:
    facts = {"label": label, "subject": subject, "role": flow.role,
             "destination": flow.destination, "purpose": flow.purpose}
    for r in load(path or PACKS[flow.pack]):
        when = r.get("when", {})
        if all(facts[k] in (v if isinstance(v, list) else [v]) for k, v in when.items()):
            return Decision(r["action"], r["id"], r.get("why", ""), r.get("scope", "span"), r.get("coarse", ""))
    raise AssertionError("unreachable: catch-all rule")
