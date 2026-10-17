import json
import os
import queue
import threading
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import ROOT, gateway, policy
from .detect import CONTEXT_MODEL, LABELS
from .policy import Flow, PolicyError
from .transform import Vault

HERE = Path(__file__).parent
# the page, built from web/ by `npm run build`; the API works without it
WEB = ROOT / "web" / "out"
# ponytail: one request at a time; vaults and GLiNER are not shared safely across threads
LOCK = threading.Lock()
# dev-only: worst-case scenarios behind a toggle, never shown in a normal run
DEV = os.environ.get("CHAPERONE_DEV") == "1"
# rule editing in the UI; off unless whoever starts the server turns it on, so staff cannot loosen their own checks
ADMIN = os.environ.get("CHAPERONE_ADMIN") == "1"

app = FastAPI(title="Chaperone")
# a web page that rebinds its own domain to 127.0.0.1 still sends that domain as Host: refuse it
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
# fonts ship with the app, so the page needs no internet
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


MAX_TEXT = 4000  # about a page; keeps the local model's 4k-token window safe


class ChatIn(BaseModel):
    session_id: str
    text: str = Field(min_length=1, max_length=MAX_TEXT)
    role: str
    destination: str
    purpose: str
    use_context: bool = True
    include: list[dict] = []  # "include anyway": [{label, text, reason}] for identifiers the purpose would omit
    pack: str = "default"  # policy pack: "default" or "safe_harbor"


def _pack(name: str) -> str:
    return name if name in policy.current().packs else "default"


@app.get("/")
def index() -> Response:
    # no-cache still allows a 304, but the browser must ask, so a new version is never hidden behind an old one
    if not (WEB / "index.html").exists():
        return Response("The page is not built yet. Run: cd web && npm ci && npm run build", status_code=503,
                        media_type="text/plain", headers={"Cache-Control": "no-cache"})
    return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/api/meta")
def meta(data: str = "") -> dict:
    fixture = "scenarios_worst.json" if DEV and data == "worst" else "scenarios.json"
    p = policy.current()
    return {"roles": list(p.roles), "destinations": list(policy.DESTINATIONS), "purposes": list(p.purposes),
            "purpose_labels": {pid: x["label"] for pid, x in p.purposes.items()},
            "scenarios": json.loads((HERE / fixture).read_text()), "dev": DEV, "max_text": MAX_TEXT,
            "packs": [{"id": k.id, "name": k.name, "short": k.short, "description": k.description} for k in p.packs.values()],
            "admin": ADMIN, "policy_error": p.error, "context_model": CONTEXT_MODEL,
            "endpoints": {"internal": gateway.recipient("internal"), "external": gateway.recipient("external")}}


@app.post("/api/chat")
def chat(body: ChatIn) -> dict:
    flow = Flow(body.role, body.destination, body.purpose, _pack(body.pack))
    with LOCK:
        return gateway.chat(body.text, flow, body.session_id, body.use_context, body.include)


# same as /api/chat, but one JSON line per pipeline step as it finishes, then {"step": "result"} with the full result
@app.post("/api/chat/stream")
def chat_stream(body: ChatIn) -> StreamingResponse:
    flow = Flow(body.role, body.destination, body.purpose, _pack(body.pack))
    events: queue.Queue = queue.Queue()

    def run() -> None:
        try:
            with LOCK:
                result = gateway.chat(body.text, flow, body.session_id, body.use_context, body.include,
                                      on_step=lambda step, data: events.put({"step": step, **data}))
            events.put({"step": "result", "result": result})
        except Exception as exc:  # noqa: BLE001 - the page needs an end to the stream; the terminal gets the details
            traceback.print_exc()
            events.put({"step": "error", "error": type(exc).__name__})
        finally:
            events.put(None)

    def lines():
        while (event := events.get()) is not None:
            yield json.dumps(event, ensure_ascii=False) + "\n"

    threading.Thread(target=run, daemon=True).start()
    return StreamingResponse(lines(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store"})


class CompareIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT)
    flows: list[dict] = [{"role": "Doctor", "destination": "internal", "purpose": "general"},
                         {"role": "Doctor", "destination": "external", "purpose": "general"},
                         {"role": "Intern", "destination": "external", "purpose": "general"}]
    use_context: bool = True
    pack: str = "default"


# W3: one message, several flows, side by side. Dry runs: nothing is sent to any AI, no session is touched.
@app.post("/api/compare")
def compare(body: CompareIn) -> dict:
    with LOCK:
        runs = []
        for f in body.flows[:4]:
            flow = Flow(f["role"], f["destination"], f["purpose"], _pack(body.pack))
            r = gateway.analyze(body.text, flow, Vault(), body.use_context)
            r.pop("protected")
            runs.append(r)
    return {"text": body.text, "runs": runs}


# what an identifier-only cloak would send for this message, and what the attacker infers from it (our ablation)
@app.post("/api/baseline")
def baseline(body: ChatIn) -> dict:
    with LOCK:
        return gateway.baseline(body.text, Flow(body.role, body.destination, body.purpose, _pack(body.pack)))


# ---------- rules: everyone may read them; only admin mode may change them ----------

def _policies_view() -> dict:
    p = policy.current()
    return {
        "packs": [{"id": k.id, "name": k.name, "short": k.short, "description": k.description, "extends": k.extends,
                   "edited": k.edited,
                   "rules": list(k.own)} for k in p.packs.values()],
        "purposes": [{"id": pid, **x} for pid, x in p.purposes.items()],
        "edited_purposes": p.edited_purposes, "error": p.error, "admin": ADMIN,
        "vocabulary": {"label": list(LABELS), "subject": list(policy.SUBJECTS), "role": list(p.roles),
                       "destination": list(policy.DESTINATIONS), "purpose": list(p.purposes),
                       "action": list(policy.ACTIONS), "minimisable": list(policy.MINIMISABLE)},
    }


def _admin() -> None:
    if not ADMIN:
        raise HTTPException(403, "Rule editing is off. Start the server with CHAPERONE_ADMIN=1 to turn it on.")


class PolicyIn(BaseModel):
    rules: list[dict] = Field(max_length=500)
    purposes: dict[str, dict] | None = None


class PreviewIn(PolicyIn):
    pack: str
    text: str = Field(min_length=1, max_length=MAX_TEXT)
    role: str
    destination: str
    purpose: str
    use_context: bool = True


@app.get("/api/policies")
def policies() -> dict:
    return _policies_view()


@app.put("/api/policies/{pack}")
def save_policies(pack: str, body: PolicyIn) -> dict:
    _admin()
    with LOCK:
        try:
            before, after = policy.save_local(pack, body.rules, body.purposes)
        except PolicyError as exc:
            raise HTTPException(422, str(exc)) from None
        gateway.audit_event("policy_change", {"pack": pack, "before": before, "after": after})
        return _policies_view()


@app.delete("/api/policies/{pack}")
def reset_policies(pack: str) -> dict:
    _admin()
    with LOCK:
        try:
            before, after = policy.reset_local(pack)
        except PolicyError as exc:
            raise HTTPException(422, str(exc)) from None
        gateway.audit_event("policy_reset", {"pack": pack, "before": before, "after": after})
        return _policies_view()


# the same message under the saved rules and under the edited ones; dry runs, nothing is sent or saved
@app.post("/api/policies/preview")
def preview_policies(body: PreviewIn) -> dict:
    _admin()
    flow = Flow(body.role, body.destination, body.purpose, _pack(body.pack))
    with LOCK:
        before = gateway.analyze(body.text, flow, Vault(), body.use_context)
        try:
            with policy.preview(body.pack, body.rules, body.purposes):
                after = gateway.analyze(body.text, flow, Vault(), body.use_context)
        except PolicyError as exc:
            raise HTTPException(422, str(exc)) from None
    for r in (before, after):
        r.pop("protected")
    return {"before": before, "after": after}


@app.get("/api/records.csv")
def records() -> Response:
    return Response(gateway.processing_record(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="chaperone-processing-record.csv"'})


@app.post("/api/reset/{session_id}")
def reset(session_id: str) -> dict:
    gateway.SESSIONS.pop(session_id, None)
    return {"ok": True}


class PersonIn(BaseModel):
    value: str = Field(min_length=2, max_length=200)


# POST, not GET: the name or ID asked about stays out of URLs and server logs
@app.post("/api/person-report")
def person_report(body: PersonIn) -> dict:
    with LOCK:
        return gateway.person_report(body.value)


@app.get("/api/audit/verify")
def verify_audit() -> dict:
    with LOCK:
        return gateway.verify_log()


# the page's scripts and styles; mounted last, so every route above wins
app.mount("/", StaticFiles(directory=WEB, check_dir=False), name="web")
