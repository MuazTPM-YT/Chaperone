## Inference leaks: `dev` split (32 messages, 28 forbidden attributes)

Grader: `llama3.1:8b` with its own yes/no prompt (the in-loop attacker is qwen2.5:3b with different prompts). On the raw text the grader could infer 23 of 28 attributes; leak rates below use those as the denominator. Grader sanity check: asked each claim about an unrelated control message, it said yes 1 of 28 times.

| System | Inference leak rate ↓ | Proxies | Quasi-identifiers | Hinglish | Usefulness ↑ | Blocked | False alarms on controls | Latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|
| Names and IDs only (our ablation) | **100% (23/23)** | 100% (16/16) | 100% (9/9) | 100% (5/5) | 94% | 0/32 | 0/6 | 2055 / 3688 ms |
| Chaperone, attacker and purpose off | **70% (16/23)** | 62% (10/16) | 67% (6/9) | 80% (4/5) | 88% | 0/32 | 0/6 | 439 / 949 ms |
| Chaperone full | **30% (7/23)** | 19% (3/16) | 44% (4/9) | 40% (2/5) | 84% | 2/32 | 0/6 | 3840 / 7146 ms |

- **Inference leak rate**: forbidden attributes the grader can still conclude from the outbound text.
- **Usefulness**: share of the task's key facts (names, days, amounts) present in the restored reply from the simulated external model. A keyword check, not a quality judgement.
- **False alarms**: control messages (nothing personal to infer) that the system changed or blocked.
- **Latency** is the time to build the outbound text on this laptop. The names-and-IDs row also runs one attacker pass, because the UI shows what that pass finds.

Messages: both 2, control 6, proxy 15, quasi 9.
