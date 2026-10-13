## Results: `dev` split (86 examples, 169 gold spans)

### Gateway outcome

| System | Leak rate ↓ | Over-redaction ↓ | Protect/allow acc. | 4-way action acc. | Request blocks (TP/FP/FN) | Latency p50 / p95 |
|---|---|---|---|---|---|---|
| FlowGuard (full) | 3.0% (3/100) | 0.0% (0/69) | 98.2% | 98.2% | 5/0/0 | 890 / 2430 ms |
| FlowGuard (no context layer) | 39.0% (39/100) | 0.0% (0/69) | 76.9% | 75.7% | 0/0/5 | 38 / 55 ms |
| Presidio + India recognizers | 38.0% (38/100) | 71.0% (49/69) | 48.5% | — | 0/0/5 | 5 / 8 ms |

Leak rate = sensitive gold spans whose raw text reached the outbound payload. Over-redaction = spans that should pass but were altered or blocked.

### Detection F1 by label (n = gold spans)

| Label | n | FlowGuard (full) | FlowGuard (no context layer) | Presidio + India recognizers |
|---|---|---|---|---|
| AADHAAR | 8 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| PAN | 8 | 0.93 (P 1.00 R 0.88) | 0.93 (P 1.00 R 0.88) | 0.93 (P 1.00 R 0.88) |
| GSTIN | 3 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| IFSC | 1 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) | not supported |
| UPI | 2 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) | not supported |
| PHONE | 8 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| EMAIL | 3 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) |
| VEHICLE | 2 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) | 0.67 (P 1.00 R 0.50) |
| PERSON | 56 | 0.98 (P 1.00 R 0.96) | 0.96 (P 1.00 R 0.93) | 0.79 (P 0.67 R 0.96) |
| ORG | 9 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) | not supported |
| LOCATION | 3 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) | 0.46 (P 0.30 R 1.00) |
| AGE | 5 | 0.89 (P 1.00 R 0.80) | 0.89 (P 1.00 R 0.80) | not supported |
| DATE | 7 | 1.00 (P 1.00 R 1.00) | 1.00 (P 1.00 R 1.00) | not supported |
| HEALTH | 24 | 0.88 (P 1.00 R 0.79) | 0.00 (P 0.00 R 0.00) | not supported |
| COMPENSATION | 14 | 1.00 (P 1.00 R 1.00) | 0.00 (P 0.00 R 0.00) | not supported |
| MNPI | 6 | 1.00 (P 1.00 R 1.00) | 0.00 (P 0.00 R 0.00) | not supported |
| HR | 6 | 0.83 (P 0.83 R 0.83) | 0.00 (P 0.00 R 0.00) | not supported |
| LEGAL | 4 | 1.00 (P 1.00 R 1.00) | 0.00 (P 0.00 R 0.00) | not supported |
| *Identifiers + entities* | | **0.98** (P 1.00 R 0.97) | **0.97** (P 1.00 R 0.95) | **0.74** (P 0.72 R 0.76) |
| *Only labels Presidio supports* | | **0.98** (P 1.00 R 0.97) | **0.97** (P 1.00 R 0.95) | **0.82** (P 0.72 R 0.96) |
| *Context categories* | | **0.93** (P 0.98 R 0.89) | **0.00** (P 0.00 R 0.00) | **0.00** (P 0.00 R 0.00) |

### Leak rate by language

| System | en | hinglish |
|---|---|---|
| FlowGuard (full) | 2.8% (2/72) | 3.6% (1/28) |
| FlowGuard (no context layer) | 36.1% (26/72) | 46.4% (13/28) |
| Presidio + India recognizers | 34.7% (25/72) | 46.4% (13/28) |
