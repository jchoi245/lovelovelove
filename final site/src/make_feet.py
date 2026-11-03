"""Build the footprint SVGs used by Movement (and the decorate tray) from the Figma parts.

Figma node 27:850 ("new footstep asset") has four shoe prints, each a left + right pair:
heels (purple), boots (peach, toe and heel are separate parts), sneakers (blue) and dress shoes (yellow).
The Figma exports live untouched in ../assets/v2/feet/figma/; this writes, into ../assets/v2/feet/:
    <type>-l.svg, <type>-r.svg   one shoe each, cropped to the shoe
    <type>-pair.svg              both shoes laid out as in Figma
Part positions are the Figma insets converted to px; the drawn paths themselves are untouched.
Run: python3 make_feet.py
"""
import re
from pathlib import Path
from svgpath import subpaths

FEET = Path(__file__).parent.parent / 'assets' / 'v2' / 'feet'
FIG = FEET / 'figma'


def inner(svg):
    """Everything inside the root <svg>, minus Figma's clip wrapper and defs."""
    body = re.sub(r'^<svg[^>]*>|</svg>\s*$', '', svg.strip())
    body = re.sub(r'<defs>.*?</defs>', '', body, flags=re.S)
    return re.sub(r'\s*clip-path="url\(#[^)]*\)"', '', body).strip()


def size(svg):
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    return float(vb.group(1)), float(vb.group(2))


def write(name, w, h, body, x0=0.0, y0=0.0):
    (FEET / name).write_text(
        f'<svg width="{w:.2f}" height="{h:.2f}" viewBox="{x0:.2f} {y0:.2f} {w:.2f} {h:.2f}" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg">\n{body}\n</svg>\n')


def compose(name, parts):
    """parts: [(file, x, y)] placed with a translate; writes a tight svg around them."""
    body, W, H = [], 0, 0
    for f, x, y in parts:
        svg = (FIG / f).read_text()
        w, h = size(svg)
        W, H = max(W, x + w), max(H, y + h)
        body.append(f'<g transform="translate({x:.2f} {y:.2f})">{inner(svg)}</g>')
    write(name, W, H, '\n'.join(body))


def split(src, stem):
    """A pair drawn in one svg: split its paths into the left and right shoe by where they sit."""
    svg = (FIG / src).read_text()
    W, _ = size(svg)
    sides = {'l': [], 'r': []}
    for m in re.finditer(r'<path[^>]*\sd="([^"]*)"[^>]*/>', svg):
        pts = [p for s in subpaths(m.group(1), n=6) for p in s]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        side = 'l' if (min(xs) + max(xs)) / 2 < W / 2 else 'r'
        sides[side].append((m.group(0), min(xs), min(ys), max(xs), max(ys)))
    for side, paths in sides.items():
        x0 = min(p[1] for p in paths) - .5; y0 = min(p[2] for p in paths) - .5
        x1 = max(p[3] for p in paths) + .5; y1 = max(p[4] for p in paths) + .5
        write(f'{stem}-{side}.svg', x1 - x0, y1 - y0, '\n'.join(p[0] for p in paths), x0, y0)
    (FEET / f'{stem}-pair.svg').write_text(svg)


# boots: toe and heel are separate parts (Figma 27:1406, insets resolved to px)
compose('boot-l.svg', [('boot-l.svg', 0, 0), ('boot-heel-l.svg', 19.84, 129.53)])
compose('boot-r.svg', [('boot-r.svg', 8.80, 0), ('boot-heel-r.svg', 0, 127.90)])
compose('boot-pair.svg', [('boot-l.svg', 0, 0), ('boot-heel-l.svg', 19.84, 129.53),
                          ('boot-r.svg', 113.13, 2.31), ('boot-heel-r.svg', 104.32, 130.21)])
# sneakers: one part per shoe (Figma 27:1379)
compose('sneaker-pair.svg', [('sneaker-l.svg', 0, 0), ('sneaker-r.svg', 103.87, 1.53)])
# heels and dress shoes: both shoes in one drawing (Figma 27:1462, 27:1468)
split('heels-pair.svg', 'heels')
split('dress-pair.svg', 'dress')
# sneakers come as one file per shoe already
for side in 'lr':
    (FEET / f'sneaker-{side}.svg').write_text((FIG / f'sneaker-{side}.svg').read_text())

print(sorted(p.name for p in FEET.glob('*.svg')))
