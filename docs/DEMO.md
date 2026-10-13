# Demo runbook (4-minute video)

## Before recording

1. Plug in the laptop (the GPU throttles on battery). Close heavy apps.
2. Turn Wi-Fi **off**. Everything below runs offline.
3. Set the power profile to performance: `powerprofilesctl set performance`.
4. OBS shares the GPU with the local model and roughly doubles check time. In OBS pick the x264 (CPU) encoder,
   or record with a light setting, and check that a scenario still answers in about 1 s.
5. Start the gateway and wait for `context layer ok`:
   ```sh
   uv run --frozen python -m flowguard
   ```
6. Open `http://127.0.0.1:8000` in a 1920×1080 browser window, zoom 100%.
7. Dry run: click every scenario once. The first click after a cold start can take 2–3 s.
8. If a scenario misbehaves on camera, click it again: the context model is small and not fully deterministic.
   Scenarios 1–7 pass as tests (`uv run --frozen pytest tests/test_scenarios.py`); run that first.

## Script

| Time | Show | Say |
|---|---|---|
| 0:00–0:25 | Title, then the start screen ("What happens when you press Check and send") | Clinics, CA firms and college offices paste client data into AI chatbots. Keyword filters can't tell when the same words are fine or a leak. FlowGuard decides per flow: what it is, whose it is, who sends it, where it goes, why. |
| 0:25–0:55 | Scenario 1: "Leave, no detail", then "Leave for chemotherapy" | Same scheduling request. The name passes because a scheduler needs it. Add "chemotherapy" and the local model flags a health detail; it leaves only as "[health detail]". Point at the rule in the Decisions table. |
| 0:55–1:25 | Scenario 2: "Internal HR summarizer", then "External marketing copilot" | Same sentence. HR on the internal model: salary passes. Sales to an external marketing tool: the whole request is blocked, nothing crosses the dashed line. |
| 1:25–1:50 | Scenario 3: both PAN buttons | The PAN's 4th letter tells us who holds it. C means company: business data, passes. P means a person: masked as [PAN_1]. Presidio would redact both. |
| 1:50–2:10 | Scenario 4: both buttons | A valid Aadhaar (checksum) is masked. A 12-digit order number is left alone. Presidio checks the checksum too; our edge is what comes next. |
| 2:10–2:30 | Scenario 5 | Hinglish: "Rahul ka salary 14 lakh hai". Detected as pay, turned into a salary band. |
| 2:30–2:55 | Scenario 6: both buttons | Apple's public revenue passes. Our own revenue before Thursday's announcement is unpublished price-sensitive information: blocked. |
| 2:55–3:30 | Scenario 7 | A patient note goes to an external AI for a discharge summary. Names and phone become placeholders, age and date get coarser, clinical detail stays so the summary is useful. The reply comes back with the real names, put back on this laptop. Switch the reply to "As the AI wrote it" to show the AI only ever saw placeholders. |
| 3:30–3:50 | Untick "Local AI check", click scenario 1b again | If the local model is down, the UI says so: IDs and names are still caught, health details are not. No silent failure. |
| 3:50–4:00 | Results slide | Dev set: leak rate 2% vs 38% for Presidio with India recognizers on; over-redaction 0% vs 71%. Held-out numbers on the slide. |

## Facts for questions

- An outbound guard checks every request for any raw value masked in the conversation and refuses to send on a hit.
  A test simulates a masking bug and proves no network call happens (`tests/test_gateway.py`).
- The audit log stores HMAC tags, never raw values.
- Switching to a real external API: three lines in `.env`, no code change.
