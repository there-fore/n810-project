# Handover: N810 + Oracle node (as of 2026-10-23)

Paste this into a new Claude chat to continue. Connections, launchers, the node's Ollama setup and the loaded model were checked and changed on 2026-10-21; billing was last checked 2026-10-16. Re-check anything marked "verify" before relying on it.

**Private details** (IP addresses, billing, budget alert, account type) live only in `N810-private.md` (git-ignored). This file is in the public repo; keep them out of it.

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

## N810 state (verify)

- Laptop can log in to the N810 as root with `ssh n810` (key `~/.ssh/id_rsa_n810`).
- The N810 has its own key for onode: `/root/.ssh/id_rsa_onode` (no passphrase), copied also to `/home/user/.ssh/`.
- Short name `onode2` is in `/root/.ssh/config` and `/home/user/.ssh/config` (the user copy points at `/home/user/.ssh/id_rsa_onode`). **Confirmed 2026-10-21 as `user`**: from the laptop (`su user -c "ssh -o BatchMode=yes onode2 echo ok"`, 3.6 s including the handshake) and by Rose typing `ssh onode2` in X Terminal.
- Launchers (all in `/home/user`, linked in `/usr/bin`):
  - `ask <question>`: pipes the question to `n810-ask` on the node. Plain text, fast. Tested 2026-10-21 as `user` over SSH from the laptop: 26–36 s per answer with the spec sheet, facts correct. The older OpenCode-based `ask` is kept as `/home/user/ask.opencode.bak`.
  - `agent <task>`: pipes the task to `n810-agent` on the node (OpenCode with tools and files, in `~/work`). Tested 2026-10-21: `agent show me the files in this folder` ran `ls` and answered correctly, but took 491 s.
  - `oc`: opens OpenCode in full-screen mode on the node. **It shows garbled text** (`66;`, `w=1`) on the N810 terminal. Not usable as the demo screen.
- **The N810's clock is wrong** (files made in October show August dates). Don't trust file times on the device; set the date before anything depends on it.
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
- **Course dossiers** (`mfadt/sld-fall-2026/dossiers`) hold the measured advice on Ollama, OpenCode and the node. `dossiers-index.md` in this repo says where to look.

## Demo plan

1. Show the N810 as the interface and the node as the computer.
2. `ask what is a Nokia N810?` (about 30 s). Check `ollama ps` on the node first; the warm-up service should already have the model loaded.
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

## Files

- `N810-setup.md` (public notes, in repo): setup log, Oracle node section, references.
- `N810-private.md` (local only, git-ignored): IPs, budget, account and security details.
- `onode-legacy-setup.sh` (in repo): the script that set up port 2222 on the node. Already run once successfully.
- `dossiers-index.md` (PR there-fore/n810-project#3): index of the course dossiers, with what each file answers and where.
- Class repo: `mfadt/sld-fall-2026` (private). Useful guides: `docs/oracle-ampere-node.md`, `docs/coding-on-your-node.md`, `docs/first-build-on-a-device.md`. Your login has access.
- Class wiki: `mfadt/sld-fall-2026` wiki. The N810 devices are on the "Nokia Devices Library" page.

## Working style

Rose prefers short steps with a clear check after each one, and wants the AI to explain each action before doing it. Rose has also asked for the screen to be checked before deciding next steps. Use plain language. Keep replies short. Ask before any change to the Oracle account or to shared security settings.
