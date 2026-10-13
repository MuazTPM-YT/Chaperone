import json

import pytest

from flowguard import gateway
from flowguard.policy import Flow
from flowguard.transform import OutboundLeak, Vault, guard, restore

EXTERNAL = Flow("Manager", "external", "general")
AADHAAR = "7260 1815 9082"


def test_guard_catches_respaced_and_cased_values():
    for payload in ("id 726018159082", "id 7260-1815-9082", "dear SURESH KUMAR"):
        with pytest.raises(OutboundLeak):
            guard(payload, [AADHAAR, "Suresh Kumar"])
    guard("id [AADHAAR_1], dear [PERSON_1]", [AADHAAR, "Suresh Kumar"])  # clean payload passes


def test_guard_stops_a_leak_before_any_network_call(monkeypatch, llm):
    # simulate a transform bug: spans detected, but the text goes out untouched
    real_apply = gateway.apply
    monkeypatch.setattr(gateway, "apply", lambda text, *a: (text, real_apply(text, *a)[1]))
    r = gateway.chat(f"Customer Aadhaar {AADHAAR} needs a KYC update.", EXTERNAL, "s1", use_context=False)
    assert llm.calls == []
    assert r["sent"] is False and "guard refused" in r["error"]


def test_session_history_is_guarded_too(llm):
    gateway.chat(f"Customer Aadhaar {AADHAAR} needs a KYC update.", EXTERNAL, "s1", use_context=False)
    gateway.chat("Draft the reply.", EXTERNAL, "s1", use_context=False)
    sent = json.dumps(llm.calls, ensure_ascii=False)
    assert "[AADHAAR_1]" in sent and "7260" not in sent


def test_pseudonyms_are_consistent_and_sticky_per_destination(llm):
    a = gateway.chat(f"Aadhaar {AADHAAR} is wrong.", EXTERNAL, "s1", use_context=False)
    b = gateway.chat("Recheck 726018159082 please.", EXTERNAL, "s1", use_context=False)
    assert "[AADHAAR_1]" in a["outbound"] and "[AADHAAR_1]" in b["outbound"]
    internal = gateway.chat("Recheck 726018159082 please.", Flow("Manager", "internal", "general"), "s1",
                            use_context=False)
    assert "726018159082" in internal["outbound"]  # internal vault is separate


def test_restore_tolerates_mangled_placeholders():
    v = Vault()
    p1 = v.placeholder("PERSON", "Ramesh Rao")
    v.placeholder("PERSON", "Sunita Rao")
    reply = f"{p1} was treated. person_2 was informed. PERSON 1's wife is [Person_2]. {p1}'s ECG ok."
    out, stats = restore(reply, v)
    assert out == ("Ramesh Rao was treated. Sunita Rao was informed. Ramesh Rao's wife is Sunita Rao. "
                   "Ramesh Rao's ECG ok.")
    assert stats == {"exact": 2, "fuzzy": 3}


def test_restore_does_not_confuse_1_and_10():
    v = Vault()
    for n in range(10):
        v.placeholder("PERSON", f"Name{n}")
    out, _ = restore("[PERSON_10] and [PERSON_1]", v)
    assert out == "Name9 and Name0"


def test_audit_log_holds_no_raw_values(llm):
    gateway.chat(f"Suresh Kumar, Aadhaar {AADHAAR}, PAN ABKPS7312M", EXTERNAL, "s1", use_context=False)
    log = gateway.AUDIT_PATH.read_text()
    for raw in ("Suresh", "7260", "ABKPS7312M"):
        assert raw not in log
    rec = json.loads(log)
    assert {d["rule"] for d in rec["decisions"]} == {"personal-ids-external"}
    assert all(len(d["value_hmac"]) == 16 for d in rec["decisions"])


def test_example_audit_key_is_rejected(monkeypatch, llm):
    monkeypatch.setenv("AUDIT_HMAC_KEY", "change-me")
    with pytest.raises(RuntimeError, match="AUDIT_HMAC_KEY"):
        gateway.chat("hello", EXTERNAL, "s1", use_context=False)
