# N810 Cheat Sheet

What to type, where, and what's installed. Current state only; the history is in [N810-setup.md](N810-setup.md). Last checked 2026-10-25.

**First check which machine you're on.** Each short name only exists on one machine: `n810` on the laptop, `onode2` on the N810. Typed on the wrong one, it fails with `Name or service not known` or `Could not resolve hostname`.

## On the N810 (X Terminal, as `user`)

Open X Terminal from Menu > Utilities > X Terminal.

| Type | What it does | Time |
|---|---|---|
| `ask <question>` | Plain-text answer from `gemma4:e4b` on the node | 26–36 s |
| `agent <task>` | OpenCode file or coding task on the node, in `~/work` | Minutes (491 s for one task) |
| `oc` | OpenCode full-screen. Prints garbage (`66;`, `w=1`); don't use | — |
| `ssh onode2` | Log in to the node as `n810` | ~3.6 s |
| `/sbin/ifconfig wlan0` | Current IP (read `inet addr:`) | — |
| `sudo gainroot` | Root shell | — |
| `du -sk /media/mmc2/*` | Folder sizes on the internal card, in KB | — |

Examples: `ask what is a Nokia N810?` · `agent show me the files in this folder`

### Typing on the N810
- **Symbols** (`|`, `<`, `>`): blue Fn key plus the printed symbol, or the on-screen keyboard.
- **The bar at the bottom of X Terminal** has Tab, Esc, PgUp, PgDn and Ctrl.
- **No lone apostrophes.** `what's` opens a quote the shell waits to close. Write `what is`, or put the whole question in double quotes.
- **Put spaces between parts:** `ls -la /media/mmc2`, not `ls -la/media/mmc2`.
- **Long output scrolls away.** Add `| more` (Space for the next page, q to quit).
- **Network tools are in `/sbin`.** Type the full path, as in `/sbin/ifconfig`.
- **The keyboard is slow.** Use the short commands above, not full ones.

### Screen (800x480, X Terminal)
- Plain text only, printed line by line. Full-screen programs that ask the terminal about itself (OpenCode, other modern text interfaces) print garbage.
- `ask` replies are kept short, with no markdown or tables, and Unicode punctuation is swapped for ASCII on the node.
- Not measured yet: how many columns and rows X Terminal shows, and whether `ask` replies fit without scrolling.

## Sensors at a glance (for design)

Measured 2026-10-25 in one dim room. Paths, raw numbers and probe scripts: [probes/SENSORS.md](probes/SENSORS.md).

| Sensor | Gives | Speed | Good for | Watch out |
|---|---|---|---|---|
| Touch | X/Y (and pressure) | ~50 updates/s while moving | Poke, pet, hold (tell apart by timing and movement) | Press firmly; light touches drop out. A still finger sends nothing. Targets about 60–80 px. |
| Light | 0 (covered) to ~90 lux indoors | New value every ~0.4 s | Sleep/wake, "lights off" | Covering takes ~0.8 s to reach 0. Tilting the device changes it too. |
| Keyboard slide | open / closed | Instant | Big one-off event ("open a door") | Opening also tilts the device, so light jumps too. |
| Mic | Loudness (8 kHz mono) | 100 ms slices | Clap = startle (sharp spike); voice = attention (longer hump) | Takes ~1 s to start: keep it running. Compare with the room's usual level, not a fixed number. |
| Lock switch, headphone jack | on / off | — | Possible extra events | Not verified yet |

Everything above reacts on the device in under ~200 ms. Only narration and speech recognition go to the node (seconds). Not available: accelerometer, gyroscope. Not probed yet: webcam, Wi-Fi, GPS.

## On the laptop (PowerShell)

| Type | What it does |
|---|---|
| `ssh n810 <command>` | Run one command on the N810 as root, e.g. `ssh n810 uname -a` |
| `ssh n810` | Log in to the N810 as root |
| `ssh -o BatchMode=yes n810 uname -a` | Check that key login works (fails instead of asking for a password) |
| `ssh onode` | Log in to the node as `ubuntu` |
| `cmd /c "ssh onode2 bash -s < file.sh"` | Run a script on the node without PowerShell adding `\r` to every line |

**`ssh n810` picks the network by itself.** Before connecting, `~/.ssh/n810-at-home.cmd` checks the laptop's Wi-Fi: on the **home Wi-Fi** it uses `<N810-home-IP>`, anywhere else the phone hotspot address. One saved key covers both (`HostKeyAlias n810`). Check which address it will use: `ssh -G n810 | findstr hostname`.

If a network gives the N810 a new address, change that address in `~/.ssh/config`: the `Match … exec` rule for home, the `Host n810` entry for the phone. Find the N810's address on the device with `/sbin/ifconfig wlan0`. The laptop and N810 must be on the same network; at school or a coworking space, use the phone hotspot (those networks usually block devices from reaching each other).

**N810 Wi-Fi settings** (per connection, under Advanced): home Wi-Fi = power saving **Off**, WPA2 only, 100 mW. Power saving off cut average ping from 204 ms to 24 ms; leave it on for battery use.

## On the node (`ssh onode`)

| Type | What it does |
|---|---|
| `ollama ps` | Is `gemma4:e4b` loaded? (should say `UNTIL Forever`) |
| `~/llamatalk/start.sh` | Start the speech and Gemma E2B servers |
| `~/llamatalk/stop.sh` | Stop them. Do this before an `ask` demo unless you're showing speech. |
| `~/sld-fall-2026/examples/coder-tools/coder-node.sh verify` | Check the Ollama coder profile |
| `~/sld-fall-2026/examples/coder-tools/coder-node.sh warm` | Load `gemma4:e4b` by hand |

The prompt should read `ubuntu@smalldevllmnode`. If it doesn't, you're still on the laptop.

## What's installed

### N810
| Name | Kind | Purpose |
|---|---|---|
| rootsh | package | Root shell (`sudo gainroot`) |
| openssh (client, server) | package | SSH in from the laptop and out to the node; sftp, scp |
| pc-connectivity-manager, maemo-control-usb | package | USB networking setup (not in use yet) |
| `ask`, `agent`, `oc` | script in `/home/user`, linked in `/usr/bin` | Launchers above |
| `id_rsa_onode`, `onode2` config | key and config, in both `/root/.ssh` and `/home/user/.ssh` | Login to the node |
| python2.5, python2.5-pygame (with numeric, libsdl-ttf) | package, added 2026-10-25 | Python 2.5.2 + pygame 1.7.1 for the creature demo and probes |
| gstreamer0.10-tools | package, added 2026-10-25 | `gst-launch-0.10`, used to record the mic (`dsppcmsrc`) |

Package catalog: `http://maemo.viniciuspaes.com/extras/`, distribution `diablo`, components `free non-free`. The mirror is unsigned, so command-line installs need `apt-get install --allow-unauthenticated <package>`. Sensor paths and measurements: [probes/SENSORS.md](probes/SENSORS.md).

**Clock:** the N810 resets to 1970 on every reboot (no `hwclock`). After each boot, set it from the laptop in PowerShell, before installs or anything time-based:
`ssh n810 date -u ((Get-Date).ToUniversalTime().ToString('MMddHHmmyyyy.ss'))`

### Node
| Name | Where | Purpose |
|---|---|---|
| Ollama 0.40.5 + `gemma4:e4b` | systemd service | The model behind `ask` and `agent` |
| `ollama-warmup.service` | systemd | Reloads `gemma4:e4b` whenever Ollama starts |
| OpenCode 1.19.3 | `/usr/local/bin/opencode` | Agent behind `agent` |
| `n810-ask`, `n810-agent` | `/usr/local/bin` | Node side of `ask` and `agent` |
| `ssh-legacy.service` | systemd | SSH for the N810 only (port 2222, user `n810`) |
| llamatalk | `~/llamatalk` (ubuntu user), started by hand | Speech recognition, Gemma E2B, speech |

### Node services and ports
| Port | Service | Reachable from |
|---|---|---|
| 22 | Main SSH (`ubuntu`) | Laptop |
| 2222 | Legacy SSH (`n810` only, key only) | N810 (open to the internet) |
| 11434 | Ollama | Node only |
| 8091 | llamatalk speech recognition (Qwen3-ASR) | Node only |
| 8092 | llamatalk language model (Gemma E2B) | Node only |
| 8093 | llamatalk speech (Pocket TTS) | Node only |

Services that are "node only" are reached from the N810 by going through `onode2`.

## Before a demo
1. On the node: `ollama ps` shows `gemma4:e4b` loaded.
2. On the node: `~/llamatalk/stop.sh`, unless the demo uses speech.
3. On the N810: on the phone hotspot; `ask` with a short question as a warm-up.
