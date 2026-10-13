# interactive: append one labelled case to a split (default heldout). Validates as you type.
#   uv run python eval/add_case.py            -> eval/heldout.jsonl
#   uv run python eval/add_case.py --split dev
import argparse
import json
from pathlib import Path

from run_eval import ACTIONS, DESTINATIONS, LABELS, PURPOSES, ROLES

ROOT = Path(__file__).resolve().parent


def pick(prompt: str, options: list[str]) -> str:
    while True:
        value = input(f"{prompt} {options}: ").strip()
        if value in options:
            return value
        print(f"  pick one of {options}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="heldout")
    path = ROOT / f"{ap.parse_args().split}.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
    prefix = path.stem[:4]
    text = input("Message text: ").strip()
    case = {"id": f"{prefix}-{len(rows) + 1:03d}", "pair": input("Pair id (blank if none): ").strip(),
            "lang": pick("Language", ["en", "hinglish"]), "role": pick("Sender role", ROLES),
            "destination": pick("Destination", DESTINATIONS), "purpose": pick("Purpose", PURPOSES),
            "text": text, "block_request": pick("Whole request blocked?", ["no", "yes"]) == "yes", "spans": []}
    print("Sensitive or notable spans, one per line as: exact text | LABEL | action. Blank line ends.")
    print(f"  labels: {LABELS}\n  actions: {ACTIONS}")
    while line := input("  span> ").strip():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3 or parts[0] not in text or parts[1] not in LABELS or parts[2] not in ACTIONS:
            print("  rejected: need 'text | LABEL | action' with text copied exactly from the message")
            continue
        case["spans"].append(parts)
    with path.open("a") as f:
        f.write(json.dumps(case, ensure_ascii=False) + "\n")
    print(f"saved {case['id']} to {path.name}")


if __name__ == "__main__":
    main()
