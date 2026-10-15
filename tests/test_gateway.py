import json

import pytest

from chaperone import gateway
from chaperone.policy import Flow
from chaperone.transform import OutboundLeak, Vault, guard, restore

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


def test_flow_change_mid_conversation_does_not_stall_it(llm):
    # scheduling sends the name as typed; the next flow masks it. The raw name already sits in the history,
    # so re-guarding the history against it used to refuse every later message.
    gateway.chat("Book a call with Priya Sharma on Friday.", Flow("Manager", "external", "scheduling"), "s1",
                 use_context=False)
    b = gateway.chat("Write a thank-you note to Priya Sharma.", EXTERNAL, "s1", use_context=False)
    c = gateway.chat("Make it shorter.", EXTERNAL, "s1", use_context=False)
    assert b["outbound"] == "Write a thank-you note to [PERSON_1]."
    assert b["sent"] and c["sent"] and len(llm.calls) == 3


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


def test_first_name_alone_gets_the_full_names_placeholder(llm):
    r = gateway.chat("Rohan Deshpande joined in May. Rohan's car is in the visitor slot.", EXTERNAL, "s1",
                     use_context=False)
    assert "Rohan" not in r["outbound"]
    assert r["outbound"].count("[PERSON_1]") == 2
    assert restore("Tell [PERSON_1] to move it.", gateway.vault_for("s1", "external"))[0] == "Tell Rohan Deshpande to move it."


def test_placeholders_follow_reading_order(llm):
    r = gateway.chat("Ward round: Ramesh Rao, Sunita Rao and Kiran Patil need discharge notes.", EXTERNAL, "s1",
                     use_context=False)
    assert r["outbound"].startswith("Ward round: [PERSON_1], [PERSON_2] and [PERSON_3]")


def test_message_length_is_bounded():
    from fastapi.testclient import TestClient

    from chaperone.app import MAX_TEXT, app

    client = TestClient(app)
    body = {"session_id": "s", "role": "Manager", "destination": "external", "purpose": "general"}
    assert client.post("/api/chat", json={**body, "text": "x" * (MAX_TEXT + 1)}).status_code == 422
    assert client.post("/api/chat", json={**body, "text": ""}).status_code == 422


def test_prompt_names_bracket_rules_only_when_brackets_were_sent():
    # the 3B model copied "[health detail]" and "(Type and Number)" from a prompt that named them
    assert "bracket" not in gateway.system_prompt("Move the 1:1 with Priya to Friday.")
    assert "placeholders" in gateway.system_prompt("Invoice to [PERSON_1].")
    assert "vague" in gateway.system_prompt("On leave for [health detail].")
    assert "vague" not in gateway.system_prompt("Invoice to [PERSON_1].")


DISCHARGE = "Patient Ramesh Rao admitted with chest pain. Wife Sunita Rao can be reached at 98450 12345. Summarise."
CLINIC = Flow("Doctor", "external", "clinical_summary")


def test_purpose_omits_what_the_task_does_not_need(llm):
    r = gateway.chat(DISCHARGE, CLINIC, "s-p1", use_context=False)
    assert "[PHONE omitted]" in r["outbound"] and "98450" not in r["outbound"]
    assert [s["rule"] for s in r["spans"] if s["label"] == "PHONE"] == ["purpose-minimisation"]
    invoice = gateway.chat("Bill Suresh Kumar, PAN ABKPS7312M, for the audit.", Flow("Accountant", "external", "invoicing"),
                           "s-p2", use_context=False)
    assert "[PAN_1]" in invoice["outbound"]  # an invoice needs the PAN


def test_include_anyway_needs_a_reason_and_is_logged_without_raw_values(llm):
    reason = "Ward clerk Ravi Kumar needs the contact on the note"
    r = gateway.chat(DISCHARGE, CLINIC, "s-p3", use_context=False,
                     include=[{"label": "PHONE", "text": "98450 12345", "reason": reason}])
    assert "[PHONE_1]" in r["outbound"] and r["overrides"][0]["label"] == "PHONE"
    log = gateway.AUDIT_PATH.read_text()
    assert "98450" not in log and "Ravi" not in log and "needs the contact on the note" in log


def test_compare_runs_one_message_through_several_flows_without_sending(llm):
    from fastapi.testclient import TestClient

    from chaperone.app import app

    r = TestClient(app).post("/api/compare", json={"text": DISCHARGE, "use_context": False}).json()
    assert [x["flow"]["role"] + "/" + x["flow"]["destination"] for x in r["runs"]] == [
        "Doctor/internal", "Doctor/external", "Intern/external"]
    assert "Ramesh Rao" in r["runs"][0]["outbound"] and "Ramesh Rao" not in r["runs"][1]["outbound"]
    assert llm.calls == [] and gateway.SESSIONS == {}


def test_processing_record_lists_categories_and_no_raw_values(llm):
    gateway.chat(DISCHARGE, CLINIC, "s-rec", use_context=False)
    rows = gateway.processing_record().splitlines()
    assert rows[0].startswith("time_utc,conversation,sender_role") and len(rows) == 2
    assert "Doctor,external,clinical_summary,default,True,False" in rows[1] and "PERSON" in rows[1]
    assert "Ramesh" not in rows[1] and "98450" not in rows[1]


def test_steps_are_reported_in_pipeline_order(llm):
    llm.reply = "Noted for [PERSON_1]."
    steps = []
    r = gateway.chat(DISCHARGE, CLINIC, "s-st", use_context=False, on_step=lambda step, data: steps.append((step, data)))
    assert [s for s, _ in steps] == ["detect", "decide", "attack", "ready", "guard", "reply", "restore"]
    data = dict(steps)
    assert {"label": "PHONE", "text": "98450 12345"} in [{k: i[k] for k in ("label", "text")} for i in data["detect"]["items"]]
    assert data["decide"]["counts"]["omit"] == 1 and data["attack"]["skipped"] == "local AI unavailable"
    assert data["ready"]["outbound"] == r["outbound"] and data["reply"]["reply"] == "Noted for [PERSON_1]."
    assert data["restore"]["restored"] == r["restored"] == "Noted for Ramesh Rao."


def test_guard_refusal_ends_the_steps_before_sending(monkeypatch, llm):
    real_apply = gateway.apply
    monkeypatch.setattr(gateway, "apply", lambda text, *a: (text, real_apply(text, *a)[1]))
    steps = []
    gateway.chat(f"Aadhaar {AADHAAR} is wrong.", EXTERNAL, "s-g", use_context=False,
                 on_step=lambda step, data: steps.append(step))
    assert steps == ["detect", "decide", "attack", "ready"] and llm.calls == []


def test_stream_endpoint_sends_steps_then_the_full_result(llm):
    from fastapi.testclient import TestClient

    from chaperone.app import app

    body = {"session_id": "s-http", "text": DISCHARGE, "role": "Doctor", "destination": "external",
            "purpose": "clinical_summary", "use_context": False}
    with TestClient(app).stream("POST", "/api/chat/stream", json=body) as res:
        assert res.headers["content-type"].startswith("application/x-ndjson")
        events = [json.loads(line) for line in res.iter_lines() if line]
    assert [e["step"] for e in events] == ["detect", "decide", "attack", "ready", "guard", "reply", "restore", "result"]
    result = events[-1]["result"]
    assert result["sent"] and "98450" not in result["outbound"] and result["spans"]
