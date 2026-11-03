"""The areas a dragged emotion colour can snap into on the decorate board: the same five gaps inside the
ring of dancers that the Emotion infographic fills (never the dancers' bodies).

The gaps are found exactly as fit_emotion.py finds them: each of the five original Figma emotion blobs sat
in one gap the outline closes off, and Visible Smile and Curiosity share the big centre gap, split where
the two blobs met. Here each area is kept only a few px inside the line, so a dropped colour fills it.

Writes ../assets/v2/deco-regions.json: [{"id", "cx", "cy", "area", "pts": [[x, y], ...]}] in artboard px.
Run: /tmp/claude-501/venv/bin/python fit_regions.py
"""
import json
import re
from pathlib import Path
import cv2
import numpy as np
from svgpath import subpaths

ASSETS = Path(__file__).parent.parent / 'assets'
W, H = 1512, 982
DANCERS_AT = (222, 247)
EMO_AT = (244, 255)
INSET = 5          # px between a fill's edge and the line (the outline squirms by under 2px)

d = re.search(r' d="([^"]*)"', (ASSETS / 'v2' / 'dancers.svg').read_text()).group(1)
line = np.zeros((H, W), np.uint8)
for s in subpaths(d, *DANCERS_AT):
    cv2.polylines(line, [s.round().astype(np.int32)], True, 255, 4)
_, lab = cv2.connectedComponents((line == 0).astype(np.uint8), connectivity=4)

blobs = []
for m in re.finditer(r'<path id="(Blob \d)" d="([^"]*)"', (ASSETS / 'emo_fill.svg').read_text()):
    mask = np.zeros((H, W), np.uint8)
    cv2.fillPoly(mask, [p.round().astype(np.int32) for p in subpaths(m.group(2), *EMO_AT)], 1)
    blobs.append(dict(mask=mask, hole=np.bincount(lab[mask > 0]).argmax(),
                      dist=cv2.distanceTransform((1 - mask).astype(np.uint8), cv2.DIST_L2, 5)))

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * INSET + 1, 2 * INSET + 1))
regions = []
for b in blobs:
    region = lab == b['hole']
    for o in blobs:
        if o is not b and o['hole'] == b['hole']:
            region &= b['dist'] <= o['dist']
    region = cv2.erode(region.astype(np.uint8), kernel)
    region = (cv2.GaussianBlur(region.astype(np.float32), (0, 0), 2.5) > .5).astype(np.uint8)
    cs, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = cv2.approxPolyDP(max(cs, key=cv2.contourArea), 1.0, True)[:, 0, :]
    M = cv2.moments(c)
    regions.append({'cx': round(M['m10'] / M['m00'], 1), 'cy': round(M['m01'] / M['m00'], 1),
                    'area': int(cv2.contourArea(c)), 'pts': c.tolist()})

for i, r in enumerate(regions):
    r['id'] = f'r{i}'
(ASSETS / 'v2' / 'deco-regions.json').write_text(json.dumps(regions, separators=(',', ':')))
print(len(regions), 'areas:', [r['area'] for r in regions])
