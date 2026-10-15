import json

from fastapi.testclient import TestClient

from chaperone import gateway
from chaperone.app import app
from chaperone.policy import Flow

EXTERNAL = Flow("Manager", "external", "general")
INTERNAL = Flow("Manager", "internal", "general")


def test_person_report_finds_every_request_that_carried_them(llm):
    gateway.chat("Suresh Kumar, Aadhaar 7260 1815 9082, needs a KYC update.", EXTERNAL, "s1", use_context=False)
    gateway.chat("Recheck 726018159082 please.", INTERNAL, "s1", use_context=False)
    gateway.chat("Kavita Rao, phone 98450 12345, asked for a call.", EXTERNAL, "s2", use_context=False)

    r = gateway.person_report("7260-1815-9082")  # written another way: same person
    assert r["matches"] == 2
    ext, inside = r["rows"]
    assert ext["flow"]["destination"] == "external" and ext["items"][0]["action"] == "pseudonymize"
    assert ext["items"][0]["placeholder"] == "[AADHAAR_1]" and ext["recipient"]["host"] == "llm.invalid"
    assert inside["items"][0]["action"] == "pass"
    assert gateway.person_report("suresh  KUMAR")["matches"] == 1
    assert gateway.person_report("Nobody Here")["matches"] == 0
    assert "Kavita" not in json.dumps(r) and "98450" not in json.dumps(r)


def test_first_name_alone_counts_for_the_full_name(llm):
    gateway.chat("Rohan Deshpande joined in May. Rohan's car is in the visitor slot.", EXTERNAL, "s1",
                 use_context=False)
    rows = gateway.person_report("Rohan Deshpande")["rows"]
    assert len(rows) == 1 and len(rows[0]["items"]) == 2


def test_seal_finds_an_edited_or_removed_line(llm):
    for text in ("Aadhaar 7260 1815 9082 is wrong.", "Call 98450 12345.", "Hello there."):
        gateway.chat(text, EXTERNAL, "s1", use_context=False)
    good = gateway.verify_log()
    assert good["ok"] and good["chained"] == 3 and good["legacy"] == 0 and len(good["head"]) == 16

    lines = gateway.AUDIT_PATH.read_text().splitlines()
    gateway.AUDIT_PATH.write_text("\n".join([lines[0], lines[1].replace('"blocked": false', '"blocked": true'),
                                             lines[2]]) + "\n")
    assert gateway.verify_log()["broken_at"] == 2

    gateway.AUDIT_PATH.write_text("\n".join([lines[0], lines[2]]) + "\n")
    assert gateway.verify_log()["broken_at"] == 2

    gateway.AUDIT_PATH.write_text("\n".join([lines[1], lines[0], lines[2]]) + "\n")
    assert gateway.verify_log()["broken_at"] == 1


def test_lines_from_before_the_seal_are_counted_not_trusted(llm):
    gateway.AUDIT_PATH.write_text(json.dumps({"ts": "old", "decisions": []}) + "\n")
    gateway.chat("Hello there.", EXTERNAL, "s1", use_context=False)
    r = gateway.verify_log()
    assert r["ok"] and r["legacy"] == 1 and r["chained"] == 1
    with gateway.AUDIT_PATH.open("a") as f:
        f.write(json.dumps({"ts": "slipped in", "decisions": []}) + "\n")
    assert gateway.verify_log()["broken_at"] == 3


def test_report_and_seal_endpoints(llm):
    gateway.chat("Suresh Kumar needs a KYC update.", EXTERNAL, "s1", use_context=False)
    client = TestClient(app, base_url="http://127.0.0.1")
    r = client.post("/api/person-report", json={"value": "Suresh Kumar"}).json()
    assert r["matches"] == 1 and r["log"]["ok"]
    assert client.post("/api/person-report", json={"value": "x"}).status_code == 422
    assert client.get("/api/audit/verify").json()["chained"] == 1
