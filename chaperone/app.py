import json
import os
import queue
import threading
import traceback
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import gateway
from .detect import CONTEXT_MODEL
from .policy import PACKS, Flow
from .transform import Vault

HERE = Path(__file__).parent
ROLES = ["Manager", "HR", "Sales", "Intern", "Doctor", "Accountant"]
PURPOSES = ["general", "scheduling", "hr_summary", "marketing", "clinical_summary", "invoicing"]
# ponytail: one request at a time; vaults and GLiNER are not shared safely across threads
LOCK = threading.Lock()
# dev-only: worst-case scenarios behind a toggle, never shown in a normal run
DEV = os.environ.get("CHAPERONE_DEV") == "1"

app = FastAPI(title="Chaperone")
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
    return name if name in PACKS else "default"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(HERE / "static" / "index.html")


@app.get("/api/meta")
def meta(data: str = "") -> dict:
    fixture = "scenarios_worst.json" if DEV and data == "worst" else "scenarios.json"
    return {"roles": ROLES, "destinations": ["internal", "external"], "purposes": PURPOSES,
            "scenarios": json.loads((HERE / fixture).read_text()), "dev": DEV, "max_text": MAX_TEXT,
            "packs": [{"id": "default", "name": "Standard rules"}, {"id": "safe_harbor", "name": "HIPAA Safe Harbor mode"}],
            "context_model": CONTEXT_MODEL,
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
