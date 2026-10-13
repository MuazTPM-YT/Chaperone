import hashlib
import hmac
import json
import os
import time
from dataclasses import asdict
from datetime import UTC, datetime

import httpx

from . import ROOT
from .detect import detect
from .policy import Decision, Flow, decide
from .transform import OutboundLeak, Vault, apply, guard, restore

AUDIT_PATH = ROOT / "data" / "audit.jsonl"
SYSTEM_PROMPT = ("You are a workplace assistant for a small Indian organisation. Do the task the user asks for: "
                 "draft, summarise, rewrite or answer. Write the finished result, not a template, and never just "
                 "repeat the message back. Some names and numbers were replaced by bracketed placeholders (a type "
                 "and a number); use them exactly as written, brackets included, wherever the real value belongs. "
                 "Never invent new placeholders and never ask what they stand for. Bracketed phrases such as "
                 "[health detail] or a salary band are deliberately vague; keep them vague. Reply in English "
                 "unless the user asks otherwise.")

# ponytail: in-memory sessions, lost on restart; fine for a single-user local gateway
SESSIONS: dict[str, dict[str, Vault]] = {}


def need(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required env var {name} (copy .env.example to .env)")
    return value


def vault_for(session_id: str, destination: str) -> Vault:
    return SESSIONS.setdefault(session_id, {}).setdefault(destination, Vault())


# detect -> decide -> transform, no network except the local context model
def analyze(text: str, flow: Flow, vault: Vault, use_context: bool = True, model: str | None = None) -> dict:
    t0 = time.perf_counter()
    det = detect(text, use_context=use_context, model=model)
    decisions = []
    for s in det.spans:
        d = decide(s.label, s.subject, flow)
        if d.action == "pass" and vault.holds(s.label, s.text):
            d = Decision("pseudonymize", "session-sticky", "Masked earlier in this conversation, so it stays masked.")
        decisions.append(d)
    outbound, applied = apply(text, det.spans, decisions, vault)
    blocker = next((a.decision for a in applied if a.decision.scope == "request" and a.decision.action == "block"), None)
    protected = list(vault.raw.values()) + [a.span.text for a in applied if a.decision.action != "pass"]
    timings = {**det.timings, "total_ms": (time.perf_counter() - t0) * 1000}
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
        "protected": protected,
        "timings": {k: round(v, 1) for k, v in timings.items()},
    }


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
    AUDIT_PATH.parent.mkdir(exist_ok=True)
    with AUDIT_PATH.open("a") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def chat(text: str, flow: Flow, session_id: str, use_context: bool = True) -> dict:
    vault = vault_for(session_id, flow.destination)
    result = analyze(text, flow, vault, use_context)
    protected = result.pop("protected")
    result.update(reply=None, restored=None, restore_stats=None, error=None, sent=False)
    if not result["blocked"]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *vault.history,
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
            result["restored"], result["restore_stats"] = restore(reply, vault)
    audit(session_id, result)
    return result
