# score Chaperone and a Presidio baseline on one labelled JSONL split
#   uv run python eval/run_eval.py --split dev
#   uv run python eval/run_eval.py --split dev --models qwen2.5:3b,qwen3:1.7b,gemma3:1b
import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from chaperone import policy
from chaperone.gateway import analyze
from chaperone.policy import Flow
from chaperone.transform import value_pattern

LABELS = ["AADHAAR", "PAN", "GSTIN", "IFSC", "UPI", "PHONE", "EMAIL", "VEHICLE", "PERSON", "ORG", "LOCATION",
          "AGE", "DATE", "HEALTH", "COMPENSATION", "MNPI", "HR", "LEGAL"]
SEMANTIC = ["HEALTH", "COMPENSATION", "MNPI", "HR", "LEGAL"]
# roles, purposes and actions come from the rule files, like everywhere else
ROLES = list(policy.current().roles)
DESTINATIONS = list(policy.DESTINATIONS)
PURPOSES = list(policy.current().purposes)
ACTIONS = list(policy.ACTIONS)

# Presidio entity -> our label. DATE_TIME left out of scoring: it also covers "next week", a wider definition.
PRESIDIO_MAP = {"IN_AADHAAR": "AADHAAR", "IN_PAN": "PAN", "IN_GSTIN": "GSTIN", "IN_VEHICLE_REGISTRATION": "VEHICLE",
                "PHONE_NUMBER": "PHONE", "EMAIL_ADDRESS": "EMAIL", "PERSON": "PERSON", "LOCATION": "LOCATION",
                "ORGANIZATION": "ORG"}
PRESIDIO_THRESHOLD = 0.3  # drops 0.01-score guesses such as IN_PAN on any 10-digit number
PRESIDIO_SUPPORTS = {"AADHAAR", "PAN", "GSTIN", "VEHICLE", "PHONE", "EMAIL", "PERSON", "LOCATION"}


def load(path: Path) -> list[dict]:
    rows = []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        ex = json.loads(line)
        problems = [f"{key} {ex[key]!r}" for key, allowed in
                    (("role", ROLES), ("destination", DESTINATIONS), ("purpose", PURPOSES)) if ex[key] not in allowed]
        for text, label, action in ex["spans"]:
            if text not in ex["text"]:
                problems.append(f"span {text!r} not in text")
            if label not in LABELS or action not in ACTIONS:
                problems.append(f"span {text!r}: bad label/action {label}/{action}")
        if problems:
            raise SystemExit(f"{path.name} line {n} ({ex.get('id')}): " + "; ".join(problems))
        rows.append(ex)
    return rows


def gold_spans(ex: dict) -> list[dict]:
    out = []
    for text, label, action in ex["spans"]:
        start = ex["text"].find(text)
        while start >= 0:
            out.append({"start": start, "end": start + len(text), "text": text, "label": label, "action": action})
            start = ex["text"].find(text, start + 1)
    return out


def overlaps(a: dict, b: dict) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


# ---------- systems: each returns spans [{start,end,label,action}], outbound, ms ----------

def run_ours(ex: dict, use_context: bool, model: str | None) -> dict:
    from chaperone.transform import Vault

    flow = Flow(ex["role"], ex["destination"], ex["purpose"])
    # the no-context row measures detection alone, so it skips the refusal a real send would get
    r = analyze(ex["text"], flow, Vault(), use_context=use_context, model=model, refuse_unchecked=use_context)
    spans = [{"start": s["start"], "end": s["end"], "label": s["label"], "action": s["action"],
              "covered": s["covered"]} for s in r["spans"]]
    return {"spans": spans, "outbound": r["outbound"], "ms": r["timings"]["total_ms"],
            "context_ms": r["timings"].get("context_ms"), "context_ok": r["context_ok"]}


@lru_cache(maxsize=1)
def presidio():
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.predefined_recognizers import (
        InAadhaarRecognizer,
        InGstinRecognizer,
        InPanRecognizer,
        InPassportRecognizer,
        InVehicleRegistrationRecognizer,
        InVoterRecognizer,
    )

    engine = AnalyzerEngine()  # default: spaCy en_core_web_lg
    for rec in (InAadhaarRecognizer, InPanRecognizer, InGstinRecognizer, InVehicleRegistrationRecognizer,
                InVoterRecognizer, InPassportRecognizer):
        engine.registry.add_recognizer(rec())  # India recognizers ship disabled; enable them
    return engine


def run_presidio(ex: dict) -> dict:
    t0 = time.perf_counter()
    found = presidio().analyze(text=ex["text"], language="en", score_threshold=PRESIDIO_THRESHOLD)
    # flow-blind baseline: redact everything it finds, highest score wins overlaps
    keep: list = []
    for f in sorted(found, key=lambda f: (-f.score, f.start)):
        if not any(f.start < k.end and k.start < f.end for k in keep):
            keep.append(f)
    out = ex["text"]
    for f in sorted(keep, key=lambda f: -f.start):
        out = out[: f.start] + f"<{f.entity_type}>" + out[f.end:]
    ms = (time.perf_counter() - t0) * 1000
    # detection credit uses every hit, not only the overlap winner
    spans = [{"start": f.start, "end": f.end, "label": PRESIDIO_MAP.get(f.entity_type, f.entity_type),
              "action": "redact", "covered": False} for f in found]
    return {"spans": spans, "outbound": out, "ms": ms, "context_ms": None, "context_ok": None}


# ---------- scoring ----------

def effective_action(g: dict, pred: dict) -> str:
    if pred["outbound"] is None:
        return "block"
    acts = [p["action"] for p in pred["spans"] if overlaps(g, p) and p["action"] != "pass" and not p["covered"]]
    order = {"redact": 3, "block": 3, "generalize": 2, "pseudonymize": 1}
    return max(acts, key=lambda a: order[a]) if acts else "pass"


def score(examples: list[dict], preds: list[dict]) -> dict:
    tp: dict = defaultdict(int)
    fp: dict = defaultdict(int)
    fn: dict = defaultdict(int)
    action_ok = protect_ok = n_gold = 0
    leaks = sensitive = over = passes = 0
    by_lang: dict = defaultdict(lambda: [0, 0])
    block_tp = block_fp = block_fn = 0
    for ex, pred in zip(examples, preds):
        golds = gold_spans(ex)
        used = set()
        for g in golds:
            hit = next((i for i, p in enumerate(pred["spans"])
                        if i not in used and p["label"] == g["label"] and overlaps(g, p)), None)
            if hit is None:
                fn[g["label"]] += 1
            else:
                used.add(hit)
                tp[g["label"]] += 1
        for i, p in enumerate(pred["spans"]):
            if i not in used and p["label"] in LABELS:
                fp[p["label"]] += 1
        for g in golds:
            act = effective_action(g, pred)
            n_gold += 1
            action_ok += act == g["action"]
            protect_ok += (act != "pass") == (g["action"] != "pass")
            out = pred["outbound"]
            present = out is not None and bool(value_pattern(g["text"]).search(out))
            if g["action"] != "pass":
                sensitive += 1
                leaks += present
                by_lang[ex["lang"]][0] += present
                by_lang[ex["lang"]][1] += 1
            else:
                passes += 1
                over += not present
        blocked = pred["outbound"] is None
        block_tp += blocked and ex["block_request"]
        block_fp += blocked and not ex["block_request"]
        block_fn += (not blocked) and ex["block_request"]
    ms = [p["ms"] for p in preds]
    ctx = [p["context_ms"] for p in preds if p["context_ms"] is not None]
    return {"tp": tp, "fp": fp, "fn": fn, "n_gold": n_gold, "action_acc": action_ok / n_gold,
            "protect_acc": protect_ok / n_gold, "leak": (leaks, sensitive), "over": (over, passes),
            "leak_by_lang": dict(by_lang), "block": (block_tp, block_fp, block_fn),
            "p50": pct(ms, 50), "p95": pct(ms, 95), "ctx_p50": pct(ctx, 50), "ctx_p95": pct(ctx, 95),
            "context_fail": sum(p["context_ok"] is False for p in preds)}


def pct(xs: list[float], q: int) -> float | None:
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    return statistics.quantiles(xs, n=100, method="inclusive")[q - 1]


def prf(m: dict, labels: list[str]) -> tuple[float, float, float, int]:
    tp = sum(m["tp"][label] for label in labels)
    fp = sum(m["fp"][label] for label in labels)
    fn = sum(m["fn"][label] for label in labels)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f, tp + fn


def fmt(x: float | None, pctg: bool = False) -> str:
    if x is None:
        return "—"
    return f"{100 * x:.1f}%" if pctg else f"{x:.2f}"


def report(split: str, n: int, results: dict[str, dict]) -> str:
    names = list(results)
    lines = [f"## Results: `{split}` split ({n} examples, {results[names[0]]['n_gold']} gold spans)", ""]
    lines += ["### Gateway outcome", "",
              ("| System | Leak rate ↓ | Over-redaction ↓ | Protect/allow acc. | 4-way action acc. | "
               "Request blocks (TP/FP/FN) | Latency p50 / p95 |"),
              "|---|---|---|---|---|---|---|"]
    for name, m in results.items():
        lk, ls = m["leak"]
        ov, ps = m["over"]
        act = "—" if name.startswith("Presidio") else fmt(m["action_acc"], True)
        lines.append(f"| {name} | {fmt(lk / ls if ls else 0, True)} ({lk}/{ls}) | {fmt(ov / ps if ps else 0, True)} "
                     f"({ov}/{ps}) | {fmt(m['protect_acc'], True)} | {act} | {'/'.join(map(str, m['block']))} | "
                     f"{m['p50']:.0f} / {m['p95']:.0f} ms |")
    lines += ["", ("Leak rate = sensitive gold spans whose raw text reached the outbound payload. "
                   "Over-redaction = spans that should pass but were altered or blocked."), ""]
    lines += ["### Detection F1 by label (n = gold spans)", "",
              "| Label | n | " + " | ".join(names) + " |", "|---|---|" + "---|" * len(names)]
    for label in LABELS:
        n_l = results[names[0]]["tp"][label] + results[names[0]]["fn"][label]
        if not n_l:
            continue
        cells = []
        for name, m in results.items():
            if name.startswith("Presidio") and label not in PRESIDIO_SUPPORTS:
                cells.append("not supported")
            else:
                p, r, f, _ = prf(m, [label])
                cells.append(f"{f:.2f} (P {p:.2f} R {r:.2f})")
        lines.append(f"| {label} | {n_l} | " + " | ".join(cells) + " |")
    for group, labels in (("Identifiers + entities", [lb for lb in LABELS if lb not in SEMANTIC]),
                          ("Only labels Presidio supports", sorted(PRESIDIO_SUPPORTS)),
                          ("Context categories", SEMANTIC)):
        cells = []
        for name, m in results.items():
            p, r, f, _ = prf(m, labels)
            cells.append(f"**{f:.2f}** (P {p:.2f} R {r:.2f})")
        lines.append(f"| *{group}* | | " + " | ".join(cells) + " |")
    lines += ["", "### Leak rate by language", "", "| System | " + " | ".join(
        sorted(results[names[0]]["leak_by_lang"])) + " |", "|---|" + "---|" * len(results[names[0]]["leak_by_lang"])]
    for name, m in results.items():
        cells = [f"{fmt(a / b if b else 0, True)} ({a}/{b})" for _, (a, b) in sorted(m["leak_by_lang"].items())]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def bench_models(split: str, examples: list[dict], models: list[str]) -> str:
    lines = [f"## Context-model benchmark: `{split}` ({len(examples)} examples)", "",
             "| Model | Context F1 | P | R | Leak rate | 4-way action acc. | Context p50 / p95 | Failures |",
             "|---|---|---|---|---|---|---|---|"]
    for model in models:
        run_ours(examples[0], True, model)  # warm-up: load weights into VRAM
        m = score(examples, [run_ours(ex, True, model) for ex in examples])
        p, r, f, _ = prf(m, SEMANTIC)
        lk, ls = m["leak"]
        lines.append(f"| {model} | **{f:.2f}** | {p:.2f} | {r:.2f} | {fmt(lk / ls, True)} | "
                     f"{fmt(m['action_acc'], True)} | {m['ctx_p50']:.0f} / {m['ctx_p95']:.0f} ms | "
                     f"{m['context_fail']} |")
        print(lines[-1], flush=True)
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", help="dev | heldout")
    ap.add_argument("--models", help="comma list: benchmark context models instead of the full report")
    ap.add_argument("--no-presidio", action="store_true")
    args = ap.parse_args()
    examples = load(ROOT / "eval" / f"{args.split}.jsonl")
    if not examples:
        raise SystemExit(f"eval/{args.split}.jsonl has no cases yet; add some with eval/add_case.py")
    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(exist_ok=True)
    if args.models:
        md = bench_models(args.split, examples, args.models.split(","))
        (out_dir / f"models_{args.split}.md").write_text(md)
        print(md)
        return
    run_ours(examples[0], True, None)  # warm-up
    results = {"Chaperone (full)": score(examples, [run_ours(ex, True, None) for ex in examples]),
               "Chaperone (no context layer)": score(examples, [run_ours(ex, False, None) for ex in examples])}
    if not args.no_presidio:
        run_presidio(examples[0])
        results["Presidio + India recognizers"] = score(examples, [run_presidio(ex) for ex in examples])
    md = report(args.split, len(examples), results)
    (out_dir / f"results_{args.split}.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
