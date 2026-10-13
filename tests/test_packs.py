import subprocess
from pathlib import Path

from flowguard import gateway
from flowguard.detect import deterministic
from flowguard.policy import Flow, decide, load
from flowguard.transform import Vault

NOTE = ("Patient Ramesh Rao, 54-year-old male from Udupi, admitted on 12 March 2026, MRN: KMC-88213. "
        "His father, aged 93, visited. Records at https://records.example.com/p/88213 from 10.0.4.17.")
HARBOR = Flow("Doctor", "external", "clinical_summary", "safe_harbor")


def test_safe_harbor_dates_to_year_ages_over_89_grouped():
    r = gateway.analyze(NOTE, HARBOR, Vault(), use_context=False)
    out = r["outbound"]
    assert "[DATE_1: 2026]" in out and "12 March" not in out
    assert "54-year-old" in out  # ages up to 89 may stay
    assert "[AGE_1: 90 or older]" in out and "93" not in out
    for raw in ("Ramesh", "Udupi", "KMC-88213", "records.example.com", "10.0.4.17"):
        assert raw not in out, raw


def test_pack_runs_first_and_falls_through_to_the_base_rules():
    rules = [r["id"] for r in load(Path(__file__).parent.parent / "flowguard" / "policies_safe_harbor.yaml")]
    assert rules[0] == "hipaa-a-names" and rules[-1] == "default-cautious"
    assert decide("MNPI", "individual", Flow("Manager", "external", "general", "safe_harbor")).rule == "mnpi-never-external"


def test_new_identifier_detectors_take_only_the_number():
    found = {(s.label, s.text) for s in deterministic("MRN: KMC-88213, A/c No 123456789012, see https://x.example.com/a.")}
    assert ("MRN", "KMC-88213") in found and ("ACCOUNT", "123456789012") in found and ("URL", "https://x.example.com/a") in found


def test_no_compliance_claim_anywhere_in_the_repo():
    phrase = "HIPAA" + " compliant"
    hits = subprocess.run(["git", "grep", "-i", "-I", phrase], capture_output=True, text=True, check=False,
                          cwd=Path(__file__).parent.parent).stdout
    assert hits == "", hits
