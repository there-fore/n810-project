# Creature demo sketch (October)

A short demo, **separate from the final project** ([PROJECT.md](PROJECT.md), Environmental Vibe DJ). Its purpose is to show what the N810 can do before the final project. Brief written 2026-10-25 from the original handover and the sensor probes. The proposed design and build plan are under [Design](#design-proposed-2026-10-25) and [Build plan](#build-plan).

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

## Design (proposed 2026-10-25)

Rose chose these on 2026-10-25: a **shy hatchling called Mote**, a **guided 2-minute script**, **chirps + text** (no spoken narration), and an LLM that gives **mood-change lines** and **answers what you say**. Talking starts by **just speaking** (no button). The keyboard door opens onto **the outside room**. The demo ends with a **goodnight line**. The numbers below (thresholds, trust points, timings) are Claude's first proposal for Rose to review; tune them on the device.

### Who Mote is

- **What it is:** a small round blob that has just hatched inside the N810. It has never seen anything outside the screen.
- **What it wants:** to learn what is outside the device. Opening the keyboard ("the door") is the thing it wants most.
- **Personality:** shy and curious. It starts timid, hides from loud sounds, and warms up to petting, being held and a gentle voice.
- **How it talks:** first person, present tense, short wide-eyed sentences (12 words at most). It doesn't know the names of things, so it describes them by feel: "a warm thing", "the big bright". Example: *"Something warm touched me. I think it was you."*
- **Why this suits the LLM:** Gemma E2B invents facts. Mote knows no facts, only what it has sensed, so its "fact sheet" is its own memory list and anything odd it says reads as a hatchling's guess.

### Mood and memory (all on the device)

**Trust** is one number from 0 to 10, starting at 3. It sets the mood band:

| Trust | Mood | Looks like |
|---|---|---|
| 0–3 | **timid** | Small, eyes half open, stays near the bottom edge |
| 4–6 | **curious** | Normal size, looks toward your finger |
| 7–10 | **fond** | Bigger, bouncy, follows your finger |

| Event | Trust change |
|---|---|
| Petting | +1 for every 300 px stroked, added up over quick swipes; at most +3 per petting session, which ends after 2 s without petting. (Changed in step 2: Rose pets in quick swipes and wants petting to win Mote over fast) |
| Hold (comfort) | +1 once per hold; also ends a hide early |
| Gentle voice (it hears you talk) | +1 per reply |
| Single poke | 0 |
| 3 or more pokes within 5 s | −1 |
| Clap / loud bang | −2 |
| Door opens (it sees outside) | +2 |

**Memories** are a list of the last 8 events, each with the time since it woke: *woke up*, *petted*, *poked*, *poked a lot*, *startled by a loud sound*, *held*, *heard "…"*, *saw outside (bright / dim)*. They stay on the device and are sent with every LLM request; the LLM is told it knows nothing else.

### Demo script (about 2 minutes, guided)

The presenter does each step. Every step's reaction happens on the device at once; the "Mind" column is the LLM line that follows a couple of seconds later.

| Time | Presenter does | Mote does (instantly) | Mind says (about 2 s later) | Trust → mood |
|---|---|---|---|---|
| 0:00 | Holds a thumb over the light sensor while introducing the demo | Asleep, curled up, slow breathing. Ignores voice while asleep | — | 3 timid |
| 0:15 | Uncovers the sensor | Eyes flicker open, stretch, a little chirp | Wake line: *"It's bright. Is someone there?"* | 3 timid |
| 0:25 | Strokes Mote slowly for about 3 s | Leans into the finger, purr chirp, blush | Mood line (timid → curious) | 5 curious |
| 0:40 | Pokes it once | Flinch, "eep" chirp, bounce | — | 5 curious |
| 0:50 | Claps once | Shrinks and hides at the bottom, eyes shut, for 3 s, then peeks out | Startle line (curious → timid): *"That was loud. I'll stay small."* | 3 timid |
| 1:05 | Holds a finger still on it | Calms, eyes close happily, comes back out | Mood line (timid → curious) | 4 curious |
| 1:15 | Says something gentle, e.g. "Hi Mote, it's okay" | Ripples around its "ears" while listening, then a thought bubble | Reply to what was said | 5 curious |
| 1:35 | Slides the keyboard out | The door opens: the background becomes the outside room, Mote peeks out | Door line about the outside, bright or dim from the light sensor | 7 fond |
| 1:50 | Closes the keyboard, covers the light sensor | Yawns, eyes droop | Goodnight line that mentions one memory, then it sleeps | 7 fond |

Mood lines and the startle line merge when they happen together (one line, not two).

### Affordance → behaviour (with thresholds)

Starting numbers come from [probes/SENSORS.md](probes/SENSORS.md). Mic and light use the room's recent level (the "baseline"), not fixed values, so the same code works in a dim room and a bright one.

| Affordance | Read how | Detect when | Mote does |
|---|---|---|---|
| **Light covered** | Poll `lux` 3 times a second | First reading ≤ 2 → *drowsy* (eyes half-close, feels instant). Still ≤ 2 after 2 s → *asleep* | Sleeps. While awake for 20 s or more, falling asleep triggers the goodnight line first |
| **Light uncovered** | Same | First reading ≥ 5: eyes start opening at once (1 s). Dark again during that second → back to sleep. (Waiting for 2 readings made it wake 2–4 s late.) | Wakes (wake line) |
| **Light, after a slide** | — | Ignore light changes for 1.5 s after the keyboard moves, because opening it tilts the device | — |
| **Poke** | pygame mouse events | Down and up within 0.6 s, moved less than 20 px (measured taps: 0.05–0.55 s, drifting up to 18 px) | Squints `> <` and squashes. 3 or more in 5 s → annoyed for 2 s (shakes, turns reddish, thick frown), trust −1 |
| **Pet** | Same | Finger down on Mote and moved 25 px within the first 0.6 s, or 60 px at any time | Smiles `^ ^`, blushes, leans toward the finger; trust rises |
| **Hold** | Same, plus a timer (a still finger sends no events) | Pressed for over 1 s without becoming a pet (a pressing finger drifts up to ~30 px), or petting and then resting the finger for 1 s. 60 px of rubbing turns it back into a pet | Closes its eyes contentedly `u u`, settles lower and wider, breathes slower and deeper, small hearts float up; ends a hide early |
| **Touch targets** | — | Mote is at least 200 px wide; its hit area adds a 40 px margin (aim is off by up to ~30 px). A lift and press again within 0.1 s, nearby, during a pet or hold counts as one touch (light presses drop out); fast pokes stay separate | — |
| **Mood looks** | — | Timid: smaller (85%), eyes a third closed. Curious: normal size, eyes follow your finger. Fond: bigger (110%), hops, follows your finger across the screen | — |
| **Keyboard opens** | Poll `slide/state` 10 times a second | `closed` → `open` | Door scene (outside room); door line 1 s later, using the light level after it settles |
| **Keyboard closes** | Same | `open` → `closed` | Back inside |
| **Clap** | Mic loudness every 100 ms; baseline = median of the last 5 s of quiet slices (at least 2) | One slice above 20 × baseline and above 600, back below 5 × baseline within 300 ms | Startle and hide for 3 s (1.5 s if fond), trust −2. While asleep: it stirs and rolls over but stays asleep |
| **Voice** | Same | Above 8 × baseline and above 40 for at least 0.8 s of the last 1 s (short dips allowed) | Starts listening (ripples). Keeps 0.5 s of audio from before, so the first word isn't cut |
| **Voice ends** | Same | Below 4 × baseline for 0.7 s, or 6 s in total | Sends the recording to the mind; thought bubble |
| **Mic, ignored** | — | While asleep (except a clap), while thinking, for 300 ms after each chirp (the speaker is close to the mic), and the first 100 ms after the mic starts (a click) | — |

The mic runs from start to end (it takes about 1 s to start).

### When and what the LLM says

**Triggers** (boundaries only, never in the middle of an event):

1. Waking up
2. A mood band change (timid ↔ curious ↔ fond)
3. After a startle, when Mote peeks out again
4. The door opening (with "bright" or "dim" from the light sensor)
5. The viewer speaking (reply to what it heard)
6. Goodnight, when the light is covered after Mote has been awake 20 s or more

**Pacing:** one request at a time. Unprompted lines (1–4, 6) wait at least 8 s after the last one; if several pile up, only the newest is sent. Replies to speech skip the wait.

**What it sends:** a short system prompt (Mote's personality and rules: 12 words at most, first person, no real names or facts, plain ASCII, no emoji) and the state: the trigger, mood, trust, memories and, for speech, what it heard.

**While the mind thinks:** a thought bubble with three dots. Mote keeps breathing and blinking and still reacts to touch, light and claps; nothing on the device waits for the network.

**Showing the line:** a speech bubble above Mote for 4 s plus 0.1 s per character, then it fades. A chirp plays when it appears.

**If the mind is slow or offline:** after 4 s, the bubble closes and Mote just smiles. For the goodnight line, it falls asleep anyway. Each trigger also has one fixed fallback line on the device, so the whole script works without onode.

### How it fits together

- **On the N810: `mote.py`** (Python 2.5 + pygame), one loop at about 25 frames a second that draws Mote and polls light and the slide. A thread reads the mic (`gst-launch-0.10 dsppcmsrc` writing raw audio to the program; to check: `fdsink` or `filesink location=/dev/stdout`) and works out the loudness. Another thread holds **one** open `ssh onode2` connection to the mind.
- **On onode: `mote-mind`**, a small helper (in the `n810` user's home) started by that SSH connection. It reads one request at a time: a text request, or a recording (8 kHz). For a recording it resamples to 16 kHz, normalizes the volume, sends it to speech recognition (port 8091), strips the `language English<asr_text>` prefix, then asks Gemma E2B (port 8092) and returns one line.
- **Python 2.5 has no `json` module**, so the two sides talk in simple `key=value` lines plus a byte count for audio.
- **Expected waits:** text line about 2 s; speech reply about 1.3 s + 2 s + sending the audio.

## Build plan

Each step ends with a test Rose can do on the device in a visible terminal, with timed prompts. Nothing gets installed or changed on the N810 or onode without her OK.

1. **Smallest loop: a blob that sleeps when the light is covered.** No network, no touch, no sound. First check that pygame can open full screen on the N810's display from an SSH session (`DISPLAY=:0`, as `user`). Then draw Mote breathing and blinking, poll `lux` at 3 Hz, and use the drowsy / asleep / wake thresholds above. Test: cover and uncover 5 times; it should go drowsy at once, sleep after about 2 s and wake within about 1 s, every time.
   **Done 2026-10-25** ([mote/mote.py](mote/mote.py)): see [Step 1 results](#step-1-results-2026-10-25) below.
2. **Touch:** poke, pet and hold, with trust and the mood bands. Show trust in a small debug corner.
   **Done 2026-10-25**: see [Step 2 results](#step-2-results-2026-10-25) below.
3. **Keyboard door:** the outside room, plus the 1.5 s light-ignore window.
4. **Mic:** baseline, clap startle and hide, chirps, and the 300 ms mute after each chirp.
5. **Mind, text only:** write `mote-mind` on onode (with Rose's OK), the open SSH connection, the wake and mood lines, the thought bubble, the 4 s timeout and fallback lines.
6. **Voice:** listening detection, sending the recording, the reply.
7. **Rehearse:** run the script 3 times end to end, measure memory and CPU, log the mic and light levels, and retune the thresholds in the demo room.

## Step 1 results (2026-10-25)

[mote/mote.py](mote/mote.py) draws Mote breathing and blinking and follows the light sensor. Run it from the laptop:

```
scp mote/mote.py mote/run-mote.sh n810:/tmp/
ssh -t n810 sh /tmp/run-mote.sh test
```

`test` shows timed COVER / UNCOVER prompts at the top-left of the N810's screen (the terminal shows them 1–2 s late) and prints a summary. Without `test` it runs until the top-right corner is tapped; a number (e.g. `20`) quits after that many seconds. `run-mote.sh` starts it as `user` on the N810's screen (`DISPLAY=:0`; the display needs no key).

- **Display:** pygame opens full screen on the N810 from an SSH session (checked by Rose).
- **Light, 5 rounds** (seconds after each prompt, including Rose's reaction): drowsy 0.8–1.9 s, asleep 3.0–4.0 s, eyes open 0.8–1.2 s, fully awake 1.8–2.2 s. Every round worked.
- **Sensor timing:** covering takes lux from about 9 to 0 in 0.3–0.4 s; uncovering usually jumps from 0 to 7–10 in one reading, once via 1 first (0.7 s).
- **Speed:** a steady 25 frames per second. Python used about 35–50% of the processor (`top`: 35% awake), the screen server (Xomap) about 6%. Drawing takes 5–8 ms per frame. Step 2 dropped to 20 frames per second awake and 10 asleep: about 19%.
- **Memory:** about 6.5 MB resident. The web browser's background process (`browserd`) was also running.

## Step 2 results (2026-10-25)

[mote/mote.py](mote/mote.py) now feels touch. Run the touch test from the laptop (after copying the files over as in step 1):

```
ssh -t n810 sh /tmp/run-mote.sh touch
```

It prompts on the N810's screen: poke twice, pet, hold, then poke 4 times fast, and prints what Mote felt in each step. `annoy` runs only the fast pokes, twice. `raw` logs every touch event pygame delivers. The bottom-left corner shows trust, mood and the last thing Mote felt.

- **Final run** (the 5th touch test): poke 1 of 2 (the miss lasted 0.55 s, so the limit went from 0.4 to 0.6 s afterwards, untested), pet 6 swipes → +2, hold → +1, fast pokes 5 of 5 felt and annoyed on the 3rd. Rose saw the squint, smile, fond and (after making it stronger) annoyed looks clearly.
- **Touch reaches pygame in screen pixels.** An aim test ([probes/aim_probe.py](probes/aim_probe.py), 5 crosses) put taps within about 10 px, with one 32 px off in the top-right corner. Early pokes landed about 70 px right of Mote's edge, so the touch margin went from 20 to 40 px and the prompts say "the middle of Mote".
- **How Rose touches:** taps last 0.05–0.55 s and drift up to 18 px. Petting is quick swipes of 0.15–0.9 s and 80–200 px with lifts in between, not one long stroke. Fast pokes come about 0.1–0.2 s apart, close enough that joining dropouts merged them into one "pet" until dropouts were limited to pets and holds.
- **Speed:** 20 frames per second, about 19% of the processor (down from 35% at 25 frames per second).
- **Not yet:** touch while asleep is ignored (the design doesn't say what it should do). Hiding (from a clap) comes with the mic step, so "hold ends a hide early" is untested.
- **Hold gets its own look** (after the step 2 runs): held, Mote closes its eyes in a `u u` curve, settles lower and wider, breathes slower and deeper, and floats small hearts. Before this it used the petting smile, so a hold only stood out when it changed the mood (as in the 3rd touch run, 6 → 7, fond). Rose: "clear, keep it". Checked with `hold` mode (`ssh -t n810 sh /tmp/run-mote.sh hold`).
- **Hold vs slow drift:** one hold drifted 28 px in its first second and was taken as a pet. Pet now needs 25 px within 0.6 s (or 60 px any time), and a hold allows drift. A pet that rests for 1 s becomes a hold. Last `hold` run: 2 of 2 holds felt (one after petting, with a lift in between). Petting and then resting without lifting is not tested yet.
- **Light during the touch runs:** in one `hold` run the sensor read 2 lux and Mote fell asleep before the test began. Rose's hand was covering the sensor by accident, so the device was fine. The light thresholds are still fixed numbers (the design's "relative to the room's level" is not built), but nothing so far shows that is a problem.
