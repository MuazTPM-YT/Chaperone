# Slides 6 to 8: full text

Every line on slides 6 to 8, top to bottom, left to right, so it can be retyped by hand. **Bold** marks the bold
words. Sources for each claim: `docs/slides-6-8-facts.md`.

## Slide 6: Impacts and Benefits

*Intro box (grey):* We tested **Chaperone** on office messages we wrote and labelled ourselves, in English and Hinglish.
Each time we asked one thing: after the checks, what can a reader of the outgoing text still find out?

**What we measured**

Three light-green tiles:

1. **23/23 → 7/23**
   **hidden facts a reader could still guess**
   Names-and-IDs-only masking vs Chaperone, judged by a separate grader model. 32 messages, 23 guessable facts; the
   middle of 5 runs (range 7 to 9).
2. **2% vs 37%**
   **of sensitive details still sent**
   Chaperone vs Presidio with its India recognizers: 2 vs 38 of 102 details, in 86 labelled messages. Presidio also
   changed 70% of details that should pass; we changed 3%.
3. **3.3 s**
   **per message on a 4 GB laptop**
   Middle of 32 runs on an RTX 3050 laptop, AI reply included. Every check runs on the laptop itself.

**Who it helps**

1. **Staff keep using AI.**
   The receptionist can still ask a chatbot to finish the discharge notes. Names go out as [PERSON_1] and come back
   **filled in**, so nobody has to remember what to delete.
2. **Owners can show where data went.**
   DPDP (India's data protection law) wants personal data used only for a stated purpose. Each message carries one,
   and a **sealed log** shows where data went.
3. **Patients and clients keep their secrets.**
   A diagnosis, a salary or a court case stays on the laptop unless the flow allows it. A drug name that **gives
   away** an illness is made vague first.
4. **Made for Indian offices.**
   It checks **Aadhaar and PAN** check digits, reads Hinglish, and runs on an ordinary laptop with a 4 GB GPU. The
   checks need no cloud account.

*Note (grey italic):* How we tested: 86 and 32 messages, written, labelled and tuned on by our team. Results on a
held-out set, still being filled, are the ones that count.

## Slide 7: Business Impact & Scalability

*Intro box (grey):* The checks run on a laptop the office already has, so starting costs little. What we'd charge for
is the part that grows with the office: **shared rules and audit** for many offices, and ready rule packs per sector.

**Cost**

- [Built] **Runs on what they own.**
  One laptop with a 4 GB GPU. The checks use open models on it (Qwen2.5 3B, GLiNER), so there's **no cloud bill**.¹
- [Built] **No per-seat DLP licence.**
  Enterprise DLP (data loss prevention) is priced for banks. Our code is open source (MIT) and sets up with **one
  script**.

**Revenue**

- [Built] **Open-source core.**
  The gateway, rules, attacker and audit log stay **free** to use and to read.
- [Next] **Paid hosted dashboard.**
  One place to set the rules for several offices and read their **sealed logs**.
- [Next] **Sector rule packs.**
  One pack ships today (HIPAA Safe Harbor, for clinics). **Finance, HR and education** come next.

**Market**

- **A deadline for everyone.**
  The DPDP Rules give every data fiduciary (anyone deciding how personal data is used) until **13 May 2027**.²
- **Who we start with.**
  Clinics, CA firms, college offices and SMEs (small and medium businesses): client data, and **no IT team** for DLP.

**How it scales**

Three light-green cards:

- **Users**
  - [Built] One laptop, one person
  - [Next] One office server, with a login
  - [Next] Many offices, one policy dashboard
- **Locations**
  - [Built] Aadhaar, PAN, GSTIN, UPI and Hinglish
  - [Built] New rule sets as plain YAML files
  - [Next] ID and language packs per country or region
- **Use cases**
  - [Built] AI agents through MCP (how AI agents call tools)
  - [Next] A proxy for any OpenAI-compatible chat app
  - [Next] A browser extension for ChatGPT and Claude

*Footnotes (grey italic, 9 pt):*

¹ Qwen2.5 3B's licence covers research use, so a paid version would ship a local model licensed for business. It's one
setting (CONTEXT_MODEL).

² PIB, 17 Nov 2025: DPDP Rules notified with an 18-month phase-in. Bar & Bench, Nov 2025: Gazette dated 13 Nov 2025,
deadline 13 May 2027.

## Slide 8: Additional links

Three light-green cards with green numbers:

1. **GitHub repo**
   **https://github.com/MuazTPM-YT/devhack2026-round1**
   The code, the tests, the eval scripts with their saved results, and a README that shows how to check every number.
2. **Google Drive (demo video)**
   **[Drive link: to add]**
3. **Deployment (optional)**
   No hosted version on purpose: it runs on your own laptop. Setup takes a few commands (see the README).
   git clone, then ./setup.sh, then uv run --frozen python -m chaperone, and open 127.0.0.1:8000.

*Template note, unchanged:* (Rename The file name to your team name while submitting)
