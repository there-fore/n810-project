# Touch aim probe for the N810 (Python 2.5 + pygame, run as user on DISPLAY=:0).
# Shows a cross at 5 places, one at a time; tap its centre. Prints where each
# tap landed in pygame, and the average offset, to check the screen's aim.
import sys, time
import pygame
from pygame.locals import *

TARGETS = [(400, 240), (100, 100), (700, 100), (100, 380), (700, 380)]
SECS = 5.0                 # time per cross

pygame.init()
screen = pygame.display.set_mode((800, 480), FULLSCREEN)
pygame.mouse.set_visible(0)
font = pygame.font.Font(None, 32)
results = []
for i, (tx, ty) in enumerate(TARGETS):
    screen.fill((40, 52, 78))
    pygame.draw.line(screen, (250, 226, 160), (tx - 30, ty), (tx + 30, ty), 3)
    pygame.draw.line(screen, (250, 226, 160), (tx, ty - 30), (tx, ty + 30), 3)
    pygame.draw.circle(screen, (250, 120, 120), (tx, ty), 4)
    msg = 'Cross %d of %d: tap its centre once' % (i + 1, len(TARGETS))
    screen.blit(font.render(msg, 1, (230, 230, 240)), (220, 220 + (ty < 240 and 60 or -60)))
    pygame.display.flip()
    print '>>> %s (cross at %d,%d)' % (msg, tx, ty)
    sys.stdout.flush()
    pygame.event.clear()
    end = time.time() + SECS
    tap = None
    while time.time() < end:
        for ev in pygame.event.get():
            if ev.type == MOUSEBUTTONDOWN and tap is None:
                tap = ev.pos
                print '    tap at %d,%d  offset %+d,%+d' % (tap[0], tap[1], tap[0] - tx, tap[1] - ty)
                sys.stdout.flush()
        time.sleep(0.02)
    results.append(((tx, ty), tap))
pygame.quit()

got = [(t, p) for t, p in results if p]
print '--- %d of %d crosses tapped ---' % (len(got), len(results))
for (tx, ty), p in results:
    if p:
        print 'cross %3d,%3d  tap %3d,%3d  offset %+4d,%+4d' % (tx, ty, p[0], p[1], p[0] - tx, p[1] - ty)
    else:
        print 'cross %3d,%3d  no tap' % (tx, ty)
if got:
    dx = sum([p[0] - t[0] for t, p in got]) / float(len(got))
    dy = sum([p[1] - t[1] for t, p in got]) / float(len(got))
    print 'average offset %+.0f,%+.0f px' % (dx, dy)
