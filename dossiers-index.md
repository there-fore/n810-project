# Index of the course dossiers

Source: https://github.com/mfadt/sld-fall-2026/tree/main/dossiers
Indexed 2026-10-21 at commit `5202a75` (last dossier change 2026-10-08). If the folder has changed since, re-check before trusting a section number.

Dossiers are the instructor's development record: what was tried on the demo node, what it measured, and what was wrong. Corrections stay in the text with dates. `MEASURE[name]` marks an open question. Student guides live in `docs/`.

**Fetch one file:**

```bash
gh api repos/mfadt/sld-fall-2026/contents/dossiers/node-coder-tools.md -H "Accept: application/vnd.github.raw"
```

**Check for changes since this index:**

```bash
gh api "repos/mfadt/sld-fall-2026/commits?path=dossiers&per_page=5" --jq ".[] | .sha[0:7] + \" \" + .commit.committer.date + \" \" + .commit.message"
```

Line numbers below (`L123`) are where each section starts at the indexed commit.

## Start here

- **`README.md`**: the map. "What is current" (L62) is a table of which claims still stand when dossiers disagree. "Still open" (L114) lists the `MEASURE` markers.

## Most relevant to the N810 project

Your node runs 4 OCPU / 23 GB, `gemma4:e4b`, and OpenCode.

| File | What it answers | Go to |
|---|---|---|
| `node-coder-tools.md` | Running OpenCode, Hermes and Claude Code on the node, and how each breaks | §2 L56 measurements (OpenCode: 6.7k-token overhead, ~6 min cold, 2–2.5 s warm). §3.3 L125: the 5-minute client timeout means the first request fails. §5 L258: the node goes cold after automatic updates. §6 L279: what to do |
| `node-harness.md` | What the node is good for: prefill speed, context window, which model | §1.1 L28 prefill ~17–24 tok/s. §1.2 L52: overflow is silent. §2.1 L131: coder profile, `OLLAMA_CONTEXT_LENGTH=65536`, and how the box died. §3.1 L337: `gemma4:e4b` is the model to host a 64k coder tool. §6 L639: no MCP on this node |
| `node-tuning-candidates.md` | Node tweaks not yet applied | §1.1 L21: 5-minute load timeout. §2.2 L169: needrestart restarts Ollama. §2.3 L189: a warm-up unit. §2.5 L241: give Ollama scheduling priority. §5 L330: order to try them |
| `self-hosted-ai-kit.md` | Plan A for one student on the free 4 OCPU / 24 GB node | Phases 0–6 from L147. Phase 3 L257: exposing the service in three steps (Open WebUI, access). §4 L853: model ladder. §6 L919: results, including the 16/96 rerun at L951 |
| `sld-benchmark-results-20260911.md` | Raw benchmark table for 9 models (prompt/gen tok/s, RAM, load time). `gemma4:e4b`: ~20 tok/s generation | Whole file (has terminal escape codes) |

## Coding with the node (older, in reading order)

| File | What it answers | Go to |
|---|---|---|
| `node-coding-assistant.md` | Can the node run a coding assistant, and what makes it fast? (§1 has since expired) | §2 L82: the tool list is the limit. §3 L100: `gh` via a shell tool, no MCP. §4 L122: what made it fast |
| `node-delegation.md` | Can a paid model hand grunt work to the node? | §2 L103 executing 5/5. §3 L127: reviewing is the weak link. §4 L174: the test belongs on the paid side |
| `node-delegation-in-anger.md` | One real task in a real repo, with a paid-model control | §4 L119: the paid model made the same mistakes. §5 L147: the node saves ~$0.19/task |
| `node-16x96-first-day.md` | The node resized to 16 OCPU / 96 GB, and an OpenCode run on it | §3 L66 ladder. §5 L110: agent loop vs benchmark (OpenCode overhead 6.7–8k tokens, `small_model`, keep-alive). §6 L142: two sessions on one slot. §9 L249: measurement errors |
| `sld-benchmark-results-20260913.md` | Same 9-model battery at 16/96 | Results L54 |
| `sld-benchmark-analysis.md` | A benchmark plan whose scripts never ran; replaced by `sld-battery.sh` | Historical only |

## Other projects and infrastructure

| File | What it answers | Go to |
|---|---|---|
| `d12-lab-cluster.md` | Idle D12 lab GPU workstations as course machines (~170–180 tok/s on `gemma4:e4b`) | §2–2c L33–169: the three boxes. §5 L276: architecture. §6 L310: Tailscale. §8 L340: open questions |
| `first-build-video.md` | Making the "first build on a device" guide and video, tested on an emulated Raspberry Pi 3B | §5 L148: what the emulator hides. §6 L190: validation step by step. §7 L450: emulator vs real Pi. §9 L493: the recorded take |
| `edge0-m1-macos-protocol.md` (+ `edge0-bench.sh`) | A test plan (not results) for running models on an 8 GB M1 Air | "Pitfalls" L145, "Picking this up" L157 |
| `sketchgen-gallery.md` | Spec for a gallery that generates its own p5 sketches | §3 L103: the gate. §6 L367: credentials. §8 L428: what "unattended" means |
| `sketchgen-build-plan.md` | Task packets handed to agents to build sketchgen | §1 L49: ground rules. §5 L158: packets. §12 L385: status |
| `sketchgen-build-day.md`, `sketchgen-day-two.md` | Records of the build night and the operator's day | "What broke" sections (L79, L105) |
| `sketchgen-job-166.md` | One job that never finished a frame, and the escalation | §2 L45, §5 L107 |
| `week4-pulse-survey.md` | Student survey, Week 4 and Week 6 (n = 15; guides "too dense") | §2 L57 results. §3 L75/L105 readings. §4 L165: what changed |

## Not covered anywhere

The N810, Maemo, legacy SSH, and how terminal UIs render on old devices (the garbled `oc` screen). For those, see `N810-setup.md` and `HANDOVER.md` in this repo.
