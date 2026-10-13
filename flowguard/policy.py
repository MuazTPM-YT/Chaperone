from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

ACTIONS = ("pass", "pseudonymize", "generalize", "block")
WHEN_KEYS = ("label", "subject", "role", "destination", "purpose")
DEFAULT_PATH = Path(__file__).with_name("policies.yaml")


@dataclass(frozen=True)
class Flow:
    role: str
    destination: str
    purpose: str


@dataclass(frozen=True)
class Decision:
    action: str
    rule: str
    why: str
    scope: str = "span"


# load rules, fail loud on typos so a bad policy never silently passes data
@lru_cache(maxsize=4)
def load(path: Path = DEFAULT_PATH) -> tuple[dict, ...]:
    rules = yaml.safe_load(path.read_text())["rules"]
    for r in rules:
        bad = set(r.get("when", {})) - set(WHEN_KEYS)
        if bad or r["action"] not in ACTIONS or r.get("scope", "span") not in ("span", "request"):
            raise ValueError(f"bad policy rule {r.get('id')}: keys {bad}, action {r['action']}")
    if rules[-1].get("when"):
        raise ValueError("last policy rule must be a catch-all (no 'when')")
    return tuple(rules)


def decide(label: str, subject: str, flow: Flow, path: Path = DEFAULT_PATH) -> Decision:
    facts = {"label": label, "subject": subject, "role": flow.role,
             "destination": flow.destination, "purpose": flow.purpose}
    for r in load(path):
        when = r.get("when", {})
        if all(facts[k] in (v if isinstance(v, list) else [v]) for k, v in when.items()):
            return Decision(r["action"], r["id"], r.get("why", ""), r.get("scope", "span"))
    raise AssertionError("unreachable: catch-all rule")
