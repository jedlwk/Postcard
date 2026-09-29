#!/usr/bin/env python3
"""Approval hook for Postcard builds. Used by both Claude Code and Codex.

Claude Code calls it on PreToolUse (it may allow or deny any step).
Codex calls it on PermissionRequest, which only fires when Codex was about to
ask the user, and answers with {"behavior": "allow" | "deny"}.

Silent (no opinion, normal behaviour) unless a Postcard form session
is running AND the tool call comes from the folder that session builds into.
Then:
  - a step on the short safe list, with the page's toggle on -> allow
  - anything else -> an Allow/Deny card on the page; no answer in 5 min -> deny
"""
import json, os, re, shlex, sys, time, uuid

PLUGIN = os.environ.get('PLUGIN_ROOT') or os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PLUGIN, 'skills', 'postcard', 'scripts'))
import tripstate as ts

WAIT = 300
PAGE_FRESH = 20   # seconds; older than this means nobody is looking at the form
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
    if tool == 'apply_patch':           # Codex file edits: every touched path must be in the trips folder
        patch = command_text(inp)
        if re.search(r'^\*\*\* Delete File:', patch, re.M):
            return False
        paths = re.findall(r'^\*\*\* (?:Add|Update) File: (.+)$|^\*\*\* Move to: (.+)$', patch, re.M)
        paths = [a or b for a, b in paths]
        base = sess.get('claude_cwd', out)
        return bool(paths) and all(inside(x if os.path.isabs(x) else os.path.join(base, x), out) for x in paths)
    if tool == 'Bash':
        cmd = command_text(inp)
        if re.fullmatch(r'\s*(open|xdg-open|start)\s+"?http://127\.0\.0\.1:\d+/[^"\s]*"?\s*', cmd):
            return True               # opening our own form
        if re.search(r'\brm\b|\bsudo\b|\bcurl\b.*\|\s*(sh|bash)|>\s*/(?!dev/null)', cmd):
            return False
        env = {}
        for seg in re.split(r'&&|\|\||;|\|', cmd):
            try:
                words = shlex.split(seg)
            except ValueError:
                return False
            while words and re.fullmatch(r'[A-Za-z_]\w*=.*', words[0]):   # VAR=value prefixes
                k, v = words.pop(0).split('=', 1)
                env[k] = v
            words = [re.sub(r'\$\{?(\w+)\}?', lambda m: env.get(m.group(1), m.group(0)), x) for x in words]
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


def command_text(inp):
    """Codex may pass the command as a list of argv parts."""
    c = inp.get('command', '')
    if isinstance(c, list):
        if len(c) >= 3 and c[0] in ('bash', 'sh', 'zsh') and c[1] in ('-lc', '-c'):
            return c[2]
        return shlex.join(str(x) for x in c)
    return str(c)


def describe(tool, inp):
    if tool == 'WebSearch':
        return 'Search the web', inp.get('query', '')
    if tool == 'WebFetch':
        return 'Open a web page', inp.get('url', '')
    if tool == 'Bash':
        return 'Run a command', command_text(inp)[:400]
    if tool == 'apply_patch':
        files = re.findall(r'^\*\*\* (?:Add|Update|Delete) File: (.+)$', command_text(inp), re.M)
        return 'Change files', ', '.join(files)[:400] or 'a file edit'
    if tool in ('Write', 'Edit', 'MultiEdit'):
        return 'Change a file', inp.get('file_path', '')
    return f'Use {tool}', json.dumps(inp)[:300]


CODEX = False   # set in main() from the event name


def decide(decision, reason):
    if CODEX:
        d = {'behavior': decision}
        if decision == 'deny':
            d['message'] = reason
        out = {'hookEventName': 'PermissionRequest', 'decision': d}
    else:
        out = {'hookEventName': 'PreToolUse', 'permissionDecision': decision, 'permissionDecisionReason': reason}
    print(json.dumps({'hookSpecificOutput': out}))
    return 0


def main():
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return 0
    global CODEX
    CODEX = ev.get('hook_event_name') == 'PermissionRequest' or '--codex' in sys.argv
    if not CODEX and 'turn_id' in ev:
        return 0                      # Codex PreToolUse can't approve; Codex uses PermissionRequest instead
    sess = ts.active_session()
    cwd = ev.get('cwd', '')
    if not sess or not (inside(cwd, sess['out_root']) or inside(cwd, sess.get('claude_cwd', sess['out_root']))):
        return 0                      # not a form build: stay out of the way
    tool, inp = ev.get('tool_name', ''), ev.get('tool_input') or {}
    safe = is_safe(tool, inp, sess)
    kind = tool if safe and tool in ('WebSearch', 'WebFetch', 'Write', 'Edit', 'Read', 'apply_patch') else ''
    if safe and (sess.get('auto_approve', True) or kind in sess.get('always_kinds', [])):
        return decide('allow', 'Approved by the trip form')
    try:
        seen = float(open(ts.SEEN).read())
    except (OSError, ValueError):
        seen = 0
    if ts.now() - seen > PAGE_FRESH:
        return 0                      # form not open: let the agent ask as usual
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
