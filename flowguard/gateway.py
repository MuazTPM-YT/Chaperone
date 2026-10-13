import hashlib
import hmac
import json
import os
import re
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime

import httpx

from . import ROOT, attack, purpose, verify
from .detect import SEMANTIC, Span, detect_cached
from .policy import Decision, Flow, decide
from .transform import OutboundLeak, Vault, apply, canonical, guard, restore_marked

AUDIT_PATH = ROOT / "data" / "audit.jsonl"
BASE_PROMPT = ("You are a workplace assistant for a small Indian organisation. Do the task the user asks for: "
               "draft, summarise, rewrite or answer. Write the finished result, not a template, and never just "
               "repeat the message back. Reply in English unless the user asks otherwise.")
PLACEHOLDER_RULE = (" Some names and numbers were replaced by placeholders in square brackets. Copy each one exactly, "
                    "brackets included, where the real value belongs. Never invent new ones and never ask what they "
                    "stand for.")
VAGUE_RULE = " Other bracketed phrases are deliberately vague; keep them vague."
PLACEHOLDER = re.compile(r"\[[A-Z]+_\d+\]")
VAGUE = re.compile(r"\[(?![A-Z]+_\d+\])[^\]\n]+\]")


# a 3B model copies whatever the prompt names, so rules about brackets appear only when brackets were sent
def system_prompt(outbound: str) -> str:
    return (BASE_PROMPT + (PLACEHOLDER_RULE if PLACEHOLDER.search(outbound) else "")
            + (VAGUE_RULE if VAGUE.search(outbound) else ""))

# ponytail: in-memory sessions, lost on restart; fine for a single-user local gateway
SESSIONS: dict[str, dict[str, Vault]] = {}


def need(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required env var {name} (copy .env.example to .env)")
    return value


def vault_for(session_id: str, destination: str) -> Vault:
    return SESSIONS.setdefault(session_id, {}).setdefault(destination, Vault())


# detect -> decide -> transform -> attack and tighten; no network except the local models
def analyze(text: str, flow: Flow, vault: Vault, use_context: bool = True, model: str | None = None,
            use_attack: bool = True, use_purpose: bool = True, include: list[dict] | None = None) -> dict:
    t0 = time.perf_counter()
    det = detect_cached(text, use_context=use_context, model=model)
    spans = list(det.spans)
    decisions = []
    for s in spans:
        d = decide(s.label, s.subject, flow)
        if d.coarse == "age90" and (m := re.search(r"\d+", s.text)) and int(m.group()) <= 89:
            d = Decision("pass", "safe-harbor-age-under-90", "Safe Harbor keeps ages up to 89; only older ages are grouped.")
        if d.action == "pass" and vault.holds(s.label, s.alias or s.text):
            d = Decision("pseudonymize", "session-sticky", "Masked earlier in this conversation, so it stays masked.")
        decisions.append(d)
    outbound, applied = apply(text, spans, decisions, vault)

    # W2: identifiers the stated purpose does not need are omitted, not masked (DPDP data minimisation)
    t_purpose = time.perf_counter()
    overrides: list[dict] = []
    if use_purpose and outbound is not None:
        wanted = {(i["label"], canonical(i["label"], i["text"])): i.get("reason", "") for i in include or []}
        task = purpose.TASKS.get(flow.purpose, flow.purpose)
        for k, a in enumerate(applied):
            if a.decision.action not in ("pass", "pseudonymize", "generalize") or not purpose.omits(flow.purpose, a.span.label):
                continue
            key = (a.span.label, canonical(a.span.label, a.span.alias or a.span.text))
            if key in wanted:
                overrides.append({"label": a.span.label, "text": a.span.text, "reason": wanted[key]})
                continue
            decisions[k] = Decision("block", "purpose-minimisation",
                                    f"Not needed to {task}, so it is left out (purpose limitation, data minimisation).")
        if any(d.rule == "purpose-minimisation" for d in decisions):
            outbound, applied = apply(text, spans, decisions, vault)
    purpose_ms = (time.perf_counter() - t_purpose) * 1000

    earlier = [m["content"] for m in vault.history if m["role"] == "user"]
    rounds, unresolved, skipped = [], [], ""
    t_attack = time.perf_counter()
    if not use_attack:
        skipped = "turned off"
    elif not det.context_ok:
        skipped = "local AI unavailable"
    elif outbound is None:
        skipped = "request already blocked"
    elif not attack.forbidden_categories(flow):
        skipped = "this flow allows every category"
    else:
        for rnd in range(attack.MAX_ROUNDS + 1):
            if outbound is None:
                break
            r, infs = attack.timed_attack(outbound, earlier, flow, rnd, model)
            rounds.append(r)
            live = [inf for inf in infs if inf.forbidden and not inf.disclosed]
            if not live:
                break
            if rnd == attack.MAX_ROUNDS:
                unresolved = live
                break
            changed = _tighten(text, live, spans, decisions, r, model)
            if not changed:
                unresolved = live
                break
            outbound, applied = apply(text, spans, decisions, vault)
    blocker: Decision | None
    if unresolved:
        outbound = None
        guesses = "; ".join(sorted({inf.guess for inf in unresolved}))
        blocker = Decision("block", "attacker-not-cleared",
                           f"After {attack.MAX_ROUNDS} tightening rounds a local attacker could still infer: {guesses}. "
                           "Edit the message and try again.", "request")
    else:
        blocker = next((a.decision for a in applied if a.decision.scope == "request" and a.decision.action == "block"), None)
    protected = list(vault.raw.values()) + [a.span.text for a in applied if a.decision.action != "pass"]
    timings = {**det.timings, "purpose_ms": purpose_ms, "attack_ms": (time.perf_counter() - t_attack) * 1000,
               "total_ms": (time.perf_counter() - t0) * 1000}
    return {
        "original": text,
        "flow": asdict(flow),
        "outbound": outbound,
        "blocked": outbound is None,
        "block_reason": asdict(blocker) if blocker else None,
        "context_ok": det.context_ok,
        "context_error": det.context_error,
        "spans": [{**asdict(a.span), **asdict(a.decision), "replacement": a.replacement, "covered": a.covered}
                  for a in applied],
        "attack": {"ran": bool(rounds), "skipped": skipped, "max_rounds": attack.MAX_ROUNDS,
                   "rounds": [attack.as_dict(r) for r in rounds],
                   "unresolved": [asdict(inf) for inf in unresolved]},
        "overrides": overrides,
        "protected": protected,
        "timings": {k: round(v, 1) for k, v in timings.items()},
    }


# what an identifier-only cloak would send (names and IDs masked, meaning left as typed), and what the attacker gets from it.
# our own ablation for comparison, not any specific product
def baseline(text: str, flow: Flow, model: str | None = None) -> dict:
    t0 = time.perf_counter()
    det = detect_cached(text, model=model)
    decisions = [Decision("pass", "baseline", "") if s.label in SEMANTIC else decide(s.label, s.subject, flow) for s in det.spans]
    sent, _ = apply(text, det.spans, decisions, Vault())
    infs = attack.attack(sent, [], flow, model) if sent and det.context_ok else []
    return {"outbound": sent, "inferences": [asdict(i) for i in infs], "context_ok": det.context_ok,
            "ms": round((time.perf_counter() - t0) * 1000, 1)}


# replace only the words the attacker relied on: vague first, blocked if the same words still give it away
def _tighten(text: str, live: list, spans: list[Span], decisions: list[Decision], r: "attack.Round",
             model: str | None) -> bool:
    changed = False
    for inf in live:
        for cand in attack.evidence_spans(text, inf, spans, block=False, model=model):
            # touching or overlapping an earlier attacker span of the same kind: grow that one, no token soup
            hit = next((k for k, s in enumerate(spans) if s.source == "attacker" and s.label == cand.label
                        and cand.start <= s.end + 2 and s.start <= cand.end + 2
                        and not text[min(s.end, cand.end):max(s.start, cand.start)].strip(" ,;")), None)
            if hit is not None and not (cand.start < spans[hit].end and spans[hit].start < cand.end):
                old = spans[hit]
                s0, e0 = min(old.start, cand.start), max(old.end, cand.end)
                spans[hit] = replace(old, start=s0, end=e0, text=text[s0:e0])
                r.tightened.append(cand.text)
                changed = True
                continue
            why = f"A local attacker inferred \"{inf.guess}\" from these words."
            if hit is None:
                spans.append(cand)
                decisions.append(Decision("generalize", "attacker-tighten", why))
                r.tightened.append(cand.text)
                changed = True
            elif decisions[hit].action != "block":
                decisions[hit] = Decision("block", "attacker-block", why + " Making them vague was not enough.")
                r.tightened.append(spans[hit].text)
                changed = True
    return changed


# the only door to an LLM: guard runs first, every time
def send(destination: str, messages: list[dict], protected: list[str]) -> str:
    guard(json.dumps(messages, ensure_ascii=False), protected)
    guard("\n".join(m["content"] for m in messages), protected)
    prefix = destination.upper()
    base, model = need(f"{prefix}_LLM_BASE_URL"), need(f"{prefix}_LLM_MODEL")
    key = os.environ.get(f"{prefix}_LLM_API_KEY", "")
    r = httpx.post(f"{base.rstrip('/')}/chat/completions", timeout=120,
                   headers={"Authorization": f"Bearer {key}"} if key else {},
                   json={"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 700})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# E2: per conversation, what the external AI could now infer about people, turn by turn
def _record_exposure(vault: Vault, result: dict) -> None:
    rounds = result["attack"]["rounds"]
    for inf in rounds[-1]["inferences"] if rounds else []:
        status = "already disclosed earlier" if inf["disclosed"] else "allowed for this flow"
        entry = {"turn": len(vault.sources), "category": inf["category"], "guess": inf["guess"], "status": status}
        if not any(e["category"] == entry["category"] and e["guess"] == entry["guess"] for e in vault.exposure):
            vault.exposure.append(entry)
    result["exposure"] = list(vault.exposure)


# an override reason is free text; names and ids in it are replaced before it reaches the log
def mask_reason(reason: str) -> str:
    out = reason[:300]
    for sp in sorted(detect_cached(out, use_context=False).spans, key=lambda x: -x.start):
        out = out[:sp.start] + f"[{sp.label}]" + out[sp.end:]
    return out


def audit(session_id: str, result: dict) -> None:
    secret = need("AUDIT_HMAC_KEY")
    if secret == "change-me":
        raise RuntimeError("AUDIT_HMAC_KEY still has the example value; run ./setup.sh or set a random key")
    key = secret.encode()

    def tag(v: str) -> str:
        return hmac.new(key, v.encode(), hashlib.sha256).hexdigest()[:16]

    line = {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "session": tag(session_id),
        "flow": result["flow"],
        "blocked": result["blocked"],
        "sent": result["sent"],
        "context_ok": result["context_ok"],
        "decisions": [{"label": s["label"], "subject": s["subject"], "source": s["source"], "rule": s["rule"],
                       "action": s["action"], "value_hmac": tag(s["text"]),
                       "placeholder": s["replacement"] if s["action"] == "pseudonymize" else None}
                      for s in result["spans"]],
    }
    line["overrides"] = [{"label": o["label"], "value_hmac": tag(o["text"]), "reason": mask_reason(o["reason"])}
                         for o in result.get("overrides", [])]
    AUDIT_PATH.parent.mkdir(exist_ok=True)
    with AUDIT_PATH.open("a") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def chat(text: str, flow: Flow, session_id: str, use_context: bool = True, include: list[dict] | None = None) -> dict:
    vault = vault_for(session_id, flow.destination)
    result = analyze(text, flow, vault, use_context, include=include)
    vault.sources.append(text)
    protected = result.pop("protected")
    result.update(reply=None, restored=None, restore_stats=None, restore_marks=[], flags=[], error=None, sent=False,
                  exposure=list(vault.exposure))
    if not result["blocked"]:
        sent_so_far = "\n".join([m["content"] for m in vault.history if m["role"] == "user"] + [result["outbound"]])
        messages = [{"role": "system", "content": system_prompt(sent_so_far)}, *vault.history,
                    {"role": "user", "content": result["outbound"]}]
        t0 = time.perf_counter()
        try:
            reply = send(flow.destination, messages, protected)
        except OutboundLeak as exc:
            result["error"] = f"Outbound guard refused to send: {exc}"
        except httpx.HTTPError as exc:
            result["error"] = f"LLM call failed: {type(exc).__name__}"
        else:
            result["sent"] = True
            result["timings"]["llm_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            vault.history += [{"role": "user", "content": result["outbound"]},
                              {"role": "assistant", "content": reply}]
            result["reply"] = reply
            result["restored"], result["restore_stats"], result["restore_marks"] = restore_marked(reply, vault)
            result["flags"] = verify.check(result["restored"], vault.sources)
            _record_exposure(vault, result)
    audit(session_id, result)
    return result
