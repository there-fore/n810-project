# Light sensor + switch probe for the N810 (Python 2.5).
# Polls the TSL2563 lux/adc files and the gpio-switch states 10x a second,
# prints a line only when something changes, walks through timed prompts,
# then reports lux range, how often lux really updates, and CPU cost.
# Usage: python2.5 sysfs_probe.py
import os, sys, time

LIGHT = '/sys/devices/platform/i2c_omap.2/i2c-0/0-0029/'
SW = '/sys/devices/platform/gpio-switch/'
FILES = [('lux', LIGHT + 'lux'), ('adc', LIGHT + 'adc'),
         ('slide', SW + 'slide/state'), ('lock', SW + 'kb_lock/state'),
         ('phones', SW + 'headphone/state')]
PROMPTS = [('Leave everything alone (baseline)', 5),
           ('COVER the light sensor with your hand (try the top edge near the webcam)', 8),
           ('UNCOVER it', 5),
           ('SLIDE the keyboard OUT', 5),
           ('SLIDE the keyboard back IN', 5),
           ('FLICK the lock switch on the side, then back', 6),
           ('Optional: plug headphones in and out', 6)]
PERIOD = 0.1

def read(path):
    # sysfs values are regenerated on each read from offset 0
    f = open(path)
    try:
        return f.read().strip()
    finally:
        f.close()

t0 = time.time()
cpu0 = os.times()
last = dict([(k, read(p)) for k, p in FILES])
print '%6.1fs start  %s' % (0, '  '.join(['%s=%s' % (k, last[k]) for k, p in FILES]))
lux_seen = {}                      # prompt label -> list of lux values
lux_changes = []                   # times lux value changed
reads = 0
for label, secs in PROMPTS:
    print '>>> %s (%d s)' % (label, secs)
    sys.stdout.flush()
    lux_seen[label] = []
    end = time.time() + secs
    while time.time() < end:
        now = time.time() - t0
        for k, p in FILES:
            v = read(p)
            reads += 1
            if k == 'lux':
                lux_seen[label].append(int(v))
            if v != last[k]:
                print '%6.1fs %-6s %s -> %s' % (now, k, last[k], v)
                sys.stdout.flush()
                if k == 'lux':
                    lux_changes.append(now)
                last[k] = v
        time.sleep(PERIOD)
cpu1 = os.times()
wall = time.time() - t0

print '=== SUMMARY'
for label, secs in PROMPTS:
    v = lux_seen[label]
    print '  lux %4d..%-5d %s' % (min(v), max(v), label.split('(')[0].strip())
if len(lux_changes) > 1:
    gaps = [b - a for a, b in zip(lux_changes, lux_changes[1:])]
    print 'lux changed %d times; shortest gap %.2f s' % (len(lux_changes), min(gaps))
cpu = (cpu1[0] - cpu0[0]) + (cpu1[1] - cpu0[1])
print 'reads: %d (%.0f/s)  CPU: %.2f s over %.0f s (%.1f%%)' % (
    reads, reads / wall, cpu, wall, 100 * cpu / wall)
