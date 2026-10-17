# Slide 7 facts and sources

Every claim on slide 7 ("Business Impact & Scalability"), with where it comes from. Checked on 2026-10-17 against
`main` (code unchanged since `ab05a85`). Deck: `/home/Muaz/Downloads/DevHack-fixed-shots.pptx`. Backup before this
version: `/home/Muaz/Documents/DevHack.backup-slide7-v2.pptx`. Style: `docs/deck-style.md`, matched to slide 6 as
you last saved it (intro box at 1.46 in, cards in the slide 6 tile grid, gaps of 0.20 in).

No customer, pilot or partner is claimed. Everything on the go-to-market card is marked as a plan ("Next").

## Intro

| Claim | Source |
|---|---|
| The heavy work runs on the laptop the office already owns | Detection, the attacker, restore, verify and audit run locally: `detect.py` `OLLAMA_URL` default `127.0.0.1`; GLiNER on CPU (`pyproject.toml`); `__main__.py` binds `127.0.0.1` |
| So our cost per office is mostly the hosted dashboard, not computers or cloud AI | Reasoning from the line above: we run no compute for the checks. The dashboard is not built yet (see below). No margin is claimed |

## How we make money

| Item | Marker | Source |
|---|---|---|
| Free core: the gateway, rules and audit log stay free (MIT) | Built | `LICENSE` (MIT); `chaperone/gateway.py`, `policy.py`, the audit log in `gateway.audit`. The GitHub repo is private today, so "free to use" needs it made public |
| Hosted dashboard: shared rules and sealed logs across offices | Next | Not in the code: the app has no login and listens on `127.0.0.1` only |
| Planned price: ₹499 per office a month | Next (planned) | Our proposal, not charged. Compared with TallyPrime Silver (one user) at ₹750 a month plus 18% GST, from Tally's own page "TallyPrime Pricing for Seasonal Businesses", updated 12 May 2026: https://tallysolutions.com/tally/tallyprime-pricing-for-seasonal-businesses/ |
| Sector rule packs: HIPAA Safe Harbor ships today | Built | `chaperone/policies_safe_harbor.yaml`; picked up by `policy.py` `_pack_files` |
| Finance, HR and education packs come next | (in the Built item's text) | Not in the code |

## Why now, and who pays

| Claim | Source |
|---|---|
| Every data fiduciary, by 13 May 2027 | PIB explainer, 17 Nov 2025: "The Rules introduce an eighteen-month period for phased compliance" and "Every Data Fiduciary must issue a separate consent notice": https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf. Bar & Bench: Gazette notification dated 13 Nov 2025, "i.e., May 13, 2027": https://www.barandbench.com/amp/story/view-point/meity-notifies-final-digital-personal-data-protection-rules-2025. (PIB gives the notification date as 14 Nov 2025) |
| A data fiduciary is anyone deciding how personal data is used | Plain wording of the DPDP Act's definition (the person who decides the purpose and means of processing) |
| Small offices first: clinics, CA firms and colleges, with no IT team | Target users in the README and slide 2. Not a market statistic |
| Hard to copy: local-first by design | `__main__.py` (`127.0.0.1`), local models; README "Guarantees" |
| Made for India | `detect.py` Indian ID patterns with python-stdnum checks, Hinglish in `CONTEXT_PROMPT` |
| A hand-labeled test set others would have to rebuild | `eval/dev.jsonl`, `eval/inference_dev.jsonl`, written and labeled by the team (`eval/README.md`). No count is given here: slide 6 owns the numbers |

Left out: a market-size number. 2026 reports of Udyam (MSME) registrations disagree (7.83 crore and 8.84 crore), and
the parliament answers could not be opened, so no statistic is on the slide.

## How we reach them (marked Next: a plan, not done)

| Step | Note |
|---|---|
| 1 Start next door: our own college office, then clinics we can visit in Mangaluru and Udupi | Plan only. No visit or agreement has happened |
| 2 Go through associations of CAs and doctors | Plan only. No association is named or claimed |
| 3 Let open source spread it: developers set it up for offices they help | Plan only. Needs the repo to be public |

## How it scales (roadmap)

| Row | Today (in the code) | Next | Later |
|---|---|---|---|
| Users | One laptop, one person: `__main__.py` binds `127.0.0.1`, sessions in memory (`gateway.SESSIONS`) | An office server, with a login: not in the code | Many offices sharing one dashboard: not in the code |
| Locations | India: Indian IDs and Hinglish: `detect.py` `RX`, `_valid`, `CONTEXT_PROMPT` | ID and language packs per country: not in the code | Other countries' privacy rules: not in the code (rule sets are YAML, `policy.py` `_pack_files`, so new rules need no code) |
| Use cases | AI agents (MCP) and the web page: `chaperone/mcp_server.py`; `web/` served by `app.py` | A proxy for any OpenAI-style chat app: **not in the code**. `app.py` has 14 routes, `/` and `/api/*` only; `gateway.send` is a client of OpenAI-style endpoints, not a proxy | A browser extension for ChatGPT, Claude: not in the code |

No dates are given.

## Footnotes

| Footnote | Source |
|---|---|
| ¹ Qwen2.5 3B's license covers research use; a paid version would ship a local model licensed for business; it's one setting (CONTEXT_MODEL) | Qwen Research License Agreement, sections 1(i), 2(a), 2(b): https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE; `detect.py` `CONTEXT_MODEL` |
| ² DPDP dates | PIB and Bar & Bench, above |
| ³ Planned price, compared with TallyPrime | Tally's page above |

## Not repeated from other slides

No feature mechanism (slide 3), step or tool (slide 4), or measured number (slide 6) is restated. The roadmap's
"Indian IDs and Hinglish" and "AI agents (MCP)" name where it runs today, not how it works.
