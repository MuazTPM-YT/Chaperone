## Results: `dev` split (86 examples, 169 gold spans)

### Gateway outcome

| System | Leak rate ↓ | Over-redaction ↓ | Protect/allow acc. | 4-way action acc. | Request blocks (TP/FP/FN) | Latency p50 / p95 |
|---|---|---|---|---|---|---|
| FlowGuard (full) | 2.0% (2/102) | 3.0% (2/67) | 97.6% | 97.0% | 5/0/0 | 1985 / 13131 ms |
| FlowGuard (no context layer) | 38.2% (39/102) | 0.0% (0/67) | 76.9% | 75.7% | 0/0/5 | 40 / 52 ms |
| Presidio + India recognizers | 37.3% (38/102) | 70.1% (47/67) | 49.7% | — | 0/0/5 | 6 / 9 ms |

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
| HEALTH | 24 | 0.73 (P 0.65 R 0.83) | 0.00 (P 0.00 R 0.00) | not supported |
| COMPENSATION | 14 | 1.00 (P 1.00 R 1.00) | 0.00 (P 0.00 R 0.00) | not supported |
| MNPI | 6 | 1.00 (P 1.00 R 1.00) | 0.00 (P 0.00 R 0.00) | not supported |
| HR | 6 | 0.83 (P 0.83 R 0.83) | 0.00 (P 0.00 R 0.00) | not supported |
| LEGAL | 4 | 1.00 (P 1.00 R 1.00) | 0.00 (P 0.00 R 0.00) | not supported |
| *Identifiers + entities* | | **0.98** (P 1.00 R 0.97) | **0.97** (P 1.00 R 0.95) | **0.74** (P 0.72 R 0.76) |
| *Only labels Presidio supports* | | **0.98** (P 1.00 R 0.97) | **0.97** (P 1.00 R 0.95) | **0.82** (P 0.72 R 0.96) |
| *Context categories* | | **0.85** (P 0.80 R 0.91) | **0.00** (P 0.00 R 0.00) | **0.00** (P 0.00 R 0.00) |

### Leak rate by language

| System | en | hinglish |
|---|---|---|
| FlowGuard (full) | 1.4% (1/74) | 3.6% (1/28) |
| FlowGuard (no context layer) | 35.1% (26/74) | 46.4% (13/28) |
| Presidio + India recognizers | 33.8% (25/74) | 46.4% (13/28) |
