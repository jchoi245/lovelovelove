"""Cut the eight emotion icons out of the Figma asset frame (node 84:3), one SVG each.

The frame export (assets/v2/emo-icons/figma/emotion-assets.svg) holds every icon as loose line work; each
icon is cropped by its area (from the Figma layer bounds, with a little room for the line ends), the frame's
background, the text labels and any neighbouring icon's lines are left out. Writes assets/v2/emo-icons/<name>.svg.
Run: python3 make_emo_icons.py
"""
import re
from pathlib import Path

ICONS = Path(__file__).parent.parent / 'assets' / 'v2' / 'emo-icons'
PAD = 8
AREAS = {                       # x, y, w, h in the Figma frame, and the icon's own line colour
    'calm':            (152, 195, 220, 203, '#FFD29C'),
    'excited':         (451, 153, 211, 196, '#FFF492'),
    'energetic':       (725, 153, 208, 174, '#9FD8FF'),
    'curiosity':       (1029, 108, 152, 302, '#C49FFF'),
    'angry':           (120, 655, 207, 236, '#1350A8'),
    'tired':           (292, 687, 309, 184, '#4D1A59'),
    'energetic-night': (699, 697, 207, 174, '#9FD8FF'),
    'curiosity-night': (965, 626, 152, 302, '#C49FFF'),
}

LINE = 5        # line width for every icon (Figma draws them at 2, which turns hairline once scaled down)
# stronger versions of the Figma colours, same hues, so the icons read on the page (the night ones are
# also lifted, so they show on the dark ground)
STRONGER = {'#FFD29C': '#F7A24A',   # calm: orange
            '#FFF492': '#EFC81C',   # excited: yellow
            '#9FD8FF': '#3DA9F5',   # energetic: blue
            '#C49FFF': '#9B5CF6',   # curiosity: purple
            '#1350A8': '#4D86FF',   # angry: blue
            '#4D1A59': '#C25BE0'}   # tired: violet


def thicker(m):
    """Widen a line: stroked lines get LINE; lines drawn as thin filled shapes get a matching edge."""
    p = re.sub(r'\s(stroke-width|stroke-linecap|stroke-linejoin)="[^"]*"', '', m.group(0))
    stroke = re.search(r'\sstroke="(#\w+)"', p)
    fill = re.search(r'\sfill="(#\w+)"', p)
    if stroke:
        p = p.replace('/>', f' stroke-width="{LINE}" stroke-linecap="round" stroke-linejoin="round"/>')
    elif fill:
        p = p.replace('/>', f' stroke="{fill.group(1)}" stroke-width="{LINE - 2}" stroke-linejoin="round"/>')
    for figma, strong in STRONGER.items():
        p = re.sub(figma, strong, p, flags=re.I)
    return p


src = (ICONS / 'figma' / 'emotion-assets.svg').read_text()
body = re.sub(r'^<svg[^>]*>|</svg>\s*$', '', src.strip())
body = re.sub(r'<rect width="1724" height="1139"[^>]*/>', '', body)          # the frame's own backgrounds
defs = ''.join(re.findall(r'<defs>.*?</defs>', body, re.S))
body = re.sub(r'<defs>.*?</defs>', '', body, flags=re.S)
for name, (x, y, w, h, colour) in AREAS.items():
    x0, y0, ww, hh = x - PAD, y - PAD, w + 2 * PAD, h + 2 * PAD
    # only this icon's own lines (neighbouring icons overlap some areas)
    own = re.sub(r'<path\b[^>]*/>', lambda m: m.group(0) if colour.lower() in m.group(0).lower() else '', body)
    own = re.sub(r'<path\b[^>]*/>', thicker, own)
    (ICONS / f'{name}.svg').write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ww}" height="{hh}" viewBox="{x0} {y0} {ww} {hh}" fill="none">'
        f'<defs><clipPath id="c"><rect x="{x0}" y="{y0}" width="{ww}" height="{hh}"/></clipPath></defs>{defs}'
        f'<g clip-path="url(#c)">{own}</g></svg>\n')
    print(name, ww, hh)
