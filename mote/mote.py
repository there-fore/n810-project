# Mote, the October creature demo (Python 2.5 + pygame 1.7.1 on the N810).
# Build steps 1-5: a blob that breathes and blinks, sleeps when the light
# sensor is covered, feels touch (poke, pet, hold) with trust and moods,
# peeks into the outside room when the keyboard (the door) slides out,
# hears claps (startles and hides), chirps, and says short lines that its
# mind on onode writes (mote-mind) at the boundaries between moments.
# Thresholds are from CREATURE.md ("Affordance -> behaviour").
# Usage (on the N810, as user):  DISPLAY=:0 python2.5 mote.py [test|touch|door|clap|mind|...] [raw] [nomind] [secs]
#   test  = timed COVER / UNCOVER prompts, then a summary of reaction times
#   touch = timed POKE / PET / HOLD prompts, then a summary of what Mote felt
#   annoy = timed prompts to poke Mote fast, twice (checks the annoyed look)
#   hold  = timed prompts to hold Mote, then pet and hold (checks the held look)
#   door  = timed prompts to slide the keyboard out and in, then a summary
#   clap  = timed prompts to clap, talk, hold and sleep, then a summary
#   hide  = timed prompts to clap, then hold Mote while it hides (twice)
#   show  = Mote is startled on cue 3 times (no clapping), to watch the look
#   mind  = the demo script with the mind: wake, pet, clap, door, goodnight
#   nomind = don't connect to the mind (fallback lines only)
#   raw   = log every touch event pygame delivers
#   secs  = quit after this many seconds (default: run until the top-right
#           corner is tapped, or Esc / q is pressed)
import os, sys, time, math, random, array, wave, signal, threading, subprocess
import pygame
from pygame.locals import *

LUX_PATH = '/sys/devices/platform/i2c_omap.2/i2c-0/0-0029/lux'
LUX_EVERY = 1 / 3.0        # poll light 3 times a second
DARK = 2                   # lux at or below this always counts as covered
BRIGHT = 5                 # lux at or above this can count as uncovered
# Covered and uncovered follow the room: a hand over the sensor in a bright
# room still lets ~7 lux through (108 lux room, 2026-10-28).
ROOM_WINDOW = 10.0         # s: the room's level = brightest uncovered reading this recent
DARK_SHARE = 0.15          # covered = at or below this share of the room's level
BRIGHT_SHARE = 0.3         # uncovered = at or above this share of it
SLEEP_AFTER = 2.0          # covered this long (after drowsy) -> asleep
WAKE_ANIM = 1.0            # eyes take this long to open; dark again -> asleep

SLIDE_PATH = '/sys/devices/platform/gpio-switch/slide/state'
SLIDE_EVERY = 0.1          # poll the keyboard slide 10 times a second
LIGHT_IGNORE = 1.5         # s: ignore light after the keyboard moves (it tilts the device)
OUTSIDE_BRIGHT = 30        # settled lux at or above this -> "saw outside (bright)"
DOOR_TRUST = 2             # seeing outside is what Mote wants most
DOOR_WIPE = 0.6            # s: the door slides open / shut on screen
PEEK_TIME = 3.0            # s: Mote looks around the outside room
MEMORIES = 8               # remember the last this many events

# The mic: gst-launch streams 8 kHz mono 16-bit audio out of fdsink (a named
# pipe with filesink delivered nothing) to a thread that measures each slice.
MIC_CMD = ('exec gst-launch-0.10 dsppcmsrc ! audio/x-raw-int,rate=8000,channels=1 ! '
           'fdsink fd=3 3>&1 >/dev/null 2>&1')   # gst prints status on stdout
MIC_BLOCK = 640            # bytes per DSP buffer (40 ms)
MIC_SLICE = 1600           # bytes per loudness slice (100 ms)
MIC_SKIP = 1               # slices to skip at switch-on (a click)
BASE_WINDOW = 5.0          # s: baseline = median of the quiet slices this recent...
BASE_MIN = 2               # ...once there are at least this many
QUIET_TIMES = 4            # a slice below this x baseline is quiet
CLAP_TIMES = 20            # clap: one slice above this x baseline...
CLAP_FLOOR = 600           # ...and above this (claps measured 946-1350)...
CLAP_FALL = 5              # ...back below this x baseline, or below...
CLAP_DROP = 8              # ...the peak / this (a clap rings on in a big room:
                           # 1428 -> 369 -> 140 -> 68 at school, baseline 8)...
CLAP_SLICES = 3            # ...within this many slices (300 ms); else just loud
CLAP_TRUST = -2
HIDE_TIME = 3.0            # s: hides after a clap
HIDE_FOND = 1.5            # s: a fond Mote recovers faster
PEEK_OUT = 1.0             # s: peeks out after hiding
STIR_TIME = 1.0            # s: a clap while asleep makes it stir
SNAP_UNDO = 0.8            # s: a "clap" this soon before the keyboard moves was its snap
SNAP_MUTE = 0.5            # s: ignore the mic this long after the keyboard moves

SOUND_RATE = 22050
CHIRP_MUTE = 0.3           # s: ignore the mic this long after a chirp ends
                           # (the speaker's echo arrives 0.2-0.3 s after it starts)
# chirps: (seconds, start Hz, end Hz, volume, wobble Hz); 0 Hz = a gap
CHIRPS = {
    'wake': [(0.18, 900, 1600, 0.6, 0)],
    'eep':  [(0.08, 1900, 2500, 0.7, 0)],
    'grr':  [(0.3, 220, 180, 0.7, 30)],
    'purr': [(0.35, 420, 480, 0.6, 22)],
    'yelp': [(0.2, 2600, 900, 0.8, 0)],
    'peek': [(0.07, 1300, 1500, 0.5, 0), (0.06, 0, 0, 0, 0), (0.08, 1500, 1900, 0.5, 0)],
    'wow':  [(0.3, 700, 1900, 0.6, 0)],
    'say':  [(0.06, 1000, 1300, 0.5, 0), (0.04, 0, 0, 0, 0), (0.08, 1300, 1100, 0.5, 0)],
}

# The mind: one open `ssh onode2 mote-mind` (Gemma E2B on onode writes the lines)
MIND_CMD = ['ssh', '-o', 'BatchMode=yes', '-o', 'ServerAliveInterval=15', 'onode2', 'mote-mind']
MIND_WAIT = 4.0            # s: no line by then -> the fallback line
MIND_GAP = 8.0             # s: unprompted lines at least this far apart
MIND_RETRY = 15.0          # s: reconnect this long after the connection drops
MIND_STALE = 8.0           # s: a wish not sent by then is out of date
AWAKE_FOR_GOODNIGHT = 20.0 # s awake before covering -> goodnight line
SAY_TIME = 4.0             # s a line stays up...
SAY_PER_CHAR = 0.1         # ...plus this per character
SAY_WIDTH = 460            # px: lines wrap at this width
# fallback lines, so the whole script works without onode
FALLBACK = {
    'wake': "Oh! The dark is gone.",
    'mood-curious': "You're not so scary.",
    'mood-fond': "I like you. Stay close.",
    'mood-timid': "I'll be small for a bit.",
    'peekout': "Is the loud thing gone?",
    'door-bright': "So much bright out there!",
    'door-dim': "It's dim out there.",
    'goodnight': "Goodnight. You stayed with me.",
}
BUBBLE = (246, 244, 234)
BUBBLE_EDGE = (120, 110, 100)
BUBBLE_TEXT = (40, 30, 30)

POKE_TIME = 0.6            # down and up within this, and still -> poke (taps: 0.05-0.55 s)
STILL = 20                 # px: moved less than this from where it went down
                           # (taps drift 8-9 px, fast ones up to 18)
PET_MOVE = 25              # px: moved this far within PET_QUICK -> pet
PET_QUICK = 0.6            # s (swipes cover 80-200 px in well under this)
PET_FAR = 60               # px: moved this far at any time -> pet
HOLD_TIME = 1.0            # pressed this long without becoming a pet -> hold
                           # (a pressing finger can slowly drift ~30 px)
DROPOUT = 0.1              # s: lifted and back down this fast, nearby, during a
                           # pet or hold, is one touch (light presses drop out)
MARGIN = 40                # px added around Mote's body for touches (aim is off by up to ~30 px)
PET_PX = 300               # px stroked per +1 trust, added up over short swipes
PET_MAX = 3                # most trust one petting session can give
PET_GAP = 2.0              # no petting this long -> the session is over
POKES_ANNOY = 3            # this many pokes...
POKES_WITHIN = 5.0         # ...within this many seconds -> annoyed, trust -1

TRUST_START = 3
MOODS = ((3, 'timid'), (6, 'curious'), (10, 'fond'))     # (highest trust, mood)
MOOD_SCALE = {'timid': 0.85, 'curious': 1.0, 'fond': 1.1}

W, H = 800, 480
FPS_AWAKE = 20
FPS_ASLEEP = 10
QUIT_BOX = Rect(W - 80, 0, 80, 80)
PROMPT_AREA = Rect(0, 0, W, 60)
DEBUG_AREA = Rect(0, H - 40, W - 90, 40)

BG_AWAKE = (40, 52, 78)
BG_ASLEEP = (14, 16, 30)
BODY = (250, 226, 160)
BODY_DARK = (205, 180, 120)
EYE = (40, 30, 30)
CHEEK = (245, 170, 150)
BLUSH = (250, 120, 120)
ANGRY = (245, 175, 140)
TEXT = (230, 230, 240)
DIM_TEXT = (150, 160, 190)

T0 = time.time()
EVENTS = []                # (time, name) for the test summaries
MIC = None                 # the Mic, once started
MIND = None                # the Mind, once started
SOUNDS = {}                # chirp name -> (pygame Sound, seconds)
SAY_FONT = None

def now():
    return time.time() - T0

def log(msg):
    print '%6.1f  %s' % (now(), msg)
    sys.stdout.flush()

def note(name):
    EVENTS.append((now(), name))

def read_file(path):
    try:
        f = open(path)
        try:
            return f.read().strip()
        finally:
            f.close()
    except IOError:
        return None

def read_lux():
    try:
        return int(float(read_file(LUX_PATH)))
    except (TypeError, ValueError):
        return None

def read_slide():
    # 'open' or 'closed' (None if unreadable)
    s = read_file(SLIDE_PATH)
    if s in ('open', 'closed'):
        return s
    return None

def mix(a, b, k):
    return tuple([int(a[i] + (b[i] - a[i]) * k) for i in range(3)])

def draw_heart(screen, x, y, s, color):
    # two bumps and a point; (x, y) is between the bumps, s is half the width
    pygame.draw.circle(screen, color, (x - s / 2, y), s / 2 + 1)
    pygame.draw.circle(screen, color, (x + s / 2, y), s / 2 + 1)
    pygame.draw.polygon(screen, color, [(x - s, y + 1), (x + s, y + 1), (x, y + s * 13 / 10)])

ROOM_LEVELS = 4            # the outside room, drawn at 4 darknesses (awake .. asleep)
WALL = (104, 88, 84)
FLOOR = (92, 66, 48)
FLOOR_LINE = (74, 52, 38)
SKIRTING = (70, 56, 52)
RUG = (124, 82, 92)
FRAME = (210, 196, 172)
SKY = (150, 200, 236)
NIGHT_SKY = (24, 30, 64)
SUN = (252, 228, 130)
MOON = (230, 230, 200)
CLOUD = (240, 244, 250)
LEAF = (90, 150, 90)
POT = (180, 100, 70)
LAMP = (240, 210, 150)
POLE = (60, 50, 50)

def draw_room(surf, dark):
    # the outside room as Mote sees it: wall, floor, window, picture, plant,
    # lamp. dark = 0 (awake) .. 1 (asleep) dims it toward the sleep colour.
    def c(col):
        return mix(col, BG_ASLEEP, dark * 0.85)
    surf.fill(c(WALL))
    pygame.draw.rect(surf, c(FLOOR), Rect(0, 360, W, H - 360))
    for x in range(-40, W + 120, 130):                   # floorboards
        pygame.draw.line(surf, c(FLOOR_LINE), (x, 363), (x - 60, H), 2)
    pygame.draw.line(surf, c(SKIRTING), (0, 360), (W, 360), 6)
    pygame.draw.ellipse(surf, c(RUG), Rect(W / 2 - 220, 380, 440, 70))
    # window with sun and a cloud, or the moon once it is dark
    win = Rect(80, 90, 210, 170)
    pygame.draw.rect(surf, c(FRAME), win.inflate(16, 16))
    pygame.draw.rect(surf, mix(SKY, NIGHT_SKY, dark), win)
    if dark < 0.5:
        pygame.draw.circle(surf, c(SUN), (win.right - 50, win.top + 45), 24)
        for dx, dy, r in ((50, 100, 18), (72, 92, 22), (96, 102, 16)):
            pygame.draw.circle(surf, c(CLOUD), (win.left + dx, win.top + dy), r)
    else:
        pygame.draw.circle(surf, c(MOON), (win.right - 50, win.top + 45), 18)
    pygame.draw.line(surf, c(FRAME), (win.centerx, win.top), (win.centerx, win.bottom), 6)
    pygame.draw.line(surf, c(FRAME), (win.left, win.centery), (win.right, win.centery), 6)
    pygame.draw.rect(surf, c(FRAME), Rect(win.left - 16, win.bottom + 8, win.width + 32, 10))
    # a picture of a mountain
    pic = Rect(370, 110, 100, 76)
    pygame.draw.rect(surf, c(FRAME), pic.inflate(12, 12))
    pygame.draw.rect(surf, c(SKY), pic)
    pygame.draw.polygon(surf, c(LEAF), [(pic.left, pic.bottom), (pic.left + 40, pic.top + 20),
                                        (pic.left + 70, pic.bottom - 20), (pic.right, pic.bottom)])
    # plant in a pot, left
    pygame.draw.polygon(surf, c(POT), [(110, 300), (190, 300), (178, 360), (122, 360)])
    for dx, dy, w, h in ((-40, -60, 40, 70), (0, -90, 34, 90), (30, -55, 40, 62)):
        pygame.draw.ellipse(surf, c(LEAF), Rect(150 + dx - w / 2, 300 + dy, w, h))
    # floor lamp, right
    pygame.draw.line(surf, c(POLE), (660, 180), (660, 352), 5)
    pygame.draw.ellipse(surf, c(POLE), Rect(630, 346, 60, 14))
    pygame.draw.polygon(surf, c(LAMP), [(620, 182), (700, 182), (680, 128), (640, 128)])

def dist(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


class Touch:
    # Turns pygame mouse events into poke / pet / hold. A still finger sends
    # no events, so hold comes from tick(). Each method returns a list of
    # (name, pos): down, move, pet, hold, poke, up.
    def __init__(self):
        self.g = None          # the touch in progress
        self.up_at = None      # (time, pos) of a lift that may be a dropout
        self.downs = self.dropouts = 0
        self.stroked = 0.0     # px petted since take_stroked() last ran

    def down(self, t, pos, on_mote):
        self.downs += 1
        # join a dropout only during a pet or hold: fast pokes also lift and
        # come back down within 0.1 s, and must stay separate
        if self.up_at and t - self.up_at[0] < DROPOUT \
                and self.g['kind'] in ('pet', 'hold') \
                and dist(pos, self.up_at[1]) < 40:
            self.up_at = None
            self.dropouts += 1
            return self.move(t, pos)
        out = self.finish()
        if on_mote:
            self.g = {'t': t, 'at': pos, 'pos': pos, 'far': 0,
                      'kind': None, 'moved_t': t}
            out.append(('down', pos))
        return out

    def move(self, t, pos):
        g = self.g
        if not g or self.up_at:
            return []
        step = dist(pos, g['pos'])
        if step >= 3:                      # jitter is about 2 px
            g['moved_t'] = t
            if g['kind'] == 'pet':
                self.stroked += step
        g['pos'] = pos
        g['far'] = max(g['far'], dist(pos, g['at']))
        out = [('move', pos)]
        quick = t - g['t'] < PET_QUICK and g['far'] >= PET_MOVE
        if g['kind'] != 'pet' and (quick or g['far'] >= PET_FAR):
            g['kind'] = 'pet'
            self.stroked += g['far']       # quick swipes are only a few jumps
            out.append(('pet', pos))
        return out

    def up(self, t, pos):
        if self.g:
            self.up_at = (t, pos)
        return []

    def finish(self):
        # the finger really lifted: report a poke if it was one, then the lift
        g, out = self.g, []
        if g:
            secs = (self.up_at or (now(), 0))[0] - g['t']
            log('lift after %.2f s, moved %d px, %s' % (secs, g['far'],
                g['kind'] or 'tap'))
            if g['kind'] is None and secs < POKE_TIME and g['far'] < STILL:
                out.append(('poke', g['at']))
            out.append(('up', g['pos']))
        self.g = self.up_at = None
        return out

    def tick(self, t):
        if self.up_at and t - self.up_at[0] >= DROPOUT:
            return self.finish()
        g = self.g
        if g and not self.up_at and (
                (g['kind'] is None and t - g['t'] >= HOLD_TIME) or
                (g['kind'] == 'pet' and t - g['moved_t'] >= HOLD_TIME)):
            # pressed a while, or petted and then rested: a hold. Distances
            # restart here, so it takes PET_FAR of rubbing to pet again.
            g['kind'] = 'hold'
            g['at'], g['far'] = g['pos'], 0
            return [('hold', g['pos'])]
        return []

    def take_stroked(self):
        px, self.stroked = self.stroked, 0.0
        return px


def rms(chunk):
    # loudness of a slice; Maemo's Python has no audioop, and every other
    # sample is plenty (the whole slice took a third of the processor)
    s = array.array('h', chunk).tolist()[::2]
    return int((sum([v * v for v in s]) / float(len(s))) ** 0.5)


class Mic:
    # reads the mic in a thread; take() turns the slices into 'clap' / 'loud'
    def __init__(self, verbose):
        self.verbose = verbose     # log every slice that isn't quiet
        self.proc = None
        self.lock = threading.Lock()
        self.slices = []           # (arrival time, level) not yet handled
        self.count = 0
        self.mute_until = 0
        self.muted = 0             # slices ignored after a chirp
        self.quiet = []            # (time, level) of recent quiet slices
        self.spike = None          # level of a possible clap
        self.spike_base = 0
        self.after = 0             # slices since the spike
        self.started = None

    def start(self):
        try:
            self.proc = subprocess.Popen(MIC_CMD, shell=True, stdout=subprocess.PIPE)
        except OSError, e:
            log('mic not started: %s' % e)
            return
        self.thread = threading.Thread(target=self.read)
        self.thread.setDaemon(True)
        self.thread.start()

    def read(self):
        buf = ''
        f = self.proc.stdout
        while True:
            d = f.read(MIC_BLOCK)
            if not d:
                break
            if self.started is None:
                self.started = now()
                log('mic streaming')
            buf += d
            while len(buf) >= MIC_SLICE:
                level = rms(buf[:MIC_SLICE])
                buf = buf[MIC_SLICE:]
                self.lock.acquire()
                try:
                    self.slices.append((now(), level))
                finally:
                    self.lock.release()
        log('mic stopped')

    def stop(self):
        if self.proc:
            try:
                os.kill(self.proc.pid, signal.SIGTERM)
            except OSError:
                pass
            self.proc = None
            self.thread.join(1.0)  # let it finish before Python shuts down

    def baseline(self):
        if len(self.quiet) < BASE_MIN:
            return None
        s = sorted([l for _, l in self.quiet])
        return max(1, s[len(s) / 2])

    def take(self):
        # returns [(name, level, baseline)] for the slices that arrived
        self.lock.acquire()
        try:
            got, self.slices = self.slices, []
        finally:
            self.lock.release()
        heard = []
        for t, level in got:
            self.count += 1
            if self.count <= MIC_SKIP:
                continue
            if t < self.mute_until:
                self.muted += 1
                continue
            self.quiet = [(s, l) for s, l in self.quiet if t - s < BASE_WINDOW]
            base = self.baseline()
            if self.verbose and base and level >= QUIET_TIMES * base:
                log('mic %d (baseline %d)' % (level, base))
            if self.spike is not None:
                # a clap is one spike, gone again within 300 ms
                self.after += 1
                if level < max(CLAP_FALL * self.spike_base, self.spike / CLAP_DROP):
                    heard.append(('clap', self.spike, self.spike_base))
                    self.spike = None
                elif self.after >= CLAP_SLICES:
                    heard.append(('loud', self.spike, self.spike_base))
                    self.spike = None
                continue
            if base and level > CLAP_TIMES * base and level > CLAP_FLOOR:
                self.spike, self.spike_base, self.after = level, base, 0
                continue
            if base is None or level < QUIET_TIMES * base:
                self.quiet.append((t, level))
        return heard


def make_chirp(path, parts):
    # writes a short whistle: each part sweeps from one pitch to another
    out = array.array('h')
    ph = 0.0
    for secs, f0, f1, vol, wobble in parts:
        n = int(SOUND_RATE * secs)
        for i in range(n):
            k = i / float(n)
            if not f0:
                out.append(0)
                continue
            ph += 2 * math.pi * (f0 + (f1 - f0) * k) / SOUND_RATE
            amp = 14000 * vol * math.sin(math.pi * k)    # soft in, soft out
            if wobble:
                amp *= 0.6 + 0.4 * math.sin(2 * math.pi * wobble * i / SOUND_RATE)
            out.append(int(amp * math.sin(ph)))
    w = wave.open(path, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SOUND_RATE)
    w.writeframes(out.tostring())
    w.close()


def load_chirps():
    # made once and kept in /tmp (they take a few seconds to compute)
    if not pygame.mixer.get_init():
        log('no sound: the mixer did not start')
        return
    t = now()
    for name, parts in CHIRPS.items():
        path = '/tmp/mote-%s-1.wav' % name
        if not os.path.exists(path):
            make_chirp(path, parts)
        SOUNDS[name] = (pygame.mixer.Sound(path), sum([p[0] for p in parts]))
    log('chirps ready in %.1f s' % (now() - t))


def chirp(name):
    if name not in SOUNDS:
        return
    sound, secs = SOUNDS[name]
    sound.play()
    if MIC:
        MIC.mute_until = max(MIC.mute_until, now() + secs + CHIRP_MUTE)


class Mind:
    # one SSH connection to mote-mind, kept open; one request at a time.
    # Mote sets mote.wants; tick() sends it, and shows the line (or the
    # fallback after MIND_WAIT) in a speech bubble.
    def __init__(self, enabled):
        self.enabled = enabled
        self.proc = None
        self.ready = False
        self.lock = threading.Lock()
        self.replies = []          # (time, line) from mote-mind, not yet handled
        self.sent = []             # request numbers awaiting a reply, oldest first
        self.seq = 0
        self.asked = None          # (number, trigger, time) while thinking
        self.said = None           # (text, trigger, until) while a line shows
        self.last_said = -100.0
        self.last_try = -100.0
        self.connect_t = 0

    def connect(self):
        self.last_try = self.connect_t = now()
        self.sent = []
        try:
            self.proc = subprocess.Popen(MIND_CMD, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=open('/dev/null', 'w'))
        except OSError, e:
            log('mind not started: %s' % e)
            self.proc = None
            return
        th = threading.Thread(target=self.read, args=(self.proc,))
        th.setDaemon(True)
        th.start()
        self.write('trigger=hello')

    def read(self, proc):
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.rstrip('\n')
            if line == 'ready':
                self.ready = True
                log('mind ready (%.1f s to connect)' % (now() - self.connect_t))
                continue
            self.lock.acquire()
            try:
                self.replies.append((now(), line))
            finally:
                self.lock.release()
        if self.proc is proc:
            self.ready = False
            self.proc = None
            log('mind connection closed')

    def write(self, text):
        try:
            self.proc.stdin.write(text + '\n')
            self.proc.stdin.flush()
            return True
        except (IOError, OSError, AttributeError), e:
            log('mind: cannot send (%s)' % e)
            return False

    def stop(self):
        proc, self.proc = self.proc, None
        if proc:
            try:
                proc.stdin.close()
                os.kill(proc.pid, signal.SIGTERM)
            except (IOError, OSError):
                pass

    def status(self):
        if not self.enabled:
            return 'off'
        if self.asked:
            return 'thinking'
        return self.ready and 'ready' or 'connecting'

    def tick(self, mote):
        t = now()
        if self.enabled and self.proc is None and t - self.last_try >= MIND_RETRY:
            self.connect()
        self.lock.acquire()
        try:
            got, self.replies = self.replies, []
        finally:
            self.lock.release()
        for at, line in got:
            if not self.sent:
                continue
            n = self.sent.pop(0)
            if not self.asked or self.asked[0] != n:
                log('mind: late line dropped: %s' % line)
                continue
            n, trig, t0 = self.asked
            self.asked = None
            if line.startswith('line=') and line[5:].strip():
                text = line[5:].strip()
                if trig == 'goodnight' and 'night' not in text.lower():
                    text += ' Goodnight.'
                self.say(text, trig, 'mind %.1f s' % (at - t0))
            else:
                log('mind: %s' % line)
                self.say(FALLBACK[trig], trig, 'fallback, mind error')
        if self.asked and t - self.asked[2] >= MIND_WAIT:
            n, trig = self.asked[:2]
            self.asked = None
            if n is None:
                self.say(FALLBACK[trig], trig, 'fallback, no mind')
            else:
                self.say(FALLBACK[trig], trig, 'fallback, no line in %.0f s' % MIND_WAIT)
        if self.said and t >= self.said[2]:
            self.said = None
        trig = mote.wants
        if trig and not self.asked:
            if mote.state == 'asleep' and trig != 'goodnight':
                log('mind: %s dropped (asleep)' % trig)
                mote.wants = None
            elif t - mote.wants_t > MIND_STALE:
                log('mind: %s dropped (out of date)' % trig)
                mote.wants = None
            elif trig == 'goodnight' or t - self.last_said >= MIND_GAP:
                mote.wants = None
                self.ask(trig, mote)

    def ask(self, trig, mote):
        self.seq += 1
        note('ask ' + trig)
        req = 'trigger=%s\tmood=%s\ttrust=%d\tmemories=%s' % (
            trig, mote.mood(), mote.trust, mote.memory_text())
        if self.ready and self.write(req):
            self.sent.append(self.seq)
            self.asked = (self.seq, trig, now())
            log('mind: asked %s' % trig)
        else:
            # no mind: think for a second, then the fallback line
            self.asked = (None, trig, now() - MIND_WAIT + 1.0)
            log('mind: %s, not asked (%s)' % (trig, self.status()))

    def say(self, text, trig, source):
        t = now()
        self.said = (text, trig, t + SAY_TIME + SAY_PER_CHAR * len(text))
        self.last_said = t
        chirp('say')
        log('says (%s, %s): %s' % (trig, source, text))
        note('says %s (%s)' % (trig, source.split(',')[0]))


def wrap(text, font, width):
    lines, cur = [], ''
    for word in text.split():
        trial = cur and cur + ' ' + word or word
        if cur and font.size(trial)[0] > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


BUBBLE_KEY = (255, 0, 255)  # see-through colour of a bubble image

def bubble_key(mind):
    # what the bubble shows; it is only redrawn when this changes
    if mind.said:
        return ('say', mind.said[0])
    if mind.asked:
        return ('think', int(now() * 3) % 3)             # the dots take turns
    return None


def make_bubble(key, mote, where):
    # draws a bubble once into its own image: returns (rect on screen, image).
    # where = (x, top of Mote) when the bubble first appeared; it stays there.
    mx, top = where
    if key[0] == 'say':
        lines = [SAY_FONT.render(l, 1, BUBBLE_TEXT, BUBBLE)
                 for l in wrap(key[1], SAY_FONT, SAY_WIDTH)]
        lh = SAY_FONT.get_linesize()
        w = max([l.get_width() for l in lines]) + 36
        h = lh * len(lines) + 24
        tail = 30                                        # clear of Mote's head
        x = max(10, min(W - w - 10, mx - w / 2))
        y = max(66, top - 40 - tail - h)
        img = pygame.Surface((w, h + tail)).convert()
        img.fill(BUBBLE_KEY)
        tx = mx - x                                      # tail, pointing at Mote
        tx = max(20, min(w - 20, tx))
        pts = [(tx - 14, h - 2), (tx + 14, h - 2), (tx, h + tail - 1)]
        pygame.draw.polygon(img, BUBBLE, pts)
        pygame.draw.lines(img, BUBBLE_EDGE, 0, [pts[0], pts[2], pts[1]], 2)
        pygame.draw.rect(img, BUBBLE, Rect(0, 0, w, h))
        pygame.draw.rect(img, BUBBLE_EDGE, Rect(0, 0, w, h), 2)
        pygame.draw.line(img, BUBBLE, pts[0], pts[1], 2)
        for i, l in enumerate(lines):
            img.blit(l, (18, 12 + i * lh))
    else:
        img = pygame.Surface((120, 110)).convert()
        img.fill(BUBBLE_KEY)
        cloud = Rect(5, 5, 110, 60)
        for r, cx, cy in ((7, 15, 100), (11, 30, 82)):  # trail toward Mote
            pygame.draw.circle(img, BUBBLE, (cx, cy), r)
        pygame.draw.ellipse(img, BUBBLE, cloud)
        pygame.draw.ellipse(img, BUBBLE_EDGE, cloud, 2)
        for i in range(3):
            on = key[1] == i
            pygame.draw.circle(img, on and BUBBLE_TEXT or BUBBLE_EDGE,
                               (36 + 24 * i, 35), on and 7 or 5)
        x = min(W - 125, mx + 90)
        y = max(66, top - 120)
    img.set_colorkey(BUBBLE_KEY)
    return Rect((x, y), img.get_size()), img


class Mote:
    def __init__(self):
        self.state = 'awake'       # awake, drowsy, asleep, waking
        self.since = now()
        self.dark_since = None
        self.bright_since = None
        self.room = []             # (time, lux) of recent uncovered readings
        self.next_blink = now() + 2
        self.blink_until = 0
        self.trust = TRUST_START
        self.expr = None           # face: notice, flinch, happy, calm, annoyed
        self.expr_until = 0        # 0 = until something changes it
        self.expr_since = now()
        self.phase = 0.0           # breathing, kept smooth when its pace changes
        self.felt = '-'            # last thing felt, for the debug corner
        self.finger = None
        self.pet_px = 0.0          # px stroked in this petting session
        self.pet_gain = 0          # trust this session has given
        self.pet_last = 0
        self.pokes = []
        self.scale = MOOD_SCALE[self.mood()]
        self.x = float(W / 2)
        self.last_t = now()
        self.body = None
        self.color = BODY
        self.door = False          # keyboard out: the outside room shows
        self.door_t = -10.0        # when the keyboard last moved
        self.light_quiet_until = 0 # ignore light until then (the slide tilts it)
        self.ignored = []          # lux readings ignored since the slide moved
        self.outside_pending = False   # note what it saw once the light settles
        self.memories = []         # (time, text), the last MEMORIES events
        self.stir_since = -10.0    # a clap while asleep
        self.wants = None          # the newest thing Mote wants to say (a trigger)
        self.wants_t = 0.0         # when it wanted it
        self.startle = None        # (time, trust, memories) before the last fright
        self.awake_since = 0.0

    def mood(self):
        for top, name in MOODS:
            if self.trust <= top:
                return name

    def change_trust(self, d, why, say=True):
        # say=False when another line covers it (the peek-out, the door)
        old, old_mood = self.trust, self.mood()
        self.trust = max(0, min(10, self.trust + d))
        msg = 'trust %d -> %d (%s)' % (old, self.trust, why)
        if self.mood() != old_mood:
            msg += ', mood %s -> %s' % (old_mood, self.mood())
            if say:
                self.want('mood-' + self.mood())
        log(msg)
        note('trust %d' % self.trust)

    def want(self, trigger):
        # the mind sends only the newest, so this replaces any older wish
        if self.wants and self.wants != trigger:
            log('wants %s (replaces %s)' % (trigger, self.wants))
        self.wants = trigger
        self.wants_t = now()

    def memory_text(self):
        # "what,seconds ago|..." for mote-mind
        t = now()
        return '|'.join(['%s,%d' % (m, t - s) for s, m in self.memories])

    def set_expr(self, expr, secs=0):
        if expr != self.expr:
            self.expr_since = now()
        self.expr = expr
        self.expr_until = secs and now() + secs or 0

    def set_state(self, state, lux):
        log('lux=%-3s %s -> %s' % (lux, self.state, state))
        note(state)
        if state == 'drowsy' and self.state == 'awake' \
                and now() - self.awake_since >= AWAKE_FOR_GOODNIGHT:
            self.want('goodnight')
        elif state == 'awake' and self.wants == 'goodnight':
            self.wants = None                            # uncovered again in time
        self.state = state
        self.since = now()
        if state == 'awake':
            self.awake_since = self.since
        if state == 'waking':
            chirp('wake')
            self.remember('woke up')
            self.want('wake')
        if state != 'awake':
            self.finger = None
            self.set_expr(None)

    def hit(self, pos):
        return self.body is not None \
            and self.body.inflate(2 * MARGIN, 2 * MARGIN).collidepoint(pos)

    def remember(self, text):
        self.memories = (self.memories + [(now(), text)])[-MEMORIES:]
        log('memory: %s (%d kept)' % (text, len(self.memories)))

    def feel_slide(self, state, first=False):
        # state is 'open' or 'closed'; first = the reading at startup
        if state is None or (state == 'open') == self.door:
            return
        t = now()
        self.door = state == 'open'
        if first:
            self.door_t = t - DOOR_WIPE                  # no wipe, no trust
            log('keyboard already %s' % state)
            return
        self.door_t = t
        self.light_quiet_until = t + LIGHT_IGNORE
        if MIC:
            MIC.mute_until = max(MIC.mute_until, t + SNAP_MUTE)
        if self.startle and t - self.startle[0] < SNAP_UNDO and self.expr == 'hide':
            # the keyboard snaps as it slides, just before the switch: not a clap
            st, self.trust, self.memories = self.startle
            self.startle = None
            self.set_expr(None)
            log('the "clap" %.1f s ago was the keyboard: fright undone, trust %d' % (
                t - st, self.trust))
            note('fright undone (keyboard)')
        log('keyboard %s (light ignored for %.1f s)' % (state, LIGHT_IGNORE))
        note('door ' + state)
        if self.door and self.state == 'asleep':
            log('door opened while asleep: Mote does not see it')
        elif self.door:
            self.set_expr('peek', PEEK_TIME)
            chirp('wow')
            self.felt = 'saw outside'
            self.change_trust(DOOR_TRUST, 'door opened', False)
            self.outside_pending = True
        else:
            if self.outside_pending:
                log('door closed before the light settled: nothing remembered')
            self.outside_pending = False
            if self.expr == 'peek':
                self.set_expr(None)
            if self.state != 'asleep':
                self.felt = 'back inside'

    def door_k(self):
        # how far the door is open on screen: 0 = inside .. 1 = the outside room
        k = (now() - self.door_t) / DOOR_WIPE
        if self.door:
            return min(1.0, k)
        return max(0.0, 1.0 - k)

    def room_level(self):
        if not self.room:
            return 0
        return max([l for _, l in self.room])

    def light_limits(self):
        # (covered at or below, uncovered at or above), from the room's level
        room = self.room_level()
        return max(DARK, int(room * DARK_SHARE)), max(BRIGHT, int(room * BRIGHT_SHARE))

    def feel_light(self, lux):
        t = now()
        if lux is None:
            return
        if t < self.light_quiet_until:
            self.ignored.append(lux)
            return
        if self.ignored:
            msg = 'light ignored: %d readings, lux %d-%d' % (len(self.ignored),
                min(self.ignored), max(self.ignored))
            log(msg)
            note(msg)
            self.ignored = []
        if self.outside_pending:
            self.outside_pending = False
            kind = lux >= OUTSIDE_BRIGHT and 'bright' or 'dim'
            self.remember('saw outside (%s)' % kind)
            note('saw outside %s (lux %d)' % (kind, lux))
            self.want('door-' + kind)
        dark, bright = self.light_limits()
        if lux > dark:
            # the room's level; while covered, the last one is kept
            self.room = [(s, l) for s, l in self.room if t - s < ROOM_WINDOW] + [(t, lux)]
        if lux <= dark:
            if self.dark_since is None:
                log('covered: lux %d <= %d (room %d)' % (lux, dark, self.room_level()))
            self.bright_since = None
            if self.dark_since is None:
                self.dark_since = t
        elif lux >= bright:
            self.dark_since = None
            if self.bright_since is None:
                self.bright_since = t
        if self.state == 'awake' and self.dark_since is not None:
            self.set_state('drowsy', lux)
        elif self.state == 'drowsy':
            if self.bright_since is not None:
                self.set_state('awake', lux)
            elif t - self.dark_since >= SLEEP_AFTER:
                self.set_state('asleep', lux)
        elif self.state == 'asleep' and self.bright_since is not None:
            # first bright reading: eyes start opening at once (feels instant)
            self.set_state('waking', lux)
        elif self.state == 'waking' and self.dark_since is not None:
            # dark again before the eyes are fully open: back to sleep
            self.set_state('asleep', lux)

    def feel_sound(self, name, level, base):
        t = now()
        if name == 'loud':
            log('loud sound %d (baseline %d), not a clap' % (level, base))
            note('loud, not a clap')
            return
        log('clap %d (baseline %d)' % (level, base))
        if self.state not in ('awake', 'waking'):
            # asleep (or dozing off): it stirs and rolls over, stays asleep
            self.stir_since = t
            log('clap while %s: stirs' % self.state)
            note('stir (%s)' % self.state)
            return
        if self.state == 'waking':
            self.set_state('awake', '')
        secs = self.mood() == 'fond' and HIDE_FOND or HIDE_TIME
        self.finger = None
        if self.wants:
            log('fright: %s not said' % self.wants)
            self.wants = None
        self.startle = (t, self.trust, list(self.memories))
        self.set_expr('hide', secs)
        chirp('yelp')
        self.felt = 'startled'
        note('startle')
        self.change_trust(CLAP_TRUST, 'loud sound', False)
        self.remember('startled by a loud sound')

    def feel_touch(self, name, pos):
        if name in ('poke', 'pet', 'hold') and self.state != 'awake':
            log('touch %s ignored (%s)' % (name, self.state))
            note('touch %s (ignored, %s)' % (name, self.state))
        if self.state != 'awake':
            return
        if self.expr == 'hide':
            # hiding: only a still, comforting hold reaches it
            if name == 'hold':
                log('held while hiding: comes out early')
                note('hide ended by hold')
            else:
                if name in ('poke', 'pet'):
                    log('touch %s ignored (hiding)' % name)
                    note('touch %s (ignored, hiding)' % name)
                return
        t = now()
        if name in ('poke', 'pet', 'hold'):
            log('touch %s at %s' % (name, pos))
            note('touch ' + name)
            self.felt = name
        if name in ('down', 'move'):
            self.finger = pos
            if name == 'down' and self.expr not in ('flinch', 'annoyed'):
                self.set_expr('notice')
        elif name == 'poke':
            self.pokes = [p for p in self.pokes if t - p < POKES_WITHIN] + [t]
            if len(self.pokes) >= POKES_ANNOY:
                self.pokes = []
                self.set_expr('annoyed', 2.0)
                self.felt = 'poked a lot'
                note('touch annoyed')
                self.change_trust(-1, 'poked a lot')
                self.remember('poked a lot')
                chirp('grr')
            elif self.expr != 'annoyed':
                self.set_expr('flinch', 0.4)
                self.remember('poked')
                chirp('eep')
        elif name == 'pet':
            if self.expr != 'happy':
                chirp('purr')
            self.set_expr('happy')
        elif name == 'hold':
            self.set_expr('calm')
            chirp('purr')
            self.remember('held')
            self.change_trust(1, 'held')
        elif name == 'up':
            self.finger = None
            if self.expr == 'happy':
                self.set_expr('happy', 0.8)      # keeps smiling between swipes
            elif self.expr in ('notice', 'calm'):
                self.set_expr(None)

    def update(self, stroked):
        # stroked = px petted since the last frame
        t = now()
        dt = t - self.last_t
        self.last_t = t
        if self.state == 'waking' and t - self.since >= WAKE_ANIM:
            self.set_state('awake', '')
        if self.state == 'awake' and t >= self.next_blink:
            self.blink_until = t + 0.15
            self.next_blink = t + random.uniform(2.5, 6.0)
        if self.expr == 'hide' and t >= self.expr_until:
            self.set_expr('peekout', PEEK_OUT)           # the coast is clear?
            chirp('peek')
            log('peeks out')
            note('peek out')
            self.want('peekout')
        if self.expr_until and t >= self.expr_until:
            self.set_expr(None)
        period = 2.2                                     # s per breath
        if self.state == 'asleep':
            period = 4.0
        elif self.expr == 'calm':
            period = 3.6                                 # held: slower
        self.phase = (self.phase + dt * 2 * math.pi / period) % (2 * math.pi)
        if self.pet_px and t - self.pet_last > PET_GAP:
            self.pet_px, self.pet_gain = 0.0, 0          # petting session over
        if stroked and self.state == 'awake':
            self.pet_px += stroked
            self.pet_last = t
            if self.pet_px >= PET_PX and self.pet_gain < PET_MAX:
                self.pet_px -= PET_PX
                self.pet_gain += 1
                if self.pet_gain == 1:
                    self.remember('petted')      # once per petting session
                self.change_trust(1, 'petted')
        # size and place follow the mood; fond Mote follows your finger
        target = MOOD_SCALE[self.mood()]
        self.scale += (target - self.scale) * min(1.0, dt * 3)
        tx = W / 2
        if self.mood() == 'fond' and self.finger:
            tx = max(250, min(W - 250, self.finger[0]))
        step = 200 * dt
        self.x += max(-step, min(step, tx - self.x))

    def lid(self):
        # 0 = eyes fully open, 1 = fully closed
        t = now()
        if self.state == 'asleep':
            return 1.0
        if self.state == 'drowsy':
            return min(0.6, 0.3 + (t - self.since) * 0.3)
        if self.state == 'waking':
            k = (t - self.since) / WAKE_ANIM
            return 1.0 - k + 0.4 * math.sin(k * math.pi * 3) * (1 - k)
        if t < self.blink_until:
            return 1.0
        if self.expr == 'annoyed':
            return 0.45
        if self.expr == 'hide':
            return 1.0
        if self.expr in ('notice', 'peek', 'peekout'):
            return 0.0
        if self.mood() == 'timid':
            return 0.35
        return 0.0

    def darkness(self):
        # 0 = awake .. 1 = asleep, for the background
        t = now()
        if self.state == 'asleep':
            return min(1.0, (t - self.since) / 1.5)
        elif self.state == 'drowsy':
            return 0.4
        elif self.state == 'waking':
            return max(0.0, 1.0 - (t - self.since) / WAKE_ANIM)
        return 0.0

    def background(self):
        # the inside colour; in the outside room, roughly the wall's
        if self.door:
            return mix(WALL, BG_ASLEEP, self.darkness() * 0.85)
        return mix(BG_AWAKE, BG_ASLEEP, self.darkness())

    def draw(self, screen):
        # draws Mote (not the background); returns the area it covered
        t = now()
        asleep = self.state == 'asleep'
        calm = self.expr == 'calm'
        breath = math.sin(self.phase)
        depth = 0.03
        if asleep:
            bw, bh = 280, 150                            # curled up, flatter
        else:
            bw, bh = 240, 190
        if calm:                                         # held: settles, sinks
            k = min(1.0, (t - self.expr_since) / 0.6)
            bw, bh = int(bw * (1 + 0.08 * k)), int(bh * (1 - 0.12 * k))
            depth = 0.05                                 # deeper, slower breaths
        stretch = squash = hop = lean = 0
        if self.state == 'waking':
            stretch = math.sin((t - self.since) / WAKE_ANIM * math.pi) * 30
        if self.expr == 'flinch':
            squash = 25 * max(0.0, self.expr_until - t) / 0.4
        if self.expr == 'peek':                          # rises, tall and alert
            stretch = 18 * min(1.0, (t - self.expr_since) / 0.4)
        # hiding (after a clap): small, low, trembling; peeking out undoes it
        hide = 0.0
        if self.expr == 'hide':
            hide = min(1.0, (t - self.expr_since) / 0.15)
        elif self.expr == 'peekout':
            hide = max(0.0, 1.0 - (t - self.expr_since) / 0.6)
        scale = self.scale * (1 - 0.4 * hide)
        bw = int((bw * (1 + depth * breath) - stretch * 0.5 + squash) * scale)
        bh = int((bh * (1 - depth * breath) + stretch - squash) * scale)
        if self.mood() == 'fond' and self.state == 'awake' and not calm and not hide:
            hop = int(abs(math.sin(t * math.pi / 0.6)) * 10)
        if self.finger and self.expr == 'happy':
            lean = max(-15, min(15, (self.finger[0] - self.x) / 4))
        shake = 0
        self.color = BODY
        if self.expr == 'annoyed':                       # shakes, goes red
            shake = int(math.sin(t * 2 * math.pi * 8) * 5)
            self.color = ANGRY
        elif self.expr == 'hide':                        # trembles
            shake = int(math.sin(t * 2 * math.pi * 12) * 3)
        if asleep and t - self.stir_since < STIR_TIME:   # stirs: rolls a little
            k = (t - self.stir_since) / STIR_TIME
            shake = int(math.sin(k * math.pi * 2) * 14 * (1 - k))
            bh += int(math.sin(k * math.pi) * 12)
        cx = int(self.x + lean + shake)
        body = Rect(cx - bw / 2, 400 + int(50 * hide) - hop - bh, bw, bh)
        self.body = body
        pygame.draw.ellipse(screen, BODY_DARK, body.move(0, 6))
        pygame.draw.ellipse(screen, self.color, body)
        area = body.inflate(10, 20)

        ey = body.top + bh * 2 / 5
        cheek = CHEEK
        if self.expr in ('happy', 'calm'):
            cheek = BLUSH
        for ex in (cx - bw / 3, cx + bw / 3):
            pygame.draw.circle(screen, cheek, (ex, ey + 30), 10)
        self.draw_eyes(screen, cx, ey, bw)

        # floating z's while asleep
        if asleep and FONT:
            for i in range(3):
                k = ((t - self.since) / 3.0 + i / 3.0) % 1.0
                img = FONT.render('z', 1, mix(TEXT, BG_ASLEEP, k))
                pos = (int(cx + bw / 2 - 10 + k * 60), int(body.top - 20 - k * 120))
                screen.blit(img, pos)
                area = area.union(Rect(pos, img.get_size()))

        # a small heart floats up every 1.6 s while held
        if calm:
            k = ((t - self.expr_since) % 1.6) / 1.6
            s = 9
            hx = int(cx + bw / 4 + math.sin(k * math.pi * 2) * 6)
            hy = int(body.top - 6 - k * 70)
            draw_heart(screen, hx, hy, s, mix(BLUSH, self.background(), k))
            area = area.union(Rect(hx - s - 2, hy - s - 2, 2 * s + 4, 3 * s))
        return area

    def draw_eyes(self, screen, cx, ey, bw):
        lid = max(0.0, min(1.0, self.lid()))
        look = (0, 0)
        if self.finger and self.mood() != 'timid':
            dx, dy = self.finger[0] - cx, self.finger[1] - ey
            d = max(1.0, math.sqrt(dx * dx + dy * dy))
            look = (int(5 * dx / d), int(5 * dy / d))
        r = 15
        if self.expr == 'notice':
            r = 17                                       # eyes widen
        elif self.expr == 'peek':                        # wide, looking around
            r = 17
            k = now() - self.expr_since
            look = (int(7 * math.sin(k * 2 * math.pi / 1.5)), -3)
        elif self.expr == 'peekout':                     # wary: quick glances
            r = 17
            k = now() - self.expr_since
            look = (int(7 * math.sin(k * 2 * math.pi / 0.5)), -2)
        for side, ex in ((-1, cx - bw / 5), (1, cx + bw / 5)):
            if self.expr == 'happy':                     # ^ ^
                pygame.draw.lines(screen, EYE, 0,
                    [(ex - 12, ey + 4), (ex, ey - 6), (ex + 12, ey + 4)], 4)
            elif self.expr == 'calm':                    # closed, content: u u
                pygame.draw.lines(screen, EYE, 0, [(ex - 13, ey), (ex - 7, ey + 5),
                    (ex, ey + 7), (ex + 7, ey + 5), (ex + 13, ey)], 4)
            elif self.expr == 'flinch':                  # > <
                pygame.draw.lines(screen, EYE, 0, [(ex + 8 * side, ey - 8),
                    (ex - 8 * side, ey), (ex + 8 * side, ey + 8)], 4)
            elif lid >= 0.95:
                pygame.draw.line(screen, EYE, (ex - 14, ey + 4), (ex + 14, ey + 4), 4)
            else:
                px, py = ex + look[0], ey + look[1]
                pygame.draw.circle(screen, EYE, (px, py), r)
                pygame.draw.circle(screen, (255, 255, 255), (px + 5, py - 5), 4)
                if lid > 0:
                    size = 2 * r + 14
                    pygame.draw.rect(screen, self.color,
                        Rect(ex - r - 7, ey - r - 7, size, int(size * lid) + 1))
            if self.expr == 'annoyed':                   # frown: thick brows
                pygame.draw.line(screen, EYE, (ex + 22 * side, ey - 34),
                                 (ex - 16 * side, ey - 16), 7)


def light_schedule():
    # (start time, text on screen, event name for the summary)
    steps = [(0, 'Get ready: hold the N810 normally, cover nothing', None)]
    t = 6
    for i in range(1, 6):
        steps.append((t, 'Round %d of 5: COVER the light sensor in 3...' % i, None))
        steps.append((t + 3, 'COVER the light sensor now (keep it covered)', 'cover'))
        steps.append((t + 9, 'Get ready to UNCOVER in 3...', None))
        steps.append((t + 12, 'UNCOVER now', 'uncover'))
        t += 18
    steps.append((t, 'Done', 'done'))
    return steps


TOUCH_TRIES = [
    ('POKE the middle of Mote once: quick, firm tap', 4, 'poke 1 (expect: poke)'),
    ('POKE the middle of Mote once again', 4, 'poke 2 (expect: poke)'),
    ('PET Mote: stroke it side to side', 6, 'pet (expect: pet, trust +2 or +3)'),
    ('HOLD: press the middle of Mote, keep still', 4, 'hold (expect: hold, trust +1)'),
    ('POKE Mote 4 times, fast', 5, 'pokes (expect: pokes, annoyed, trust -1)'),
]
HOLD_TRIES = [
    ('HOLD: press the middle of Mote, keep still', 5, 'hold 1 (expect: hold)'),
    ('PET Mote a little, then HOLD it still', 7, 'pet then hold (expect: pet, hold)'),
]
ANNOY_TRIES = [
    ('POKE Mote 4 times, fast, then watch it', 5, 'pokes 1 (expect: annoyed)'),
    ('POKE Mote 4 times, fast, once more', 5, 'pokes 2 (expect: annoyed)'),
]

def touch_schedule(tries):
    steps = [(0, 'Get ready: hold the N810 screen up, light uncovered', None)]
    t = 5
    for text, secs, label in tries:
        steps.append((t, text + ' in 3...', None))
        steps.append((t + 3, text + ' NOW', 'try ' + label))
        steps.append((t + 3 + secs, 'Lift your finger and wait', None))
        t += 3 + secs + 3
    steps.append((t, 'Done', 'done'))
    return steps


def door_schedule():
    steps = [(0, 'Get ready: keyboard IN, light sensor uncovered', None)]
    t = 6
    for i in range(1, 4):
        steps.append((t, 'Round %d of 4: SLIDE the keyboard OUT in 3...' % i, None))
        steps.append((t + 3, 'SLIDE the keyboard OUT now, then watch Mote',
                      'try out %d (expect: door open, trust +2, saw outside)' % i))
        steps.append((t + 10, 'Get ready to slide it back IN in 3...', None))
        steps.append((t + 13, 'SLIDE the keyboard back IN now',
                      'try in %d (expect: door closed)' % i))
        t += 19
    # last round: fall asleep and wake up in the outside room
    steps.append((t, 'Round 4 of 4: SLIDE the keyboard OUT in 3...', None))
    steps.append((t + 3, 'SLIDE the keyboard OUT now', 'try out 4 (expect: door open)'))
    steps.append((t + 7, 'Keep it out. COVER the light sensor in 3...', None))
    steps.append((t + 10, 'COVER the light sensor now (keep it covered)',
                  'try cover (expect: drowsy, asleep, the room dims)'))
    steps.append((t + 15, 'Get ready to UNCOVER in 3...', None))
    steps.append((t + 18, 'UNCOVER now', 'try uncover (expect: waking, awake)'))
    steps.append((t + 22, 'Get ready to slide it back IN in 3...', None))
    steps.append((t + 25, 'SLIDE the keyboard back IN now', 'try in 4 (expect: door closed)'))
    steps.append((t + 31, 'Done', 'done'))
    return steps


def clap_schedule():
    steps = [(0, 'Get ready: stay quiet, light sensor uncovered', None)]
    t = 6
    for i in range(1, 4):
        steps.append((t, 'Round %d of 3: CLAP once, close to the N810, in 3...' % i, None))
        steps.append((t + 3, 'CLAP once now, then watch Mote',
                      'try clap %d (expect: startle, trust -2, peek out)' % i))
        t += 11
    steps.append((t, 'Next: TALK out loud for 3 s, in 3...', None))
    steps.append((t + 3, 'TALK out loud now (Mote should NOT startle)',
                  'try talk (expect: no startle)'))
    t += 10
    steps.append((t, 'Next: CLAP, then HOLD the middle of Mote still, in 3...', None))
    steps.append((t + 3, 'CLAP now, then HOLD Mote still right away',
                  'try clap and hold (expect: startle, hold ends the hide)'))
    t += 10
    steps.append((t, 'Lift your finger. Next: POKE Mote twice, slowly, in 3...', None))
    steps.append((t + 3, 'POKE Mote twice, slowly (it chirps, no startle)',
                  'try pokes (expect: 2 pokes, no startle)'))
    t += 10
    steps.append((t, 'Next: COVER the light sensor, in 3...', None))
    steps.append((t + 3, 'COVER the light sensor now (keep it covered)',
                  'try cover (expect: drowsy, asleep)'))
    steps.append((t + 9, 'Keep it covered and SLAP the table once with your other hand',
                  'try clap asleep (expect: stir, stays asleep)'))
    steps.append((t + 14, 'UNCOVER now', 'try uncover (expect: waking)'))
    steps.append((t + 19, 'Done', 'done'))
    return steps


def hide_schedule():
    # a clap, then a hold while Mote hides, twice
    steps = [(0, 'Get ready: stay quiet, light sensor uncovered', None)]
    t = 6
    for i in range(1, 3):
        steps.append((t, 'Round %d of 2: CLAP once, in 3...' % i, None))
        steps.append((t + 3, 'CLAP once now', 'try clap %d (expect: startle)' % i))
        steps.append((t + 4.5, 'Now HOLD the middle of Mote, keep still',
                      'try hold %d (expect: hold ends the hide, trust +1)' % i))
        steps.append((t + 9, 'Lift your finger and wait', None))
        t += 13
    steps.append((t, 'Done', 'done'))
    return steps


def show_schedule():
    # no clapping needed: Mote is startled on cue (event names start 'fake')
    steps = [(0, 'Watch Mote: it gets a fright in 3 s (no need to clap)', None)]
    t = 3
    for i, mood in ((1, 'timid'), (2, 'timid'), (3, 'fond')):
        steps.append((t, 'Startle %d of 3 (%s): hides for %s s, then peeks out' % (
            i, mood, mood == 'fond' and HIDE_FOND or HIDE_TIME), 'fake clap ' + mood))
        steps.append((t + 6, 'Next one in 2 s...', None))
        t += 8
    steps.append((t, 'Done', 'done'))
    return steps


def mind_schedule():
    # the demo script, minus voice
    steps = [(0, 'Get ready: first you will COVER the light sensor', None),
             (6, 'COVER the light sensor now, keep it covered', None)]
    t = 6
    steps.append((t + 8, 'UNCOVER now', 'try wake (expect: wake line)'))
    steps.append((t + 15, 'Next: PET Mote, in 3...', None))
    steps.append((t + 18, 'PET Mote now: stroke it side to side',
                  'try pet (expect: mood line, timid -> curious)'))
    steps.append((t + 28, 'Next: CLAP once, in 3...', None))
    steps.append((t + 31, 'CLAP once now', 'try clap (expect: hide, then a peek-out line)'))
    steps.append((t + 42, 'Next: SLIDE the keyboard OUT, in 3...', None))
    steps.append((t + 45, 'SLIDE the keyboard OUT now', 'try door (expect: door line)'))
    steps.append((t + 56, 'Next: slide it IN, then COVER the sensor, in 3...', None))
    steps.append((t + 59, 'Slide the keyboard IN, then COVER the sensor',
                  'try goodnight (expect: goodnight line, sleeps)'))
    steps.append((t + 75, 'Done', 'done'))
    return steps


def tries_summary(mote, what):
    log('--- %s summary (seconds after each prompt) ---' % what)
    marks = [i for i in range(len(EVENTS))
             if EVENTS[i][1].startswith('try ') or EVENTS[i][1] == 'done']
    for a, b in zip(marks, marks[1:]):
        t0 = EVENTS[a][0]
        got = ['%s +%.1f' % (n, t - t0) for t, n in EVENTS[a + 1:b]]
        log('%s\n         %s' % (EVENTS[a][1][4:], ', '.join(got) or 'nothing'))
    log('trust now %d (%s); memories: %s' % (mote.trust, mote.mood(),
        '; '.join([m for _, m in mote.memories]) or 'none'))
    if MIC:
        log('mic: %d slices, %d ignored after chirps, baseline now %s' % (
            MIC.count, MIC.muted, MIC.baseline()))


def light_summary():
    log('--- summary (seconds after each prompt) ---')
    rounds = 0
    for i in range(len(EVENTS)):
        t, name = EVENTS[i]
        if name not in ('cover', 'uncover'):
            continue
        if name == 'cover':
            rounds += 1
        found = {}
        for t2, n2 in EVENTS[i + 1:]:
            if n2 in ('cover', 'uncover', 'done'):
                break
            if n2 not in found:
                found[n2] = t2 - t
        if name == 'cover':
            log('round %d cover:   drowsy %s   asleep %s' % (rounds,
                fmt(found.get('drowsy')), fmt(found.get('asleep'))))
        else:
            log('round %d uncover: eyes open %s   fully awake %s' % (rounds,
                fmt(found.get('waking')), fmt(found.get('awake'))))


def touch_summary(touch, mote):
    log('--- touch summary ---')
    marks = [i for i in range(len(EVENTS))
             if EVENTS[i][1].startswith('try ') or EVENTS[i][1] == 'done']
    for a, b in zip(marks, marks[1:]):
        felt, trust = [], ''
        for t, n in EVENTS[a + 1:b]:
            if n.startswith('touch '):
                felt.append(n[6:])
            elif n.startswith('trust '):
                trust = n
        log('%-42s felt: %s  %s' % (EVENTS[a][1][4:], ', '.join(felt) or 'nothing', trust))
    log('finger down %d times, %d dropouts joined; trust now %d (%s)' % (
        touch.downs, touch.dropouts, mote.trust, mote.mood()))

def fmt(x):
    if x is None:
        return 'never'
    return '%.1f s' % x


def main():
    global FONT, MIC, MIND, SAY_FONT
    args = sys.argv[1:]
    mode = None
    limit = None
    for a in args:
        if a.isdigit():
            limit = int(a)
        elif a in ('test', 'touch', 'annoy', 'hold', 'door', 'clap', 'hide', 'show', 'mind'):
            mode = a
    raw = 'raw' in args            # log every touch event pygame delivers

    # the mic takes about half a second to start, so it starts first
    MIC = Mic(mode in ('clap', 'hide'))
    MIC.start()
    # so does the mind's SSH connection (about 3 s)
    MIND = Mind('nomind' not in args)
    if MIND.enabled:
        MIND.connect()
    pygame.mixer.pre_init(SOUND_RATE, -16, 1, 512)
    pygame.init()
    screen = pygame.display.set_mode((W, H), FULLSCREEN)
    pygame.mouse.set_visible(0)
    try:
        FONT = pygame.font.Font(None, 48)
        SMALL = pygame.font.Font(None, 28)
        SAY_FONT = pygame.font.Font(None, 36)
    except Exception, e:
        log('no font: %s' % e)
        FONT = SMALL = SAY_FONT = None
    clock = pygame.time.Clock()
    load_chirps()
    # the outside room is drawn once per darkness level, then only copied
    rooms = []
    for i in range(ROOM_LEVELS):
        room = pygame.Surface((W, H)).convert()
        draw_room(room, i / float(ROOM_LEVELS - 1))
        rooms.append(room)
    mote = Mote()
    touch = Touch()
    log('started, lux=%s, mode %s' % (read_lux(), mode or 'free run'))
    mote.feel_slide(read_slide(), True)

    steps = []
    if mode == 'test':
        steps = light_schedule()
    elif mode == 'touch':
        steps = touch_schedule(TOUCH_TRIES)
    elif mode == 'hold':
        steps = touch_schedule(HOLD_TRIES)
    elif mode == 'annoy':
        steps = touch_schedule(ANNOY_TRIES)
    elif mode == 'door':
        steps = door_schedule()
    elif mode == 'clap':
        steps = clap_schedule()
    elif mode == 'hide':
        steps = hide_schedule()
    elif mode == 'show':
        steps = show_schedule()
    elif mode == 'mind':
        steps = mind_schedule()
    if steps and limit is None:
        limit = steps[-1][0] + 1
    prompt = ''
    next_lux = next_slide = 0
    last_lux = last_scene = last_prompt = last_debug = last_area = None
    bubble = where = bubble_shown = None   # (rect, image), where it sits, its key
    frames, fps_t0, cpu0 = 0, now(), time.clock()
    running = True
    while running:
        t = now()
        felt = []
        for ev in pygame.event.get():
            if raw and ev.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION):
                log('raw %s %s on Mote: %s' % (pygame.event.event_name(ev.type),
                    ev.pos, mote.hit(ev.pos)))
            if ev.type == QUIT:
                running = False
            elif ev.type == KEYDOWN and mode == 'door':
                # the keyboard is out and held: keys must not end the test
                log('key %s pressed (ignored)' % pygame.key.name(ev.key))
            elif ev.type == KEYDOWN and ev.key in (K_ESCAPE, K_q):
                running = False
            elif ev.type == MOUSEBUTTONDOWN:
                if QUIT_BOX.collidepoint(ev.pos):
                    running = False
                else:
                    felt += touch.down(t, ev.pos, mote.hit(ev.pos))
            elif ev.type == MOUSEMOTION:
                felt += touch.move(t, ev.pos)
            elif ev.type == MOUSEBUTTONUP:
                felt += touch.up(t, ev.pos)
        felt += touch.tick(t)
        for name, pos in felt:
            mote.feel_touch(name, pos)
        if limit is not None and t >= limit:
            running = False

        while steps and t >= steps[0][0]:
            st, prompt, name = steps.pop(0)
            log('>>> ' + prompt)
            if name:
                note(name)
            if name and name.startswith('fake clap'):
                if name.endswith('fond'):
                    mote.trust = 8                       # fond hides for less
                mote.feel_sound('clap', 0, 0)

        if t >= next_slide:
            next_slide = t + SLIDE_EVERY
            mote.feel_slide(read_slide())
        if t >= next_lux:
            next_lux = t + LUX_EVERY
            lux = read_lux()
            if mode in ('test', 'door') and lux != last_lux:
                log('lux %s -> %s' % (last_lux, lux))
            last_lux = lux
            mote.feel_light(lux)
        for name, level, base in MIC.take():
            mote.feel_sound(name, level, base)
        mote.update(touch.take_stroked())
        MIND.tick(mote)

        # redraw only what changed: Mote's old and new area, the prompt and
        # the debug corner. The whole screen while the background fades or
        # the door slides; the outside room changes in 4 steps as it dims.
        bg = mote.background()
        key = SAY_FONT and bubble_key(MIND)
        k = mote.door_k()
        level = int(round(mote.darkness() * (ROOM_LEVELS - 1)))
        if k >= 1:
            scene = ('room', level)
        elif k > 0:
            scene = ('door', bg, level, k)
        else:
            scene = ('inside', bg)
        room = rooms[level]

        def paint(rect):
            if k >= 1:
                rect = rect.clip(screen.get_rect())
                screen.blit(room, rect, rect)
            else:
                screen.fill(bg, rect)

        debug = 'trust %d  %s   felt: %s' % (mote.trust, mote.mood(), mote.felt)
        if mote.door:
            debug += '   door open'
        if MIC.started is not None:
            debug += '   mic %s' % (MIC.baseline() or '-')
        debug += '   mind %s' % MIND.status()
        if scene != last_scene:
            if k >= 1:
                screen.blit(room, (0, 0))
            else:
                screen.fill(bg)
                if k > 0:                                # the door, part open
                    w = int(W * k)
                    r = Rect((W - w) / 2, 0, w, H)
                    screen.blit(room, r, r)
                    pygame.draw.line(screen, FRAME, r.topleft, r.bottomleft, 4)
                    pygame.draw.line(screen, FRAME, r.topright, r.bottomright, 4)
            area = mote.draw(screen)
            dirty = None
        else:
            if key != bubble_shown and bubble:           # the old bubble goes
                paint(bubble[0])
            paint(last_area)
            area = mote.draw(screen)
            dirty = [area.union(last_area)]
            if key != bubble_shown and bubble:
                dirty.append(bubble[0])
        # the bubble is drawn once, then again only where Mote overlaps it
        if key != bubble_shown:
            if key is None:
                bubble, where = None, None
            else:
                if where is None or key[0] != bubble_shown[0]:
                    where = (int(mote.x), mote.body.top)
                bubble = make_bubble(key, mote, where)
            bubble_shown = key
            if bubble:
                screen.blit(bubble[1], bubble[0])
                if dirty is not None:
                    dirty.append(bubble[0])
        elif bubble and (dirty is None or area.colliderect(bubble[0])
                         or last_area.colliderect(bubble[0])):
            screen.blit(bubble[1], bubble[0])
            if dirty is not None:
                dirty.append(bubble[0])
        if dirty is None or prompt != last_prompt:
            if dirty is not None:
                paint(PROMPT_AREA)
                dirty.append(PROMPT_AREA)
            if prompt and SMALL:
                screen.blit(SMALL.render(prompt, 1, TEXT), (20, 20))
        if dirty is None or debug != last_debug:
            if dirty is not None:
                paint(DEBUG_AREA)
                dirty.append(DEBUG_AREA)
            if SMALL:
                screen.blit(SMALL.render(debug, 1, DIM_TEXT), (20, H - 32))
        if dirty is None:
            pygame.display.flip()
        else:
            pygame.display.update(dirty)
        last_scene, last_prompt, last_debug, last_area = scene, prompt, debug, area

        if mote.state == 'asleep':
            clock.tick(FPS_ASLEEP)
        else:
            clock.tick(FPS_AWAKE)
        frames += 1
        if t - fps_t0 >= 10:
            cpu = time.clock()
            log('fps %.1f, cpu %d%%' % (frames / (t - fps_t0),
                100 * (cpu - cpu0) / (t - fps_t0)))
            frames, fps_t0, cpu0 = 0, t, cpu

    if mode == 'test':
        light_summary()
    elif mode in ('touch', 'annoy', 'hold'):
        touch_summary(touch, mote)
    elif mode == 'door':
        tries_summary(mote, 'door')
    elif mode in ('clap', 'hide', 'mind'):
        tries_summary(mote, mode)
    MIC.stop()
    MIND.stop()
    pygame.quit()
    log('stopped')

if __name__ == '__main__':
    try:
        main()
    finally:
        if MIC:
            MIC.stop()             # never leave gst-launch holding the mic
        if MIND:
            MIND.stop()
