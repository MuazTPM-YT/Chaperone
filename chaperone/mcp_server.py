# E3: Chaperone as an MCP tool server over stdio, so any agent routes outbound text through the same checks.
# JSON-RPC 2.0, one message per line (MCP stdio transport). No SDK: three methods are all we need.
#   uv run --frozen python -m chaperone.mcp_server
import json
import sys

from . import gateway
from .app import MAX_TEXT, PURPOSES, ROLES
from .policy import PACKS, Flow

PROTOCOL = "2025-06-18"
FLOW_ARGS = {
    "text": {"type": "string", "maxLength": MAX_TEXT, "description": "The message the agent wants to send."},
    "role": {"type": "string", "enum": ROLES, "description": "Who in the organisation is sending it."},
    "destination": {"type": "string", "enum": ["internal", "external"],
                    "description": "internal = the organisation's own model; external = a third-party AI service."},
    "purpose": {"type": "string", "enum": PURPOSES, "description": "What the message is for."},
    "pack": {"type": "string", "enum": list(PACKS), "default": "default"},
    "session_id": {"type": "string", "default": "mcp",
                   "description": "Same id across calls keeps placeholders stable and lets the attacker see earlier messages."},
}
REQUIRED = ["text", "role", "destination", "purpose"]
TOOLS = [
    {"name": "chaperone_check",
     "description": "Dry run. Shows what would leave for this flow (placeholders, vague wording, omitted identifiers) and "
                    "what a local attacker could still infer. Nothing is sent anywhere.",
     "inputSchema": {"type": "object", "properties": FLOW_ARGS, "required": REQUIRED}},
    {"name": "chaperone_send",
     "description": "Send through Chaperone: the protected text goes to the flow's model, the reply comes back with real "
                    "values restored locally. Refuses to send if the local attacker is not cleared.",
     "inputSchema": {"type": "object", "properties": FLOW_ARGS, "required": REQUIRED}},
]


class BadArgs(ValueError):
    pass


def _flow(args: dict) -> Flow:
    for key in REQUIRED:
        if not isinstance(args.get(key), str) or not args[key]:
            raise BadArgs(f"missing argument: {key}")
    allowed = {"role": ROLES, "destination": ["internal", "external"], "purpose": PURPOSES}
    for key, values in allowed.items():
        if args[key] not in values:
            raise BadArgs(f"{key} must be one of {values}")
    if len(args["text"]) > MAX_TEXT:
        raise BadArgs(f"text is longer than {MAX_TEXT} characters")
    pack = args.get("pack", "default")
    if pack not in PACKS:
        raise BadArgs(f"pack must be one of {list(PACKS)}")
    return Flow(args["role"], args["destination"], args["purpose"], pack)


# what changed and why, without echoing the raw values back into the agent's transcript
def _summary(r: dict) -> dict:
    return {
        "outbound": r["outbound"],
        "blocked": r["blocked"],
        "block_reason": r["block_reason"] and r["block_reason"]["why"],
        "changes": [{"label": s["label"], "action": s["action"], "rule": s["rule"], "sent_as": s["replacement"]}
                    for s in r["spans"] if s["action"] != "pass"],
        "attacker": {"rounds": len(r["attack"]["rounds"]),
                     "still_inferable": [i["guess"] for i in r["attack"]["unresolved"]],
                     "note": "No inference found by the local check is not a guarantee."},
    }


def call(name: str, args: dict) -> dict:
    flow, session = _flow(args), str(args.get("session_id") or "mcp")
    if name == "chaperone_check":
        r = gateway.analyze(args["text"], flow, gateway.Vault())
        r.pop("protected")
        return _summary(r)
    if name == "chaperone_send":
        r = gateway.chat(args["text"], flow, f"mcp:{session}")
        return {**_summary(r), "sent": r["sent"], "error": r["error"], "reply": r["restored"],
                "flags": [{"text": f["text"], "reason": f["reason"]} for f in r["flags"]]}
    raise BadArgs(f"unknown tool: {name}")


def handle(msg: dict) -> dict | None:
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return None  # a notification, e.g. notifications/initialized
    if method == "initialize":
        result: dict = {"protocolVersion": msg.get("params", {}).get("protocolVersion", PROTOCOL),
                        "capabilities": {"tools": {}}, "serverInfo": {"name": "chaperone", "version": "2.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = msg.get("params", {})
        try:
            out, failed = call(params.get("name", ""), params.get("arguments") or {}), False
        except BadArgs as exc:
            out, failed = {"error": str(exc)}, True
        result = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}], "isError": failed}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main() -> None:
    out, sys.stdout = sys.stdout, sys.stderr  # model loaders print; only JSON-RPC may reach the client
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            reply = handle(json.loads(line))
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        if reply is not None:
            out.write(json.dumps(reply, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
