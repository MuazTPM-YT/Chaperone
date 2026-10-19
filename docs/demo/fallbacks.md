# If a scene goes wrong while recording

General rule: click **New chat** and take it again. The local model is small and not fully the same every run.
Never change the voiceover to describe something the take doesn't show.

Backup pictures from real runs are in `docs/screenshots/`. Record a backup take of every scene during the rehearsal
too, and cut to it if the live take fails.

| Scene | What goes wrong | What to do |
|---|---|---|
| Any | Waits are much longer than in `script.md` (slow GPU) | Check OBS uses the x264 (CPU) encoder and the laptop is plugged in. Cut the wait in editing. If one check takes more than 10 s, restart the gateway and warm up again. |
| Any | The page says "Could not reach the gateway" | The gateway stopped. Run `uv run --frozen python -m chaperone` again, wait for `context layer ok`, warm up. |
| Any | Top bar says "Local AI check: offline" when it shouldn't | Ollama is down. `sudo systemctl start ollama`, then send one warm-up message (about 6 s). |
| 2 | The Intern send also shows the earlier chat | You didn't click **New chat** first. Take it again. |
| 3 | The attacker finds nothing in round 1 (no amber "!"), or blocks the message ("Still inferable") | Take it again. In testing, 5 of 5 runs tightened "HbA1c" and passed on round 2. Backup: `docs/screenshots/attacker-hinglish.png` (a real run, same result as the script). |
| 3 | The cardiologist reply is full of made-up placeholders like `[BRANCH_NAME]` | Expected: the AI invents them. Don't show the reply. Show only the attacker Details and "External AI received" (scroll up). |
| 3 | Over time | Drop the cardiologist part (1:28 to 1:41) and its two voiceover sentences. Saves about 13 s. |
| 4 | No take shows the invented-age flag after 8 takes | Cut to `docs/screenshots/s7.png` for 2:06 to 2:13 (a real run with "50-year-old" flagged). Keep the voiceover. |
| 4 | Details shows "sent as as typed" under the Allowed health items | A small text bug in the page. Don't scroll down to the Allowed items; stop at "Left out, Phone". |
| 5 | The person report is empty | The fresh log has no discharge request yet. Record scene 4 first. Type the name exactly: `Ramesh Rao`. |
| 5 | `sealcheck` says "Seal intact." on the copy | The `sed` didn't match: that line has no `"sent": true`. Pick another line with the `grep` in the checklist and copy the log again. |
| 5 | `sealcheck` prints nothing | The function isn't defined in this terminal. Paste it again from the checklist. |
| 6 | The top bar stays green after stopping Ollama | That text was checked before with Ollama on (cached). Send a text never used before, e.g. `Draft a note to the team: Kavya is off on Friday for her dental surgery, her calls move to Arjun.` The block happens either way; only the red "offline" note needs a new text. |
| 6 | Ollama doesn't come back | `sudo systemctl restart ollama`, then `ollama list`. |
| 7 | Claude Code asks for permission for the tool | Start it again with `--allowedTools mcp__chaperone__chaperone_check` (see the checklist). |
| 7 | Claude Code doesn't find the tool | Type `/mcp` in Claude Code to see the server state. Check the folder in `mcp.json`. |
| 7 | Claude Code fails or is down | Show the MCP server directly instead (same JSON result, tested): pipe the three JSON-RPC lines from `fallbacks-mcp` below into `uv run --frozen python -m chaperone.mcp_server`. Then change the voiceover line to "Here an agent's tool call goes through Chaperone first." |

## fallbacks-mcp

Run from the repo folder. The last line of output is the `chaperone_check` result.

```fish
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"chaperone_check","arguments":{"text":"Rakesh ka HbA1c 9.1 aaya, doctor ne metformin shuru kiya. Next week ki review meeting reschedule karo.","role":"Manager","destination":"external","purpose":"general"}}}' | uv run --frozen python -m chaperone.mcp_server 2>/dev/null
```
