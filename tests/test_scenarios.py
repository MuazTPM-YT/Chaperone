# demo scenarios 1-7, full stack: regex + GLiNER + local context LLM (needs Ollama running)
import json
from pathlib import Path

import pytest

from flowguard import gateway
from flowguard.policy import Flow

SCENARIOS = json.loads((Path(gateway.__file__).parent / "scenarios.json").read_text())


@pytest.mark.parametrize("sc", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_scenario(sc, llm):
    r = gateway.chat(sc["text"], Flow(sc["role"], sc["destination"], sc["purpose"]), f"s-{sc['id']}")
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
