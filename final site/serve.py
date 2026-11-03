"""Serve the Circle Dance site, plus the shared gallery for "decorate your own Circle Dance".

    python3 serve.py              # http://localhost:5179
    python3 serve.py --port 8000
    python3 serve.py --host 0.0.0.0   # let other devices on the same network open it too

Everything is a normal static file, except:
    GET    /api/gallery       ->  JSON list of captures, newest first: [{"id", "time", "name", "url"}]
    POST   /api/gallery       ->  body is one PNG (Content-Type: image/png), the maker's name in the
                                  X-Name header (URI-encoded); saved into ./gallery/. The reply carries a
                                  one-off delete key that only the uploading browser keeps.
    DELETE /api/gallery/<id>  ->  needs that key in the X-Delete-Token header

Without this server (e.g. on static hosting) the page keeps captures in the visitor's own browser instead.
"""
import argparse
import hashlib
import hmac
import json
import re
import secrets
import time
import unicodedata
from urllib.parse import unquote
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = Path(__file__).parent
GALLERY = SITE / 'gallery'
MAX_BYTES = 12 * 1024 * 1024
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
ID_RE = re.compile(r'^\d{10,16}-[0-9a-f]{6}$')


def clean_name(raw):
    """Plain text only: no control characters, single spaces, at most 40 characters."""
    name = unquote(raw or '', errors='replace')
    name = ''.join(ch for ch in name if unicodedata.category(ch)[0] != 'C')
    return ' '.join(name.split())[:40]


def meta(stem):
    try:
        return json.loads((GALLERY / f'{stem}.json').read_text())
    except (OSError, ValueError):
        return {}


class Handler(SimpleHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split('?')[0] != '/api/gallery':
            return super().do_GET()
        items = []
        for f in sorted(GALLERY.glob('*.png'), reverse=True):     # names start with the time, so this is newest first
            items.append({'id': f.stem, 'time': int(f.stem.split('-')[0]), 'name': meta(f.stem).get('name', ''),
                          'url': f'gallery/{f.name}'})
        self._json(200, items)

    def do_POST(self):
        if self.path.split('?')[0] != '/api/gallery':
            return self._json(404, {'error': 'not found'})
        length = int(self.headers.get('Content-Length') or 0)
        if not 0 < length <= MAX_BYTES:
            return self._json(413, {'error': 'image too large'})
        data = self.rfile.read(length)
        if self.headers.get('Content-Type') != 'image/png' or not data.startswith(PNG_SIGNATURE):
            return self._json(415, {'error': 'expected a PNG'})
        GALLERY.mkdir(exist_ok=True)
        now = int(time.time() * 1000)
        name = f'{now}-{secrets.token_hex(3)}'
        maker = clean_name(self.headers.get('X-Name'))
        token = secrets.token_urlsafe(18)
        (GALLERY / f'{name}.png').write_bytes(data)
        (GALLERY / f'{name}.json').write_text(json.dumps(
            {'name': maker, 'time': now, 'token_sha256': hashlib.sha256(token.encode()).hexdigest()}))
        self._json(201, {'id': name, 'time': now, 'name': maker, 'url': f'gallery/{name}.png', 'token': token})

    def do_DELETE(self):
        m = re.fullmatch(r'/api/gallery/([^/?]+)', self.path.split('?')[0])
        if not m or not ID_RE.match(m.group(1)):
            return self._json(404, {'error': 'not found'})
        stem = m.group(1)
        png = GALLERY / f'{stem}.png'
        if not png.exists():
            return self._json(404, {'error': 'not found'})
        want = meta(stem).get('token_sha256')
        got = hashlib.sha256((self.headers.get('X-Delete-Token') or '').encode()).hexdigest()
        if not want or not hmac.compare_digest(want, got):
            return self._json(403, {'error': 'only the person who made this capture can delete it'})
        png.unlink()
        (GALLERY / f'{stem}.json').unlink(missing_ok=True)
        self._json(200, {'deleted': stem})


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=5179)
    args = ap.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(SITE)))
    print(f'Circle Dance on http://{"localhost" if args.host == "127.0.0.1" else args.host}:{args.port}')
    server.serve_forever()
