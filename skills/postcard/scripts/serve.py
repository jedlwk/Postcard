#!/usr/bin/env python3
"""Local server for the trip form. Stdlib only.

    python3 serve.py start [--out <folder for trips>]   opens the form, returns at once
    python3 serve.py stop

It serves app/trip-form.html, takes the brief, reports Claude's progress,
relays approval requests from the hook, and serves the finished file.
Binds to 127.0.0.1 only, checks the Host header, and every API call needs
the per-session token that is only in the URL Claude opens.
"""
import argparse, json, os, secrets, shutil, signal, socket, subprocess, sys, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tripstate as ts

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'trip-form.html')
MAX_LIFE = 8 * 3600          # a build never needs longer than this
STALE_AFTER = 20 * 60        # no progress for this long: tell the page


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class Handler(BaseHTTPRequestHandler):
    server_version = 'trip-form'

    def log_message(self, *a):
        pass

    # ---------------------------------------------------------------- helpers
    def _host_ok(self):
        host = (self.headers.get('Host') or '').split(':')[0]
        return host in ('127.0.0.1', 'localhost')

    def _token_ok(self, q):
        tok = self.headers.get('X-Token') or (q.get('token') or [''])[0]
        return secrets.compare_digest(tok, self.server.session['token'])

    def _send(self, code, body, ctype='application/json'):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get('Content-Length') or 0)
        if n > 40_000_000:
            raise ValueError('too large')
        return json.loads(self.rfile.read(n) or b'{}')

    # ---------------------------------------------------------------- routes
    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {'error': 'host'})
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path in ('/', '/index.html'):
            with open(APP, 'rb') as f:
                return self._send(200, f.read(), 'text/html; charset=utf-8')
        if not self._token_ok(q):
            return self._send(403, {'error': 'token'})
        if u.path == '/api/state':
            with open(ts.SEEN, 'w') as f:
                f.write(str(ts.now()))
            return self._send(200, state())
        if u.path == '/api/download':
            st = ts.read(ts.STATUS, {}) or {}
            path = st.get('output')
            if not path or not os.path.isfile(path):
                return self._send(404, {'error': 'not ready'})
            with open(path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(path)}"')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        return self._send(404, {'error': 'no route'})

    def do_POST(self):
        if not self._host_ok():
            return self._send(403, {'error': 'host'})
        u = urlparse(self.path)
        if not self._token_ok(parse_qs(u.query)):
            return self._send(403, {'error': 'token'})
        try:
            body = self._body()
        except ValueError:
            return self._send(400, {'error': 'bad body'})
        sess = self.server.session
        if u.path == '/api/brief':
            if ts.read(ts.BRIEF):
                return self._send(409, {'error': 'A brief was already sent for this session.'})
            body['attachments'] = save_attachments(body.get('attachments') or [])
            body['received_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            ts.write(ts.BRIEF, body)
            ts.write(ts.STATUS, {'pct': 2, 'stage': 'Brief received. Waiting for your agent to start.',
                                 'log': [], 'updated_at': ts.now()})
            return self._send(200, {'ok': True})
        if u.path == '/api/settings':
            sess['auto_approve'] = bool(body.get('auto_approve'))
            ts.write(ts.SESSION, sess)
            return self._send(200, {'ok': True, 'auto_approve': sess['auto_approve']})
        if u.path == '/api/decision':
            rid = ''.join(c for c in str(body.get('id', '')) if c.isalnum())
            if not rid or not os.path.exists(os.path.join(ts.APPROVALS, rid + '.req.json')):
                return self._send(404, {'error': 'no such request'})
            req = ts.read(os.path.join(ts.APPROVALS, rid + '.req.json'), {}) or {}
            if body.get('allow') and body.get('always') and req.get('kind'):
                kinds = set(sess.get('always_kinds', [])); kinds.add(req['kind'])
                sess['always_kinds'] = sorted(kinds); ts.write(ts.SESSION, sess)
            ts.write(os.path.join(ts.APPROVALS, rid + '.res.json'), {'allow': bool(body.get('allow'))})
            return self._send(200, {'ok': True})
        return self._send(404, {'error': 'no route'})


def save_attachments(items):
    """Screenshots arrive as data URLs; write them out so Claude can Read them."""
    import base64, re
    folder = os.path.join(ts.HOME, 'attachments'); os.makedirs(folder, exist_ok=True)
    paths = []
    for i, it in enumerate(items[:8], 1):
        m = re.match(r'data:image/(png|jpe?g|webp|gif);base64,(.+)', str((it or {}).get('data', '')), re.S)
        if not m:
            continue
        path = os.path.join(folder, f'screenshot-{i}.{m.group(1).replace("jpeg", "jpg")}')
        with open(path, 'wb') as f:
            f.write(base64.b64decode(m.group(2)))
        paths.append(path)
    return paths


def state():
    sess = ts.read(ts.SESSION, {}) or {}
    st = ts.read(ts.STATUS) or {}
    pending = []
    for name in sorted(os.listdir(ts.APPROVALS)):
        if name.endswith('.req.json'):
            rid = name[:-9]
            if not os.path.exists(os.path.join(ts.APPROVALS, rid + '.res.json')):
                r = ts.read(os.path.join(ts.APPROVALS, name))
                if r:
                    pending.append(r)
    stale = bool(st) and not st.get('done') and not pending and ts.now() - st.get('updated_at', ts.now()) > STALE_AFTER
    brief = ts.read(ts.BRIEF) or {}
    return {'auto_approve': sess.get('auto_approve', True), 'brief_sent': bool(brief), 'trip_name': brief.get('name', ''), 'est_minutes': brief.get('est_minutes'),
            'always_kinds': sess.get('always_kinds', []),
            'status': st, 'pending': pending, 'stale': stale, 'server_time': ts.now()}


def default_out(cwd):
    """Save next to the user's work, unless Claude was started with no real folder."""
    c = os.path.realpath(cwd)
    if 'scratch-workspaces' in c or c.startswith(('/tmp', '/private/tmp', '/var/folders')) or c == os.path.expanduser('~'):
        return os.path.expanduser('~/Postcard')
    return c


def launch(out):
    """Start the server detached, open the form, print the link, return at once."""
    ts.ensure()
    ts.ensure_pillow()
    old = ts.active_session()
    if old:
        url = f'http://127.0.0.1:{old["port"]}/#t={old["token"]}'
    else:
        os.makedirs(out, exist_ok=True)
        log = open(os.path.join(ts.HOME, 'server.log'), 'w')
        subprocess.Popen([sys.executable, os.path.abspath(__file__), 'serve', '--out', out, '--cwd', os.getcwd()],
                         stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
        url = None
        for _ in range(100):
            time.sleep(0.1)
            s = ts.active_session()
            if s and s.get('started', 0) > time.time() - 30:
                url = f'http://127.0.0.1:{s["port"]}/#t={s["token"]}'
                break
        if not url:
            sys.exit('The form server did not start. See ~/.postcard/server.log')
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass
    print(f'Form opened in your browser. If it did not appear, open: {url}')
    print(f'Guides will be saved in: {out}')


def serve(out, cwd):
    ts.ensure()
    shutil.rmtree(os.path.join(ts.HOME, 'attachments'), ignore_errors=True)
    for p in (ts.BRIEF, ts.STATUS, ts.SEEN):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(ts.APPROVALS, ignore_errors=True); ts.ensure()
    port = free_port()
    sess = {'port': port, 'token': secrets.token_urlsafe(18), 'pid': os.getpid(), 'active': True,
            'auto_approve': True, 'out_root': os.path.realpath(out), 'claude_cwd': os.path.realpath(cwd),
            'skill_root': os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'started': ts.now()}
    srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    srv.session = sess
    srv.timeout = 1
    ts.write(ts.SESSION, sess)

    def shutdown(*_):
        sess['active'] = False
        ts.write(ts.SESSION, sess)
        ts.clear_attachments()
        sys.exit(0)
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    while ts.now() - sess['started'] < MAX_LIFE:
        srv.handle_request()
    shutdown()


def stop():
    s = ts.read(ts.SESSION)
    ts.clear_attachments()
    if s and ts.pid_alive(s.get('pid')):
        os.kill(int(s['pid']), signal.SIGTERM)
        print('stopped')
    else:
        print('not running')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('start', help='open the form (returns immediately)')
    a.add_argument('--out', help='folder for trip guides (default: current folder, or ~/Postcard)')
    b = sub.add_parser('serve', help=argparse.SUPPRESS); b.add_argument('--out', required=True); b.add_argument('--cwd', required=True)
    sub.add_parser('stop')
    sub.add_parser('url')
    args = ap.parse_args()
    if args.cmd == 'start':
        launch(os.path.realpath(os.path.expanduser(args.out)) if args.out else default_out(os.getcwd()))
    elif args.cmd == 'serve':
        serve(args.out, args.cwd)
    elif args.cmd == 'stop':
        stop()
    else:
        s = ts.active_session()
        print(f'http://127.0.0.1:{s["port"]}/#t={s["token"]}' if s else 'not running')
