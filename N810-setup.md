# Nokia N810: Specs, Connecting, and Efficiency

Notes for PSAM 5600 B (Small Linux Devices, Large Language Models), Fall 2026. The N810 is used as an interface and terminal; heavy computation runs on a remote Oracle node.

Machine-specific details are kept out of this public file. Placeholders such as `<N810-IP>` mark where they go.

## Quick Reference

| Task | Command or setting |
|---|---|
| Root shell (N810) | `sudo gainroot` |
| N810's current IP | `/sbin/ifconfig wlan0`, read `inet addr:` |
| SSH from laptop | `ssh -o HostKeyAlgorithms=+ssh-rsa -o KexAlgorithms=+diffie-hellman-group14-sha1 root@<N810-IP>` |
| SSH after key setup | `ssh n810` |
| Package catalog | `http://maemo.viniciuspaes.com/extras/`, distribution `diablo`, components `free non-free` |
| Terminal app | Menu > Utilities > X Terminal |

---

## 1. Specs

### Hardware
| Part | Spec | Note |
|---|---|---|
| CPU | TI OMAP 2420, ARM11, 400 MHz | Main constraint; no AES hardware |
| RAM | 128 MB | Plus 112 MB swap on the internal card |
| Device memory | 249.5 MB flash | OS and installed apps |
| Internal memory card | ~2 GB flash, soldered in (1.83 GB usable) | Not removable; mounted at `/media/mmc2` |
| miniSD slot | External card | `/media/mmc1` when inserted |
| Display | 4.1", 800x480, resistive touch | Stylus or firm press |
| Input | Slide-out QWERTY | Symbols via Fn or on-screen keyboard |
| Audio | Speaker, mic, 3.5 mm jack, Bluetooth A2DP | Mic adequate for voice and VoIP |
| Camera | Front webcam, low resolution | Video calls |
| Wireless | Wi-Fi 802.11b/g, Bluetooth 2.0 + EDR | Wi-Fi is the only internet link |
| GPS | Built in | |
| USB | 2.0, client and host modes | Networking, mass storage, peripherals |
| Cellular | None | No carrier calls or SMS |

### Software
| Item | Detail |
|---|---|
| OS | Maemo 4.1 "Diablo" (OS2008, 5.2008.43-7), Debian-based. Not Maemo 5, which is the N900's OS. |
| Shell | BusyBox v1.6.1 (ash). No wget or curl. Network tools are in `/sbin`; call them by full path. |
| SSH | OpenSSH 4.7p1 (2008). RSA and DSA only; no ed25519. Modern clients need legacy flags. |
| Browser | MicroB. Most modern HTTPS sites fail. |
| User | Normal user (uid 29999); root via rootsh. |

### Installed for this project
| Package | Size | Purpose |
|---|---|---|
| rootsh | 33 kB | Root shell |
| openssh (client, server, common) | 1.6 MB | SSH in and out; includes sftp and scp |
| pc-connectivity-manager | 5.3 MB | USB networking setup; created `devel_adhoc` and `dummy_iap` profiles |
| maemo-control-usb | 0.1 MB | USB mode switch (overlaps with the manager) |

### Fit
- **Strong:** text entry, control panels, terminal and SSH, image viewing, audio playback, small data exchange.
- **With limits:** VoIP, voice capture (recognize on the server), small C programs.
- **Offload:** anything compute-heavy, speech recognition, language models.
- **Poor:** modern web, video, large data.

---

## 2. Connecting

Every connection needs three layers: a **link** (radio or cable), **addressing** (both ends on one network), and a **service** (something listening, such as `sshd`). When something fails, find the lowest layer that doesn't work.

### Wi-Fi and software
1. Join the phone hotspot in Settings > Connections. iPhone hotspots assign `172.20.10.x` addresses.
2. In Application manager > Application catalogs, disable the dead maemo.org and Nokia catalogs and add the mirror from the Quick Reference. The web address must include `/extras/`, and the distribution must be `diablo`.
3. Install rootsh, then openssh. Set the root password during install.

### Laptop → N810 (status: link and server confirmed)
- **Ping:** 0% loss, average 229 ms. The hotspot lets clients reach each other.
- **First SSH attempt** failed with `no matching host key type found. Their offer: ssh-rsa,ssh-dss`. Modern SSH disables `ssh-rsa`. Use the Quick Reference command, type `yes` at the fingerprint prompt, then enter the password. If a new "no matching…" error appears, it names the next algorithm to add.

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
4. Test with `ssh n810 uname -a`. If the hotspot reassigns the address, edit only `HostName`.

An assistant's shell reaches only the networks its machine is on. Run it on the laptop, not in the cloud.

### N810 → Oracle node (status: not started)
The node accepts ed25519 keys only, which OpenSSH 4.7 can't use.
1. On the N810: `ssh-keygen -t rsa -b 2048`.
2. Add the N810's public key to the node's `~/.ssh/authorized_keys`.
3. On the node, allow SHA-1 RSA in `/etc/ssh/sshd_config`, scoped to the N810 if possible, then restart SSH:
   ```
   HostKeyAlgorithms +ssh-rsa
   PubkeyAcceptedAlgorithms +ssh-rsa
   ```
   This weakens the node slightly. Untested.
4. From the N810: `ssh ubuntu@<node-ip>`.

### Other routes
| Route | Status | When to use |
|---|---|---|
| USB networking (N810 `192.168.2.15`, host `192.168.2.14`) | Tools installed; Windows needs a special driver | No Wi-Fi available |
| Ad-hoc Wi-Fi (`devel_adhoc` profile) | Untested | No hotspot, or a hotspot that isolates clients |
| Bluetooth PAN | Untested | Low bandwidth, cable-free |
| Laptop as package server (`python3 -m http.server`) | Fallback | Mirror down. Packages must be gzip-compressed. |

### Repositories
- **Working:** `maemo.viniciuspaes.com/extras/` (Diablo Extras). It's a hobby server; install what you need and don't bulk-download.
- **Dead:** `catalogue.tableteer.nokia.com`, `repository.maemo.org`, `n8xx.com`.
- **Missing from the mirror:** `libicd-network-dummy`, which blocks the `maemo-pc-connectivity` metapackage. Its useful parts install individually.
- Use only `diablo` catalogs. Fremantle (N900) packages fail on the N810.

---

## 3. Efficiency

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

### Memory
- 128 MB of RAM is the hardest limit. Keep the 112 MB swap enabled.
- Close unused apps, and prefer small C programs over interpreted languages.
- Turn off `sshd` when it's not in use (`/etc/init.d/ssh stop` as root). This frees memory and closes an open login port.

### Network
- Each round trip on the hotspot costs about 229 ms, so batch requests and reuse one SSH connection instead of opening many.
- Send compact data, and compress only when transfer time saved exceeds CPU time spent.
- About 10% of transmitted Wi-Fi packets showed errors. Keep the N810 close to the phone.
- Offload work when local compute time > transfer time + round trip + remote compute time.

### Battery
- Wi-Fi and polling drain the small battery fastest. Prefer event-driven waits so the device can sleep.

---

## Oracle Node (`onode`)

The compute side of the project. The N810 sends requests here; the node does the heavy work. Connection details are in the private notes file, not this one.

| Item | State |
|---|---|
| OS | Ubuntu 24.04.5 LTS, arm64 (aarch64), kernel 7.0.0-1013-oracle |
| Resources | 16 CPUs, 94 GB RAM, 139 GB disk (about 21% used), no GPU |
| Swap | 16 GB `/swapfile`, persistent, `vm.swappiness=10` |
| Build tools | gcc 13.3, cmake 3.28, build-essential, python3-pip, python3-venv |
| Containers | Docker 29.1.3 with Compose 2.40.3; the `ubuntu` user is in the `docker` group |
| Other tools | GitHub CLI 2.45.0 (not signed in), OCI CLI 3.95.0 and `oci-ai-speech-realtime` in `~/venvs/oci`, htop, unzip, zstd, tmux, jq |
| Updates | unattended-upgrades enabled, iptables-persistent installed (no ports opened) |
| Course repo | Copy of `mfadt/sld-fall-2026` at `~/sld-fall-2026`, taken from the laptop (onode cannot clone it anonymously) |

### AI model (Ollama)
- **Ollama 0.40.5** runs as a systemd service on `127.0.0.1:11434`. It answers only from the node itself.
- **Model:** `gemma4:e4b` (6.6 GB), the course's recommended coding model.
- **Coder profile:** set with `coder-node.sh apply`, verified with `verify`. Context is 65,536 tokens, one model loaded at a time, flash attention and q8 KV cache on, keep-alive `-1`. Only `gemma4:e4b` has been measured with it.
- **Warm-up:** `coder-node.sh warm` loads the model. The setting `OLLAMA_KEEP_ALIVE=-1` does not survive a service restart, so re-run `warm` after an update restarts Ollama.
- **OpenCode 1.19.3** is installed. Its first run is slow (about 6 minutes); later turns take a few seconds.

### Commands that matter
```bash
ssh onode                                                  # connect from the laptop
~/sld-fall-2026/examples/coder-tools/coder-node.sh verify  # check the profile (no sudo)
~/sld-fall-2026/examples/coder-tools/coder-node.sh warm    # load gemma4:e4b
ollama ps                                                  # what is loaded right now
```

### Lessons from setup
- The course scripts were copied from a Windows clone with CRLF line endings, so Linux failed on the shebang (`bash\r`). Fix: `sed -i "s/\r$//"` on the `.sh` files. A `.gitattributes` with `*.sh text eol=lf` would prevent this on future clones.
- Running course scripts with `sudo` may be blocked by automated permission checks. Run `apply` yourself in an SSH session.
- Always confirm the terminal is on onode (prompt reads `ubuntu@smalldevllmnode`) before running node commands. A laptop PowerShell tab will fail `cd ~/...`.

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

## Log
**2026-10-16:** Read the course wiki and docs and added the references above. Set up `onode`: build tools, Docker, GitHub CLI, OCI CLI, 16 GB swap, course repo copy, and a reboot onto the new kernel. Ollama 0.40.5 runs as a CPU-only service. Downloaded `gemma4:e4b`, applied and verified the coder profile, and loaded the model. OpenCode installed; its first warm-up turn was started.

**2026-10-09:** Mirror added; rootsh, openssh, pc-connectivity-manager, maemo-control-usb installed. N810 on hotspot Wi-Fi. Laptop ping confirmed; SSH needs the legacy host-key flag (retry pending). Cleanup: maps, games, music, themes removed.

## Next Steps
1. Retry SSH from the laptop with the legacy flags.
2. Set up key login from a local assistant session on the laptop.
3. Finish cleanup (`WMPInfo.xml`, `Video`, `Downloads`, `.apt-archive-cache`); recheck free space.
4. Connect the N810 to the Oracle node.
5. Measure round trip to the node; decide what to offload.
