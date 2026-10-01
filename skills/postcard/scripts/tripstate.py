"""Shared state for the trip form: where files live and how to read/write them.

Everything sits in ~/.postcard/ so the server, the hook and Claude's
progress calls all agree without passing paths around. One build at a time.
"""
import json, os, subprocess, sys, time

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


def clear_attachments():
    """Booking screenshots can hold passport or booking numbers. Delete them when done."""
    import shutil
    shutil.rmtree(os.path.join(HOME, 'attachments'), ignore_errors=True)


def now():
    return time.time()


def ensure_pillow():
    """Photos need Pillow; install it once, quietly, so users never have to."""
    try:
        import PIL  # noqa: F401
        return
    except ImportError:
        pass
    import subprocess
    print('Installing Pillow for photo processing (one time)...', flush=True)
    for extra in ([], ['--user'], ['--break-system-packages', '--user']):
        r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'pillow', *extra], capture_output=True)
        if r.returncode == 0:
            return
    print('Could not install Pillow automatically. Run: python3 -m pip install pillow', flush=True)
