# Handover: N810 + Oracle node (as of 2026-10-23)

Paste this into a new Claude chat to continue. Connections, launchers, the node's Ollama setup and the loaded model were checked and changed on 2026-10-21; billing was last checked 2026-10-16. Re-check anything marked "verify" before relying on it.

**Private details** (IP addresses, billing, budget alert, account type) live only in `N810-private.md` (git-ignored). This file is in the public repo; keep them out of it.

**Where things are:** commands, launchers and ports in `CHEATSHEET.md`; how each setup stage was done (clean the device, secure the connections, build on the node) in `N810-setup.md`; the art project in `PROJECT.md`. Update the cheat sheet whenever a command, launcher or service changes.

## Goal

Rose Chan (PSAM 5600 B, Small Linux Devices / Large Language Models, Fall 2026, instructor David Carroll) is building a project on a Nokia N810 (Maemo 4 "Diablo", 2008). The N810 is the interface. Heavy AI work runs on a free Oracle cloud node ("onode"), using a local open-source model (Gemma 4 e4b via Ollama) and the OpenCode coding tool. Final demo: show AI working on the N810's 800x480 screen.

## Machines and access

| Name | What | How to connect |
|---|---|---|
| Laptop | Windows 11, runs Claude Code | Project folder `C:\Users\email\Projects\n810-project` (git repo, `there-fore/n810-project`) |
| onode | Oracle Cloud, Ubuntu 24.04 arm64, instance `smalldevLLMnode`, US East (Ashburn) | From laptop: `ssh onode` (user `ubuntu`, port 22, ed25519 key) |
| onode2 | Same node, separate legacy SSH service for the N810 only | From N810: `ssh onode2` (user `n810`, port 2222, RSA key) |
| n810 | Nokia N810, Maemo 4, OpenSSH 4.7 | From laptop: `ssh n810` (root, RSA key, legacy flags in `~/.ssh/config`). IP is assigned by the phone hotspot and can change; current value in `N810-private.md`. |

The N810 normally runs as the regular user `user` (home `/home/user`), not root. Root can't see `user`'s files.

## Node state (verify)

- Resized 2026-10-16 from 16 OCPU / 96 GB to **4 OCPU / 23 GB** to cut cost. Boot disk 140 GB (can grow, not shrink). Swap 16 GB.
- **Ollama 0.40.5** on `127.0.0.1:11434`, model `gemma4:e4b` (6.6 GB). CPU only. A model must be loaded before a fast reply (`ollama ps`).
- Ollama settings (`/etc/systemd/system/ollama.service.d/override.conf`): `OLLAMA_CONTEXT_LENGTH=65536`, `OLLAMA_KEEP_ALIVE=-1`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`, flash attention on, `q8_0` KV cache.
- **Warm-up service** (added 2026-10-21): `/etc/systemd/system/ollama-warmup.service`, enabled and wanted by `ollama.service`. Every time Ollama starts, it waits for the API and loads `gemma4:e4b` with `keep_alive: -1`. Tested by restarting Ollama: the model was back in 16 s (about 1.5 min when not in the page cache). Undo: `sudo systemctl disable ollama-warmup` and delete the file.
- **needrestart rule** (added 2026-10-21): `/etc/needrestart/conf.d/ollama.conf` stops needrestart from restarting Ollama after automatic security updates, which would unload the model. Syntax checked; not yet tested on a real update.
- **OpenCode 1.19.3** at `/usr/local/bin/opencode` (copied for the `n810` user) and `~/.opencode/bin/opencode` (ubuntu user).
- **Legacy SSH on port 2222**: `ssh-legacy.service` runs `sshd` with `/etc/ssh/sshd_config.legacy`. Allows only user `n810`, key login only, SHA-1 KEX and ssh-rsa added. Port 22 is unchanged.
- Host firewall: TCP 2222 allowed and saved (`netfilter-persistent`).
- Oracle security list: TCP 2222 ingress from `0.0.0.0/0` added by Rose on the Default Security List of `vcn-sdllm`. This opens the port to the internet. The login is key-only.
- The `n810` user has its own key (`~/.ssh/authorized_keys` holds the N810's public key).
- **OpenCode config for `n810`** (fixed 2026-10-21): `/home/n810/.config/opencode/opencode.jsonc` defines a local `ollama` provider (`http://127.0.0.1:11434/v1`, model `gemma4:e4b`, also the default and small model) and raises `headerTimeout`/`chunkTimeout` to 15 min. Before this the file was empty, so `opencode run -m ollama/gemma4:e4b` failed with "Model not found" (shown on the N810 as "Unexpected server error"). The old file is `opencode.jsonc.bak`. The Oct 16 first-run log `/home/n810/warmup.log` (read with `sudo`) shows the same missing-model failure; it is no longer relevant.
- On 2026-10-21 `ollama ps` showed `gemma4:e4b` loaded, window 65536, `UNTIL Forever`, 100% CPU.
- Node-side helpers for the N810 (both in `/usr/local/bin`, updated 2026-10-21):
  - `n810-ask`: Python. Reads a question on stdin, calls Ollama's `/api/chat` directly (streaming, `think: false`, `keep_alive: -1`), prints plain text with Unicode punctuation swapped for ASCII. System prompt asks for short, plain-text answers for an 800x480 screen, and includes a short, correct N810 spec sheet that the model must use for N810 questions (without it, Gemma called the N810 a Series 40 smartphone with a 2.1-inch screen). No OpenCode, so replies start in seconds. The version without the spec sheet is `n810-ask.bak`.
  - `n810-agent`: shell. Reads a task on stdin and runs `opencode run -m ollama/gemma4:e4b` in `~/work` with `TERM=dumb NO_COLOR=1`. OpenCode sends about 6,700 tokens first, so it takes minutes. `~/work` holds one test file, `notes.txt`.
  - The only copies of these scripts and the N810 launchers are on the node and the N810; they are not in the repo.
- **llamatalk** (added 2026-10-23, ubuntu user, details and measurements in `N810-setup.md`): speech recognition, Gemma 4 E2B and text-to-speech servers, built from source in `~/llamatalk`, models in `~/llamatalk-models` (4.4 GB). They listen on `127.0.0.1` only: 8091 speech recognition (Qwen3-ASR), 8092 language model (Gemma E2B), 8093 speech (Pocket TTS). Start with `~/llamatalk/start.sh`, stop with `~/llamatalk/stop.sh`. Not a systemd service: after a reboot they stay off. About 6.7 GB of RAM in use; 11.6 GB stayed free with `gemma4:e4b` also loaded. Measured: E2B answers a short question in 2.1 s (21 tok/s), speech at about 2x real time, recognition 1.3 s. Nothing on the N810 uses them yet. Ollama, the warm-up service and the n810 helpers were not changed.

## N810 state (verify)

- Laptop can log in to the N810 as root with `ssh n810` (key `~/.ssh/id_rsa_n810`).
- The N810 has its own key for onode: `/root/.ssh/id_rsa_onode` (no passphrase), copied also to `/home/user/.ssh/`.
- Short name `onode2` is in `/root/.ssh/config` and `/home/user/.ssh/config` (the user copy points at `/home/user/.ssh/id_rsa_onode`). **Confirmed 2026-10-21 as `user`**: from the laptop (`su user -c "ssh -o BatchMode=yes onode2 echo ok"`, 3.6 s including the handshake) and by Rose typing `ssh onode2` in X Terminal.
- Launchers (all in `/home/user`, linked in `/usr/bin`):
  - `ask <question>`: pipes the question to `n810-ask` on the node. Plain text, fast. Tested 2026-10-21 as `user` over SSH from the laptop: 26–36 s per answer with the spec sheet, facts correct. The older OpenCode-based `ask` is kept as `/home/user/ask.opencode.bak`.
  - `agent <task>`: pipes the task to `n810-agent` on the node (OpenCode with tools and files, in `~/work`). Tested 2026-10-21: `agent show me the files in this folder` ran `ls` and answered correctly, but took 491 s.
  - `oc`: opens OpenCode in full-screen mode on the node. **It shows garbled text** (`66;`, `w=1`) on the N810 terminal. Not usable as the demo screen.
- **The N810's clock is wrong** (files made in October show August dates). On 2026-10-25 it read August 1970, which broke apt's key checks; it was set from the laptop with `date -u`. There is no `hwclock`, and a reboot resets it to 1970 (confirmed); set it after every boot (command in `CHEATSHEET.md`).
- **Direct link tried 2026-10-25:** USB networking parked (no data link with the original cable; OS2008's `g_ether` also fails with Windows, bug 3243). Bluetooth pairs but has no PAN. Details in `N810-setup.md`, Other routes. At home the N810 now joins the home Wi-Fi directly (address in `N810-private.md`), and `ssh n810` picks the home or phone-hotspot address automatically via a `Match exec` rule in `~/.ssh/config` (`~/.ssh/n810-at-home.cmd`; backup `config.bak-2026-10-25`). Power saving Off on the N810 cut ping from ~204 to ~24 ms. School/coworking Wi-Fi is untested and likely blocks device-to-device traffic; use the phone hotspot there.
- **Added 2026-10-25:** Python 2.5.2, pygame 1.7.1 and `gst-launch-0.10`. The mic records (8 kHz mono via `dsppcmsrc`), which solves the recording half of open task 10. Sensor paths and measurements for touch, light, slide and mic are in `probes/SENSORS.md`.
- The N810 is not tied to the laptop's Wi-Fi. It needs the phone hotspot (`rose`) to reach the internet and onode.

## Billing and cost (verify in the Oracle console)

- Account, usage figures and the budget alert are in `N810-private.md`.
- The class guide gives Always Free as 4 OCPU / 24 GB. Newer published sources say 2 OCPU / 12 GB. This is unresolved.
- The monthly budget alert repeats, so **delete it after 2026-12-20**.
- Stopping the node stops compute charges but not the boot disk or reserved IP. Use Stop, never Terminate.

## Key decisions made

- Use a separate legacy SSH service on port 2222 for the N810, rather than weakening port 22 for everyone.
- Shrink the node to 4/23 to reduce cost, and grow it again if the Week 11 model needs more RAM.
- OpenCode runs with the local model, `gemma4:e4b`, so nothing is sent to Claude or Anthropic. OpenCode is a separate tool, not Claude.
- llamatalk goes on onode only; the N810 can't run any of it. It was built from source rather than using the prebuilt release from its one-person repo. Only the `asr e2b tts` model sets were fetched, because Ollama already has E4B. Its servers stay on `127.0.0.1` and are reached through `onode2`, so no new ports were opened.

## Lessons learned

- **The N810 keyboard is hard to type on.** Keep commands short. Use the `onode2` alias and `ask`, not the full commands.
- **PowerShell pipes add Windows line endings** (`\r`), which broke shell scripts. Run files with `cmd /c "ssh onode2 bash -s < file.sh"`, or strip CRLF first (`sed -i 's/\r$//' file`).
- **N810 OpenSSH 4.7** has no `KexAlgorithms` option on the client. It already offers SHA-1 KEX by default.
- **Oracle console pages** often don't render in the built-in browser pane. Use short URLs from the menu, not guessed URLs. A wrong URL once signed Rose out.
- **Automatic permission checks** block changes that weaken security, such as opening ports or enabling legacy algorithms on shared services. Rose has to run those herself, or approve a permission rule.
- **OpenCode's full-screen TUI** sends terminal queries the N810 terminal can't answer, so it prints garbage. Use `ask` (plain mode) for the N810.
- **OpenCode is too heavy for plain questions on 4 OCPU.** It sends about 6,700 tokens before your question and runs as an agent with tools: a factual question took 228 s and printed a `webfetch` tool call instead of an answer. Plain questions go straight to Ollama (`ask`); OpenCode is only for file tasks (`agent`).
- **OpenCode gives up after 5 minutes by default**, which is shorter than its first prompt takes here. The `n810` config raises this to 15 minutes.
- **A small model invents niche facts.** Put the facts it needs in the system prompt.
- **Don't type a lone apostrophe on the N810.** Its shell treats `what's` as an open quote. Write `what is`, or wrap the question in double quotes.
- **Ubuntu's automatic updates can restart Ollama** (via needrestart), which unloads the model. The warm-up service and needrestart rule cover this.
- **Ollama and llamatalk share 4 cores.** Both can stay loaded (memory is fine), but whichever is working slows the other. Stop llamatalk before an `ask` demo unless you're showing speech.
- **Gemma E2B is fast but gets facts wrong** (it called the N810 a smartphone). Give it the spec sheet, as `n810-ask` does for E4B.
- **The speech recognizer adds a prefix**, `language English<asr_text>`, before the text it heard. Strip it.
- **Course dossiers** (`mfadt/sld-fall-2026/dossiers`) hold the measured advice on Ollama, OpenCode and the node. `dossiers-index.md` in this repo says where to look.

## Demo plan

1. Show the N810 as the interface and the node as the computer.
2. `ask what is a Nokia N810?` (about 30 s). Check `ollama ps` on the node first; the warm-up service should already have the model loaded. Run `~/llamatalk/stop.sh` first unless the demo uses speech.
3. `ask draw an ASCII-art Nokia N810 with its specs underneath` (the visual, about 35 s). The spec list is correct; the drawing itself is a rough blob.
4. Optional: `agent show me the files in this folder` (about 8 minutes; start it before talking about it, or skip).

## Open tasks

1. Try `ask` by hand in X Terminal on the N810 (so far it was run over SSH from the laptop). Check the text looks right on the 800x480 screen.
2. Decide whether `agent` (491 s for one task) belongs in the demo.
3. Optional: find out why `ask` doesn't reuse the cached system prompt (answers went from 16–21 s to 26–36 s when the spec sheet was added). Optional: print a fixed ASCII drawing and only generate the specs.
4. Decide the node size: 4/23 (cost) vs 2/12 (free tier per newer sources) vs back to 16/96. Confirm with David Carroll first.
5. Confirm billing: trial or Academy, remaining credit, and whether usage is billed after the trial.
6. Delete the monthly budget alert after 2026-12-20.
7. Keep `N810-private.md` out of git (it is git-ignored).
8. Optional: an ASCII status screen script on the node for live numbers in the demo.
9. Decide whether a fast `ask` should use Gemma E2B on port 8092 (about 2 s) instead of `gemma4:e4b` (26–36 s). It needs the spec sheet.
10. Speech on the N810: recording works since 2026-10-25 (`gst-launch-0.10 dsppcmsrc`, 8 kHz mono, see `probes/SENSORS.md`); `play-sound` exists for playback. Still to build: a `talk` launcher: record a WAV, send it through `onode2`, play the spoken reply. Shrink replies to 8 kHz on the node first (about 47 KB per second of speech at 24 kHz).

## Files

- `CHEATSHEET.md` (in repo): what to type on each machine, launchers, installed software, node services and ports, demo checklist.
- `N810-setup.md` (in repo): device profile, then the three setup stages with status, what's left and lessons; course references; dated log.
- `PROJECT.md` (in repo): the Environmental Vibe DJ concept, Big Questions, sensor inputs and build phases.
- `N810-private.md` (local only, git-ignored): IPs, budget, account and security details.
- Rose's archived notes, `claude/N810 Capabilities and Bottlenecks 2026-10-23.md` in Claude (not in the repo): older detail that wasn't carried over (package versions, the full connection log, the USB diagnostic ladder, N900 class-guide notes). Frozen as of 2026-10-21; ask Rose for it if a detail isn't in the repo.
- `onode-legacy-setup.sh` (in repo): the script that set up port 2222 on the node. Already run once successfully.
- llamatalk's `start.sh`, `stop.sh` and the test script (`~/llamatalk/test/smoke.sh`) exist only on the node, not in the repo.
- `CREATURE.md` (in repo): brief for the October creature demo sketch (concept, latency budget, measured sensors, open design questions). **Start the creature work here.**
- `probes/` (in repo): sensor probe scripts (Python 2.5, run on the N810) and `SENSORS.md`, the measured sensor table.
- `dossiers-index.md` (in repo): index of the course dossiers, with what each file answers and where.
- Class repo: `mfadt/sld-fall-2026` (private). Useful guides: `docs/oracle-ampere-node.md`, `docs/coding-on-your-node.md`, `docs/first-build-on-a-device.md`. Your login has access.
- Class wiki: `mfadt/sld-fall-2026` wiki. The N810 devices are on the "Nokia Devices Library" page.

## Working style

Rose prefers short steps with a clear check after each one, and wants the AI to explain each action before doing it. Rose has also asked for the screen to be checked before deciding next steps. Use plain language. Keep replies short. Ask before any change to the Oracle account or to shared security settings.
