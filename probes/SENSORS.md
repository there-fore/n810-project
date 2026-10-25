# N810 sensor table

Measured 2026-10-25 on the N810 over `ssh n810` (root), for the October creature demo. Each probe is a small Python 2.5 script in this folder; copy it over and run it on the device (commands below). Numbers come from one room (dim indoor light) and one session, so treat ranges as starting points: the creature should learn each room's normal level as it runs and react to changes relative to it.

## Summary

| Input | Read path | Range seen | Update rate | CPU cost | Notes |
|---|---|---|---|---|---|
| Touchscreen (TSC2301) | `/dev/input/event3` (root only), or X mouse events in pygame (any user, already in screen pixels) | Raw 12-bit: X ≈ 410–3640, Y ≈ 650–3430. Pressure 50–97 when pressed firmly | ~52 Hz while the finger moves; nothing while still | 0.5% idle, 11% streaming in Python | Still finger wobbles ≈ 8 raw units (≈ 2 px). Light presses drop out; press firmly. Pressure may read lower for a firmer press (unconfirmed). |
| Ambient light (TSL2563) | `/sys/devices/platform/i2c_omap.2/i2c-0/0-0029/lux` (and `adc`, two raw channels) | 0 (covered) to 87 lux in this room | ~0.4 s per new value | 6.2% polling 5 files at 10 Hz (poll lux at ~3 Hz instead) | Covered → 0 in ~0.8 s. `adc` (e.g. `1288 203`) is finer than `lux` and wobbles ±5 at rest. |
| Keyboard slide | `/sys/devices/platform/gpio-switch/slide/state` | `open` / `closed` | Instant, one clean change per slide | Included above | Opening the keyboard also changed light (23 → 81), likely from tilting the device. |
| Lock switch | `/sys/devices/platform/gpio-switch/kb_lock/state` | `open` seen only | — | — | **Not verified:** no change seen during the probe. |
| Headphone jack | `/sys/devices/platform/gpio-switch/headphone/state` | `disconnected` seen only | — | — | **Not tested.** |
| Microphone | `gst-launch-0.10 dsppcmsrc ! filesink` (raw PCM, add a WAV header) | RMS per 100 ms: quiet 1–2, speech 50–240, clap 946–1350 | 8 kHz mono 16-bit only; DSP sends 40 ms (640-byte) buffers | 3.7% (the DSP does the work) | Starts 0.67–1.0 s after launch, so keep it running. A click at switch-on (first ~100 ms) must be skipped. Clap = one spike gone in ~200 ms; speech stays up for over a second. |

## What this means for the creature

- **Touch:** read position and lift from pygame mouse events; read `event3` only if pressure is wanted. A held finger sends no events (Linux drops unchanged values), so detect gestures by timing: *poke* = down and up in under 0.3 s, *pet* = down and moving slowly, *hold* = down and still for over 1 s.
- **Light:** sleep when lux falls near 0 for a few seconds; wake when it rises. Poll at 2–3 Hz.
- **Slide:** a clean binary event; poll at ~10 Hz (or test `select()` on the sysfs file later).
- **Mic:** startle when a 100 ms slice exceeds ~20x the recent average. Clap and voice can be separate reactions by shape. For speech recognition on the node, normalize volume first (peaks only reach about −28 dB).
- **Budget:** everything above runs on the device in under ~200 ms. Only narration and speech recognition go to onode.

## Toolkit on the device

Installed 2026-10-25 from the Diablo mirror (unsigned, so `--allow-unauthenticated`): `python2.5` 2.5.2, `python2.5-pygame` 1.7.1 (with numeric, libsdl-ttf), `gstreamer0.10-tools` 0.10.13. Already present: GTK 2.10, SDL 1.2.8, SDL_image, SDL_mixer. Maemo's Python has no `audioop`, so RMS is computed by hand. `gst-launch-0.10` here has no `-q`.

## Running the probes

From the laptop, in the repo folder:

```
scp probes/touch_probe.py n810:/tmp/ ; ssh n810 python2.5 /tmp/touch_probe.py
scp probes/touch_probe.py n810:/tmp/ ; ssh n810 python2.5 /tmp/touch_probe.py hold
scp probes/sysfs_probe.py n810:/tmp/ ; ssh n810 python2.5 /tmp/sysfs_probe.py
scp probes/mic_probe.py n810:/tmp/ ; ssh n810 python2.5 /tmp/mic_probe.py ; scp n810:/tmp/mic.wav probes/mic-sample.wav
```

Each script prints timed prompts (`>>>`). The terminal shows them about 1–2 s late over SSH, so allow for that. Recordings (`*.wav`) are git-ignored.

## Open

- Lock switch and headphone jack: retest with longer prompts.
- Pressure direction (does lower mean firmer?): test with deliberate soft vs hard presses.
- Mic gain: `dsppcmsrc` has a mixer interface that may allow raising it.
- Readings in a noisy room and at the demo venue (log levels from the creature itself).
- Not probed: webcam motion, Wi-Fi signal, GPS.
