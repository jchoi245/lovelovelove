"""Build ../index.html from index.template.html.

Fills in the parts that come straight from Figma: the footprint layer
(placed from movement.v2.txt) and the emotion colour regions.
Run: python3 build.py
"""
import hashlib
import math
import re
from pathlib import Path

HERE = Path(__file__).parent
SITE = HERE.parent

# Movement (Figma 26:129): 95 shoe-print pairs, each placed exactly as in the frame. movement.v2.txt holds
# every pair's type, size and transform; the art is the pair from the new footstep asset (make_feet.py).
# The dancers sit 7px further left and 21px lower on the site than in that frame, so the prints shift by
# the same amount and land on the same spots around the figures.
SHOE = {'H': 'heels', 'B': 'boot', 'S': 'sneaker', 'D': 'dress'}
DX, DY = 222 - 229, 247 - 226


def pair(t, w, h, extra=''):
    return f'<img alt="" class="absolute block inset-0 size-full max-w-none" src="assets/v2/feet/{SHOE[t]}-pair.svg">{extra}'


# Step size: overall smaller than in Figma (SCALE), varied per print. A slow wave across the artboard makes
# whole stretches of a trail grow and shrink together (like people slowing down and striding out), and a
# small per-print jitter keeps it from looking mechanical.
SCALE, SWELL, JITTER = 0.7, 0.3, 0.08


def step_scale(nid, x, y):
    wave = (math.sin(x * 0.0105 + 0.8) + math.sin(y * 0.0135 - 1.3) + math.sin((x + y) * 0.006 + 2.1)) / 3
    jitter = (int(hashlib.md5(nid.encode()).hexdigest()[:6], 16) / 0xFFFFFF - 0.5) * 2
    return SCALE * (1 + SWELL * wave + JITTER * jitter)


def prints(name):
    """One absolutely placed, Figma-transformed div per shoe-print pair listed in a placements file."""
    out = []
    for row in (HERE / name).read_text().splitlines():
        if not row.strip() or row.startswith('#'):
            continue
        main, _, more = row.partition(' +')
        nid, t, w, h, a, b_, c, d, e, f = main.split()
        extra = ''
        if more:   # a second, smaller pair tucked inside this one and cut off by its edge, as in Figma
            t2, w2, h2, x2, y2, r2 = more.split()
            extra = (f'<div class="absolute" style="left:{x2}px;top:{y2}px;width:{w2}px;height:{h2}px;'
                     f'transform-origin:0 0;transform:rotate({-float(r2):g}deg)">{pair(t2, w2, h2)}</div>')
        # each print shrinks about its own centre (so the trails keep their paths) by a size that swells and
        # eases along the ground, plus a little jitter, so neighbouring steps differ without looking random
        k = step_scale(nid, float(e) + DX, float(f) + DY)
        cx, cy = float(w) / 2, float(h) / 2
        out.append((SHOE[t],
            f'    <div class="fp-unit fp-step absolute overflow-hidden" data-node-id="{nid}" style="left:0;top:0;width:{w}px;height:{h}px;'
            f'transform-origin:0 0;transform:matrix({a},{b_},{c},{d},{float(e) + DX:.2f},{float(f) + DY:.2f}) '
            f'translate({cx:g}px,{cy:g}px) scale({k:.3f}) translate({-cx:g}px,{-cy:g}px)">{pair(t, w, h, extra)}</div>'))
    return out


def by_shoe(rows):
    """Each shoe type in its own sheet, so the trails can drift separately in the parallax."""
    return '\n'.join(f'     <div class="mv-shoe" data-shoe="{shoe}">\n' + '\n'.join(h for t, h in rows if t == shoe) + '\n     </div>'
                     for shoe in SHOE.values() if any(t == shoe for t, _ in rows))


# day (Figma 26:129) and night (Figma 26:6158, laid out on the same artboard and figure position)
day_prints, night_prints = prints('movement.v2.txt'), prints('movement.night.txt')
foot = ('    <div class="mv-day">\n' + by_shoe(day_prints) + '\n    </div>\n'
        '    <div class="mv-night">\n' + by_shoe(night_prints) + '\n    </div>')
n_units = len(day_prints) + len(night_prints)

# Duration (Figma 57:13400 by day, 57:15925 at night): eyes in four sizes, one per duration band, placed exactly as in the frame
# (shifted with the dancers like the footprints). The eye files carry 2.5px of room for their 5px outline,
# so each sits 2.5px up and left inside its Figma box.
EYE = {'s': (84.59, 15.92, 89.5923, 20.92), 'm': (84.59, 29.6, 89.5921, 34.1901),
       'l': (84.58, 61.08, 89.5823, 66.0805), 'xl': (84.58, 75.99, 89.5824, 80.9907)}


def eyes(name):
    out = []
    for row in (HERE / name).read_text().splitlines():
        if not row.strip() or row.startswith('#'):
            continue
        nid, size, a, b_, c, d, e, f = row.split()
        gw, gh, aw, ah = EYE[size]
        out.append(
            f'      <div class="dur-eye absolute" data-node-id="{nid}" style="left:0;top:0;width:{gw}px;height:{gh}px;'
            f'transform-origin:0 0;transform:matrix({a},{b_},{c},{d},{float(e) + DX:.2f},{float(f) + DY:.2f})">'
            f'<img alt="" src="assets/v2/eyes/eye-{size}.svg" style="left:-2.5px;top:-2.5px;width:{aw}px;height:{ah}px"></div>')
    return '\n'.join(out)


# day (Figma 57:13400) and night (Figma 57:15925), same artboard and figure position
dur_eyes = ('    <div class="dur-day">\n' + eyes('duration.v2.txt') + '\n    </div>\n'
            '    <div class="dur-night">\n' + eyes('duration.night.txt') + '\n    </div>')


# Emotion (Figma 84:3): line-drawn mood icons scattered across the screen, how many of each following its
# share (made-up data until the real numbers come in). Day and night have their own moods. Each mood sits
# on its own sheet so it can drift separately in the parallax. Placement is random but seeded, so the layout
# is the same on every visit; icons keep clear of the title, ring, chips, caption and legend, and of each other.
import random
EMO_SIZE = {'calm': (232, 215), 'excited': (223, 208), 'energetic': (220, 186), 'curiosity': (164, 314),
            'angry': (219, 248), 'tired': (321, 196), 'energetic-night': (219, 186), 'curiosity-night': (164, 314)}
EMO_DAY = [('calm', 7), ('excited', 5), ('energetic', 4), ('curiosity', 4)]                      # 35 / 25 / 20 / 20 %
EMO_NIGHT = [('tired', 6), ('angry', 2), ('energetic-night', 4), ('curiosity-night', 4)]          # 35 / 15 / 25 / 25 %
KEEP_CLEAR = [(0, 0, 330, 190), (590, 20, 925, 165), (1230, 0, 1512, 360), (1170, 650, 1512, 982), (0, 890, 800, 982)]


def scatter(moods, seed):
    rnd, placed, out = random.Random(seed), [], {}
    todo = [m for m, n in moods for _ in range(n)]
    rnd.shuffle(todo)
    for mood in todo:
        w0, h0 = EMO_SIZE[mood]
        for _ in range(4000):
            k = rnd.uniform(.42, .7)
            w, h = w0 * k, h0 * k
            x, y = rnd.uniform(20 + w / 2, 1492 - w / 2), rnd.uniform(20 + h / 2, 962 - h / 2)
            if any(x + w / 2 > a and x - w / 2 < c and y + h / 2 > b and y - h / 2 < d for a, b, c, d in KEEP_CLEAR):
                continue
            r = max(w, h) / 2
            if any(math.hypot(x - px, y - py) < (r + pr) * .8 for px, py, pr in placed):
                continue
            placed.append((x, y, r))
            out.setdefault(mood, []).append(
                f'<div class="emo-icon" style="left:{x:.0f}px;top:{y:.0f}px;width:{w:.0f}px;height:{h:.0f}px;'
                f'transform:translate(-50%,-50%) rotate({rnd.uniform(-20, 20):.0f}deg)">'
                f'<img alt="" src="assets/v2/emo-icons/{mood}.svg"></div>')
            break
    return '\n'.join(f'      <div class="emo-sheet" data-emo="{m.replace("-night", "")}">' + ''.join(out.get(m, [])) + '</div>'
                     for m, _ in moods)


svg = ('    <div class="emo-day">\n' + scatter(EMO_DAY, 8403) + '\n    </div>\n'
       '    <div class="emo-night">\n' + scatter(EMO_NIGHT, 8404) + '\n    </div>')

# Dancers: Figma's export, unchanged apart from an id/class for the page (the clip box gets a few px of room).
dancers = (SITE / 'assets' / 'v2' / 'dancers.svg').read_text()
dancers = dancers.replace('<svg preserveAspectRatio="none" overflow="visible" style="display: block;" width="1132" height="585"',
                          '<svg id="dancers-svg" class="absolute block inset-0 size-full" role="img" aria-label="Line drawing of eleven figures holding hands in a circle" preserveAspectRatio="none" overflow="visible" width="1132" height="585"', 1)
dancers = dancers.replace('<rect width="1132" height="585" fill="white"/>', '<rect x="-8" y="-8" width="1148" height="601" fill="white"/>', 1)
assert 'dancers-svg' in dancers and 'x="-8"' in dancers

# Group size: a lavender version of every group shape (Figma 45:12632). It is the same drawing with the
# green gradient's two colours swapped for the lavender pair, written to assets/v2/group/. By day every
# group is lavender; at night the page swaps them all back to the original green (see setNight).
LAVENDER = {'#74CCD1': '#887398', '#E1ECBC': '#E7DEEC'}
(SITE / 'assets' / 'v2' / 'group').mkdir(parents=True, exist_ok=True)
for src in (SITE / 'assets').glob('grp_*.svg'):
    art = src.read_text()
    for green, lav in LAVENDER.items():
        art = re.sub(green, lav, art, flags=re.I)
    (SITE / 'assets' / 'v2' / 'group' / src.name).write_text(art)


def colour_groups(html):
    """Every group shape in the Group Size layer (and its legend) starts out in the day colour, lavender."""
    a = html.index('<!-- 5 · group size -->')
    b = html.index('<h2 class="title">Group Size</h2>', a)
    return html[:a] + html[a:b].replace('src="assets/grp_', 'src="assets/v2/group/grp_') + html[b:]


out = colour_groups((HERE / 'index.template.html').read_text())
out = (out.replace('{{DANCERS}}', dancers)
          .replace('{{DUR_EYES}}', dur_eyes)
          .replace('{{MV_FOOT}}', foot)
          .replace('{{EMO_ICONS}}', svg))
assert 'MISSING_' not in out, re.findall(r'MISSING_\w+', out)
(SITE / 'index.html').write_text(out)
print('steps:', out.count('fp-step '), 'units:', out.count('fp-unit '), 'shoe pairs:', n_units, 'bytes:', len(out))
