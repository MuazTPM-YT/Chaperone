import hashlib
import json
import os
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

from . import ROOT
from .detect import LABELS

ACTIONS = ("pass", "pseudonymize", "generalize", "block")
WHEN_KEYS = ("label", "subject", "role", "destination", "purpose")
RULE_KEYS = ("id", "when", "action", "scope", "coarse", "why")
SCOPES = ("span", "request")
COARSE_STYLES = ("", "year", "age90")
SUBJECTS = ("individual", "business", "unknown")
# each destination is an endpoint in .env (INTERNAL_LLM_*, EXTERNAL_LLM_*), so the set is fixed in code
DESTINATIONS = ("internal", "external")
# only identifiers may be left out for a purpose: dropping a name or a clinical fact would make the answer wrong
MINIMISABLE = ("PHONE", "EMAIL", "UPI", "AADHAAR", "PAN", "GSTIN", "IFSC", "VEHICLE")
RULE_ID = re.compile(r"[a-z0-9][a-z0-9-]{1,62}")
WHY_MAX = 300

HERE = Path(__file__).parent
DEFAULT_PATH = HERE / "policies.yaml"
# admin edits from the UI; kept apart from the shipped files and never committed
LOCAL_PATH = ROOT / "data" / "policies.local.yaml"


class PolicyError(ValueError):
    pass


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


@dataclass(frozen=True)
class Pack:
    id: str
    name: str
    short: str  # for the rules switch in the top bar
    description: str
    extends: str  # id of the pack whose rules run after this one's, or ""
    own: tuple[dict, ...]  # this pack's rules, as edited
    rules: tuple[dict, ...]  # what decide() walks: own rules, then the extended pack's
    edited: bool  # own rules come from the local file, not the shipped one


@dataclass(frozen=True)
class Policies:
    packs: dict[str, Pack]
    roles: tuple[str, ...]
    purposes: dict[str, dict]  # id -> {label, task, omit}
    edited_purposes: bool = False
    error: str = ""  # set when a file changed on disk but is invalid; the last good rules stay in use
    files: tuple[str, ...] = field(default=())


# ---------- validation: every message says what is wrong in words an admin can act on ----------

def _values(v: object) -> list:
    return v if isinstance(v, list) else [v]


def _check_rule(r: object, vocab: dict[str, tuple[str, ...]]) -> None:
    if not isinstance(r, dict):
        raise PolicyError("each rule must be a mapping with id, action and why")
    rid = r.get("id")
    if not isinstance(rid, str) or not RULE_ID.fullmatch(rid):
        raise PolicyError(f"rule id {rid!r}: use 2 to 63 lowercase letters, digits and dashes")
    if extra := set(r) - set(RULE_KEYS):
        raise PolicyError(f"rule {rid}: unknown field {', '.join(sorted(extra))}")
    when = r.get("when", {})
    if not isinstance(when, dict):
        raise PolicyError(f"rule {rid}: 'when' must be a mapping")
    for key, value in when.items():
        if key not in WHEN_KEYS:
            raise PolicyError(f"rule {rid}: unknown condition '{key}' (use {', '.join(WHEN_KEYS)})")
        values = _values(value)
        if not values or not all(isinstance(x, str) for x in values):
            raise PolicyError(f"rule {rid}: condition '{key}' needs one value or a list of values")
        if unknown := [x for x in values if x not in vocab[key]]:
            raise PolicyError(f"rule {rid}: {key} {', '.join(unknown)} is not one of {', '.join(vocab[key])}")
    action = r.get("action")
    if action not in ACTIONS:
        raise PolicyError(f"rule {rid}: action {action!r} is not one of {', '.join(ACTIONS)}")
    if r.get("scope", "span") not in SCOPES:
        raise PolicyError(f"rule {rid}: scope must be 'span' or 'request'")
    if r.get("scope") == "request" and action != "block":
        raise PolicyError(f"rule {rid}: only a block can stop the whole message")
    if r.get("coarse", "") not in COARSE_STYLES:
        raise PolicyError(f"rule {rid}: coarse must be one of year, age90")
    if r.get("coarse") and action != "generalize":
        raise PolicyError(f"rule {rid}: a vagueness style needs the action made vague (generalize)")
    why = r.get("why")
    if not isinstance(why, str) or not why.strip() or len(why) > WHY_MAX:
        raise PolicyError(f"rule {rid}: give a reason of 1 to {WHY_MAX} characters; users see it")


def _check_rules(rules: list[dict], vocab: dict[str, tuple[str, ...]], needs_catch_all: bool) -> None:
    seen: set[str] = set()
    for i, r in enumerate(rules):
        _check_rule(r, vocab)
        if r["id"] in seen:
            raise PolicyError(f"rule id {r['id']} is used twice")
        seen.add(r["id"])
        if not r.get("when") and i < len(rules) - 1:
            raise PolicyError(f"rule {r['id']} matches everything, so the rules after it never run; move it last")
    if needs_catch_all and (not rules or rules[-1].get("when")):
        raise PolicyError("the last rule must be a catch-all with no conditions, so every item gets a decision")


def _check_purposes(purposes: dict[str, dict]) -> None:
    for pid, p in purposes.items():
        if not isinstance(p, dict) or not isinstance(p.get("label"), str) or not isinstance(p.get("task"), str):
            raise PolicyError(f"purpose {pid}: needs a label and a task")
        omit = p.get("omit", [])
        if not isinstance(omit, list) or (bad := [x for x in omit if x not in MINIMISABLE]):
            raise PolicyError(f"purpose {pid}: only identifiers can be left out ({', '.join(MINIMISABLE)}), "
                              f"not {', '.join(map(str, bad)) if isinstance(omit, list) else omit}")


# ---------- building the rule set from the shipped files and the local edits ----------

def _pack_files() -> dict[str, Path]:
    files = {"default": DEFAULT_PATH}
    for path in sorted(HERE.glob("policies_*.yaml")):
        files[path.stem.removeprefix("policies_")] = path
    return files


def _read_yaml(path: Path, shown: str) -> dict:
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise PolicyError(f"{shown} is not valid YAML: {exc}".replace("\n", " ")) from None
    if not isinstance(data, dict):
        raise PolicyError(f"{shown} must be a mapping")
    return data


def _build(local: dict) -> Policies:
    files = _pack_files()
    raw = {pid: _read_yaml(path, f"chaperone/{path.name}") for pid, path in files.items()}
    base = raw["default"]
    roles = tuple(base.get("roles") or ())
    purposes = {pid: {"label": p.get("label", ""), "task": p.get("task", ""), "omit": list(p.get("omit", []))}
                for pid, p in (base.get("purposes") or {}).items()}
    if not roles or not purposes:
        raise PolicyError("chaperone/policies.yaml must list roles and purposes")
    if edits := (local.get("default") or {}).get("purposes"):
        for pid, p in edits.items():
            if pid not in purposes:
                raise PolicyError(f"data/policies.local.yaml: unknown purpose {pid}")
            purposes[pid] = {**purposes[pid], "omit": list(p.get("omit", []))}
    _check_purposes(purposes)
    vocab = {"label": LABELS, "subject": SUBJECTS, "role": roles, "destination": DESTINATIONS,
             "purpose": tuple(purposes)}
    by_name = {path.name: pid for pid, path in files.items()}

    def own(pid: str) -> tuple[list[dict], bool]:
        edit = (local.get(pid) or {}).get("rules")
        return (list(edit), True) if edit is not None else (list(raw[pid].get("rules") or []), False)

    def resolve(pid: str, seen: tuple[str, ...] = ()) -> list[dict]:
        if pid in seen:
            raise PolicyError(f"rule packs extend each other in a loop: {' > '.join((*seen, pid))}")
        parent = by_name.get(raw[pid].get("extends", ""), "")
        return own(pid)[0] + (resolve(parent, (*seen, pid)) if parent else [])

    packs = {}
    for pid in files:
        if (extends := raw[pid].get("extends")) and extends not in by_name:
            raise PolicyError(f"chaperone/{files[pid].name} extends {extends}, which does not exist")
        rules, edited = own(pid)
        _check_rules(rules, vocab, needs_catch_all=not extends)
        full = resolve(pid)
        _check_rules(full, vocab, needs_catch_all=True)
        name = str(raw[pid].get("name") or pid)
        packs[pid] = Pack(pid, name, str(raw[pid].get("short") or name), str(raw[pid].get("description") or ""),
                          by_name.get(extends or "", ""), tuple(rules), tuple(full), edited)
    if unknown := set(local) - set(packs):
        raise PolicyError(f"data/policies.local.yaml: unknown rule pack {', '.join(sorted(unknown))}")
    return Policies(packs, roles, purposes, bool((local.get("default") or {}).get("purposes")),
                    files=tuple(sorted(str(p) for p in files.values())))


def _read_local() -> dict:
    return _read_yaml(LOCAL_PATH, "data/policies.local.yaml") if LOCAL_PATH.exists() else {}


# ---------- live state: files are re-read when they change; a bad change never replaces good rules ----------

_LOCK = threading.Lock()
_state: Policies | None = None
_stamp: tuple = ()
_preview: ContextVar[Policies | None] = ContextVar("policy_preview", default=None)


def _disk_stamp() -> tuple:
    paths = [*_pack_files().values(), LOCAL_PATH]
    return tuple((str(p), p.stat().st_mtime_ns if p.exists() else 0) for p in paths)


def current() -> Policies:
    if (shown := _preview.get()) is not None:
        return shown
    global _state, _stamp
    stamp = _disk_stamp()
    with _LOCK:
        if _state is None or stamp != _stamp:
            try:
                _state = _build(_read_local())
            except PolicyError as exc:
                if _state is None:
                    raise  # at start there is nothing safe to fall back on: fail loud
                _state = replace(_state, error=_where(exc))
            _stamp = stamp
        return _state


# name the file to fix: the shipped rules alone build, so the fault is in the local edits
def _where(exc: PolicyError) -> str:
    msg = str(exc)
    if LOCAL_PATH.exists() and "data/policies.local.yaml" not in msg:
        try:
            _build({})
            return f"data/policies.local.yaml: {msg}"
        except PolicyError:
            pass
    return msg


def decide(label: str, subject: str, flow: Flow) -> Decision:
    facts = {"label": label, "subject": subject, "role": flow.role,
             "destination": flow.destination, "purpose": flow.purpose}
    packs = current().packs
    for r in packs.get(flow.pack, packs["default"]).rules:
        if all(facts[k] in _values(v) for k, v in r.get("when", {}).items()):
            return Decision(r["action"], r["id"], r.get("why", ""), r.get("scope", "span"), r.get("coarse", ""))
    raise AssertionError("unreachable: every pack ends with a catch-all rule")


# one rule file on its own, as shipped, with its extended packs; no local edits (tests and tools)
def load(path: Path = DEFAULT_PATH) -> tuple[dict, ...]:
    pid = "default" if path == DEFAULT_PATH else path.stem.removeprefix("policies_")
    return _build({}).packs[pid].rules


# ---------- edits from the admin UI ----------

def _with_edit(local: dict, pack: str, rules: list[dict] | None, purposes: dict | None) -> dict:
    out = {k: dict(v) for k, v in local.items()}
    entry = out.setdefault(pack, {})
    if rules is not None:
        entry["rules"] = rules
    if purposes:
        if pack != "default":
            raise PolicyError("purposes are set once, in the Standard rules")
        entry["purposes"] = {pid: {"omit": list(p.get("omit", []))} for pid, p in purposes.items()}
    return out


# check an edit without saving it; returns the rule set it would produce
def validate_edit(pack: str, rules: list[dict], purposes: dict | None) -> Policies:
    if pack not in _pack_files():
        raise PolicyError(f"unknown rule pack {pack}")
    return _build(_with_edit(_read_local(), pack, rules, purposes))


# fingerprint of what a pack decides, to log what changed without logging the rules themselves
def fingerprint(p: Policies, pack: str) -> str:
    body = json.dumps({"rules": p.packs[pack].rules, "purposes": p.purposes}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def _write_local(local: dict) -> None:
    if not local:
        LOCAL_PATH.unlink(missing_ok=True)
        return
    LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = LOCAL_PATH.with_suffix(".tmp")
    header = "# Rule edits made in the Chaperone UI (admin mode). Delete this file to go back to the shipped rules.\n"
    with tmp.open("w") as f:
        f.write(header + yaml.safe_dump(local, sort_keys=False, allow_unicode=True))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, LOCAL_PATH)  # atomic: a crash leaves the old file or the new one, never half of one


# returns (before, after) fingerprints
def save_local(pack: str, rules: list[dict], purposes: dict | None) -> tuple[str, str]:
    before = current()
    after = validate_edit(pack, rules, purposes)
    _write_local(_with_edit(_read_local(), pack, rules, purposes))
    return fingerprint(before, pack), fingerprint(after, pack)


# drop one pack's local edits (and, for the Standard rules, the purpose edits); returns (before, after)
def reset_local(pack: str) -> tuple[str, str]:
    if pack not in _pack_files():
        raise PolicyError(f"unknown rule pack {pack}")
    before = current()
    local = _read_local()
    local.pop(pack, None)
    after = _build(local)
    _write_local(local)
    return fingerprint(before, pack), fingerprint(after, pack)


# decisions inside this block use the candidate rules; nothing is saved and other requests are unaffected
@contextmanager
def preview(pack: str, rules: list[dict], purposes: dict | None) -> Iterator[Policies]:
    token = _preview.set(validate_edit(pack, rules, purposes))
    try:
        yield _preview.get()  # type: ignore[misc]
    finally:
        _preview.reset(token)
