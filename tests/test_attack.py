from dataclasses import replace

import pytest

from chaperone import attack, gateway
from chaperone.attack import Inference, _verified
from chaperone.detect import detect
from chaperone.policy import Flow
from chaperone.transform import Vault

TEAM = Flow("Manager", "external", "general")
NOTE = "Draft a note to the team: Priya is on leave for three weeks, she has started letrozole and will be back soon."


def test_fabricated_and_token_only_evidence_is_dropped():
    text = "[PERSON_1] is on leave; she started [HEALTH_1: a health matter] and takes letrozole."
    kept, in_current = _verified(["letrozole", "chemotherapy", "[PERSON_1]", "a health matter"], text, "")
    assert kept == ["letrozole"] and in_current  # made-up quote, a bare placeholder and our own vague words are not evidence


def test_forbidden_follows_the_flow_policy():
    assert "HEALTH" in attack.forbidden_categories(TEAM)
    assert "HEALTH" not in attack.forbidden_categories(Flow("Doctor", "external", "clinical_summary"))
    assert "IDENTITY" not in attack.forbidden_categories(Flow("Manager", "external", "scheduling"))


@pytest.fixture
def no_context_layer(monkeypatch):
    # the context layer would already blur the drug name; these tests are about the attacker loop
    monkeypatch.setattr(gateway, "detect_cached", lambda text, use_context=True, model=None:
                        replace(detect(text, use_context=False), context_ok=True))


def test_loop_tightens_only_the_evidence_then_clears(monkeypatch, no_context_layer):
    calls = []

    def fake(current, earlier, flow, model=None):
        calls.append(current)
        if "letrozole" in current:
            return [Inference("HEALTH", "breast cancer", 0.9, ["letrozole"], forbidden=True, rule="sensitive-need-to-know")]
        return []
    monkeypatch.setattr(attack, "attack", fake)
    r = gateway.analyze(NOTE, TEAM, Vault())
    assert not r["blocked"] and "letrozole" not in r["outbound"] and "will be back soon" in r["outbound"]
    assert len(r["attack"]["rounds"]) == 2 and r["attack"]["rounds"][0]["tightened"] == ["letrozole"]
    assert any(s["rule"] == "attacker-tighten" for s in r["spans"])


def test_message_that_cannot_be_cleared_is_not_sent(monkeypatch, llm, no_context_layer):
    stubborn = [Inference("HEALTH", "breast cancer", 0.9, ["on leave for three weeks"], forbidden=True, rule="x")]
    monkeypatch.setattr(attack, "attack", lambda *a, **k: list(stubborn))
    r = gateway.chat(NOTE, TEAM, "s-stubborn")
    assert [x["tightened"] for x in r["attack"]["rounds"]] == [["on leave for three weeks"], ["on leave for three weeks"], []]
    assert any(s["rule"] == "attacker-block" for s in r["spans"])
    assert r["blocked"] and r["block_reason"]["rule"] == "attacker-not-cleared"
    assert len(r["attack"]["rounds"]) == attack.MAX_ROUNDS + 1 and llm.calls == []


def test_health_proxy_is_not_dropped_by_a_word_check(monkeypatch):
    # the 3B model calls "ART centre" not health-related; that answer must not veto a specific, cited inference
    def model_says(model, question, options):
        return "specific" if "specific or vague" in question else options[-1]
    monkeypatch.setattr(attack, "_choice", model_says)
    text = "Tell the team [PERSON_1] will collect his monthly refill from the ART centre on the first Friday."
    assert attack._confirmed("m", text, Inference("HEALTH", "HIV", 0.8, ["ART centre"]))
    assert not attack._confirmed("m", text, Inference("HEALTH", "parental leave", 0.8, ["leave"]))
    assert not attack._confirmed("m", text, Inference("HEALTH", "no specific health condition", 0.8, ["refill"]))


def test_schedule_words_alone_are_not_health_evidence():
    assert attack._ordinary("on leave for three weeks") and attack._ordinary("started")
    assert not attack._ordinary("ART centre") and not attack._ordinary("every Saturday at NIMHANS")
