from flowguard.transform import Vault, restore_marked
from flowguard.verify import check

SOURCE = ["Patient Ramesh Rao, 54-year-old male, admitted on 12 March 2026 with chest pain. Fee ₹45,000."]


def kinds(reply):
    return [(f["kind"], f["text"]) for f in check(reply, SOURCE, names=False)]


def test_fabricated_age_is_flagged():
    flags = check("Ramesh Rao, a 50-year-old male, was admitted.", SOURCE, names=False)
    assert [(f["kind"], f["text"]) for f in flags] == [("age", "50-year-old")]
    assert "54" in flags[0]["reason"]


def test_values_from_the_source_are_not_flagged():
    assert kinds("Ramesh Rao, 54-year-old male, admitted on 12 March 2026 (in March 2026). Fee ₹45,000.") == []


def test_invented_date_month_amount_and_number():
    assert kinds("Admitted on 14 March 2026, seen again in April 2026, fee ₹52,000, call 98860 54321.") == [
        ("date", "14 March 2026"), ("date", "April 2026"), ("amount", "₹52,000"), ("number", "98860 54321")]


def test_bands_and_ranges_are_not_claims():
    assert kinds("Pay sits in the senior salary band (₹10–30 lakh/yr).") == []


def test_invented_name_is_flagged():
    flags = check("Dr. Kavitha Menon reviewed Ramesh Rao today.", SOURCE)
    assert [f["kind"] for f in flags] == ["name"] and "Kavitha" in flags[0]["text"]


def test_generalized_value_goes_out_coarse_and_comes_back_exact():
    v = Vault()
    token = v.placeholder("AGE", "54-year-old", "in their 50s")
    assert token == "[AGE_1: in their 50s]"
    for seen in ("[AGE_1: in their 50s]", "[AGE_1]", "AGE_1", "[age_1: 50s]"):
        out, _, marks = restore_marked(f"A {seen} man.", v)
        assert out == "A 54-year-old man.", seen
        assert out[marks[0]["start"]:marks[0]["end"]] == "54-year-old"
    assert restore_marked("[AGE_1: in their 50s] and [AGE_7]", v)[0] == "54-year-old and [AGE_7]"  # unknown stays
