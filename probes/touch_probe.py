# Touch probe for the N810 (Python 2.5, run as root).
# Reads raw events from the TSC2301 touchscreen, prints X/Y/pressure
# 4x a second, then reports sample rate, range, hold-still jitter, CPU.
# Usage: python2.5 touch_probe.py [hold] [/dev/input/event3]
#   hold = only the hold-still phase, after a 3 s get-ready countdown
import os, sys, struct, select, time

args = sys.argv[1:]
HOLD_ONLY = 'hold' in args
args = [a for a in args if a != 'hold']
DEV = args and args[0] or '/dev/input/event3'
FMT = 'llHHi'                      # struct input_event on 32-bit ARM
SIZE = struct.calcsize(FMT)        # 16 bytes
EV_SYN, EV_ABS = 0, 3
ABS_X, ABS_Y, ABS_PRESSURE = 0, 1, 24
PHASES = [('DRAG your finger around', 10.0), ('HOLD STILL, finger down', 8.0)]
if HOLD_ONLY:
    PHASES = PHASES[1:]
    for n in (3, 2, 1):
        print 'Press one spot firmly and keep still... %d' % n
        sys.stdout.flush()
        time.sleep(1)

fd = os.open(DEV, os.O_RDONLY)
cur = {ABS_X: None, ABS_Y: None, ABS_PRESSURE: None}
samples = {}                       # phase index -> list of (x, y, p)
buf = ''
t_cpu0 = os.times()
for i, (label, secs) in enumerate(PHASES):
    print '>>> %s (%d s)' % (label, secs)
    sys.stdout.flush()
    samples[i] = []
    end = time.time() + secs
    next_print = 0
    while time.time() < end:
        r, w, e = select.select([fd], [], [], 0.05)
        if r:
            buf += os.read(fd, SIZE * 64)
            while len(buf) >= SIZE:
                sec, usec, typ, code, val = struct.unpack(FMT, buf[:SIZE])
                buf = buf[SIZE:]
                if typ == EV_ABS and code in cur:
                    cur[code] = val
                elif typ == EV_SYN and cur[ABS_X] is not None:
                    samples[i].append((cur[ABS_X], cur[ABS_Y], cur[ABS_PRESSURE]))
        now = time.time()
        if now >= next_print:
            next_print = now + 0.25
            print '  x=%s y=%s p=%s  (%d samples)' % (
                cur[ABS_X], cur[ABS_Y], cur[ABS_PRESSURE], len(samples[i]))
            sys.stdout.flush()
t_cpu1 = os.times()
os.close(fd)

def stats(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return 'none'
    mean = float(sum(vals)) / len(vals)
    sd = (sum([(v - mean) ** 2 for v in vals]) / len(vals)) ** 0.5
    return 'min %d max %d range %d sd %.1f' % (min(vals), max(vals),
                                              max(vals) - min(vals), sd)

print '=== SUMMARY'
for i, (label, secs) in enumerate(PHASES):
    s = samples[i]
    strokes, down = 0, False       # a stroke = run of samples with p > 0
    for x, y, p in s:
        if p and not down:
            strokes += 1
        down = bool(p)
    print '%s: %d samples, %.0f per second, %d strokes' % (
        label.split(',')[0], len(s), len(s) / secs, strokes)
    for name, k in (('x', 0), ('y', 1), ('p', 2)):
        print '  %s: %s' % (name, stats([t[k] for t in s]))
total = sum([PHASES[i][1] for i in range(len(PHASES))])
cpu = (t_cpu1[0] - t_cpu0[0]) + (t_cpu1[1] - t_cpu0[1])
print 'CPU: %.2f s over %.0f s wall (%.1f%%)' % (cpu, total, 100 * cpu / total)
