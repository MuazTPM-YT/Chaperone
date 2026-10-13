# Evaluation data

- `dev.jsonl`: written by the builder, used for tuning. Numbers on it are optimistic.
- `heldout.jsonl`: written by teammates **without reading `flowguard/`**. Never tune on it. Its numbers go on the slides.

## Add a held-out case

```sh
uv run python eval/add_case.py
```

The tool asks for the message, the flow (sender role, destination, purpose), and the spans. It checks that each
span is copied exactly from the message.

Good cases are realistic messages from a clinic, CA firm, college office or small company. Write **contrast
pairs**: the same text sent in two flows with different correct outcomes (give both the same `pair` id). Mix
English and Hinglish. Include tricky negatives: public facts, invoice amounts, numbers that look like IDs.

## What to label

Label every span of these types, including ones that should pass:

| Label | Meaning |
|---|---|
| AADHAAR, PAN, GSTIN, IFSC, UPI, PHONE, EMAIL, VEHICLE | Indian identifiers and contact details |
| PERSON, ORG, LOCATION | Named people, organisations, places |
| AGE, DATE | An exact age or calendar date about a person |
| HEALTH | A specific person's condition, diagnosis, treatment, pregnancy |
| COMPENSATION | A specific person's pay amount (label the amount) |
| MNPI | Our company's unpublished results, deals or plans |
| HR | A specific person's rating, warning, disciplinary step, PIP |
| LEGAL | A lawsuit, complaint or court case about a person or our company |

## The house rules (decide the action from these)

Actions: `pass` (sent as is), `pseudonymize` (swapped for a placeholder, restored in the reply), `generalize`
(made vague for good, e.g. salary becomes a band), `block` (removed). If the whole request is blocked, mark every
span `block` and answer "yes" to "whole request blocked?".

Destinations: `internal` = the organisation's own model; `external` = a third-party AI service.

1. Unpublished company results or deals going **external**: block the whole request.
2. Pay data going to an external **marketing** tool: block the whole request.
3. Business data (company/firm PAN, a company's GSTIN, IFSC, company names, role mailboxes like accounts@): pass.
4. **Interns**: health, pay, HR, legal and MNPI details are blocked; personal IDs and names are pseudonymized.
5. **Doctors**: health details pass internally, and pass externally only for a `clinical_summary`.
6. **HR and Accountants**: pay passes internally. **HR and Managers**: HR and legal matters pass internally.
   **Managers and Accountants**: MNPI passes internally.
7. Any other health, pay, MNPI, HR or legal detail: generalize.
8. Everything else going **internal**: pass.
9. External **scheduling**: names and dates pass.
10. External **clinical_summary**: exact age and date are generalized.
11. Ages, dates and places otherwise pass.
12. Personal IDs and names going external: pseudonymize.
13. Anything not covered: pseudonymize.
14. **Purpose minimisation** (applies before rules 1 to 13 can send anything): identifiers the stated purpose does
    not need are left out (`block`). Clinical summary: phone, email, UPI, Aadhaar, PAN, GSTIN, IFSC, vehicle.
    HR summary: UPI, Aadhaar, GSTIN, IFSC, vehicle. Scheduling: UPI, Aadhaar, PAN, GSTIN, IFSC, vehicle. Marketing:
    all identifiers. Invoicing: Aadhaar, vehicle. General: nothing.

A GSTIN whose 6th character is `P` belongs to a sole proprietor, so it is personal. A span inside a wider
span that gets a stricter action takes that stricter action.
