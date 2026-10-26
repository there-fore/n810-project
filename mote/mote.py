# Mote, the October creature demo (Python 2.5 + pygame 1.7.1 on the N810).
# Build steps 1-2: a blob that breathes and blinks, sleeps when the light
# sensor is covered, and feels touch (poke, pet, hold) with trust and moods.
# Thresholds are from CREATURE.md ("Affordance -> behaviour").
# Usage (on the N810, as user):  DISPLAY=:0 python2.5 mote.py [test|touch] [raw] [secs]
#   test  = timed COVER / UNCOVER prompts, then a summary of reaction times
#   touch = timed POKE / PET / HOLD prompts, then a summary of what Mote felt
#   annoy = timed prompts to poke Mote fast, twice (checks the annoyed look)
#   hold  = timed prompts to hold Mote, then pet and hold (checks the held look)
#   raw   = log every touch event pygame delivers
#   secs  = quit after this many seconds (default: run until the top-right
#           corner is tapped, or Esc / q is pressed)
import sys, time, math, random
import pygame
from pygame.locals import *

LUX_PATH = '/sys/devices/platform/i2c_omap.2/i2c-0/0-0029/lux'
LUX_EVERY = 1 / 3.0        # poll light 3 times a second
DARK = 2                   # lux at or below this counts as covered
BRIGHT = 5                 # lux at or above this counts as uncovered
SLEEP_AFTER = 2.0          # covered this long (after drowsy) -> asleep
WAKE_ANIM = 1.0            # eyes take this long to open; dark again -> asleep

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
DEBUG_AREA = Rect(0, H - 40, 560, 40)

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

def now():
    return time.time() - T0

def log(msg):
    print '%6.1f  %s' % (now(), msg)
    sys.stdout.flush()

def note(name):
    EVENTS.append((now(), name))

def read_lux():
    try:
        f = open(LUX_PATH)
        try:
            return int(float(f.read().strip()))
        finally:
            f.close()
    except (IOError, ValueError):
        return None

def mix(a, b, k):
    return tuple([int(a[i] + (b[i] - a[i]) * k) for i in range(3)])

def draw_heart(screen, x, y, s, color):
    # two bumps and a point; (x, y) is between the bumps, s is half the width
    pygame.draw.circle(screen, color, (x - s / 2, y), s / 2 + 1)
    pygame.draw.circle(screen, color, (x + s / 2, y), s / 2 + 1)
    pygame.draw.polygon(screen, color, [(x - s, y + 1), (x + s, y + 1), (x, y + s * 13 / 10)])

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


class Mote:
    def __init__(self):
        self.state = 'awake'       # awake, drowsy, asleep, waking
        self.since = now()
        self.dark_since = None
        self.bright_since = None
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

    def mood(self):
        for top, name in MOODS:
            if self.trust <= top:
                return name

    def change_trust(self, d, why):
        old, old_mood = self.trust, self.mood()
        self.trust = max(0, min(10, self.trust + d))
        msg = 'trust %d -> %d (%s)' % (old, self.trust, why)
        if self.mood() != old_mood:
            msg += ', mood %s -> %s' % (old_mood, self.mood())
        log(msg)
        note('trust %d' % self.trust)

    def set_expr(self, expr, secs=0):
        if expr != self.expr:
            self.expr_since = now()
        self.expr = expr
        self.expr_until = secs and now() + secs or 0

    def set_state(self, state, lux):
        log('lux=%-3s %s -> %s' % (lux, self.state, state))
        note(state)
        self.state = state
        self.since = now()
        if state != 'awake':
            self.finger = None
            self.set_expr(None)

    def hit(self, pos):
        return self.body is not None \
            and self.body.inflate(2 * MARGIN, 2 * MARGIN).collidepoint(pos)

    def feel_light(self, lux):
        t = now()
        if lux is None:
            return
        if lux <= DARK:
            self.bright_since = None
            if self.dark_since is None:
                self.dark_since = t
        elif lux >= BRIGHT:
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

    def feel_touch(self, name, pos):
        if name in ('poke', 'pet', 'hold') and self.state != 'awake':
            log('touch %s ignored (%s)' % (name, self.state))
            note('touch %s (ignored, %s)' % (name, self.state))
        if self.state != 'awake':
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
            elif self.expr != 'annoyed':
                self.set_expr('flinch', 0.4)
        elif name == 'pet':
            self.set_expr('happy')
        elif name == 'hold':
            self.set_expr('calm')
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
        if self.expr == 'notice':
            return 0.0
        if self.mood() == 'timid':
            return 0.35
        return 0.0

    def background(self):
        t = now()
        dark = 0.0
        if self.state == 'asleep':
            dark = min(1.0, (t - self.since) / 1.5)
        elif self.state == 'drowsy':
            dark = 0.4
        elif self.state == 'waking':
            dark = max(0.0, 1.0 - (t - self.since) / WAKE_ANIM)
        return mix(BG_AWAKE, BG_ASLEEP, dark)

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
        bw = int((bw * (1 + depth * breath) - stretch * 0.5 + squash) * self.scale)
        bh = int((bh * (1 - depth * breath) + stretch - squash) * self.scale)
        if self.mood() == 'fond' and self.state == 'awake' and not calm:
            hop = int(abs(math.sin(t * math.pi / 0.6)) * 10)
        if self.finger and self.expr == 'happy':
            lean = max(-15, min(15, (self.finger[0] - self.x) / 4))
        shake = 0
        self.color = BODY
        if self.expr == 'annoyed':                       # shakes, goes red
            shake = int(math.sin(t * 2 * math.pi * 8) * 5)
            self.color = ANGRY
        cx = int(self.x + lean + shake)
        body = Rect(cx - bw / 2, 400 - hop - bh, bw, bh)
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
    global FONT
    args = sys.argv[1:]
    mode = None
    limit = None
    for a in args:
        if a.isdigit():
            limit = int(a)
        elif a in ('test', 'touch', 'annoy', 'hold'):
            mode = a
    raw = 'raw' in args            # log every touch event pygame delivers

    pygame.init()
    screen = pygame.display.set_mode((W, H), FULLSCREEN)
    pygame.mouse.set_visible(0)
    try:
        FONT = pygame.font.Font(None, 48)
        SMALL = pygame.font.Font(None, 28)
    except Exception, e:
        log('no font: %s' % e)
        FONT = SMALL = None
    clock = pygame.time.Clock()
    mote = Mote()
    touch = Touch()
    log('started, lux=%s, mode %s' % (read_lux(), mode or 'free run'))

    steps = []
    if mode == 'test':
        steps = light_schedule()
    elif mode == 'touch':
        steps = touch_schedule(TOUCH_TRIES)
    elif mode == 'hold':
        steps = touch_schedule(HOLD_TRIES)
    elif mode == 'annoy':
        steps = touch_schedule(ANNOY_TRIES)
    if steps and limit is None:
        limit = steps[-1][0] + 1
    prompt = ''
    next_lux = 0
    last_lux = last_bg = last_prompt = last_debug = last_area = None
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

        if t >= next_lux:
            next_lux = t + LUX_EVERY
            lux = read_lux()
            if mode == 'test' and lux != last_lux:
                log('lux %s -> %s' % (last_lux, lux))
            last_lux = lux
            mote.feel_light(lux)
        mote.update(touch.take_stroked())

        # redraw only what changed: Mote's old and new area, the prompt and
        # the debug corner; the whole screen while the background fades
        bg = mote.background()
        debug = 'trust %d  %s   felt: %s' % (mote.trust, mote.mood(), mote.felt)
        if bg != last_bg:
            screen.fill(bg)
            area = mote.draw(screen)
            dirty = None
        else:
            screen.fill(bg, last_area)
            area = mote.draw(screen)
            dirty = [area.union(last_area)]
        if dirty is None or prompt != last_prompt:
            screen.fill(bg, PROMPT_AREA)
            if prompt and SMALL:
                screen.blit(SMALL.render(prompt, 1, TEXT), (20, 20))
            if dirty is not None:
                dirty.append(PROMPT_AREA)
        if dirty is None or debug != last_debug:
            screen.fill(bg, DEBUG_AREA)
            if SMALL:
                screen.blit(SMALL.render(debug, 1, DIM_TEXT), (20, H - 32))
            if dirty is not None:
                dirty.append(DEBUG_AREA)
        if dirty is None:
            pygame.display.flip()
        else:
            pygame.display.update(dirty)
        last_bg, last_prompt, last_debug, last_area = bg, prompt, debug, area

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
    pygame.quit()
    log('stopped')

if __name__ == '__main__':
    main()
