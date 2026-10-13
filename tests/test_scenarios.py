# demo scenarios 1-7, full stack: regex + GLiNER + local context LLM (needs Ollama running)
import json
import re
from pathlib import Path

import pytest

from flowguard import gateway
from flowguard.policy import Flow

SCENARIOS = json.loads((Path(gateway.__file__).parent / "scenarios.json").read_text())


@pytest.mark.parametrize("sc", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_scenario(sc, llm):
    r = gateway.chat(sc["text"], Flow(sc["role"], sc["destination"], sc["purpose"], sc.get("pack", "default")), f"s-{sc['id']}")
    assert r["context_ok"], r["context_error"]
    exp = sc["expect"]
    assert r["blocked"] == exp["blocked"]
    if exp["blocked"]:
        assert r["block_reason"]["rule"] == exp["block_rule"]
        assert llm.calls == []
        return
    if exp.get("unchanged"):
        assert r["outbound"] == sc["text"], "this flow should send the message exactly as typed"
    for s in exp["sent_contains"]:
        assert s in r["outbound"]
    for s in exp["sent_excludes"]:
        assert s not in r["outbound"]
    for label in exp.get("labels", []):
        assert label in {s["label"] for s in r["spans"]}
    assert llm.calls[0]["messages"][-1]["content"] == r["outbound"]  # UI shows exactly what was sent


def test_patient_summary_comes_back_with_real_names(llm):
    llm.reply = "Discharge: [PERSON_1], in their 50s, chest pain, diabetes. Inform PERSON_2 (wife) at [PHONE_1]."
    sc = next(s for s in SCENARIOS if s["id"] == "7")
    r = gateway.chat(sc["text"], Flow(sc["role"], sc["destination"], sc["purpose"]), "s7")
    assert "Ramesh Rao" not in r["outbound"]
    assert r["restored"] == "Discharge: Ramesh Rao, in their 50s, chest pain, diabetes. Inform Sunita Rao (wife) at 98450 12345."


# a 1,274-character paste: the model reads it in windows, and first names alone stay masked
def test_long_pasted_minutes_do_not_leak(llm):
    sc = next(s for s in json.loads((Path(gateway.__file__).parent / "scenarios_worst.json").read_text()) if s["id"] == "w3")
    r = gateway.chat(sc["text"], Flow(sc["role"], sc["destination"], sc["purpose"]), "s-w3")
    assert not r["blocked"], r["block_reason"]
    for leak in ("Rohan", "Gurpreet", "Meenakshi", "Ayesha", "24 LPA", "performance improvement plan"):
        assert leak not in r["outbound"], leak


# W0: the vague age and date go out, the exact ones come back, and an invented age is flagged
def test_discharge_round_trip_restores_exact_values_and_flags_invention(llm):
    sc = next(s for s in SCENARIOS if s["id"] == "7")

    def echo_tokens(body):
        sent = body["messages"][-1]["content"]
        age = re.search(r"\[AGE_1[^\]]*\]", sent).group()
        when = re.search(r"\[DATE_1[^\]]*\]", sent).group()
        return f"[PERSON_1] ({age}) was admitted on {when}. A 50-year-old male, stable."
    llm.reply = echo_tokens
    r = gateway.chat(sc["text"], Flow(sc["role"], sc["destination"], sc["purpose"]), "s7rt")
    assert "54-year-old" not in r["outbound"] and "12 March 2026" not in r["outbound"]
    assert "[AGE_1: in their 50s]" in r["outbound"] and "[DATE_1: March 2026]" in r["outbound"]
    assert r["restored"].startswith("Ramesh Rao (54-year-old) was admitted on 12 March 2026.")
    assert [(f["kind"], f["text"]) for f in r["flags"]] == [("age", "50-year-old")]


# W1 live: an identifier-only cloak leaks the diagnosis through the medicine; our outbound does not
def test_attacker_sees_through_identifier_only_masking():
    sc = next(s for s in SCENARIOS if s["id"] == "8a")
    base = gateway.baseline(sc["text"], Flow(sc["role"], sc["destination"], sc["purpose"]))
    assert "tamoxifen" in base["outbound"]
    assert any(i["category"] == "HEALTH" for i in base["inferences"])
