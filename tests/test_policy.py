import json
import os
import shutil

import pytest
import yaml
from fastapi.testclient import TestClient

from chaperone import app as app_module
from chaperone import gateway, policy, purpose
from chaperone.policy import Flow, PolicyError, decide

MANAGER_OUT = Flow("Manager", "external", "general")


def own(pack: str = "default") -> list[dict]:
    return [dict(r) for r in policy.current().packs[pack].own]


def client() -> TestClient:
    return TestClient(app_module.app, base_url="http://127.0.0.1")


# ---------- the shipped files are the single source of truth ----------

def test_roles_purposes_and_packs_come_from_the_rule_files():
    p = policy.current()
    assert p.roles == ("Manager", "HR", "Sales", "Intern", "Doctor", "Accountant")
    assert list(p.purposes) == ["general", "scheduling", "hr_summary", "marketing", "clinical_summary", "invoicing"]
    assert p.purposes["hr_summary"]["label"] == "HR summary"
    assert set(p.packs) == {"default", "safe_harbor"} and p.packs["safe_harbor"].name == "HIPAA Safe Harbor mode"
    assert p.packs["safe_harbor"].rules[-1]["id"] == "default-cautious" and p.error == ""


# ---------- a bad rule is refused with a reason, never applied ----------

@pytest.mark.parametrize("bad, reason", [
    ({"id": "x-1", "when": {"colour": "red"}, "action": "pass", "why": "w"}, "unknown condition"),
    ({"id": "x-1", "when": {"label": "SALARY"}, "action": "pass", "why": "w"}, "SALARY"),
    ({"id": "x-1", "when": {"role": "CEO"}, "action": "pass", "why": "w"}, "CEO"),
    ({"id": "x-1", "when": {"label": "PAN"}, "action": "allow", "why": "w"}, "action"),
    ({"id": "x-1", "when": {"label": "PAN"}, "action": "pass", "scope": "request", "why": "w"}, "whole message"),
    ({"id": "x-1", "when": {"label": "DATE"}, "action": "pass", "coarse": "year", "why": "w"}, "made vague"),
    ({"id": "x-1", "when": {"label": "PAN"}, "action": "pass", "why": ""}, "reason"),
    ({"id": "Bad Id", "when": {"label": "PAN"}, "action": "pass", "why": "w"}, "id"),
    ({"id": "x-1", "action": "pass", "why": "w"}, "matches everything"),
    ({"id": "x-1", "when": {}, "action": "pass", "why": "w"}, "matches everything"),
])
def test_bad_rules_are_refused_with_a_reason(bad, reason):
    with pytest.raises(PolicyError, match=reason):
        policy.validate_edit("default", [bad, *own()], None)


def test_duplicate_ids_and_a_missing_catch_all_are_refused():
    rules = own()
    with pytest.raises(PolicyError, match="used twice"):
        policy.validate_edit("default", [rules[0], *rules], None)
    with pytest.raises(PolicyError, match="catch-all"):
        policy.validate_edit("default", rules[:-1], None)


def test_purposes_may_leave_out_identifiers_only():
    with pytest.raises(PolicyError, match="HEALTH"):
        policy.validate_edit("default", own(), {"general": {"omit": ["HEALTH"]}})


# ---------- edits apply at once, are kept apart from the shipped files, and can be undone ----------

def test_an_edit_applies_without_restart_and_reset_restores_the_shipped_rules():
    assert decide("PAN", "individual", MANAGER_OUT).action == "pseudonymize"
    rule = {"id": "pan-blocked", "when": {"label": "PAN", "destination": "external"}, "action": "block", "why": "Test."}
    policy.save_local("default", [rule, *own()], None)
    assert decide("PAN", "individual", MANAGER_OUT).rule == "pan-blocked"
    assert policy.current().packs["default"].edited
    assert "pan-blocked" not in policy.DEFAULT_PATH.read_text()  # the shipped file is never written
    policy.reset_local("default")
    assert decide("PAN", "individual", MANAGER_OUT).action == "pseudonymize"
    assert not policy.LOCAL_PATH.exists()


def test_purpose_edits_change_what_is_left_out():
    assert not purpose.omits("general", "PHONE")
    policy.save_local("default", own(), {"general": {"omit": ["PHONE"]}})
    assert purpose.omits("general", "PHONE")


def test_a_broken_file_on_disk_keeps_the_last_good_rules_and_says_why():
    policy.current()
    policy.LOCAL_PATH.parent.mkdir(exist_ok=True)
    policy.LOCAL_PATH.write_text("default:\n  rules:\n    - {id: x, action: allow}\n")
    later = os.stat(policy.LOCAL_PATH).st_mtime_ns + 10**9
    os.utime(policy.LOCAL_PATH, ns=(later, later))  # same-second writes must still count as a change
    p = policy.current()
    assert "data/policies.local.yaml" in p.error and decide("PAN", "individual", MANAGER_OUT).action == "pseudonymize"


def test_a_preview_never_leaks_into_real_decisions():
    rule = {"id": "pan-pass", "when": {"label": "PAN"}, "action": "pass", "why": "Test."}
    with policy.preview("default", [rule, *own()], None):
        assert decide("PAN", "individual", MANAGER_OUT).rule == "pan-pass"
    assert decide("PAN", "individual", MANAGER_OUT).action == "pseudonymize"


# ---------- the HTTP side: read for everyone, write for admins, every change sealed in the log ----------

def test_anyone_can_read_the_rules():
    body = client().get("/api/policies").json()
    assert [p["id"] for p in body["packs"]] == ["default", "safe_harbor"]
    assert body["admin"] is False and "PERSON" in body["vocabulary"]["label"]


def test_editing_needs_admin_mode():
    c = client()
    assert c.put("/api/policies/default", json={"rules": own()}).status_code == 403
    assert c.delete("/api/policies/default").status_code == 403
    assert c.post("/api/policies/preview", json={"pack": "default", "rules": own(), "text": "Hi",
                                                  "role": "Manager", "destination": "external",
                                                  "purpose": "general"}).status_code == 403
    assert not policy.LOCAL_PATH.exists()


def test_admin_edit_is_validated_saved_and_sealed_in_the_audit_log(monkeypatch):
    monkeypatch.setattr(app_module, "ADMIN", True)
    c = client()
    bad = c.put("/api/policies/default", json={"rules": [{"id": "x-1", "action": "pass", "why": "w"}, *own()]})
    assert bad.status_code == 422 and "matches everything" in bad.json()["detail"]
    rule = {"id": "pan-blocked", "when": {"label": "PAN"}, "action": "block", "why": "Test."}
    ok = c.put("/api/policies/default", json={"rules": [rule, *own()]})
    assert ok.status_code == 200 and ok.json()["packs"][0]["edited"] is True
    assert c.delete("/api/policies/default").status_code == 200
    events = [json.loads(line) for line in gateway.AUDIT_PATH.read_text().splitlines()]
    assert [e["event"] for e in events] == ["policy_change", "policy_reset"]
    assert events[0]["before"] != events[0]["after"] and events[1]["after"] == events[0]["before"]
    assert gateway.verify_log()["ok"] and gateway.processing_record().count("\n") == 1  # header only


def test_preview_runs_both_rule_sets_without_sending_or_saving(monkeypatch, llm):
    monkeypatch.setattr(app_module, "ADMIN", True)
    rule = {"id": "pan-pass", "when": {"label": "PAN"}, "action": "pass", "why": "Test."}
    r = client().post("/api/policies/preview", json={
        "pack": "default", "rules": [rule, *own()], "text": "Bill Suresh Kumar, PAN ABKPS7312M.",
        "role": "Accountant", "destination": "external", "purpose": "invoicing", "use_context": False}).json()
    assert "[PAN_1]" in r["before"]["outbound"] and "ABKPS7312M" in r["after"]["outbound"]
    assert llm.calls == [] and not policy.LOCAL_PATH.exists() and "protected" not in r["after"]


def test_requests_for_another_host_are_refused():
    # a web page that rebinds its own domain to 127.0.0.1 still sends its own Host header
    assert TestClient(app_module.app, base_url="http://evil.example").get("/api/policies").status_code == 400


def test_local_file_is_plain_yaml_an_admin_can_read():
    rule = {"id": "pan-blocked", "when": {"label": "PAN"}, "action": "block", "why": "Test."}
    policy.save_local("default", [rule, *own()], None)
    saved = yaml.safe_load(policy.LOCAL_PATH.read_text())
    assert saved["default"]["rules"][0]["id"] == "pan-blocked"


def test_a_new_rule_file_is_a_new_rule_set(monkeypatch, tmp_path):
    for f in ("policies.yaml", "policies_safe_harbor.yaml"):
        shutil.copy(policy.HERE / f, tmp_path / f)
    (tmp_path / "policies_strict.yaml").write_text(
        "name: Strict\nextends: policies.yaml\nrules:\n"
        "  - {id: names-blocked, when: {label: PERSON}, action: block, why: No names leave.}\n")
    monkeypatch.setattr(policy, "HERE", tmp_path)
    monkeypatch.setattr(policy, "DEFAULT_PATH", tmp_path / "policies.yaml")
    assert policy.current().packs["strict"].name == "Strict"
    assert decide("PERSON", "individual", Flow("Manager", "external", "general", "strict")).rule == "names-blocked"
