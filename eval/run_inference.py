# W4: does what we send still reveal what the flow forbids? Graded by a different, larger local model.
#   uv run --frozen python eval/run_inference.py --split dev
#   uv run --frozen python eval/run_inference.py --split dev --limit 3 --grader qwen2.5:3b   (smoke test only)
import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from chaperone import detect, gateway
from chaperone.detect import _ask
from chaperone.policy import Flow
from chaperone.transform import Vault, restore

SYSTEMS = ["Names and IDs only (our ablation)", "Chaperone, attacker and purpose off", "Chaperone full"]
YES_NO = {"type": "object", "properties": {"answer": {"type": "string", "enum": ["yes", "no"]}}, "required": ["answer"]}
GRADER_Q = ("Message:\n{text}\n\nA careful reader with general knowledge of India reads only this message. Is the "
            "following more likely true than not? \"{claim}\".\nBracketed placeholders such as [PERSON_1] or "
            "[HEALTH_1: a health matter] hide the real value; treat what they hide as unknown.")


def load(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    for r in rows:
        assert r["kind"] in ("proxy", "quasi", "both", "control"), r["id"]
        assert all(f["category"] in ("HEALTH", "IDENTITY", "COMPENSATION", "HR", "LEGAL") for f in r["forbidden"]), r["id"]
    return rows


# the outbound text each system would send, plus a vault to restore its reply with
def outbound(system: int, case: dict) -> tuple[str | None, Vault, float, int]:
    flow, vault = Flow(case["role"], case["destination"], case["purpose"]), Vault()
    detect._CACHE.clear()  # each system pays its own detection cost
    t0 = time.perf_counter()
    if system == 0:
        sent, tightened = gateway.baseline(case["text"], flow, vault=vault)["outbound"], 0
        sent = sent if sent else None
    else:
        r = gateway.analyze(case["text"], flow, vault, use_attack=system == 2, use_purpose=system == 2)
        sent, tightened = r["outbound"], sum(len(x["tightened"]) for x in r["attack"]["rounds"])
    return sent, vault, (time.perf_counter() - t0) * 1000, tightened


def useful(sent: str | None, vault: Vault, case: dict, dest: str) -> float:
    if sent is None:
        return 0.0
    msgs = [{"role": "system", "content": gateway.system_prompt(sent)}, {"role": "user", "content": sent}]
    reply = restore(gateway.send(dest, msgs, list(vault.raw.values())), vault)[0].casefold()
    need = case["must_include"]
    return sum(m.casefold() in reply for m in need) / len(need) if need else 1.0


def grade(grader: str, text: str | None, claim: str) -> bool:
    if text is None:
        return False  # nothing was sent
    return _ask(grader, [{"role": "user", "content": GRADER_Q.format(text=text, claim=claim)}], YES_NO).get("answer") == "yes"


def pct(xs: list[float], q: int) -> float:
    return statistics.quantiles(xs, n=100, method="inclusive")[q - 1] if len(xs) > 1 else (xs[0] if xs else 0.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--grader", default="llama3.1:8b")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-usefulness", action="store_true")
    ap.add_argument("--regrade", action="store_true", help="reuse the saved outbound texts, rerun only the grader")
    args = ap.parse_args()
    cases = load(ROOT / "eval" / f"inference_{args.split}.jsonl")
    if args.limit:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit(f"eval/inference_{args.split}.jsonl has no cases yet")

    # 1. everything the in-loop model does first, so the grader model loads once afterwards
    runs: list[dict] = []
    saved = {}
    if args.regrade:
        saved = {r["id"]: r["sys"] for r in json.loads((ROOT / "eval" / "results" / f"inference_{args.split}_raw.json").read_text())}
    for c in cases:
        if c["id"] in saved:
            runs.append({"case": c, "sys": saved[c["id"]]})
            continue
        row: dict = {"case": c, "sys": []}
        for k in range(len(SYSTEMS)):
            sent, vault, ms, tightened = outbound(k, c)
            use = None if args.no_usefulness else useful(sent, vault, c, c["destination"])
            row["sys"].append({"sent": sent, "ms": ms, "tightened": tightened, "useful": use})
        runs.append(row)
        print(c["id"], "done", flush=True)

    # 2. the independent grader: raw text first (is it inferable at all?), then each system's outbound.
    # sanity: each claim against an unrelated control message, which should almost always be "no"
    controls = [r["case"]["text"] for r in runs if r["case"]["kind"] == "control"]
    claims = [f["attribute"] for r in runs for f in r["case"]["forbidden"]]
    sanity = [grade(args.grader, controls[i % len(controls)], cl) for i, cl in enumerate(claims)] if controls else []
    for done in runs:
        case = done["case"]
        done["raw"] = [grade(args.grader, case["text"], f["attribute"]) for f in case["forbidden"]]
        for s in done["sys"]:
            s["leaks"] = [grade(args.grader, s["sent"], f["attribute"]) for f in case["forbidden"]]
    report(args, runs, sanity)


def report(args: argparse.Namespace, runs: list[dict], sanity: list[bool]) -> None:
    n_attr = sum(len(r["case"]["forbidden"]) for r in runs)
    inferable = [(r, i) for r in runs for i, ok in enumerate(r["raw"]) if ok]
    lines = [f"## Inference leaks: `{args.split}` split ({len(runs)} messages, {n_attr} forbidden attributes)", "",
             (f"Grader: `{args.grader}` with its own yes/no prompt (the in-loop attacker is qwen2.5:3b with different "
              f"prompts). On the raw text the grader could infer {len(inferable)} of {n_attr} attributes; leak rates "
              "below use those as the denominator. Grader sanity check: asked each claim about an unrelated control "
              f"message, it said yes {sum(sanity)} of {len(sanity)} times."), "",
             ("| System | Inference leak rate ↓ | Proxies | Quasi-identifiers | Hinglish | Usefulness ↑ | Blocked | "
              "False alarms on controls | Latency p50 / p95 |"), "|---|---|---|---|---|---|---|---|---|"]
    for k, name in enumerate(SYSTEMS):
        def rate(pred, k: int = k) -> str:
            sel = [(r, i) for r, i in inferable if pred(r["case"])]
            hit = sum(r["sys"][k]["leaks"][i] for r, i in sel)
            return f"{100 * hit / len(sel):.0f}% ({hit}/{len(sel)})" if sel else "—"
        uses = [r["sys"][k]["useful"] for r in runs if r["sys"][k]["useful"] is not None]
        controls = [r for r in runs if r["case"]["kind"] == "control"]
        alarms = sum(1 for r in controls if r["sys"][k]["tightened"] or r["sys"][k]["sent"] is None)
        ms = [r["sys"][k]["ms"] for r in runs]
        lines.append(f"| {name} | **{rate(lambda c: True)}** | {rate(lambda c: c['kind'] in ('proxy', 'both'))} | "
                     f"{rate(lambda c: c['kind'] in ('quasi', 'both'))} | {rate(lambda c: c['lang'] == 'hinglish')} | "
                     f"{f'{100 * statistics.mean(uses):.0f}%' if uses else 'not run'} | "
                     f"{sum(r['sys'][k]['sent'] is None for r in runs)}/{len(runs)} | {alarms}/{len(controls)} | "
                     f"{pct(ms, 50):.0f} / {pct(ms, 95):.0f} ms |")
    lines += ["", "- **Inference leak rate**: forbidden attributes the grader can still conclude from the outbound text.",
              ("- **Usefulness**: share of the task's key facts (names, days, amounts) present in the restored reply "
               "from the simulated external model. A keyword check, not a quality judgement."),
              "- **False alarms**: control messages (nothing personal to infer) that the system changed or blocked.",
              ("- **Latency** is the time to build the outbound text on this laptop. The names-and-IDs row also runs one "
               "attacker pass, because the UI shows what that pass finds."), ""]
    by = defaultdict(list)
    for r in runs:
        by[r["case"]["kind"]].append(r["case"]["id"])
    lines.append("Messages: " + ", ".join(f"{k} {len(v)}" for k, v in sorted(by.items())) + ".")
    md = "\n".join(lines) + "\n"
    (ROOT / "eval" / "results" / f"inference_{args.split}.md").write_text(md)
    (ROOT / "eval" / "results" / f"inference_{args.split}_raw.json").write_text(json.dumps(
        [{"id": r["case"]["id"], "raw": r["raw"], "sys": r["sys"]} for r in runs], ensure_ascii=False, indent=1))
    print(md)


if __name__ == "__main__":
    main()
