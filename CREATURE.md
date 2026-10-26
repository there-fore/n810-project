# Creature demo sketch (October)

A short demo, **separate from the final project** ([PROJECT.md](PROJECT.md), Environmental Vibe DJ). Its purpose is to show what the N810 can do before the final project. Brief written 2026-10-25 from the original handover and the sensor probes; the design itself starts here.

## Concept

A Tamagotchi-style creature living in the N810. Each of the device's affordances gets a role, and an LLM on onode narrates its memories and mood **between** moments.

| Affordance | Creature behaviour (starting idea) |
|---|---|
| Light sensor covered | Falls asleep; wakes when uncovered |
| Loud sound (clap) | Startles |
| Voice | Notices it is being talked to |
| Touch | Pet, feed, poke |
| Keyboard slides out | "Opens a door" (a scene change) |
| LLM on onode | Narrates memories and mood at the boundaries (mood changes, after an event), never in the middle of one |

The Oct 15 "ambient only" direction applies to the final project, not this demo: **touch and the screen are allowed here.**

## Design principle: the latency budget

- **Instant (< 50 ms, on the device): the "feel".** Touch, slide, light, drawing, short sounds. Never wait on the network for these.
- **Seconds (over the network to onode): the "mind".** LLM (Gemma E2B on port 8092 about 2 s; `gemma4:e4b` 26–36 s), text-to-speech (about 2x real time), speech recognition (about 1.3 s). Use them only at boundaries.

## What the sensors give (measured 2026-10-25)

Full table, paths and scripts: [probes/SENSORS.md](probes/SENSORS.md). Quick reference: [CHEATSHEET.md](CHEATSHEET.md#sensors-at-a-glance-for-design).

| Input | Reads as | Speed | Design notes |
|---|---|---|---|
| Touch | X/Y in screen pixels via pygame mouse events; pressure only from `/dev/input/event3` (root) | ~50 updates/s while moving; silent while still | Tell gestures apart by timing: *poke* = down and up in < 0.3 s; *pet* = down and moving slowly; *hold* = down and still > 1 s. Press firmly. Targets ~60–80 px. Jitter ≈ 2 px. |
| Light | `lux` 0 (covered) to ~90 indoors; readable as `user` | New value every ~0.4 s | Covered → 0 in ~0.8 s, so "falling asleep" can take a beat. Tilting the device changes it too. |
| Keyboard slide | `open` / `closed`; readable as `user` | Instant | Opening also tilts the device, so light jumps at the same time. |
| Mic | Loudness per 100 ms (8 kHz mono via `gst-launch-0.10 dsppcmsrc`) | Starts ~1 s after launch; keep it running | Quiet 1–2, voice 50–240, clap ~1000+. Clap = one spike gone in ~200 ms; voice stays up > 1 s. Compare with the room's recent level, not fixed numbers. |
| Not available | No accelerometer or gyroscope. Lock switch and headphone jack unverified. Webcam, Wi-Fi, GPS not probed. | | |

## What the device can run

- **Python 2.5.2 + pygame 1.7.1** (SDL 1.2): drawing, touch, short sounds (`pygame.mixer`), text with fonts. Old Python: no `with` without a `__future__` import, `print` is a statement, no `audioop`.
- **`play-sound`** plays WAV files; system sounds are in `/usr/share/sounds`.
- **128 MB of RAM, 400 MHz ARMv6.** One program at a time. Measure memory once the creature runs.
- **Screen 800x480.** Not yet checked: running pygame full-screen on the X display from an SSH session (it needs `DISPLAY=:0` and permission to use the display), or launching it from the N810 itself.

## Reaching the "mind" (onode)

- From the N810: `ssh onode2` (user `n810`, port 2222). Each new SSH connection costs about 3 s of N810 CPU, so **keep one connection open** and send narration requests through it.
- Gemma E2B (llamatalk, port 8092) listens on onode's `127.0.0.1` only and is reached through that SSH connection. It needs a fact sheet in its prompt, or it invents things. Not yet built: a node-side helper like `n810-ask` that takes the creature's state and returns one short line of narration.
- Network: at home the N810 uses the home Wi-Fi (about 24 ms with N810 power saving off); elsewhere the phone hotspot. `ssh n810` on the laptop picks the right address.

## Open design questions

1. **Who is the creature?** A name, a personality, what it wants. This decides what the narration sounds like.
2. **What does it remember?** Which events become memories (being woken, being poked, the door opening), and how they change its mood over minutes.
3. **What does the LLM add** that fixed rules can't? For example, connecting several memories into a short story, or answering what you say to it.
4. **What does the screen show** while the mind is thinking (2 s or more)? Idle animation, a thought bubble, nothing?
5. **How long is the demo**, and what does a viewer do in it? A script of 1–3 minutes would set the scope.
6. **Sound:** chirps from `pygame.mixer`, spoken narration (text-to-speech on the node, sent back as audio), or text only?

## Suggested first steps

1. Answer questions 1 and 5 (who, and the shape of a 1–3 minute demo).
2. Smallest complete loop: a pygame window with a blob that sleeps when the light is covered and wakes when uncovered. No network.
3. Add touch gestures, then the slide, then the mic startle.
4. Add one narration line from onode at a mood change, keeping the device responsive while it waits.
