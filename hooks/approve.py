#!/usr/bin/env python3
"""PreToolUse hook: lets the trip form approve Claude's steps during a build.

Silent (no opinion, normal Claude Code behaviour) unless a trip-form session
is running AND the tool call comes from the folder that session builds into.
Then:
  - a step on the short safe list, with the page's toggle on -> allow
  - anything else -> an Allow/Deny card on the page; no answer in 5 min -> deny
"""
import json, os, re, shlex, sys, time, uuid

PLUGIN = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PLUGIN, 'skills', 'postcard', 'scripts'))
import tripstate as ts

WAIT = 300
READ_ONLY = {'ls', 'cat', 'head', 'tail', 'wc', 'grep', 'file', 'du', 'pwd', 'echo', 'cd', 'mkdir', 'sort', 'uniq', 'cut', 'which'}


def inside(path, root):
    try:
        p = os.path.realpath(os.path.expanduser(path))
    except (TypeError, ValueError):
        return False
    return p == root or p.startswith(root.rstrip('/') + '/')


def is_safe(tool, inp, sess):
    out = sess['out_root']; skill = sess['skill_root']
    if tool in ('WebSearch', 'WebFetch', 'Read', 'Glob', 'Grep'):
        return True
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        return inside(inp.get('file_path') or inp.get('notebook_path') or '', out)
    if tool == 'Bash':
        cmd = inp.get('command', '')
        if re.search(r'\brm\b|\bsudo\b|\bcurl\b.*\|\s*(sh|bash)|>\s*/(?!dev/null)', cmd):
            return False
        for seg in re.split(r'&&|\|\||;|\|', cmd):
            try:
                words = shlex.split(seg)
            except ValueError:
                return False
            if not words:
                continue
            w = words[0]
            if w in READ_ONLY:
                continue
            if w in ('python3', 'python') and len(words) > 1 and inside(words[1], os.path.realpath(skill)):
                continue
            return False
        return True
    return False


def describe(tool, inp):
    if tool == 'WebSearch':
        return 'Search the web', inp.get('query', '')
    if tool == 'WebFetch':
        return 'Open a web page', inp.get('url', '')
    if tool == 'Bash':
        return 'Run a command', inp.get('command', '')[:400]
    if tool in ('Write', 'Edit', 'MultiEdit'):
        return 'Change a file', inp.get('file_path', '')
    return f'Use {tool}', json.dumps(inp)[:300]


def decide(decision, reason):
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                                             'permissionDecision': decision,
                                             'permissionDecisionReason': reason}}))
    return 0


def main():
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return 0
    sess = ts.active_session()
    if not sess or not inside(ev.get('cwd', ''), sess['out_root']):
        return 0                      # not a form build: stay out of the way
    tool, inp = ev.get('tool_name', ''), ev.get('tool_input') or {}
    safe = is_safe(tool, inp, sess)
    kind = tool if safe and tool in ('WebSearch', 'WebFetch', 'Write', 'Edit', 'Read') else ''
    if safe and (sess.get('auto_approve', True) or kind in sess.get('always_kinds', [])):
        return decide('allow', 'Approved by the trip form')
    rid = uuid.uuid4().hex[:12]
    title, detail = describe(tool, inp)
    req = os.path.join(ts.APPROVALS, rid + '.req.json')
    res = os.path.join(ts.APPROVALS, rid + '.res.json')
    ts.write(req, {'id': rid, 'tool': tool, 'kind': kind, 'safe': safe, 'title': title, 'detail': detail, 'at': ts.now()})
    end = time.time() + WAIT
    while time.time() < end:
        r = ts.read(res)
        if r is not None:
            for p in (req, res):
                try: os.remove(p)
                except OSError: pass
            return decide('allow' if r.get('allow') else 'deny',
                          'Approved on the trip form' if r.get('allow') else 'Declined on the trip form')
        if not ts.active_session():
            break
        time.sleep(1)
    try: os.remove(req)
    except OSError: pass
    return decide('deny', 'No answer on the trip form within 5 minutes; skipped')


if __name__ == '__main__':
    sys.exit(main())
