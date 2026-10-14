# Demo runbook (4-minute video)

## Before recording

1. Plug in the laptop (the GPU throttles on battery). Close heavy apps.
2. Turn Wi-Fi **off**. Everything below runs offline.
3. Set the power profile to performance: `powerprofilesctl set performance`.
4. OBS shares the GPU with the local model and roughly doubles check time. In OBS pick the x264 (CPU) encoder,
   or record with a light setting, and check that a scenario still answers in about 1 s.
5. Start the gateway and wait for `context layer ok`:
   ```sh
   uv run --frozen python -m chaperone
   ```
6. Open `http://127.0.0.1:8000` in a 1920×1080 browser window, zoom 100%.
7. Dry run: click every scenario once. The first click after a cold start can take 2–3 s.
8. If a scenario misbehaves on camera, click it again: the context model is small and not fully deterministic.
   The scenarios pass as tests (`uv run --frozen pytest tests/test_scenarios.py`); run that first.

## Script

| Time | Show | Say |
|---|---|---|
| 0:00–0:20 | Start screen ("What happens when you press Check and send") | Clinics, CA firms and college offices paste client data into AI chatbots. Masking names is the floor; many tools do it. Chaperone also attacks its own message before it leaves. |
| 0:20–0:45 | Scenario 1a, then 1b | Same scheduling request. The name passes because a scheduler needs it. Add "chemotherapy" and it leaves only as a vague health placeholder. Point at the rule in the Decisions table. |
| 0:45–1:05 | Scenario 2a, then 2b | Same sentence. HR on the internal model: salary passes. Sales to an external marketing tool: the whole request is blocked. |
| 1:05–1:20 | Scenario 3b, then 4a | A personal PAN and a valid Aadhaar are masked; a company PAN and an order number are not. Checksums and holder type, on the laptop. |
| 1:20–2:00 | Scenario 8a "Medicine, no diagnosis" | No diagnosis is written. Open "What an attacker could infer": the local attacker reads "tamoxifen" and infers breast cancer. That is forbidden in this flow, so the drug becomes vague and the attacker runs again. Mask-only tools would send "tamoxifen" as is. |
| 2:00–2:25 | Scenario 8b "Our only female cardiologist" | No name at all, but "our only female cardiologist" in Udupi points to one person. The attacker says so; the description is made vaguer before sending. |
| 2:25–3:00 | Scenario 7 "Discharge summary" | Names masked. Age and date leave vague, `[AGE_1: in their 50s]`, and come back exact in the reply. The wife's phone is omitted: a discharge summary does not need it. If the reply invents an age, it is underlined as "not in your message". |
| 3:00–3:20 | Scenario 10 "three flows" (or Compare three flows) | One message, three flows, side by side. The doctor's clinical summary keeps the drug; the manager's external note does not. |
| 3:20–3:40 | Safe Harbor switch, scenario 9 | HIPAA Safe Harbor mode: dates go to the year, places go. Indian IDs are our adaptation. It removes identifiers; it does not make anyone compliant. |
| 3:40–4:00 | Results slide | Dev numbers from `eval/results/`: inference leak rate for names-and-IDs-only vs Chaperone, usefulness, latency. Say they are dev numbers. |

## Facts for questions

- An outbound guard checks every request for any raw value masked in the conversation and refuses to send on a hit.
  A test simulates a masking bug and proves no network call happens (`tests/test_gateway.py`).
- The audit log stores HMAC tags, never raw values.
- Switching to a real external API: three lines in `.env`, no code change.
- The attacker is local qwen2.5:3b, at most 2 tightening rounds. If it is still not cleared, nothing is sent.
- "No inference found by the local check" is not "safe". A bigger model may infer more.
- Agents can use the same checks over MCP: `uv run --frozen python -m chaperone.mcp_server`.
