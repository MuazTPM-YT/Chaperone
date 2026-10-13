from flowguard import detect as detect_mod
from flowguard.detect import Span, _mask, _to_orig, deterministic, rupees


def labels(text):
    return {(s.label, s.text, s.subject) for s in deterministic(text)}


def test_aadhaar_needs_valid_verhoeff():
    assert ("AADHAAR", "7260 1815 9082", "individual") in labels("Aadhaar 7260 1815 9082 please")
    assert not labels("Order number 797971147104 shipped")  # 12 digits, bad check digit


def test_pan_holder_type_sets_subject():
    assert ("PAN", "AADCR4581K", "business") in labels("PAN AADCR4581K")  # C = company
    assert ("PAN", "ABKPS7312M", "individual") in labels("PAN ABKPS7312M")  # P = person
    assert ("PAN", "AAEFM2290Q", "business") in labels("PAN AAEFM2290Q")  # F = firm


def test_gstin_of_proprietor_is_personal():
    assert ("GSTIN", "29AADCR4581K1ZV", "business") in labels("GSTIN 29AADCR4581K1ZV")
    assert ("GSTIN", "29ABKPS7312M1ZZ", "individual") in labels("GSTIN 29ABKPS7312M1ZZ")
    assert not labels("GSTIN 29AADCR4581K1ZA")  # bad checksum


def test_contact_ids():
    found = labels("Call +91 98450 12345, mail priya.sharma@gmail.com or accounts@ravitraders.in, UPI rahul.k@okaxis")
    assert ("PHONE", "+91 98450 12345", "individual") in found
    assert ("EMAIL", "priya.sharma@gmail.com", "individual") in found
    assert ("EMAIL", "accounts@ravitraders.in", "business") in found  # role mailbox
    assert ("UPI", "rahul.k@okaxis", "individual") in found


def test_ifsc_vehicle_age_date():
    found = labels("IFSC SBIN0004567, car MH 12 AB 1234, a 54-year-old seen on 12 March 2026")
    assert {lb for lb, _, _ in found} == {"IFSC", "VEHICLE", "AGE", "DATE"}


def test_mask_offsets_map_back():
    text = "Deepak ka divorce case, Aadhaar 7260 1815 9082 ok"
    masked, segs = _mask(text, [Span(0, 6, "Deepak", "PERSON"), Span(32, 46, "7260 1815 9082", "AADHAAR")])
    assert masked == "[PERSON] ka divorce case, Aadhaar [AADHAAR] ok"
    a = masked.index("divorce")
    b = a + len("divorce case")
    assert text[_to_orig(a, segs, False):_to_orig(b, segs, True)] == "divorce case"
    tag = masked.index("[AADHAAR]")
    assert text[_to_orig(tag, segs, False):_to_orig(tag + 9, segs, True)] == "7260 1815 9082"


def test_rupees_reads_indian_units():
    assert rupees("₹14.2 lakh") == rupees("₹14,20,000") == 1_420_000
    assert rupees("8.5 LPA") == 850_000 and rupees("20 hazaar") == 20_000 and rupees("2 crore") == 20_000_000


def test_context_layer_offline_falls_back(monkeypatch):
    monkeypatch.setattr(detect_mod, "OLLAMA_URL", "http://127.0.0.1:9")  # nothing listens here
    d = detect_mod.detect("Customer Aadhaar 7260 1815 9082, salary 14 lakh")
    assert d.context_ok is False and "ConnectError" in d.context_error
    assert {s.label for s in d.spans} == {"AADHAAR"}  # ids still caught, pay is not
