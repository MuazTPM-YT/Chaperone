# Slide 7 facts and sources

Every claim on slide 7 ("Business Impact & Scalability"), with where it comes from. Checked on 2026-10-17 against
`main`. Deck: `/home/Muaz/Downloads/DevHack-fixed-shots.pptx`. Backup before this version:
`/home/Muaz/Documents/DevHack.backup-slide7-tiers.pptx`. Style: `docs/deck-style.md`.

No customer, pilot or partner is claimed. "We start next door" is a plan.

## Intro box

| Claim | Source |
|---|---|
| Every office that handles personal data must follow the DPDP Rules by 13 May 2027 | PIB explainer, 17 Nov 2025: "an eighteen-month period for phased compliance": https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf. Bar & Bench: Gazette dated 13 Nov 2025, "i.e., May 13, 2027": https://www.barandbench.com/amp/story/view-point/meity-notifies-final-digital-personal-data-protection-rules-2025 |
| Free to run, because the office's own laptop does the work | Detection, the attacker, restore and audit run locally: `detect.py` `OLLAMA_URL` default `127.0.0.1`; GLiNER on CPU; `__main__.py` binds `127.0.0.1` |
| We only charge when offices share rules and records across laptops | The planned hosted dashboard. Not in the code: no login, `127.0.0.1` only |

## Pricing cards

| Claim | Source |
|---|---|
| Community, free, available today: the full gateway, rules and audit log, open source (MIT) | `LICENSE` (MIT); `chaperone/gateway.py`, `policy.py`, the audit log in `gateway.audit`. **The GitHub repo is private today**, so "open source" needs it made public |
| Team, Rs. 2,499 per office a month, planned: hosted dashboard, shared rules, one sealed record | Plan only. Not in the code. The sealed record exists per laptop today (HMAC-sealed audit log, `AUDIT_HMAC_KEY`); sharing it across laptops does not |
| Business, Rs. 7,499 per organization a month, planned: setup, support, sector rule packs | Plan only. No support offer exists |
| The clinic pack (HIPAA Safe Harbor) already ships | Checked 2026-10-18: `chaperone/policies_safe_harbor.yaml` loads as pack `safe_harbor` ("HIPAA Safe Harbor mode", short name "Safe Harbor") in `policy.current().packs`; the page shows the buttons "Standard rules" and "Safe Harbor" (`web/e2e/ui.spec.ts`); `tests/test_packs.py` 4 passed |
| Prices are starting points, not charged | Our proposal. No customer, pilot or partner is claimed |
| Team is about Rs. 500 per laptop for five laptops | Rs. 2,499 / 5 = Rs. 499.80 |
| Less than a one-user TallyPrime rental (Rs. 750 a month) | Tally's page "TallyPrime Pricing for Seasonal Businesses", updated 12 May 2026: https://tallysolutions.com/tally/tallyprime-pricing-for-seasonal-businesses/ (Silver, one user, Rs. 750 a month plus 18% GST) |

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
| DPDP Rules notified 13 Nov 2025 with an 18-month phase-in (PIB, Bar & Bench) | PIB and Bar & Bench, above (PIB gives 14 Nov 2025 as the notification date) |
| TallyPrime price from tallysolutions.com | Tally's page, above |

The Qwen2.5 3B license note is no longer on the slide. It is in `README.md`, section "License".

Left out: a market-size number. 2026 reports of Udyam (MSME) registrations disagree (7.83 crore and 8.84 crore), so
no statistic is on the slide.
