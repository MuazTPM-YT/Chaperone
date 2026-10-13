import json

from flowguard import gateway, mcp_server

ARGS = {"text": "Ask Ravi to call me.", "role": "Manager", "destination": "external", "purpose": "general"}


def rpc(method, params=None, mid=1):
    return mcp_server.handle({"jsonrpc": "2.0", "id": mid, "method": method, "params": params or {}})


def test_handshake_and_tool_list():
    init = rpc("initialize", {"protocolVersion": "2025-06-18"})["result"]
    assert init["protocolVersion"] == "2025-06-18" and "tools" in init["capabilities"]
    assert mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    names = [t["name"] for t in rpc("tools/list")["result"]["tools"]]
    assert names == ["flowguard_check", "flowguard_send"]
    assert rpc("nope")["error"]["code"] == -32601


def test_bad_flow_is_a_tool_error_not_a_crash():
    r = rpc("tools/call", {"name": "flowguard_check", "arguments": {**ARGS, "destination": "pastebin"}})["result"]
    assert r["isError"] and "destination must be one of" in r["content"][0]["text"]


def test_check_summary_never_echoes_raw_values(monkeypatch):
    fake = {"outbound": "Ask [PERSON_1] to call me.", "blocked": False, "block_reason": None, "protected": ["Ravi"],
            "spans": [{"label": "PERSON", "action": "pseudonymize", "rule": "personal-ids-external",
                       "replacement": "[PERSON_1]", "text": "Ravi"}],
            "attack": {"rounds": [], "unresolved": []}}
    monkeypatch.setattr(gateway, "analyze", lambda *a, **k: dict(fake))
    r = rpc("tools/call", {"name": "flowguard_check", "arguments": ARGS})["result"]
    out = json.loads(r["content"][0]["text"])
    assert not r["isError"] and out["outbound"] == "Ask [PERSON_1] to call me."
    assert out["changes"] == [{"label": "PERSON", "action": "pseudonymize", "rule": "personal-ids-external",
                               "sent_as": "[PERSON_1]"}]
    assert "Ravi" not in r["content"][0]["text"]
