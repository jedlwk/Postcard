"""Shared state for the trip form: where files live and how to read/write them.

Everything sits in ~/.postcard/ so the server, the hook and Claude's
progress calls all agree without passing paths around. One build at a time.
"""
import json, os, time

HOME = os.path.expanduser('~/.postcard')
SESSION = os.path.join(HOME, 'session.json')
BRIEF = os.path.join(HOME, 'brief.json')
STATUS = os.path.join(HOME, 'status.json')
APPROVALS = os.path.join(HOME, 'approvals')
SEEN = os.path.join(HOME, 'page_seen')   # touched each time the form polls


def ensure():
    os.makedirs(APPROVALS, exist_ok=True)


def read(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write(path, data):
    """Atomic write, so a reader never sees half a file."""
    ensure()
    tmp = f'{path}.{os.getpid()}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def active_session():
    """The running session, or None if no server is up."""
    s = read(SESSION)
    if s and s.get('active') and pid_alive(s.get('pid')):
        return s
    return None


def now():
    return time.time()
