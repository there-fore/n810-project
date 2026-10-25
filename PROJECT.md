# Project: Environmental Vibe DJ

The artistic side of the N810 project (PSAM 5600 B, Fall 2026). The technical setup is in [N810-setup.md](N810-setup.md); commands are in [CHEATSHEET.md](CHEATSHEET.md).

> **Before technical work, reread the Big Questions.** Each technical decision should serve the chosen framing, not just work.

The N810 is personally owned, so it can be cleaned, reconfigured or reflashed freely. David Carroll approved it as the semester device (the brief mentions ARM64; the N810's ARM11 is 32-bit, and that is accepted).

## Concept (2026-10-15)

A DJ instrument that reads the room instead of the body. The N810 gathers readings from its environmental sensors (light, sound, location, radio), sends a short "vibe snapshot" each bar or two, and an LLM on the server combines that snapshot with any typed prompt to write the next live-coded music pattern. Sound plays through a speaker.

- **Why not gestures:** the N810 has no accelerometer or gyroscope, and GPS is too slow and coarse for arm movement. Gesture control would need an added Bluetooth sensor (Wii Remote, phone, or a small IMU board; a Wii Remote has been connected to an N810 before).
- **Why latency doesn't matter:** live-coding engines apply changes on the next beat or bar. The ~229 ms hotspot delay disappears inside that quantization, because changes are discrete commands, not continuous playing.
- **What makes it unique:** each sensor reads as a raw number from a Linux shell, so the sensing is visible and legible. A 2007 device reading the room and handing intention to a modern model is the course framing (device as interface to a model) in one object. It fits the threshold motif: environment crosses into sound.

## Direction (decided 2026-10-15)

- **Ambient reads over cognitive inputs.** The room is the interface; computation invisibly turns it into sound. Favor passive environmental sensing (light, room sound, radio environment, location) over deliberate controls (typing, stylus, screen).
- Keyboard prompts and the on-screen display become optional or minimal, not the center of the piece.
- Aligns with the course direction: "computation is not the interface; computation changes the interface."

## Big Questions

Technical progress doesn't settle these; check each build decision against them.

1. **What is it about?** Choose one framing and let it decide which sensors stay:
   - *The room composes itself:* the environment is the author.
   - *Translation through language:* room → machine-written description → code → sound. The vibe snapshot is itself an object worth showing.
   - *Invisible signals made audible:* lead with the Wi-Fi radio environment (the threshold motif most directly).
2. **Who is the author, and what is my role during a set?** "DJ" implies a person in control. If the room composes, is the label wrong? Am I a host, a carrier, a listener?
3. **Why the N810?** If the laptop does the heavy work, what does the N810 contribute beyond nostalgia? Candidate answers: its sensors are readable as plain numbers; its slowness enforces composition in discrete, bar-level changes; its age is part of the content.
4. **Why an LLM?** Fixed rules (light → tempo) already work. Show what the model does that rules can't: interpreting combined conditions or language. If it can't be shown, the LLM is decoration.
5. **Is the computation invisible?** Does anything in the design pull attention to screens and code? Does it obey "computation changes the interface"?
6. **What remains afterward?** Each set is unrepeatable (one place, one hour). Are patterns discarded deliberately? How does this connect to ephemerality, memory, and digital death in the thesis?
7. **Where does the sound come from, and does it matter?** Laptop speaker vs. the instrument itself changes how the audience reads the piece.
8. **How does it advance endogenous technology?** State the link to the thesis framework explicitly in the proposal.
9. **What does it add to precedents?** RjDj (2008, mic-reactive music), Endel (environment-adaptive soundscapes), Phantom Terrains (Wi-Fi sonification via hearing aid, Frank Swain and Daniel Jones), LLM + live-coding experiments. The likely answer is the combination: an LLM interpreting a room, on an obsolete, legible device.

**Biggest risk:** it reads as a clever tech demo. The answer to question 1 is the defense.

## Design affordances of the N810

- **Interface device:** screen and keyboard as a dedicated control panel or terminal.
- **Thin client:** heavy computation offloaded to the node, when local compute time > transfer time + round trip + remote compute time.
- **Voice input:** capture audio on the device, recognize on the server (llamatalk now provides recognition and speech on the node; recording on the N810 is still unsolved).
- **Location:** built-in GPS as an input.
- **Constraint as subject:** the device's limits make computing tradeoffs visible.
- **Control device:** discrete actions (buttons, toggles) work well; continuous control is limited by network latency.

## Inputs available on the N810

| Input | What it senses | Musical use |
|---|---|---|
| Ambient light sensor | Room brightness | Tempo or darkness; covering it with a hand acts as a fader |
| Microphone | Room loudness, rhythm | Density; fill silences; lock to clapping |
| Webcam | Overall motion (frame differencing) | Still room vs. dancing room (not gesture recognition) |
| GPS | Location, slowly | Music changes as you walk (sonic map) |
| Wi-Fi scan | Number and strength of nearby networks | Invisible radio environment made audible |
| Touchscreen + stylus | X–Y position and pressure | Kaoss-pad style control |
| Keyboard slide | Open/closed event | Big switch: drop, breakdown, scene change |
| Keyboard | Typed prompts | Plain-language direction for the LLM ("rainy, slower, minor key") |

## Architecture

N810 sensors → vibe snapshot (one text line per bar, e.g. `light=40 noise=62 wifi=11 slide=open`) → laptop or server → LLM writes pattern code → sound engine plays it → speaker.

Principle: build the dumbest complete loop first, then make each part smarter, so a failure points to one layer.

## Build phases

**Phase 0: Foundation.** Done: the three setup stages in [N810-setup.md](N810-setup.md) (clean device, secure connections, node services for the N810). Still to decide: the sound engine runs on the laptop first, and moves to the node only if needed. Optional: USB networking as a Wi-Fi-independent link.

**Phase 1: Each sensor becomes a number.** Started 2026-10-25: light, touch, keyboard slide and mic are measured in [probes/SENSORS.md](probes/SENSORS.md). Wi-Fi scan, GPS and webcam remain.
- Research where Diablo exposes each sensor (Maemo wiki "N810 light meter" page; Maemo location service for GPS; Wi-Fi scan tools may need root).
- Explore, easiest first: light sensor, keyboard slide, Wi-Fi scan, touchscreen (pressure?), mic loudness, GPS, webcam motion.
- Test: log each about once per second for a few minutes; record range, rate of change, CPU cost.
- Output: a sensor table.

**Phase 2: Sound engine that accepts outside changes.**
- Research which live-coding tool lets another program replace the pattern while playing (TidalCycles and Sonic Pi accept network input; Strudel runs in a browser, harder to control externally).
- Build a laptop script that receives pattern text and applies it.
- Test: changes land cleanly on the bar.

**Phase 3: Transport N810 → laptop.**
- Build the vibe snapshot format.
- Explore an SSH command vs. a small UDP message (check whether BusyBox has `nc`).
- Test delivery rate, loss on the error-prone Wi-Fi, battery drain over 30 minutes.

**Phase 4: The dumb loop (no AI).**
- Build fixed rules (light → tempo, noise → density).
- Test: cover the light sensor and hear the music change. **First milestone.**

**Phase 5: Add the LLM.**
- Build a prompt combining the snapshot and typed text, returning pattern code.
- Build a safety net: if generated code fails, keep playing the last good pattern.
- Test generation time vs. bar length; if slower, request changes every 4 or 8 bars.
- Model choice, from measurements: `gemma4:e4b` takes 26–36 s per short answer; Gemma E2B on llamatalk takes about 2 s but gets facts wrong without a fact sheet.

**Phase 6: Connection to the speaker.** Audio is born wherever the sound engine runs. Every hop between there and the speaker adds delay and a failure point, so the shortest path is the most reliable.

| Route | Path | Strengths | Risks |
|---|---|---|---|
| A. Laptop → speaker (start here) | Laptop audio out by cable or Bluetooth | Shortest path, lowest delay, most reliable; N810 is purely the controller | Sound doesn't come from the instrument itself |
| B. Stream via N810 | Laptop streams over Wi-Fi → N810 → 3.5 mm cable → powered speaker | Sound visibly comes from the instrument | Stream buffering adds seconds of delay; depends on the error-prone Wi-Fi |
| C. N810 Bluetooth | N810 → Bluetooth (A2DP) → speaker | Cable-free, wearable | A2DP on Diablo needs add-on software (verify on the mirror); Bluetooth and Wi-Fi share 2.4 GHz |

- Research what stream formats the N810's internet radio player accepts (likely MP3 over HTTP), and whether an A2DP package exists for Diablo.
- Test time from sensor change to audible change on each route; dropouts over 20 minutes; N810 volume that drives a powered speaker without distortion.

**Phase 7: The face of the instrument.**
- Build a terminal display of current sensor values and the active pattern. Plain line-by-line output only (full-screen interfaces garble on X Terminal).
- Research later: a graphical interface. Python 2.5 + pygame and GTK are both on the device since 2026-10-25, but this conflicts with the ambient direction, so keep it minimal.

**Phase 8: Performance testing.** Battery life, behavior when Wi-Fi drops, a full 20-minute set in a real room.

## Open research questions

- Sensor access paths on Diablo: light sensor and keyboard slide **found** (2026-10-25, [probes/SENSORS.md](probes/SENSORS.md)); Wi-Fi scan and GPS still open.
- Does the touchscreen report pressure? **Yes**, alongside X/Y (direction unconfirmed: a firmer press may read lower).
- Is `nc` available in BusyBox 1.6.1?
- Does Wi-Fi scanning disrupt the active connection?
- Which stream formats does the N810 play; is A2DP available for Diablo?
- How to record audio on the N810: **solved** with `gst-launch-0.10 dsppcmsrc` (8 kHz mono only).
- Can the OMAP 2420's DSP be used for on-device audio? Partly: the mic goes through the DSP, and recording costs about 4% of the ARM CPU.
