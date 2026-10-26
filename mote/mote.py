# Mote, the October creature demo (Python 2.5 + pygame 1.7.1 on the N810).
# Build step 1: a blob that breathes and blinks, goes drowsy when the light
# sensor is covered, sleeps after 2 s, and wakes when it is uncovered.
# Thresholds are from CREATURE.md ("Affordance -> behaviour").
# Usage (on the N810, as user):  DISPLAY=:0 python2.5 mote.py [test] [secs]
#   test = timed COVER / UNCOVER prompts on screen and in the terminal,
#          then a summary of how fast Mote reacted
#   secs = quit after this many seconds (default: run until the top-right
#          corner is tapped, or Esc / q is pressed)
import sys, time, math, random
import pygame
from pygame.locals import *

LUX_PATH = '/sys/devices/platform/i2c_omap.2/i2c-0/0-0029/lux'
LUX_EVERY = 1 / 3.0        # poll light 3 times a second
DARK = 2                   # lux at or below this counts as covered
BRIGHT = 5                 # lux at or above this counts as uncovered
SLEEP_AFTER = 2.0          # covered this long (after drowsy) -> asleep
WAKE_ANIM = 1.0            # eyes take this long to open; dark again -> asleep
W, H = 800, 480
FPS = 25
QUIT_BOX = Rect(W - 80, 0, 80, 80)
# only these parts of the screen are redrawn each frame (saves CPU);
# the whole screen is redrawn while the background colour fades
MOTE_AREA = Rect(170, 90, 460, 330)    # Mote, its shadow and the z's
PROMPT_AREA = Rect(0, 0, W, 60)

BG_AWAKE = (40, 52, 78)
BG_ASLEEP = (14, 16, 30)
BODY = (250, 226, 160)
BODY_DARK = (205, 180, 120)
EYE = (40, 30, 30)
CHEEK = (245, 170, 150)
TEXT = (230, 230, 240)

T0 = time.time()

def now():
    return time.time() - T0

def log(msg):
    print '%6.1f  %s' % (now(), msg)
    sys.stdout.flush()

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


class Mote:
    def __init__(self):
        self.state = 'awake'       # awake, drowsy, asleep, waking
        self.since = now()
        self.dark_since = None
        self.bright_since = None
        self.next_blink = now() + 2
        self.blink_until = 0

    def set_state(self, state, lux):
        log('lux=%-3s %s -> %s' % (lux, self.state, state))
        self.state = state
        self.since = now()

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

    def update(self):
        t = now()
        if self.state == 'waking' and t - self.since >= WAKE_ANIM:
            self.set_state('awake', '')
        if self.state == 'awake' and t >= self.next_blink:
            self.blink_until = t + 0.15
            self.next_blink = t + random.uniform(2.5, 6.0)

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
        return 0.0

    def draw(self, screen, area=None):
        # returns the background colour, so the caller knows when it changed
        t = now()
        asleep = self.state == 'asleep'
        if asleep:
            breath = math.sin(t * 2 * math.pi / 4.0)     # slow, 4 s
            dark = min(1.0, (t - self.since) / 1.5)
        else:
            breath = math.sin(t * 2 * math.pi / 2.2)
            dark = 0.0
            if self.state == 'drowsy':
                dark = 0.4
            elif self.state == 'waking':
                dark = max(0.0, 1.0 - (t - self.since) / WAKE_ANIM)
        bg = mix(BG_AWAKE, BG_ASLEEP, dark)
        if area:
            screen.fill(bg, area)
        else:
            screen.fill(bg)                  # pygame 1.7 rejects area=None

        bw, bh = 240, 190
        if asleep:
            bw, bh = 280, 150                            # curled up, flatter
        stretch = 0
        if self.state == 'waking':
            stretch = math.sin((t - self.since) / WAKE_ANIM * math.pi) * 30
        bw = int(bw * (1 + 0.03 * breath) - stretch * 0.5)
        bh = int(bh * (1 - 0.03 * breath) + stretch)
        cx, floor = W / 2, 400
        body = Rect(cx - bw / 2, floor - bh, bw, bh)
        pygame.draw.ellipse(screen, BODY_DARK, body.move(0, 6))
        pygame.draw.ellipse(screen, BODY, body)

        # eyes
        ey = body.top + bh * 2 / 5
        lid = max(0.0, min(1.0, self.lid()))
        for ex in (cx - bw / 5, cx + bw / 5):
            if lid >= 0.95:
                pygame.draw.line(screen, EYE, (ex - 14, ey + 4), (ex + 14, ey + 4), 4)
            else:
                r = 15
                pygame.draw.circle(screen, EYE, (ex, ey), r)
                pygame.draw.circle(screen, (255, 255, 255), (ex + 5, ey - 5), 4)
                if lid > 0:
                    cover = int(2 * r * lid) + 1
                    pygame.draw.rect(screen, BODY, Rect(ex - r - 1, ey - r - 1, 2 * r + 2, cover))
        for ex in (cx - bw / 3, cx + bw / 3):
            pygame.draw.circle(screen, CHEEK, (ex, ey + 30), 10)

        # floating z's while asleep
        if asleep and FONT:
            for i in range(3):
                k = ((t - self.since) / 3.0 + i / 3.0) % 1.0
                img = FONT.render('z', 1, mix(TEXT, BG_ASLEEP, k))
                screen.blit(img, (cx + bw / 2 - 10 + k * 60, body.top - 20 - k * 120))
        return bg


def test_schedule():
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


def summary(events):
    # events: list of (time, name) for cover / uncover prompts and state changes
    log('--- summary (seconds after each prompt) ---')
    rounds = 0
    for i in range(len(events)):
        t, name = events[i]
        if name not in ('cover', 'uncover'):
            continue
        if name == 'cover':
            rounds += 1
        found = {}
        for t2, n2 in events[i + 1:]:
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

def fmt(x):
    if x is None:
        return 'never'
    return '%.1f s' % x


def main():
    global FONT
    args = sys.argv[1:]
    testing = 'test' in args
    limit = None
    for a in args:
        if a.isdigit():
            limit = int(a)

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
    log('started, lux=%s, %s' % (read_lux(), testing and 'test mode' or 'free run'))

    steps = testing and test_schedule() or []
    if steps and limit is None:
        limit = steps[-1][0] + 1
    prompt, events = '', []
    next_lux = 0
    last_lux = last_bg = last_prompt = None
    frames, fps_t0, cpu0 = 0, now(), time.clock()
    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == QUIT:
                running = False
            elif ev.type == KEYDOWN and ev.key in (K_ESCAPE, K_q):
                running = False
            elif ev.type == MOUSEBUTTONDOWN and QUIT_BOX.collidepoint(ev.pos):
                running = False
        t = now()
        if limit is not None and t >= limit:
            running = False

        while steps and t >= steps[0][0]:
            st, prompt, name = steps.pop(0)
            log('>>> ' + prompt)
            if name:
                events.append((t, name))

        if t >= next_lux:
            next_lux = t + LUX_EVERY
            before = mote.state
            lux = read_lux()
            if testing and lux != last_lux:
                log('lux %s -> %s' % (last_lux, lux))
            last_lux = lux
            mote.feel_light(lux)
            if mote.state != before and testing:
                events.append((now(), mote.state))
        before = mote.state
        mote.update()
        if mote.state != before and testing:
            events.append((now(), mote.state))

        bg = mote.draw(screen, MOTE_AREA)
        bg_changed = bg != last_bg
        new_prompt = bg_changed or prompt != last_prompt
        if bg_changed:
            mote.draw(screen)                  # whole screen, new colour
        if new_prompt:
            screen.fill(bg, PROMPT_AREA)
            if prompt and SMALL:
                screen.blit(SMALL.render(prompt, 1, TEXT), (20, 20))
        last_bg, last_prompt = bg, prompt
        if bg_changed:
            pygame.display.flip()
        elif new_prompt:
            pygame.display.update([MOTE_AREA, PROMPT_AREA])
        else:
            pygame.display.update(MOTE_AREA)
        clock.tick(FPS)

        frames += 1
        if t - fps_t0 >= 10:
            cpu = time.clock()
            log('fps %.1f, cpu %d%%' % (frames / (t - fps_t0),
                100 * (cpu - cpu0) / (t - fps_t0)))
            frames, fps_t0, cpu0 = 0, t, cpu

    if testing:
        summary(events)
    pygame.quit()
    log('stopped')

if __name__ == '__main__':
    main()
