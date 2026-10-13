# PLAN: context-aware privacy gateway (DevHack 2026, PS 2.2)

Thesis: sensitivity belongs to the **flow** (what, whose, who sends, where to, why), not to the data.

## Machine (checked 13 Oct)

- RTX 3050 Laptop, 4 GB VRAM (3.7 GiB usable), CUDA 13.4. i7-11th H, 16 GB RAM.
- Ollama 0.34.4 (Arch archive build, 19 days old, per 14-day rule). GPU detected.
- Python 3.14 is system default. ML wheels are safest on **3.12** (uv-managed, already on disk).
- **Risk: only ~12 GB disk free.** Torch goes CPU-only (GPU kept for Ollama); losing LLM candidates get deleted after benchmark.

## Architecture

```
browser (static HTML)  ->  FastAPI /api/chat
  1. detect   (local)  deterministic regex + stdnum checksums  -> AADHAAR, PAN(+holder), GSTIN(+embedded PAN), IFSC, UPI, PHONE, EMAIL, VEHICLE, MONEY, AGE, DATE
                       GLiNER small (CPU)                      -> PERSON, ORG, LOCATION
                       Ollama small LLM, JSON-schema output    -> HEALTH, COMPENSATION, MNPI, HR, LEGAL phrases
  2. policy            policies.yaml, first match wins, every decision records rule id
  3. transform         pass | pseudonymize ([PERSON_1], session-sticky) | generalize (irreversible) | block (span or whole request)
  4. outbound guard    payload scanned for every raw value in session vault (case/space/digit-normalised); refuse on hit
  5. LLM               OpenAI-compatible /chat/completions (internal + external both configurable)
  6. restore           tolerant placeholder swap-back, local
  7. audit             JSONL, HMAC-SHA256 of values + placeholder ids, never raw values
```

Eval: `eval/run_eval.py` over `eval/dev.jsonl` / `eval/heldout.jsonl`, same metrics for us and Presidio.

## Decisions (section 6)

| Decision | Pick | Trade-off |
|---|---|---|
| Backend | FastAPI, Python 3.12 | ML libs are Python. |
| Frontend | One static `index.html`, vanilla JS, no build, no CDN | Next.js is nicer to grow, but adds ~400 MB node_modules, a build step and npm supply-chain surface. Plain HTML works offline in the demo and is one file. |
| "External" LLM | Ollama behind its OpenAI-compatible `/v1` endpoint, labelled "external (simulated)" | Demo needs no network. Switching to a real API = set `EXTERNAL_LLM_BASE_URL`, `EXTERNAL_LLM_MODEL`, `EXTERNAL_LLM_API_KEY` in `.env`. No code change. |
| Placeholder format | `[PERSON_1]`, `[PAN_1]` | Brackets survive most rewrites. Restore also accepts `PERSON_1`, `Person 1`, `[person_1]`, `PERSON_1's`. Mangle rate measured and reported. |
| Placeholder content | Type only | Type + role (`[PATIENT_1]`) helps reasoning but leaks role; gender hints leak more and are guessed from names (unreliable). Type is the minimum the LLM needs. |
| Context layer down | Fall back to deterministic + NER; UI shows a red "context layer offline" banner; external sends still get identifiers pseudonymized | Health/MNPI phrases will not be caught in that mode. Stated, not hidden. |
| Unknown flow default | Identifiers and names: **pseudonymize**. Semantic categories (health, salary, MNPI, HR, legal): **generalize**. | Block-by-default kills most answers; pass-by-default leaks. Pseudonymize keeps answers useful (restored) and leaks nothing raw. Effect shown in results. |
| Entity model | GLiNER `urchade/gliner_small-v2.1` (Apache-2.0), CPU, label "person name" | Splits "Rahul and Deepak"; misses some Hinglish names, so the context LLM also flags names NER missed. |
| Context LLM | **qwen2.5:3b** after benchmarking `gemma3:1b`, `qwen3:1.7b`, `qwen2.5:3b` | qwen3:1.7b is smaller but made 5 false request blocks vs 1; qwen2.5:3b also serves as the simulated external AI, so one model fits in VRAM. |
| Baseline | Presidio analyzer with India recognizers **enabled**, spaCy `en_core_web_lg` (its default) | Fair: we report where Presidio already validates checksums. |

## Dependencies (all pinned `~=x.y.z`, uv `exclude-newer` = 14 days ago)

fastapi, uvicorn, httpx (LLM + Ollama calls; also FastAPI TestClient), pyyaml (policies), python-stdnum, gliner + torch (CPU), presidio-analyzer + spacy model (baseline only). Dev: pytest, ruff, mypy.

## Learned while building

- The context LLM mistook ID numbers for MNPI. Fix: IDs and names are masked as `[AADHAAR]`, `[PERSON]` before it reads the text.
- The LLM sometimes rewrites amounts ("₹14.2 lakh" -> "₹14,20,000"); pay findings are matched to the text by value.
- `uv run` re-checks a GitHub-hosted spaCy wheel online; use `uv run --frozen` everywhere (offline-safe).
- Replies were capped at 700 tokens after one 3-minute runaway generation.
- Extra dependencies beyond the brief: `sentencepiece`, `protobuf` (GLiNER's tokenizer needs them at load time).

## Open items

1. Held-out set: teammates write it with `eval/add_case.py`, guided by `eval/README.md` (no detector internals).
2. Real external API for the video? Default stays simulated; switching is three `.env` lines.
