## Results: `dev` split (86 examples, 169 gold spans)

### Gateway outcome

| System | Leak rate ↓ | Over-redaction ↓ | Protect/allow acc. | 4-way action acc. | Request blocks (TP/FP/FN) | Latency p50 / p95 |
|---|---|---|---|---|---|---|
| FlowGuard (full) | 1.0% (1/100) | 2.9% (2/69) | 98.2% | 97.6% | 5/0/0 | 954 / 4618 ms |
| FlowGuard (no context layer) | 39.0% (39/100) | 0.0% (0/69) | 76.9% | 75.7% | 0/0/5 | 38 / 57 ms |

Leak rate = sensitive gold spans whose raw text reached the outbound payload. Over-redaction = spans that should pass but were altered or blocked.

### Detection F1 by label (n = gold spans)

| Label | n | FlowGuard (full) | FlowGuard (no context layer) |
|---|---|---|---|
| AADHAAR | 8 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| PAN | 8 | 0.93 (P 1.00 R 0.88) | 0.93 (P 1.00 R 0.88) |
| GSTIN | 3 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| IFSC | 1 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| UPI | 2 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| PHONE | 8 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| EMAIL | 3 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| VEHICLE | 2 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| PERSON | 56 | 0.98 (P 1.00 R 0.96) | 0.96 (P 1.00 R 0.93) |
| ORG | 9 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| LOCATION | 3 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| AGE | 5 | 0.89 (P 1.00 R 0.80) | 0.89 (P 1.00 R 0.80) |
| DATE | 7 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| HEALTH | 24 | 0.82 (P 0.78 R 0.88) | 0.00 (P 0.00 R 0.00) |
| COMPENSATION | 14 | 1.00 (P 1.00 R 1.00) | 0.00 (P 0.00 R 0.00) |
| MNPI | 6 | 1.00 (P 1.00 R 1.00) | 0.00 (P 0.00 R 0.00) |
| HR | 6 | 0.83 (P 0.83 R 0.83) | 0.00 (P 0.00 R 0.00) |
| LEGAL | 4 | 1.00 (P 1.00 R 1.00) | 0.00 (P 0.00 R 0.00) |
| *Identifiers + entities* | | **0.98** (P 1.00 R 0.97) | **0.97** (P 1.00 R 0.95) |
| *Only labels Presidio supports* | | **0.98** (P 1.00 R 0.97) | **0.97** (P 1.00 R 0.95) |
| *Context categories* | | **0.90** (P 0.88 R 0.93) | **0.00** (P 0.00 R 0.00) |

### Leak rate by language

| System | en | hinglish |
|---|---|---|
| FlowGuard (full) | 0.0% (0/72) | 3.6% (1/28) |
| FlowGuard (no context layer) | 36.1% (26/72) | 46.4% (13/28) |
