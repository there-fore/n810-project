# Mic streaming probe for the N810 (Python 2.5), for Mote build step 4.
# Checks that the mic can stream into a running program (gst-launch's fdsink
# writing into a pipe, read by a thread; a named pipe with filesink delivered
# nothing), and that pygame can play a sound while the mic records. Prints a
# loudness bar every 100 ms and marks the chirps.
# Usage (as user): DISPLAY=:0 python2.5 mic_stream_probe.py
import os, sys, time, math, wave, array, threading, subprocess
import pygame

RATE, WIDTH = 8000, 2
SLICE = RATE * WIDTH / 10           # 100 ms
CHIRP = '/tmp/mote-chirp-probe.wav'
SECS = 6

def rms(chunk):
    s = array.array('h', chunk)
    return int((sum([v * v for v in s]) / float(len(s))) ** 0.5)

def make_chirp(path, rate=22050):
    # a short rising whistle, 0.15 s
    n = int(rate * 0.15)
    out = array.array('h')
    ph = 0.0
    for i in range(n):
        k = i / float(n)
        ph += 2 * math.pi * (1200 + 1400 * k) / rate
        env = min(1.0, i / 200.0) * (1 - k)
        out.append(int(12000 * env * math.sin(ph)))
    w = wave.open(path, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(out.tostring())
    w.close()

levels = []                          # (time since audio started, rms)
state = {'t_audio': None, 'err': None}

def reader():
    try:
        f = proc.stdout
        buf = ''
        while True:
            d = f.read(640)
            if not d:
                break
            if state['t_audio'] is None:
                state['t_audio'] = time.time()
            buf += d
            while len(buf) >= SLICE:
                levels.append((time.time() - state['t_audio'], rms(buf[:SLICE])))
                buf = buf[SLICE:]
    except Exception, e:
        state['err'] = repr(e)

make_chirp(CHIRP)
t0 = time.time()
# gst-launch prints status lines on stdout, so the audio goes out on fd 3
cmd = ('gst-launch-0.10 dsppcmsrc ! audio/x-raw-int,rate=%d,channels=1 ! '
       'fdsink fd=3 3>&1 >/dev/null 2>&1' % RATE)
proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
th = threading.Thread(target=reader)
th.setDaemon(True)
th.start()

pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()
try:
    pygame.mixer.init(22050, -16, 1, 512)
    print 'mixer:', pygame.mixer.get_init()
    chirp = pygame.mixer.Sound(CHIRP)
except Exception, e:
    print 'mixer failed:', e
    chirp = None

while state['t_audio'] is None and time.time() - t0 < 5:
    time.sleep(0.02)
if state['t_audio'] is None:
    print 'no audio after 5 s', state['err'] or ''
    os.system('killall gst-launch-0.10 2>/dev/null')
    sys.exit(1)
print 'mic streaming after %.2f s' % ((state['t_audio'] or time.time()) - t0)
sys.stdout.flush()

plays = []
end = time.time() + SECS
for at in (2.5, 4.0):
    while time.time() - state['t_audio'] < at:
        time.sleep(0.01)
    if chirp:
        chirp.play()
        plays.append(time.time() - state['t_audio'])
        print 'chirp at %.2f s' % plays[-1]
        sys.stdout.flush()
while time.time() < end:
    time.sleep(0.05)

os.system('kill %d 2>/dev/null; killall gst-launch-0.10 2>/dev/null' % proc.pid)
time.sleep(0.3)
cpu = os.times()
if state['err']:
    print 'reader error:', state['err']
peak = max([l for t, l in levels[2:]] or [1]) or 1
for t, l in levels:
    mark = [p for p in plays if t - 0.1 < p <= t] and '  <- chirp' or ''
    print '%4.1fs %6d %s%s' % (t, l, '#' * min(50, l * 50 / peak), mark)
print '%d slices; python CPU %.2f s, gst CPU %.2f s over %.1f s' % (
    len(levels), cpu[0] + cpu[1], cpu[2] + cpu[3], time.time() - t0)
