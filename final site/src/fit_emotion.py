"""Re-fit the five emotion colour regions to the new line drawing of the dancers.

Each region fills one of the gaps the outline encloses (the same gaps the original Figma
blobs sat in), kept a little way off the line. The big centre gap is shared by Visible Smile
and Curiosity, split where the original two blobs met.
Run: /tmp/claude-501/venv/bin/python fit_emotion.py  ->  ../assets/v2/emo_fill.svg
"""
import re
from pathlib import Path
import cv2
import numpy as np
from svgpath import subpaths

ASSETS = Path(__file__).parent.parent / 'assets'
W, H = 1512, 982
DANCERS_AT = (222, 247)      # where the outline sits on the artboard
EMO_AT = (244, 255)          # where #emo-fill sits on the artboard (unchanged)
INSET = 15                   # px between a region's edge and the line (the 20px blob stroke adds 10 back)

d = re.search(r' d="([^"]*)"', (ASSETS / 'v2' / 'dancers.svg').read_text()).group(1)
line = np.zeros((H, W), np.uint8)
for s in subpaths(d, *DANCERS_AT):
    cv2.polylines(line, [s.round().astype(np.int32)], True, 255, 4)
n, lab, stats, _ = cv2.connectedComponentsWithStats((line == 0).astype(np.uint8), connectivity=4)

old = (ASSETS / 'emo_fill.svg').read_text()
blobs = []
for m in re.finditer(r'<path id="(Blob \d)" d="([^"]*)"[^>]*fill="(#\w+)"', old):
    mask = np.zeros((H, W), np.uint8)
    cv2.fillPoly(mask, [p.round().astype(np.int32) for p in subpaths(m.group(2), *EMO_AT)], 1)
    hole = np.bincount(lab[mask > 0]).argmax()          # the gap this blob sat in
    blobs.append(dict(id=m.group(1), fill=m.group(3), mask=mask, hole=hole))

# blobs sharing a gap split it by whichever original blob is nearer
for b in blobs:
    b['dist'] = cv2.distanceTransform((1 - b['mask']).astype(np.uint8), cv2.DIST_L2, 5)
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * INSET + 1, 2 * INSET + 1))
paths = []
for b in blobs:
    region = (lab == b['hole'])
    for o in blobs:
        if o is not b and o['hole'] == b['hole']:
            region &= b['dist'] <= o['dist']
    region = cv2.erode(region.astype(np.uint8), kernel)
    region = cv2.GaussianBlur(region.astype(np.float32), (0, 0), 6) > .5   # round off corners
    cs, _ = cv2.findContours(region.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, 1.2, True)[:, 0, :] - np.array(EMO_AT)
    pts = 'L'.join(f'{x} {y}' for x, y in c)
    paths.append(f'<path id="{b["id"]}" d="M{pts}Z" fill-rule="evenodd" clip-rule="evenodd" fill="{b["fill"]}" '
                 f'stroke-width="20" stroke-linejoin="round" stroke="{b["fill"]}"/>')
    print(b['id'], b['fill'], 'gap', b['hole'], 'area', int(cv2.contourArea(c)))

(ASSETS / 'v2' / 'emo_fill.svg').write_text(
    '<svg width="1067" height="572" viewBox="0 0 1067 572" fill="none" xmlns="http://www.w3.org/2000/svg">\n'
    '<g id="Interior fill">\n' + '\n'.join(paths) + '\n</g>\n</svg>\n')
