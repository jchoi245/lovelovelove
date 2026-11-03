"""One big emotion blob that fills the inside of the ring of joined arms, and where each colour sits in it.

The ring's inside is built from the five gaps the outline closes off (the same gaps the original Figma
emotion blobs sat in), joined across the narrow body parts between neighbouring gaps (legs and torsos
standing in the ring) but never across an arm, and kept off the open ground, so the colour runs right up
to the inner line of the arms all the way round.

Writes ../assets/v2/emo-blob.json in the emo-fill frame (1067 x 572, placed at 244,255 on the artboard):
    {"d": blob outline, "spots": [{"id", "colour", "cx", "cy", "r"}]}   one spot per original region,
    its radius following the region's size, so the bigger shares spread further when the colours blend.
Run: /tmp/claude-501/venv/bin/python make_emo_blob.py
"""
import json
import math
import re
from pathlib import Path
import cv2
import numpy as np
from svgpath import subpaths

ASSETS = Path(__file__).parent.parent / 'assets'
W, H = 1067, 572
PAD = 60                            # work on a padded canvas so the open ground surrounds the drawing
DANCERS_AT = (222 - 244 + PAD, 247 - 255 + PAD)   # dancers sit at 222,247 on the artboard; this frame at 244,255

# the outline, and which open areas it closes off
d = re.search(r' d="([^"]*)"', (ASSETS / 'v2' / 'dancers.svg').read_text()).group(1)
line = np.zeros((H + 2 * PAD, W + 2 * PAD), np.uint8)
for s in subpaths(d, *DANCERS_AT):
    cv2.polylines(line, [s.round().astype(np.int32)], True, 255, 3)
_, lab = cv2.connectedComponents((line == 0).astype(np.uint8), connectivity=4)
ground = (lab == lab[0, 0]).astype(np.uint8)          # the open ground all around the dancers

# the gaps: the ones the five original emotion regions sat in
gaps = np.zeros_like(line)
spots = []
svg = (ASSETS / 'v2' / 'emo_fill.svg').read_text()
for m in re.finditer(r'<path id="(Blob \d)" d="([^"]*)"[^>]*fill="(#\w+)"', svg):
    mask = np.zeros_like(line)
    cv2.fillPoly(mask, [p.round().astype(np.int32) for p in subpaths(m.group(2), PAD, PAD)], 1)
    gaps |= (lab == np.bincount(lab[mask > 0]).argmax()).astype(np.uint8)
    ys, xs = np.nonzero(mask)
    spots.append({'id': m.group(1), 'colour': m.group(3).upper(), 'cx': round(float(xs.mean()) - PAD, 1),
                  'cy': round(float(ys.mean()) - PAD, 1), 'r': round(math.sqrt(mask.sum() / math.pi) * 1.9, 1)})

# join neighbouring gaps across the body parts between them: a closing bridges anything narrower than
# BRIDGE, but an arm has open ground right behind it, so the edge stays on the arm's inner line
BRIDGE = 80
blob = cv2.morphologyEx(gaps, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (BRIDGE, BRIDGE)))
blob &= 1 - cv2.dilate(ground, np.ones((3, 3), np.uint8))
# a filled body part stays only if it really joins two gaps; a head (or a dancer standing inside one gap)
# touches a single gap, so it is left empty and the colour flows round it
gap_ids = set(np.unique(lab[gaps > 0]))
added = (blob & (1 - gaps)).astype(np.uint8)
n, al = cv2.connectedComponents(added, connectivity=4)
for i in range(1, n):
    part = (al == i).astype(np.uint8)
    touches = {g for g in np.unique(lab[cv2.dilate(part, np.ones((5, 5), np.uint8)) > 0]) if g in gap_ids}
    if len(touches) < 2:
        blob &= 1 - part
_, blab, stats, _ = cv2.connectedComponentsWithStats(blob, connectivity=4)
blob = (blab == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8)     # the one big piece
blob = (cv2.GaussianBlur(blob.astype(np.float32), (0, 0), 1.2) > .5).astype(np.uint8)
cs, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
c = cv2.approxPolyDP(max(cs, key=cv2.contourArea), .8, True)[:, 0, :] - PAD
d_out = 'M' + 'L'.join(f'{x} {y}' for x, y in c) + 'Z'
(ASSETS / 'v2' / 'emo-blob.json').write_text(json.dumps({'d': d_out, 'spots': spots}, separators=(',', ':')))
print('blob area:', int(cv2.contourArea(c)), 'spots:', [(s['id'], s['r']) for s in spots])
