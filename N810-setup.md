# Nokia N810: Setup Log

Notes for PSAM 5600 B (Small Linux Devices, Large Language Models), Fall 2026. The N810 is used as an interface and terminal; heavy computation runs on a remote Oracle node.

The work happened in three stages: **clean the device**, **secure the connections**, then **build on the node for the N810**. Each stage below says where it stands, what was done, what's left, and what was learned.

| File | For |
|---|---|
| [CHEATSHEET.md](CHEATSHEET.md) | Commands, launchers, installed software, ports. Keep this one open. |
| N810-setup.md (this file) | Device profile and how each stage was done |
| [PROJECT.md](PROJECT.md) | The art project: concept, Big Questions, build phases |
| [HANDOVER.md](HANDOVER.md) | Current status for a new assistant session |
| `N810-private.md` (git-ignored) | IP addresses, billing, account details |

Machine-specific details are kept out of this public file. Placeholders such as `<N810-IP>` mark where they go.

---

## Device profile

### Hardware
| Part | Spec | Note |
|---|---|---|
| CPU | TI OMAP 2420, ARM11 (ARMv6), 400 MHz | Main constraint; no AES hardware. Also has a 220 MHz C55x DSP. |
| RAM | 128 MB | Plus 112 MB swap on the internal card |
| Device memory | 249.5 MB flash | OS and installed apps |
| Internal memory card | ~2 GB flash, soldered in (1.83 GB usable) | Not removable; mounted at `/media/mmc2` |
| miniSD slot | External card | `/media/mmc1` when inserted |
| Display | 4.1", 800x480, resistive touch, 65,536 colours | Stylus or firm press |
| Input | Slide-out QWERTY | Symbols via Fn or on-screen keyboard |
| Audio | Stereo speakers, mic, 3.5 mm jack, Bluetooth | Mic adequate for voice and VoIP. A2DP may need an add-on on Diablo. |
| Camera | Front webcam, VGA (0.3 MP); no rear camera | Video calls |
| Wireless | Wi-Fi 802.11b/g, Bluetooth 2.0 + EDR | Wi-Fi is the only internet link |
| GPS | Built in | About one update per second; too slow for gestures |
| Sensors | Ambient light (TSL2563) and GPS only | No accelerometer or gyroscope |
| USB | 2.0, client and host modes | Networking, mass storage, peripherals |
| Cellular | None | No carrier calls or SMS |
| Battery | 1500 mAh | Real battery life not measured |
| Size | 128 x 72 x 14 mm, 226 g | |
| History | Announced October 2007, about $479; after the N800, before the N900 (2009) | |

The display colours, camera resolution, battery, size, price and history come from the spec sheet in the node's `n810-ask` (see Stage 3). They haven't been checked against a separate source here.

### Software
| Item | Detail |
|---|---|
| OS | Maemo 4.1 "Diablo" (OS2008, 5.2008.43-7), Debian-based. Kernel `2.6.21-omap1`, `armv6l`. Not Maemo 5, which is the N900's OS. |
| Shell | BusyBox v1.6.1 (ash). No wget or curl. Network tools are in `/sbin`; call them by full path. |
| Terminal | X Terminal (`osso-xterm`). Can't answer the terminal queries modern full-screen programs send. |
| SSH | OpenSSH 4.7p1 (2008). RSA and DSA only; no ed25519. Modern clients need legacy flags. The client has no `KexAlgorithms` option but offers SHA-1 key exchange by default. |
| Browser | MicroB. Most modern HTTPS sites fail. |
| Users | Normal user `user` (uid 29999, home `/home/user`); root via rootsh (home `/root`). Each has its own `~/.ssh`. |
| Clock | Wrong on this unit (October files show August dates). Don't trust file times. |

### Fit
- **Strong:** text entry, control panels, terminal and SSH, image viewing, audio playback, small data exchange, plain line-by-line text.
- **With limits:** VoIP, voice capture (recognize on the server), small C programs.
- **Offload:** anything compute-heavy, speech recognition, language models.
- **Poor:** modern web, full-screen terminal programs, video, large data.

### Working within the limits
- **Memory:** 128 MB of RAM is the hardest limit. Keep the 112 MB swap enabled. Close unused apps, and prefer small C programs over interpreted languages. Turn off `sshd` when it's not in use (`/etc/init.d/ssh stop` as root).
- **Network:** each round trip on the hotspot costs about 229 ms, so batch requests and reuse one SSH connection. Send compact data, and compress only when the transfer time saved exceeds the CPU time spent. Offload work when local compute time > transfer time + round trip + remote compute time.
- **Battery:** Wi-Fi and polling drain it fastest. Prefer event-driven waits so the device can sleep.

**Constraints, ranked:** CPU speed; memory; network dependence and latency; battery; aging software and dead repositories.

---

## Stage 1: Clean the device

**Status:** mostly done. A few folders on the internal card still need a decision.

### Software catalogs
1. Join the phone hotspot in Settings > Connections. iPhone hotspots assign `172.20.10.x` addresses.
2. In Application manager > Application catalogs, disable the dead maemo.org and Nokia catalogs and add the mirror: `http://maemo.viniciuspaes.com/extras/`, distribution `diablo`, components `free non-free`. The web address must include `/extras/`.
3. Install rootsh, then openssh. Set the root password during install.

- **Working:** `maemo.viniciuspaes.com/extras/` (Diablo Extras). It's a hobby server; install what you need and don't bulk-download.
- **Dead:** `catalogue.tableteer.nokia.com`, `repository.maemo.org`, `n8xx.com`.
- **Missing from the mirror:** `libicd-network-dummy`, which blocks the `maemo-pc-connectivity` metapackage. Its useful parts install individually.
- Use only `diablo` catalogs. Fremantle (N900) packages fail on the N810.

### Installed for this project
| Package | Size | Purpose |
|---|---|---|
| rootsh | 33 kB | Root shell |
| openssh (client, server, common) | 1.6 MB | SSH in and out; includes sftp and scp |
| pc-connectivity-manager | 5.3 MB | USB networking setup; created `devel_adhoc` and `dummy_iap` profiles |
| maemo-control-usb | 0.1 MB | USB mode switch (overlaps with the manager) |

### Storage
| Area | Total | Free before cleanup | Holds |
|---|---|---|---|
| Device memory | 249.5 MB | 114 MB | OS and apps (installed apps total 61.6 MB) |
| Internal card | 1.83 GB | 130 MB | Media, swap, caches |

**Cleanup log (internal card):**
| Item | Action |
|---|---|
| `map` (cached map tiles, the bulk of 1.6 GB of "other files") | Deleted |
| `Online Game` | Deleted |
| Music files | Deleted |
| Two Hildon themes (7 MB, device memory) | Uninstalled |
| `WMPInfo.xml` (296 bytes, Windows Media Player leftover) | To check; safe to delete |
| `Video`, `Downloads` | To review |
| `.apt-archive-cache` (downloaded packages) | Safe to clear |
| `.swap` (112 MB) | Keep. Disable only through Control Panel > Memory > Virtual, never by deleting the file. |

Check free space in Control Panel > Memory, or size folders in the terminal with `du -sk /media/mmc2/*` (hidden folders: `du -sk /media/mmc2/.[a-z]*`).

### Left to do
- Decide on `WMPInfo.xml`, `Video`, `Downloads` and `.apt-archive-cache`; recheck free space.
- Set the clock.

---

## Stage 2: Secure the connections

**Status:** all links work. Hardening is unfinished: root password login on the N810 is still on, and port 2222 on the node is open to the whole internet (login there is key-only).

Every connection needs three layers: a **link** (radio or cable), **addressing** (both ends on one network), and a **service** (something listening, such as `sshd`). When something fails, find the lowest layer that doesn't work.

### Wi-Fi
The N810 reaches the internet, and the node, only through the phone hotspot. It isn't tied to the laptop's Wi-Fi. The hotspot lets clients reach each other, which is why the laptop can reach the N810. About 10% of transmitted Wi-Fi packets showed errors; keep the N810 close to the phone.

Venue or campus Wi-Fi may not work: captive login pages and WPA2-Enterprise (eduroam) can block the N810, and many networks stop devices reaching each other. A USB link avoids both (see Other routes).

### Laptop → N810 (status: key login working)
- **Ping:** 0% loss, average 229 ms.
- **First SSH attempt** failed with `no matching host key type found. Their offer: ssh-rsa,ssh-dss`. Modern SSH disables `ssh-rsa`. With a password, connect with `ssh -o HostKeyAlgorithms=+ssh-rsa -o KexAlgorithms=+diffie-hellman-group14-sha1 root@<N810-IP>`, type `yes` at the fingerprint prompt, then enter the password. If a new "no matching…" error appears, it names the next algorithm to add.

**Key login (needed for an assistant to run commands without a password prompt):**
1. On the laptop: `ssh-keygen -t rsa -b 2048 -f %USERPROFILE%\.ssh\id_rsa_n810` (RSA, because OpenSSH 4.7 can't use ed25519).
2. Append the public key to `/root/.ssh/authorized_keys` on the N810. Set `.ssh` to mode 700 and the file to 600.
3. Add to `%USERPROFILE%\.ssh\config`:
   ```
   Host n810
     HostName <N810-IP>
     User root
     IdentityFile ~/.ssh/id_rsa_n810
     HostKeyAlgorithms +ssh-rsa
     PubkeyAcceptedAlgorithms +ssh-rsa
     KexAlgorithms +diffie-hellman-group14-sha1
   ```
4. Test with `ssh -o BatchMode=yes n810 uname -a`. BatchMode refuses to fall back to a password, so success proves the key works. If the hotspot reassigns the address, edit only `HostName`.

**Reading failures, lowest layer first:**
- `Name or service not known` / `Could not resolve hostname`: the short name wasn't found. Wrong machine, or the config entry is missing.
- `timed out` / `No route to host`: addressing or link. Check the IP and that both are on the hotspot.
- `Permission denied (publickey,password)`: everything else works; the key was rejected. Check the key is on one line in `authorized_keys`, the permissions are 700/600, and `PubkeyAcceptedAlgorithms +ssh-rsa` is set. (On 2026-10-16 the cause was that `/root/.ssh` didn't exist.)

An assistant's shell reaches only the networks its machine is on. Run it on the laptop, not in the cloud.

### N810 → Oracle node (status: working on port 2222)
The node's main SSH (port 22, user `ubuntu`) stays as it is, because OpenSSH 4.7 can't use its default algorithms, and adding old ones there would weaken login for everyone. A separate legacy SSH service runs on **port 2222**, and only the `n810` user can log in there, with a key.

1. On the N810: an RSA key was made for this link (`/root/.ssh/id_rsa_onode`, no passphrase), with a copy in `/home/user/.ssh/` for the normal terminal user. Its public key is in the node's `/home/n810/.ssh/authorized_keys`.
2. The N810 has a short entry in `/root/.ssh/config` and `/home/user/.ssh/config`, so the login is:
   ```
   ssh onode2
   ```
   (The full form, if the entry is missing: `ssh -p 2222 -i /root/.ssh/id_rsa_onode n810@<node-ip>`.)
3. The node runs the legacy service as `ssh-legacy.service` with its own config in `/etc/ssh/sshd_config.legacy`, set up by [onode-legacy-setup.sh](onode-legacy-setup.sh). It has no effect on port 22. TCP 2222 is open in the host firewall and the Oracle security list.

Test from the N810: `ssh onode2 hostname` should print `smalldevllmnode`. Confirmed as `user` in X Terminal on 2026-10-21 (about 3.6 s including the handshake).

### Other routes
| Route | Status | When to use |
|---|---|---|
| USB networking (N810 `192.168.2.15`, host `192.168.2.14`) | Tools installed; not attempted. Windows likely needs RNDIS, which OS2008's USB networking may not offer. | No Wi-Fi available |
| Ad-hoc Wi-Fi (`devel_adhoc` profile) | Untested | No hotspot, or a hotspot that isolates clients |
| Bluetooth PAN | Untested | Low bandwidth, cable-free |
| Laptop as package server (`python3 -m http.server`) | Fallback | Mirror down. Packages must be gzip-compressed. |
| Memory card or USB mass storage | Works by default | Moving files, not live control |

### Left to do
- Disable root password login on the N810 (`PasswordAuthentication no` in `/etc/ssh/sshd_config`) before using shared networks.
- Consider limiting port 2222 to fewer source addresses.
- Measure round trip and handshake time N810 → node.

### Lessons
- PowerShell pipes add Windows line endings (`\r`), which broke shell scripts sent to the node. Use `cmd /c "ssh onode2 bash -s < file.sh"`, or strip them first (`sed -i 's/\r$//' file`). The repo's `.gitattributes` keeps `.sh` files on Unix line endings.
- Automatic permission checks in the assistant block security-weakening changes (opening ports, enabling legacy algorithms). Rose runs those herself or approves a permission rule.

---

## Stage 3: Build on the node for the N810

**Status:** in progress. `ask` and `agent` work; llamatalk's speech servers run on the node but nothing on the N810 uses them yet.

### The node (`onode`)
The compute side of the project. The N810 sends requests here; the node does the heavy work. Connection details are in the private notes file, not this one.

| Item | State |
|---|---|
| OS | Ubuntu 24.04.5 LTS, arm64 (aarch64), kernel 7.0.0-1013-oracle |
| Resources | 4 CPUs, 23 GB RAM, 140 GB disk (about 26% used on 2026-10-23), no GPU. Resized from 16 CPUs / 96 GB on 2026-10-16 to cut cost. |
| Swap | 16 GB `/swapfile`, persistent, `vm.swappiness=10` |
| Build tools | gcc 13.3, cmake 3.28, build-essential, python3-pip, python3-venv |
| Containers | Docker 29.1.3 with Compose 2.40.3; the `ubuntu` user is in the `docker` group |
| Other tools | GitHub CLI 2.45.0 (not signed in), OCI CLI 3.95.0 and `oci-ai-speech-realtime` in `~/venvs/oci`, htop, unzip, zstd, tmux, jq |
| Updates | unattended-upgrades enabled, iptables-persistent installed |
| Course repo | Copy of `mfadt/sld-fall-2026` at `~/sld-fall-2026`, taken from the laptop (onode cannot clone it anonymously) |

### AI model (Ollama)
- **Ollama 0.40.5** runs as a systemd service on `127.0.0.1:11434`. It answers only from the node itself.
- **Model:** `gemma4:e4b` (6.6 GB), the course's recommended coding model.
- **Coder profile:** set with `coder-node.sh apply`, verified with `verify`. Context is 65,536 tokens, one model loaded at a time, flash attention and q8 KV cache on, keep-alive `-1`.
- **Warm-up service:** `ollama-warmup.service` reloads `gemma4:e4b` every time Ollama starts, and a needrestart rule stops automatic updates from restarting Ollama. Details in [HANDOVER.md](HANDOVER.md).
- **OpenCode 1.19.3** is installed. The `n810` user's config points it at the local Ollama model, with a 15-minute timeout.

### Launchers for the N810
Scripts in `/home/user` on the N810, linked in `/usr/bin` so they work from any folder. Each sends its input through `onode2` to a helper on the node.

| Command | Runs on the node | Speed |
|---|---|---|
| `ask <question>` | `/usr/local/bin/n810-ask`: calls Ollama directly, plain text, Unicode punctuation swapped for ASCII | 26–36 s per answer (tested as `user` over SSH from the laptop) |
| `agent <task>` | `/usr/local/bin/n810-agent`: `opencode run` in `~/work` with `TERM=dumb` | Minutes (491 s for a file listing on 4 CPUs) |
| `oc` | OpenCode full-screen | Garbled on X Terminal (`66;`, `w=1`). Not for the demo. |

**What `ask` tells the model:** answer for a small 800x480 terminal, in plain text with no markdown, tables or headings, in a few sentences unless asked for more. For N810 questions, use only the spec sheet it includes (the facts listed in the Device profile above). Without the spec sheet, Gemma called the N810 a Series 40 phone with a 2.1-inch screen.

### Speech and a fast model (llamatalk)
[llamatalk](https://github.com/mercurious/llamatalk) is a small kit built for retro handhelds: llama.cpp's `llama-server` and Pocket TTS's `tts-server`, plus a model downloader. It runs on onode only. It cannot run on the N810 (ARMv6, 128 MB RAM, no `curl`; the smallest model is 1 GB). Its value here is speech in and out, which Ollama lacks, and the faster Gemma E2B model.

- **Built from source** on 2026-10-23 with Docker (`ENGINE=docker build/build.sh`, about 5 minutes) instead of using the prebuilt release. llamatalk 0.1.0 (commit `759b3a9`), llama.cpp `6c7a87f` (CPU only), pockettts.cpp `e621509`. The programs are in `~/llamatalk/dist/llamatalk/bin/`. The build leaves a 700 MB Docker image (`llamatalk-build`) and 389 MB of sources in `~/llamatalk/build/work`. One harmless build warning: the checksum for llama-server's web chat page failed to download; the API is unaffected.
- **Models** (4.4 GB, `~/llamatalk-models`, fetched with `models.sh fetch --dir ~/llamatalk-models asr e2b tts`): Qwen3-ASR 0.6B for speech recognition, Gemma 4 E2B (QAT Q4_0) as the language model, Pocket TTS English and its voices. The `e4b` set was skipped because Ollama already has that model. Licences: Gemma Apache-2.0; Pocket TTS CC-BY-4.0 (credit it if its speech is shown or published); Qwen3-ASR not stated on the download page.
- **Servers**, all on `127.0.0.1` only (reach them from the N810 through `onode2`; no new ports):

  | Port | Server | API | Memory |
  |---|---|---|---|
  | 8091 | speech recognition (Qwen3-ASR) | `/v1/audio/transcriptions` (WAV, 16 kHz) | 1.9 GB |
  | 8092 | language model (Gemma E2B, 8k context) | `/v1/chat/completions` | 4.6 GB |
  | 8093 | speech (Pocket TTS, voice `alba`) | `/v1/audio/speech` (WAV, 24 kHz) | 0.1 GB |

- **Start and stop** with `~/llamatalk/start.sh` and `~/llamatalk/stop.sh`. Logs are in `~/llamatalk/logs/`. They are not a systemd service, so they don't come back after a reboot. With Ollama's `gemma4:e4b` also loaded, 11.6 GB of RAM stayed free.
- **They share the 4 cores with Ollama.** Idle servers cost almost nothing, but `ask` slows down while llamatalk is working. Stop llamatalk before an `ask` demo unless you're showing speech.

**Measured on 2026-10-23** (4 OCPU, Ollama loaded but idle; script and results in `~/llamatalk/test/`):

| Test | Result |
|---|---|
| Language model, short question | 2.1 s total; prompt 71 tok/s, generation 21 tok/s. Compare `ask` on `gemma4:e4b`: 26–36 s. |
| Speech, one sentence | 4.8 s of audio made in 2.3 s (about 2x real time). 24 kHz mono 16-bit WAV, 225 KB. |
| Speech recognition, that WAV resampled to 16 kHz | 1.3 s. One word wrong: "N810" heard as "8880". |

- **Gemma E2B gets facts wrong.** Asked what an N810 is, it called it "a smartphone… at a competitive price point". Give it the same spec sheet as `n810-ask` if it answers N810 questions.
- **The recognizer's output starts with `language English<asr_text>`.** A client must strip that prefix before using the text.
- **Reply audio is large for the hotspot** (about 47 KB per second of speech). Converting it to 8 kHz on the node before sending would make it a third of the size.

### Left to do
- Try `ask` by hand in X Terminal; check the text fits the 800x480 screen.
- Decide whether `agent` (491 s per task) goes in the demo.
- Decide whether a fast `ask` should use Gemma E2B (port 8092, about 2 s) instead of `gemma4:e4b` (26–36 s). It needs the spec sheet in its system prompt.
- Find a way to record audio on the N810. The GStreamer mic plugin (`dsppcm`) is there, but `gst-launch`, `arecord` and `esdrec` are missing. Playback exists (`play-sound`).
- The node-side helpers and N810 launchers exist only on those machines, not in this repo.

### Lessons
- The course scripts were copied from a Windows clone with CRLF line endings, so Linux failed on the shebang (`bash\r`). Fix: `sed -i "s/\r$//"` on the `.sh` files.
- Running course scripts with `sudo` may be blocked by automated permission checks. Run `apply` yourself in an SSH session.
- Always confirm the terminal is on onode (prompt reads `ubuntu@smalldevllmnode`) before running node commands. A laptop PowerShell tab will fail `cd ~/...`.
- OpenCode is too heavy for plain questions on 4 CPUs (it sends about 6,700 tokens first). Plain questions go straight to Ollama (`ask`); OpenCode is only for file tasks (`agent`).
- A small model invents niche facts. Put the facts it needs in the system prompt.

---

## Course References

Guides from the course repo and wiki, for when something here goes wrong. Check the wiki first for anything about SSH or the devices.

### Wiki (`mfadt/sld-fall-2026/wiki`)
| Guide | Use it for |
|---|---|
| [SSH Keys and Pairing](https://github.com/mfadt/sld-fall-2026/wiki/SSH-Keys-and-Pairing) | Reading SSH errors. Its "An old device" section covers the legacy-algorithm flags the N810 needs. Also the `Host` nickname pattern used above. |
| [Nokia Devices Library](https://github.com/mfadt/sld-fall-2026/wiki/Nokia-Devices-Library) | Specs for the N810 and the other borrowed devices. The N810 is Maemo 4.1 with no cellular radio. |
| [Copilot for Semester Projects](https://github.com/mfadt/sld-fall-2026/wiki/Copilot-for-Semester-Projects) | The working loop, device-first habits, and attribution rules (`Co-Authored-By:` trailers). |
| [Building for Symbian S60](https://github.com/mfadt/sld-fall-2026/wiki/Building-for-Symbian-S60) | Only if the N95 or N80 becomes a target. Mostly speculative. |
| [Building a Raspberry Pi Toolchain](https://github.com/mfadt/sld-fall-2026/wiki/Building-a-Raspberry-Pi-Toolchain) | Pi targets. Not the N810: its ARM11 is ARMv6, so check the triplet before using it. |

### Docs (`mfadt/sld-fall-2026/docs`)
| Guide | Use it for |
|---|---|
| [Oracle Ampere node setup](https://github.com/mfadt/sld-fall-2026/blob/main/docs/oracle-ampere-node.md) | Node setup and SSH. Chapter 5 covers first login, Chapter 6 covers the `~/.ssh/config` nickname and the weekly login rule, and Chapter 7 covers the toolchain prompt. |
| [Coding on your node](https://github.com/mfadt/sld-fall-2026/blob/main/docs/coding-on-your-node.md) | Ollama profiles (chat vs coder), swap setup (Step 1.3), and coder tools (OpenCode, Hermes, Claude Code) on the node. |
| [Self-hosted AI kit](https://github.com/mfadt/sld-fall-2026/blob/main/docs/self-hosted-ai-kit.md) | Ollama install, the `OLLAMA_*` settings, the chat page, and "When it goes wrong". |
| [Self-hosted AI kit runbook](https://github.com/mfadt/sld-fall-2026/blob/main/docs/self-hosted-ai-kit-runbook.md) | Long-form Ollama runbook with benchmarks and the Docker/front-door traps. |
| [Oracle AI services](https://github.com/mfadt/sld-fall-2026/blob/main/docs/oci-ai-services.md) | OCI CLI setup and speech/vision calls from the node. |
| [First build on a device](https://github.com/mfadt/sld-fall-2026/blob/main/docs/first-build-on-a-device.md) | The laptop→device SSH flow, `ssh-copy-id` on Windows, and "When it goes wrong". Written for a Pi; the same pattern applies to the N810. |
| [Installing software on a borrowed Nokia N900](https://github.com/mfadt/sld-fall-2026/blob/main/docs/nokia-n900-software-repos.md) | Maemo package repos and `apt-get`. N900 is Maemo 5, so the N810 (Diablo) catalogs differ. Read it for the method, not the URLs. |
| [Using Antigravity](https://github.com/mfadt/sld-fall-2026/blob/main/docs/using-antigravity.md) | The course's rules for agent-assisted work: one step at a time, paste exact errors, attribute commits. |
| [Free cloud options](https://github.com/mfadt/sld-fall-2026/blob/main/docs/free-cloud-options.md) | Alternatives if the Oracle node is unavailable. |

The course dossiers (`mfadt/sld-fall-2026/dossiers`) hold measured advice on Ollama, OpenCode and the node; [dossiers-index.md](dossiers-index.md) says where to look.

---

## Log

**2026-10-09** (Stages 1–2): Mirror added; rootsh, openssh, pc-connectivity-manager, maemo-control-usb installed. N810 on hotspot Wi-Fi. Laptop ping confirmed; SSH needs the legacy host-key flag. Cleanup: maps, games, music, themes removed.

**2026-10-16** (Stages 2–3): Read the course wiki and docs and added the references above. Set up `onode`: build tools, Docker, GitHub CLI, OCI CLI, 16 GB swap, course repo copy, and a reboot onto the new kernel. Ollama 0.40.5 runs as a CPU-only service. Downloaded `gemma4:e4b`, applied and verified the coder profile, and loaded the model. OpenCode installed. Node resized to 4 OCPU / 23 GB to reduce usage; monthly budget alert set.

**2026-10-16, later** (Stage 2): Key login laptop → N810 working (`ssh n810`). N810 connected to onode on port 2222 as the `n810` user (`ssh onode2`). OpenCode copied to `/usr/local/bin`, and its first-run setup started for `n810`.

**2026-10-21** (Stages 2–3): `ssh onode2` confirmed as `user` (from the laptop and in X Terminal). `ask` reworked to call Ollama directly through `n810-ask`; new `agent` launcher for OpenCode tasks through `n810-agent`. `gemma4:e4b` loaded and pinned, with a warm-up service that reloads it whenever Ollama starts. `ask` answers in 26–36 s; an `agent` file listing took 491 s. Found the N810's clock is wrong.

**2026-10-23** (Stage 3): Assessed llamatalk: onode only, nothing for the N810. Built it from source on onode, downloaded the `asr e2b tts` models (4.4 GB), and started its three servers on `127.0.0.1:8091–8093`. Gemma E2B answered in 2.1 s, speech was made at about 2x real time, and speech recognition took 1.3 s. Ollama and `gemma4:e4b` were left as they were. Notes split into this log, [CHEATSHEET.md](CHEATSHEET.md) and [PROJECT.md](PROJECT.md).
