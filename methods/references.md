# References

Each entry was checked on 2026-10-18 against the publisher, the venue's proceedings or Crossref. "Use" says how the
work relates to Chaperone: **basis** (we use the method as published), or **inspiration** (we built something based on
the idea, not a reproduction). Details of each step are in [techniques.md](techniques.md).

| Short form | Full citation | Checked at | Step | Use |
|---|---|---|---|---|
| Verhoeff 1969 | J. Verhoeff. *Error Detecting Decimal Codes*. Mathematical Centre Tracts 29. Mathematisch Centrum, Amsterdam, 1969. | CWI repository (ir.cwi.nl/pub/13046) | 1 | Basis: the Aadhaar check digit, run by python-stdnum. |
| Zaratiana et al. 2024 | U. Zaratiana, N. Tomeh, P. Holat, T. Charnois. "GLiNER: Generalist Model for Named Entity Recognition using Bidirectional Transformer." *NAACL 2024* (Vol. 1, Long Papers), pp. 5364–5376. | ACL Anthology 2024.naacl-long.300 | 1, 8 | Basis: we run the published `gliner_small-v2.1` model. |
| Nissenbaum 2004 | H. Nissenbaum. "Privacy as Contextual Integrity." *Washington Law Review* 79(1):119, 2004. | UW Law Digital Commons (wlr/vol79/iss1/10) | 2 | Inspiration: rules decide by sender, recipient, subject, information type and purpose. No formal CI logic. |
| Sweeney 2002 | L. Sweeney. "Achieving k-Anonymity Privacy Protection using Generalization and Suppression." *International Journal on Uncertainty, Fuzziness and Knowledge-based Systems* 10(5):571–588, 2002. | Author's page (dataprivacylab.org), DOI 10.1142/S021848850200165X | 3 | Terms only: "generalization" and "suppression". **No k-anonymity guarantee.** |
| HIPAA Safe Harbor | US 45 CFR 164.514(b)(2), de-identification by removing 18 identifier types. | Regulation text, cited in `policies_safe_harbor.yaml` | 2, 3 | Basis for the Safe Harbor rule pack (13 of 18 types detected in text). Not a compliance claim. |
| Staab et al. 2024 | R. Staab, M. Vero, M. Balunović, M. Vechev. "Beyond Memorization: Violating Privacy via Inference with Large Language Models." *ICLR 2024*. arXiv 2310.07298. | OpenReview PDF ("Published as a conference paper at ICLR 2024"), iclr.cc/virtual/2024/poster/17964 | 5 | Inspiration: the threat the attacker tests for. |
| Staab et al. 2025 | R. Staab, M. Vero, M. Balunović, M. Vechev. "Language Models are Advanced Anonymizers." *ICLR 2025*. arXiv 2402.13846 (arXiv title: "Large Language Models are Advanced Anonymizers"). | ICLR 2025 proceedings and poster page (iclr.cc/virtual/2025/poster/30788) | 5 | Inspiration: attacker and rewriter take turns. Ours is a 3B model, policy-scoped, max 2 rounds, then refuse. |
| RFC 2104 | H. Krawczyk, M. Bellare, R. Canetti. "HMAC: Keyed-Hashing for Message Authentication." RFC 2104, February 1997. | rfc-editor.org/rfc/rfc2104 | 9 | Basis: HMAC-SHA256 via Python's `hmac` module. |
| Haber & Stornetta 1991 | S. Haber, W. S. Stornetta. "How to Time-Stamp a Digital Document." *Journal of Cryptology* 3(2):99–111, 1991. | Crossref, DOI 10.1007/BF00196791 | 9 | Inspiration: each entry's value is chained into the next. No time-stamping service. |
| Schneier & Kelsey 1999 | B. Schneier, J. Kelsey. "Secure Audit Logs to Support Computer Forensics." *ACM Transactions on Information and System Security* 2(2):159–176, May 1999. | Crossref, DOI 10.1145/317087.317089 | 9 | Inspiration: MAC-chained log entries. We use one fixed key, so no forward security. |

Notes from checking:

- The arXiv page of 2402.13846 says "ICLR 2024" in its comment field. The paper is in the **ICLR 2025** proceedings,
  so 2025 is used here.
- Schneier's own site lists the TISSEC paper as "v. 1, n. 3"; Crossref says volume 2, issue 2. Crossref is used here.
- The GSTIN check character uses the Luhn mod N algorithm (N = 36). It is named in techniques.md but not cited: we
  found no primary paper for Luhn mod N, only Luhn's 1960 patent for the decimal version.
