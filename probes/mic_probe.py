# Mic probe for the N810 (Python 2.5).
# Records from the DSP mic (8 kHz mono 16-bit, the only format dsppcmsrc
# offers) with gst-launch in the background, prints QUIET / CLAP / SPEAK
# prompts once audio is flowing, saves a WAV, prints a loudness bar every
# 100 ms and the level of each phase, plus startup time and CPU cost.
# Usage: python2.5 mic_probe.py
import os, sys, time, wave, array, subprocess

def rms(chunk):
    # Maemo's Python has no audioop, so do it by hand
    s = array.array('h', chunk)
    return int((sum([v * v for v in s]) / float(len(s))) ** 0.5)

RATE, WIDTH = 8000, 2
BLOCK = 640                         # the DSP sends 640-byte (40 ms) buffers
RAW, WAV = '/tmp/mic.raw', '/tmp/mic.wav'
PHASES = [('QUIET, make no sound', 3), ('CLAP twice, close to the N810', 3),
          ('SPEAK a sentence', 4)]
SECS = sum([s for l, s in PHASES]) + 1          # 1 s spare at the end
SKIP = 2                            # ignore first 200 ms (DSP switch-on click)

if os.path.exists(RAW):
    os.remove(RAW)
# gst-launch 0.10.13 has no -q, so silence its status lines instead
cmd = ('gst-launch-0.10 dsppcmsrc num-buffers=%d ! '
       'audio/x-raw-int,rate=%d,channels=1 ! filesink location=%s >/dev/null 2>&1'
       % (SECS * RATE * WIDTH / BLOCK, RATE, RAW))
print 'Starting the mic, wait for the first prompt...'
sys.stdout.flush()
t0 = time.time()
cpu0 = os.times()
proc = subprocess.Popen(cmd, shell=True)
while not (os.path.exists(RAW) and os.path.getsize(RAW) > 0):
    time.sleep(0.02)
t_audio = time.time()
marks = []                          # (audio time, label) where each phase starts
for label, secs in PHASES:
    marks.append((time.time() - t_audio, label))
    print '>>> %s (%d s)' % (label, secs)
    sys.stdout.flush()
    time.sleep(secs)
print '>>> done, stop'
sys.stdout.flush()
rc = proc.wait()
cpu1 = os.times()
wall = time.time() - t0
data = open(RAW, 'rb').read()
audio_secs = len(data) / float(RATE * WIDTH)
print 'gst-launch exit %d, %.2f s of audio, mic took %.2f s to start' % (
    rc, audio_secs, t_audio - t0)

w = wave.open(WAV, 'wb')
w.setnchannels(1)
w.setsampwidth(WIDTH)
w.setframerate(RATE)
w.writeframes(data)
w.close()

chunk = RATE * WIDTH / 10           # 100 ms
levels = []
for i in range(0, len(data) - chunk + 1, chunk):
    levels.append(rms(data[i:i + chunk]))
peak = max(levels[SKIP:] or [1]) or 1
starts = dict([(int(round(t * 10)), l) for t, l in marks])
for n, lv in enumerate(levels):
    if n in starts:
        print '---- %s' % starts[n].split(',')[0]
    print '%4.1fs %6d %s' % (n / 10.0, lv, '#' * min(50, lv * 50 / peak))

print '=== SUMMARY (first %d ms skipped)' % (SKIP * 100)
bounds = [int(round(t * 10)) for t, l in marks] + [len(levels)]
for i, (t, label) in enumerate(marks):
    seg = levels[max(SKIP, bounds[i]):bounds[i + 1]]
    if seg:
        mid = sorted(seg)[len(seg) / 2]
        print '  %-6s typical %4d  max %4d' % (label.split()[0], mid, max(seg))
top = sorted([(lv, n / 10.0) for n, lv in enumerate(levels) if n >= SKIP])[-5:]
print 'loudest moments: %s' % ', '.join(['%.1fs=%d' % (t, lv) for lv, t in reversed(top)])
# os.times children fields (2, 3) hold gst-launch's CPU
cpu = (cpu1[2] - cpu0[2]) + (cpu1[3] - cpu0[3])
print 'gst-launch CPU: %.2f s over %.1f s (%.1f%%)' % (cpu, wall, 100 * cpu / wall)
print 'WAV saved: %s' % WAV
