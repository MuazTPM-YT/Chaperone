import json
import os
import threading
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.responses import FileResponse
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
DEV = os.environ.get("FLOWGUARD_DEV") == "1"

app = FastAPI(title="FlowGuard")


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


def _endpoint(dest: str) -> dict:
    base = os.environ.get(f"{dest}_LLM_BASE_URL", "")
    host = urlparse(base).hostname or ""
    return {"model": os.environ.get(f"{dest}_LLM_MODEL", ""), "host": host,
            "simulated": host in ("127.0.0.1", "localhost")}


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
            "endpoints": {"internal": _endpoint("INTERNAL"), "external": _endpoint("EXTERNAL")}}


@app.post("/api/chat")
def chat(body: ChatIn) -> dict:
    flow = Flow(body.role, body.destination, body.purpose, _pack(body.pack))
    with LOCK:
        return gateway.chat(body.text, flow, body.session_id, body.use_context, body.include)


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


@app.post("/api/reset/{session_id}")
def reset(session_id: str) -> dict:
    gateway.SESSIONS.pop(session_id, None)
    return {"ok": True}
