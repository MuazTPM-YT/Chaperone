# Slide 7 facts and sources

Every claim on slide 7 ("Business Impact & Scalability"), with where it comes from. Checked on 2026-10-17 against
`main`. Deck: `/home/Muaz/Downloads/DevHack-fixed-shots.pptx`. Backup before this version:
`/home/Muaz/Documents/DevHack.backup-slide7-timeline.pptx`. Style: `docs/deck-style.md`.

No customer, pilot or partner is claimed. "We start next door" is a plan.

## Top line

| Claim | Source |
|---|---|
| Free to run, because the office's own laptop does the work | Detection, the attacker, restore and audit run locally: `detect.py` `OLLAMA_URL` default `127.0.0.1`; GLiNER on CPU; `__main__.py` binds `127.0.0.1`. `LICENSE` is MIT |
| We only charge when an office wants its laptops to share the same rules | The planned hosted dashboard. Not in the code: no login, `127.0.0.1` only |

## Card 1: 13 May 2027

| Claim | Source |
|---|---|
| Offices that handle personal data must follow the DPDP Rules by 13 May 2027 | PIB explainer, 17 Nov 2025: "an eighteen-month period for phased compliance": https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf. Bar & Bench: Gazette dated 13 Nov 2025, "i.e., May 13, 2027": https://www.barandbench.com/amp/story/view-point/meity-notifies-final-digital-personal-data-protection-rules-2025 |
| We start next door: our college office, then clinics in Mangaluru and Udupi | Plan only. No visit or agreement has happened |

## Card 2: Rs. 499 a month

| Claim | Source |
|---|---|
| The core stays free | `LICENSE` (MIT). The GitHub repo is private today, so "open source" needs it made public |
| Shared rules and one audit log across laptops, in a hosted dashboard | Plan only. Not in the code |
| Rs. 499 a month | Our proposal, not charged |
| Less than a one-user TallyPrime rental (Rs. 750 a month plus GST) | Tally's page "TallyPrime Pricing for Seasonal Businesses", updated 12 May 2026: https://tallysolutions.com/tally/tallyprime-pricing-for-seasonal-businesses/. The brief said "licence"; the sourced figure is the monthly rental, so the slide says "rental" |
| The clinic pack already ships | `chaperone/policies_safe_harbor.yaml` (HIPAA Safe Harbor), found by `policy.py` `_pack_files`, listed by `app.py`, and picked with the "Safe Harbor" switch on the page (`web/e2e/ui.spec.ts`: buttons "Standard rules", "Safe Harbor"). `tests/test_packs.py` passes |
| More sectors come next | Not in the code |

## Card 3: No cloud bill

| Claim | Source |
|---|---|
| Each office brings its own laptop, so our costs barely grow | Same as the top line. The planned dashboard is the only thing we would host |
| A new country or app is a rule file or a plug-in, not a rewrite | **Partly true.** Privacy rules are YAML files (`policies_*.yaml`), so they need no code. A new country's ID formats are code: regexes in `detect.py` `RX` and checksums in `_valid`, a small addition but not a rule file. A new app plugs in through MCP today (`chaperone/mcp_server.py`, `tests/test_mcp.py` passes); a proxy is not in the code |

## Roadmap

| Item | Source |
|---|---|
| Today: one laptop | `__main__.py` binds `127.0.0.1`; sessions in memory |
| Today: Indian IDs and Hinglish | `detect.py` `RX`, `_valid`, `CONTEXT_PROMPT` |
| Today: AI agents via MCP | `chaperone/mcp_server.py`, `tests/test_mcp.py` |
| Next: an office server with logins | Not in the code |
| Next: an OpenAI-compatible proxy | **Not in the code.** `app.py` has only `/` and `/api/*` routes; `gateway.send` calls OpenAI-style endpoints but is not a proxy. So it stays under Next |
| Later: many offices on one dashboard, other countries, a browser extension | Not in the code |

## Footnote

| Claim | Source |
|---|---|
| DPDP Rules notified 13 Nov 2025 with an 18-month phase-in | PIB and Bar & Bench, above (PIB gives 14 Nov 2025 as the notification date) |
| TallyPrime's one-user rental is Rs. 750 a month | Tally's page, above (plus 18% GST) |

The Qwen2.5 3B license note is no longer on the slide. It is in `README.md`, section "License".

Left out: a market-size number. 2026 reports of Udyam (MSME) registrations disagree (7.83 crore and 8.84 crore), so
no statistic is on the slide.
