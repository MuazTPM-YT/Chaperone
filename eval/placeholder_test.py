# how often does the real LLM mangle placeholders, and does tolerant restore recover them?
#   uv run python eval/placeholder_test.py
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from run_eval import load

from chaperone.gateway import analyze, send, system_prompt
from chaperone.policy import Flow
from chaperone.transform import Vault, restore

LEFTOVER = re.compile(r"\b[A-Z]{3,}_\d+\b")


def main() -> None:
    exact = fuzzy = leftover = replies = 0
    rows = []
    for ex in load(ROOT / "eval" / "dev.jsonl"):
        if ex["destination"] != "external":
            continue
        vault = Vault()
        r = analyze(ex["text"], Flow(ex["role"], ex["destination"], ex["purpose"]), vault)
        if r["blocked"] or not vault.raw:
            continue
        msgs = [{"role": "system", "content": system_prompt(r["outbound"])}, {"role": "user", "content": r["outbound"]}]
        reply = send("external", msgs, r["protected"])
        restored, stats = restore(reply, vault)
        replies += 1
        exact += stats["exact"]
        fuzzy += stats["fuzzy"]
        left = LEFTOVER.findall(restored)
        leftover += bool(left)
        if stats["fuzzy"] or left:
            rows.append(f"- `{ex['id']}`: {stats['fuzzy']} mangled, leftover {left}")
    total = exact + fuzzy
    md = [f"## Placeholder survival ({replies} replies from the simulated external model)", "",
          f"- Placeholder mentions in replies: {total}",
          f"- Exact `[LABEL_N]` form: {exact} ({100 * exact / max(total, 1):.1f}%)",
          f"- Mangled but restored by tolerant matching: {fuzzy} ({100 * fuzzy / max(total, 1):.1f}%)",
          f"- Replies with an unrestorable leftover token: {leftover}/{replies}", "", *rows]
    out = "\n".join(md) + "\n"
    (ROOT / "eval" / "results" / "placeholders_dev.md").write_text(out)
    print(out)


if __name__ == "__main__":
    main()
