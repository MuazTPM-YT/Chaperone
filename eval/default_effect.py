# what does the cautious default cost in answer quality? same message, three defaults, real replies
#   uv run --frozen python eval/default_effect.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from flowguard import gateway
from flowguard.policy import Decision, Flow, decide
from flowguard.transform import Vault, restore

BROAD = {"sensitive-need-to-know", "personal-ids-external", "default-cautious"}
CASES = [
    ("Manager", "external", "general", "Rahul ka salary 14 lakh hai, isko appraisal email mein mention karo."),
    ("Manager", "external", "general",
     "Arjun has been diagnosed with depression and will work half days this month. Draft a note to the team."),
    ("Accountant", "external", "invoicing", "Draft an invoice to Suresh Kumar, PAN ABKPS7312M, for ₹45,000 of printing work."),
]


def run(mode: str, role: str, dest: str, purpose: str, text: str) -> tuple[str | None, str]:
    def patched(label: str, subject: str, flow: Flow, *a) -> Decision:
        d = decide(label, subject, flow)
        if d.rule in BROAD and mode != "ours":
            return Decision(mode, f"default-{mode}", "experiment")
        return d

    gateway.decide = patched  # type: ignore[assignment]
    vault = Vault()
    r = gateway.analyze(text, Flow(role, dest, purpose), vault)
    if r["blocked"]:
        return None, "(request blocked)"
    reply = gateway.send(dest, [{"role": "system", "content": gateway.SYSTEM_PROMPT},
                                {"role": "user", "content": r["outbound"]}], [] if mode == "pass" else r["protected"])
    return r["outbound"], restore(reply, vault)[0]


def main() -> None:
    out = ["## Effect of the default on answers", "",
           "Broad rules (`sensitive-need-to-know`, `personal-ids-external`) swapped for pass or block.", ""]
    for case in CASES:
        out += [f"### {case[3]}", ""]
        for mode in ("pass", "ours", "block"):
            sent, reply = run(mode, *case)
            label = {"pass": "Pass by default (leaks)", "ours": "FlowGuard default",
                     "block": "Block by default"}[mode]
            out += [f"**{label}**", "", f"- Sent: `{sent}`", f"- Reply (restored): {reply.strip()[:400]}", ""]
    md = "\n".join(out)
    (ROOT / "eval" / "results" / "default_effect.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
