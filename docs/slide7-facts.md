# Slide 7 facts and sources

Every claim on slide 7 ("Business Impact & Scalability"), with where it comes from. Checked on 2026-10-17 against
`main` (code unchanged since `ab05a85`). Deck: `/home/Muaz/Downloads/DevHack-fixed-shots.pptx`. Backup before this
version: `/home/Muaz/Documents/DevHack.backup-slide7-v3.pptx`. Style: `docs/deck-style.md`, matched to slide 6 as
you last saved it (intro box at 1.46 in, cards in the slide 6 tile grid, gaps of 0.20 in).

No customer, pilot or partner is claimed. The "we start next door" line is a plan.

## Intro

| Claim | Source |
|---|---|
| The heavy work runs on the laptop the office already owns | Detection, the attacker, restore, verify and audit run locally: `detect.py` `OLLAMA_URL` default `127.0.0.1`; GLiNER on CPU (`pyproject.toml`); `__main__.py` binds `127.0.0.1` |
| So our cost per office is mostly the hosted dashboard, not computers or cloud AI | Reasoning from the line above: we run no compute for the checks. The dashboard is not built yet (see below). No margin is claimed |

## How we make money (price ladder)

| Tier | Pill | Source |
|---|---|---|
| Free core: the gateway, rules and audit log stay free and open source (MIT) | Built | `LICENSE` (MIT); `chaperone/gateway.py`, `policy.py`, the audit log in `gateway.audit`. The GitHub repo is private today, so "open source" needs it made public |
| Office plan: hosted dashboard, shared rules and sealed logs across offices | Planned | Not in the code: the app has no login and listens on `127.0.0.1` only |
| Rs. 499 a month | Planned | Our proposal, not charged. Compared with TallyPrime Silver (one user) at Rs. 750 a month plus 18% GST, from Tally's own page "TallyPrime Pricing for Seasonal Businesses", updated 12 May 2026: https://tallysolutions.com/tally/tallyprime-pricing-for-seasonal-businesses/ |
| Sector packs: HIPAA Safe Harbor ships today | Built | `chaperone/policies_safe_harbor.yaml`; picked up by `policy.py` `_pack_files` |
| Finance, HR and education packs come next | (in the Built row's text) | Not in the code |

## Why now

| Claim | Source |
|---|---|
| 13 May 2027: every data fiduciary must follow the DPDP Rules by then | PIB explainer, 17 Nov 2025: "The Rules introduce an eighteen-month period for phased compliance" and "Every Data Fiduciary must issue a separate consent notice": https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf. Bar & Bench: Gazette notification dated 13 Nov 2025, "i.e., May 13, 2027": https://www.barandbench.com/amp/story/view-point/meity-notifies-final-digital-personal-data-protection-rules-2025. (PIB gives the notification date as 14 Nov 2025) |
| A data fiduciary is anyone deciding how personal data is used | Plain wording of the DPDP Act's definition (the person who decides the purpose and means of processing) |
| Who pays first: clinics, CA firms and college offices, with client data and no IT team | Target users in the README and slide 2. Not a market statistic |
| We start next door: our own college office and clinics in Mangaluru and Udupi, then CA and doctors' associations | A plan only. No visit, agreement or association is claimed |

Left out: a market-size number. 2026 reports of Udyam (MSME) registrations disagree (7.83 crore and 8.84 crore), and
the parliament answers could not be opened, so no statistic is on the slide. "Hard to copy" was cut (slide 3 shows
what is different).

## How it scales (roadmap)

| Row | Today (in the code) | Next | Later |
|---|---|---|---|
| Users | One laptop, one person: `__main__.py` binds `127.0.0.1`, sessions in memory (`gateway.SESSIONS`) | An office server, with a login: not in the code | Many offices sharing one dashboard: not in the code |
| Locations | India: Indian IDs and Hinglish: `detect.py` `RX`, `_valid`, `CONTEXT_PROMPT` | ID and language packs per country: not in the code | Other countries' privacy rules: not in the code (rule sets are YAML, `policy.py` `_pack_files`, so new rules need no code) |
| Use cases | AI agents (MCP) and our own chat page: `chaperone/mcp_server.py`; `web/` served by `app.py` | A proxy for any OpenAI-style chat app: **not in the code**. `app.py` has 14 routes, `/` and `/api/*` only; `gateway.send` is a client of OpenAI-style endpoints, not a proxy | A browser extension for ChatGPT, Claude: not in the code |

No dates are given.

## Footnotes

| Footnote | Source |
|---|---|
| ¹ Qwen2.5 3B's license covers research use; a paid version would ship a local model licensed for business; it's one setting (CONTEXT_MODEL) | Qwen Research License Agreement, sections 1(i), 2(a), 2(b): https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE; `detect.py` `CONTEXT_MODEL` |
| ² DPDP dates, and the planned price compared with TallyPrime | PIB, Bar & Bench and Tally's page, above |

## Not repeated from other slides

No feature mechanism (slide 3), step or tool (slide 4), or measured number (slide 6) is restated. The roadmap's
"Indian IDs and Hinglish" and "AI agents (MCP)" name where it runs today, not how it works.
