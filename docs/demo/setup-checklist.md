# Before recording

Do these in order. Commands are for fish, from the repo folder unless they say otherwise.

## 1. Laptop

- [ ] Plug in the charger. The GPU slows down on battery.
- [ ] `powerprofilesctl set performance`
- [ ] Close heavy apps (browsers with many tabs, IDEs).
- [ ] Turn on Do Not Disturb in your desktop, so no notifications show.
- [ ] Wi-Fi can stay on. Chaperone makes no internet calls in this setup (the external AI is simulated on the
  laptop). Scene 7 needs the internet, because Claude Code runs on Anthropic's servers.
- [ ] Screen recorder: 1920×1080, 30 fps. In OBS, use the x264 (CPU) encoder. A GPU encoder shares the GPU with the
  local model and makes every check slower.

## 2. Start Ollama and the gateway, then warm up

- [ ] `sudo systemctl start ollama`, then `ollama list`. It must show `qwen2.5:3b`.
- [ ] Stop any gateway that is already running (port 8000). Then start a fresh one, so every placeholder map and
  cache is empty:
  `uv run --frozen python -m chaperone`
  Wait for `context layer ok` (about 5 s).
- [ ] Warm up: in the page, run each scene once. This loads the models and fills the detection cache, so the
  recording waits are short:
  - Internal HR summarizer, External marketing copilot, the Intern salary send (scene 2)
  - the Hinglish text (scene 3), Our only female cardiologist
  - Discharge summary
- [ ] **Do not send the Offline text** (scene 6) now. If it is checked once with Ollama on, the result is cached, and
  in scene 6 the top bar stays green. The send is still blocked, but the red "offline" note doesn't show.

## 3. Audit log: clear or keep? (decide once)

| | What the person report and seal check show |
|---|---|
| **A. Fresh log for the recording (recommended)** | Only the requests you record. The seal toast says "Seal intact over N lines" and nothing else. |
| B. Keep the current log | 50+ rows for "Ramesh Rao" from testing, and the toast adds "207 older lines were written before sealing and cannot be checked." |

For A, after the warm-up and before scene 2, move the log aside. The gateway starts a new one with the next request:

```fish
mv data/audit.jsonl data/audit.before-demo.jsonl
```

After recording, keep the demo log and put the old one back:

```fish
mv data/audit.jsonl data/audit.demo.jsonl
mv data/audit.before-demo.jsonl data/audit.jsonl
```

## 4. Terminal (scenes 5, 6 and 7)

- [ ] Font size 20 pt or more, light or dark to match the browser. Window maximised.
- [ ] Hide your user name and folders from the prompt for this session:
  `function fish_prompt; echo '$ '; end`
- [ ] `cd` to the repo folder before recording, then `clear`.
- [ ] Make the demo folder: `mkdir -p /tmp/chaperone-demo`
- [ ] Add the seal-check helper for this session. It runs the same `verify_log` function as the "Check the audit log
  seal" button, but on the file you give it:

  ```fish
  function sealcheck
      uv run --frozen --directory ~/Documents/Software/DevHack2026 python -c "import sys; from pathlib import Path; from chaperone import gateway; gateway.AUDIT_PATH = Path(sys.argv[1]).resolve(); r = gateway.verify_log(); print(\"Seal intact.\" if r[\"ok\"] else f\"Seal broken at line {r[\"broken_at\"]}. {r[\"reason\"]}\")" $argv 2>/dev/null
  end
  ```

- [ ] Just before scene 5, pick the line to change. It must contain `"sent": true`:
  `grep -n '"sent": true' data/audit.jsonl | cut -c1-40 | head -3`
  Put that line number in the `sed` command of scene 5 (the script uses 3 as an example).
- [ ] Never edit `data/audit.jsonl` itself. Scene 5 only edits `/tmp/chaperone-demo/copy.jsonl`.

## 5. Claude Code for scene 7

- [ ] Write `/tmp/chaperone-demo/mcp.json` (change the folder if your repo is somewhere else):

  ```json
  {"mcpServers": {"chaperone": {"command": "uv", "args": ["run", "--frozen", "--directory", "/home/Muaz/Documents/Software/DevHack2026", "python", "-m", "chaperone.mcp_server"]}}}
  ```

- [ ] Start Claude Code in the demo folder, with only this MCP server and permission for the check tool:

  ```fish
  cd /tmp/chaperone-demo
  claude --strict-mcp-config --mcp-config mcp.json --allowedTools mcp__chaperone__chaperone_check
  ```

- [ ] The prompt to paste:

  `Before you draft anything, run this message through the chaperone_check tool as a Manager sending to an external AI for a general purpose, then show me exactly what would leave: Rakesh ka HbA1c 9.1 aaya, doctor ne metformin shuru kiya. Next week ki review meeting reschedule karo.`

- [ ] Rehearse once. The first call starts the MCP server and loads the models (about 10 s). Check the start
  banner for your email or folders, and crop or cut it if they show.
- [ ] Your own Claude Code settings (CLAUDE.md, hooks, output style) also load, and they change how the agent
  writes its answer. Cut the clip after the tool result, before the agent's own summary.

## 6. Browser

- [ ] Use a guest window or a new profile: no bookmarks bar, no extensions, no other tabs.
- [ ] Open `http://127.0.0.1:8000`, then full screen (F11).
- [ ] Zoom 125%. Don't go above 140%: under 1360 page pixels the side rail turns into a drawer.
- [ ] Theme: click the theme button (top right) until it is light.
- [ ] Click **New chat** before each scene.

## 7. Slides for scene 8

- [ ] Export slides 5 (architecture) and 6 (numbers) of `~/Downloads/DevHack-fixed-shots.pptx` as 1920×1080 PNG
  (PowerPoint or LibreOffice Impress: File, Export).
- [ ] Make the end card: the Chaperone start screen, dimmed, with `github.com/MuazTPM-YT/Chaperone` in large text.
  The repo is private today, so a viewer gets a 404. Make it public before you submit, or change the end card.

## 8. Only fictional data on screen

- [ ] Use only the preset texts and the three fixed texts in `script.md`. Every name, phone number and amount in
  them is made up.
- [ ] Never open `.env` on camera. There is no hosted AI key in this setup, and none may appear.
- [ ] The text editor in scene 1: an unsaved buffer, so no file path shows in the title bar.
- [ ] Cut the `sudo` password prompt in scene 6.

## 9. Recording order

Record in this order, then edit into the script order:

1. Scene 1 (editor, then the start screen) and the end card.
2. Scenes 2, 3 and 4. For scene 4, repeat **New chat** and **Discharge summary** until a take shows the invented-age
   flag (3 of 12 test runs had it, about 5 s a take).
3. Scene 5 (needs the scene 4 requests in the log).
4. Scene 7 (needs Ollama on).
5. Scene 6 last, because it stops Ollama. Then `sudo systemctl start ollama`. The first message after that takes
   about 6 s.
6. Put the audit log back (section 3).
