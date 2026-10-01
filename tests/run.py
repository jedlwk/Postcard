#!/usr/bin/env python3
"""Run all Postcard tests:  python3 tests/run.py

Covers the approval hook (Claude and Codex formats), the form server, the
renderer, the guide checker and the calendar file. Uses a throw-away HOME,
so it never touches your real ~/.postcard. Needs Pillow (the plugin installs it).
"""
import warnings
warnings.simplefilter('ignore')
import json, os, subprocess, sys, tempfile, time, unittest, urllib.request, http.client, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, 'skills', 'postcard')
SC = os.path.join(SKILL, 'scripts')
HOOK = os.path.join(ROOT, 'hooks', 'approve.py')
sys.path.insert(0, SC); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_images


def py(*a, env=None, inp=None, timeout=60):
    return subprocess.run([sys.executable, *a], capture_output=True, text=True, env=env, input=inp, timeout=timeout)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='postcard-test-')
        self.home = os.path.join(self.tmp, 'home'); os.makedirs(self.home)
        self.work = os.path.realpath(os.path.join(self.tmp, 'work')); os.makedirs(self.work)
        import site
        self.env = dict(os.environ, HOME=self.home, PLUGIN_ROOT=ROOT, BROWSER='true', PYTHONUSERBASE=site.getuserbase())
        self.env.pop('CLAUDE_PLUGIN_ROOT', None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class HookTests(Base):
    def session(self, **kw):
        d = os.path.join(self.home, '.postcard'); os.makedirs(os.path.join(d, 'approvals'), exist_ok=True)
        s = {'port': 1, 'token': 't', 'pid': os.getpid(), 'active': True, 'auto_approve': True, 'out_root': self.work,
             'claude_cwd': self.work, 'skill_root': SKILL, 'started': time.time()}
        s.update(kw)
        json.dump(s, open(os.path.join(d, 'session.json'), 'w'))
        open(os.path.join(d, 'page_seen'), 'w').write(str(time.time()))

    def hook(self, event, args=()):
        r = py(HOOK, *args, env=self.env, inp=json.dumps(event), timeout=20)
        return json.loads(r.stdout)['hookSpecificOutput'] if r.stdout.strip() else None

    def claude(self, tool, inp):
        return self.hook({'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': inp, 'cwd': self.work})

    def codex(self, tool, inp):
        return self.hook({'hook_event_name': 'PermissionRequest', 'turn_id': 't1', 'tool_name': tool, 'tool_input': inp, 'cwd': self.work}, ['--codex'])

    def test_silent_without_session(self):
        self.assertIsNone(self.claude('WebSearch', {'query': 'x'}))

    def test_silent_in_other_folder(self):
        self.session()
        r = py(HOOK, env=self.env, inp=json.dumps({'hook_event_name': 'PreToolUse', 'tool_name': 'WebSearch', 'tool_input': {}, 'cwd': '/'}))
        self.assertEqual(r.stdout.strip(), '')

    def test_claude_allows_safe_steps(self):
        self.session()
        self.assertEqual(self.claude('WebSearch', {'query': 'x'})['permissionDecision'], 'allow')
        self.assertEqual(self.claude('Write', {'file_path': self.work + '/Kyoto/Kyoto.html'})['permissionDecision'], 'allow')
        cmd = f'SKILL_DIR="{SKILL}"; python3 "$SKILL_DIR/scripts/progress.py" wait'
        self.assertEqual(self.claude('Bash', {'command': cmd})['permissionDecision'], 'allow')

    def test_codex_format_and_argv_commands(self):
        self.session()
        out = self.codex('Bash', {'command': ['bash', '-lc', f'python3 "{SC}/commons.py" --help']})
        self.assertEqual(out['hookEventName'], 'PermissionRequest')
        self.assertEqual(out['decision'], {'behavior': 'allow'})
        patch = '*** Begin Patch\n*** Add File: Kyoto/Kyoto.html\n+hi\n*** End Patch'
        self.assertEqual(self.codex('apply_patch', {'command': patch})['decision']['behavior'], 'allow')

    def test_codex_pretooluse_is_ignored(self):
        self.session()
        r = py(HOOK, env=self.env, inp=json.dumps({'hook_event_name': 'PreToolUse', 'turn_id': 't', 'tool_name': 'Bash', 'tool_input': {'command': 'ls'}, 'cwd': self.work}))
        self.assertEqual(r.stdout.strip(), '')

    def test_unsafe_steps_wait_for_the_page(self):
        self.session()
        for allow in (True, False):
            p = subprocess.Popen([sys.executable, HOOK], env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            p.stdin.write(json.dumps({'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_input': {'command': 'rm -rf x'}, 'cwd': self.work})); p.stdin.close()
            ap = os.path.join(self.home, '.postcard', 'approvals')
            for _ in range(60):
                reqs = [f for f in os.listdir(ap) if f.endswith('.req.json')]
                if reqs:
                    break
                time.sleep(0.2)
            self.assertTrue(reqs, 'no approval request appeared')
            rid = reqs[0][:-9]
            json.dump({'allow': allow}, open(os.path.join(ap, rid + '.res.json'), 'w'))
            out = json.loads(p.stdout.read())['hookSpecificOutput']
            self.assertEqual(out['permissionDecision'], 'allow' if allow else 'deny')
            p.wait(10)

    def test_writes_outside_the_folder_are_not_auto_approved(self):
        self.session()
        os.remove(os.path.join(self.home, '.postcard', 'page_seen'))          # page closed: hook stays out of the way
        self.assertIsNone(self.claude('Write', {'file_path': '/etc/hosts'}))
        self.assertIsNone(self.claude('Bash', {'command': 'rm -rf /'}))


class ServerTests(Base):
    def start(self):
        self.srv = subprocess.Popen([sys.executable, os.path.join(SC, 'serve.py'), 'serve', '--out', self.work, '--cwd', self.work], env=self.env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sf = os.path.join(self.home, '.postcard', 'session.json')
        for _ in range(60):
            if os.path.isfile(sf):
                break
            time.sleep(0.2)
        self.sess = json.load(open(sf)); self.base = f'http://127.0.0.1:{self.sess["port"]}'

    def tearDown(self):
        if getattr(self, 'srv', None):
            self.srv.terminate(); self.srv.wait(10)
        super().tearDown()

    def api(self, path, body=None, token=True, host=None):
        h = {'Content-Type': 'application/json'}
        if token:
            h['X-Token'] = self.sess['token']
        if host:
            h['Host'] = host
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_security(self):
        self.start()
        self.assertEqual(self.api('/')[0], 200)
        self.assertEqual(self.api('/api/state', token=False)[0], 403)
        c = http.client.HTTPConnection('127.0.0.1', self.sess['port']); c.request('GET', '/api/state', headers={'Host': 'evil.example', 'X-Token': self.sess['token']})
        self.assertEqual(c.getresponse().status, 403)

    def test_brief_progress_download_and_cleanup(self):
        self.start()
        png = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
        self.assertEqual(self.api('/api/brief', {'trip': 'test trip', 'name': 'test', 'attachments': [{'name': 'a.png', 'data': png}]})[0], 200)
        self.assertEqual(self.api('/api/brief', {'trip': 'again'})[0], 409)
        brief = json.loads(py(os.path.join(SC, 'progress.py'), 'wait', '--timeout', '5', env=self.env).stdout)
        self.assertTrue(os.path.isfile(brief['attachments'][0]))
        py(os.path.join(SC, 'progress.py'), 'step', '40', 'Finding photos', env=self.env)
        st = json.loads(self.api('/api/state')[1])
        self.assertEqual(st['status']['pct'], 40)
        guide = os.path.join(self.work, 'g.html'); open(guide, 'w').write('<h1>hi</h1>')
        py(os.path.join(SC, 'progress.py'), 'done', guide, env=self.env)
        code, body = self.api('/api/download')
        self.assertEqual((code, body), (200, b'<h1>hi</h1>'))
        self.assertFalse(os.path.isdir(os.path.join(self.home, '.postcard', 'attachments')), 'screenshots should be deleted when done')

    def test_decision_flow_and_toggle(self):
        self.start()
        self.assertEqual(self.api('/api/settings', {'auto_approve': False})[0], 200)
        ap = os.path.join(self.home, '.postcard', 'approvals')
        json.dump({'id': 'abc123', 'kind': 'WebSearch', 'title': 't', 'detail': 'd', 'at': time.time()}, open(os.path.join(ap, 'abc123.req.json'), 'w'))
        st = json.loads(self.api('/api/state')[1])
        self.assertFalse(st['auto_approve']); self.assertEqual(len(st['pending']), 1)
        self.assertEqual(self.api('/api/decision', {'id': 'abc123', 'allow': True, 'always': True})[0], 200)
        self.assertTrue(os.path.isfile(os.path.join(ap, 'abc123.res.json')))
        self.assertIn('WebSearch', json.load(open(os.path.join(self.home, '.postcard', 'session.json')))['always_kinds'])

    def test_resume_lists_unfinished_trips(self):
        os.makedirs(os.path.join(self.work, 'Trip'))
        json.dump({'title': 'Trip', 'stage': 'researched'}, open(os.path.join(self.work, 'Trip', 'plan.json'), 'w'))
        out = py(os.path.join(SC, 'progress.py'), 'resume', '--out', self.work, env=self.env).stdout
        self.assertIn('stage=researched', out); self.assertIn('not built yet', out)


class RenderTests(Base):
    def setUp(self):
        super().setUp()
        self.trip = os.path.join(self.tmp, 'trip'); os.makedirs(self.trip)
        make_images.make(os.path.join(self.trip, 'photos'))
        self.plan_path = os.path.join(self.trip, 'plan.json')
        shutil.copy(os.path.join(ROOT, 'tests', 'samples', 'sample-plan.json'), self.plan_path)
        self.plan = json.load(open(self.plan_path))

    def write(self, plan):
        json.dump(plan, open(self.plan_path, 'w'))

    def render(self):
        return py(os.path.join(SC, 'render_guide.py'), self.plan_path, env=self.env)

    def validate(self):
        return py(os.path.join(SC, 'validate_guide.py'), os.path.join(self.trip, 'Sample guide.html'), '--plan', self.plan_path, env=self.env)

    def test_render_and_validate_pass(self):
        r = self.render(); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        v = self.validate(); self.assertEqual(v.returncode, 0, v.stdout)
        page = open(os.path.join(self.trip, 'Sample guide.html')).read()
        self.assertIn('Fri 8 Oct', page)            # weekday computed from the date
        self.assertIn('Not fully fact-checked', page)
        self.assertNotIn('<script', page)

    def test_calendar_file(self):
        self.render()
        ics = open(os.path.join(self.trip, 'Sample guide.ics')).read()
        self.assertEqual(ics.count('BEGIN:VEVENT'), 5 + 1 + 1)     # 5 days, 1 flight, 1 dated book_check
        self.assertIn('DTSTART;VALUE=DATE:20270415', ics)

    def test_check_catches_bad_plans(self):
        p = json.loads(json.dumps(self.plan)); p['stops'][0]['photos'][0]['file'] = 'photos/missing.jpg'; self.write(p)
        r = py(os.path.join(SC, 'render_guide.py'), self.plan_path, '--check', env=self.env)
        self.assertEqual(r.returncode, 1); self.assertIn('not found', r.stdout)
        p = json.loads(json.dumps(self.plan)); p['verification'] = {'status': 'verified'}; p['sources'] = []; self.write(p)
        r = py(os.path.join(SC, 'render_guide.py'), self.plan_path, '--check', env=self.env)
        self.assertEqual(r.returncode, 1); self.assertIn('sources is empty', r.stdout)
        p = json.loads(json.dumps(self.plan)); del p['stops'][0]['map']['credit']; self.write(p)
        self.assertEqual(py(os.path.join(SC, 'render_guide.py'), self.plan_path, '--check', env=self.env).returncode, 1)

    def test_validator_catches_broken_guides(self):
        self.render()
        gp = os.path.join(self.trip, 'Sample guide.html'); good = open(gp).read()
        cases = {'dead tab': good.replace('for="t-stop-b"', 'for="t-nowhere"', 1), 'dead link': good.replace('href="#top"', 'href="#missing"', 1),
                 'external image': good.replace('<img src="data:image/jpeg;base64,', '<img src="https://example.com/a.jpg" data-x="', 1),
                 'script': good.replace('</body>', '<script>1</script></body>')}
        for name, bad in cases.items():
            open(gp, 'w').write(bad)
            self.assertEqual(self.validate().returncode, 1, name)
        open(gp, 'w').write(good.replace('Fri 8 Oct', 'Sat 8 Oct', 1))
        self.assertIn('weekday mismatch', self.validate().stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2, warnings='ignore')
