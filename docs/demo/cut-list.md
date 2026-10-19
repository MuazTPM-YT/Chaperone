# What the video leaves out, and why

- **PAN on an invoice (3a, 3b):** company PAN passes, personal PAN is masked. Good, but it's detail; the README covers it.
- **Twelve digits (4a, 4b):** the Aadhaar checksum. Same reason: a detail judges can read on slide 4.
- **Q3 revenue (6a, 6b):** public results pass, our own are blocked. Slides 2 and 3 already lead with it; the salary scene shows blocking.
- **Leave for chemotherapy (1a, 1b):** the attacker scene shows the same idea more strongly.
- **Medicine, no diagnosis (8a, tamoxifen):** the rules already make "tamoxifen" vague, so the attacker found nothing to tighten in 5 of 5 runs. The Hinglish note shows tightening every time.
- **Rahul ka salary (5, Hinglish):** salary is already in scene 2, and Hinglish is in scene 3.
- **Compare dialog (scenario 10, "Compare three flows"):** the button uses fixed flows (Doctor internal, Doctor external, Intern external). HR internal, Sales marketing and Intern can't be picked in the page, so scene 2 uses three sends.
- **HIPAA Safe Harbor mode (9):** needs time to explain what "modelled on HIPAA Safe Harbor" means; slide 7 covers it.
- **Rules panel and admin editing:** rules as YAML is on slide 4; editing them needs a restart with admin mode.
- **Include anyway:** a niche control; the purpose scene already shows the phone being left out.
- **Exposure ledger and the processing record CSV:** useful, but the person report and seal tell the same story faster.
- **A send to a real hosted AI:** no hosted AI key is set up (`.env` points the external AI at the local Ollama), so we can't show it honestly.
- **An internal send while Ollama is off:** in this setup the internal model is also Ollama, so it fails with "LLM call failed: ConnectError". That would confuse the fails-closed point.
- **Eval method and held-out set:** slide 6 covers it; the video only flashes the numbers and the "best-case" note.
