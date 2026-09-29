#!/usr/bin/env python3
"""Report build progress to the trip form.

    python3 progress.py wait                 block until the form sends a brief (prints it)
    python3 progress.py step 30 "Finding photos"
    python3 progress.py done "<path to finished .html>"
    python3 progress.py fail "What went wrong"

`wait` returns after --timeout seconds (default 540) with WAITING and exit code 2,
so it fits inside one Bash call; just run it again.
"""
import json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tripstate as ts


def update(**kw):
    st = ts.read(ts.STATUS, {}) or {}
    log = st.get('log', [])
    if kw.get('stage') and (not log or log[-1]['stage'] != kw['stage']):
        log.append({'stage': kw['stage'], 'at': ts.now()})
    st.update(kw, log=log, updated_at=ts.now())
    st.setdefault('started_at', ts.now())
    ts.write(ts.STATUS, st)


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd = argv[0]
    if cmd == 'wait':
        timeout = int(argv[argv.index('--timeout') + 1]) if '--timeout' in argv else 540
        end = time.time() + timeout
        while time.time() < end:
            b = ts.read(ts.BRIEF)
            if b:
                update(pct=4, stage='Your agent picked up the brief')
                print(json.dumps(b, ensure_ascii=False, indent=1))
                return 0
            if not ts.active_session():
                print('NO_SERVER: the form server is not running')
                return 3
            time.sleep(2)
        print('WAITING')
        return 2
    if cmd == 'step':
        update(pct=max(0, min(99, int(argv[1]))), stage=' '.join(argv[2:]))
    elif cmd == 'done':
        path = os.path.realpath(argv[1])
        if not os.path.isfile(path):
            sys.exit(f'no such file: {path}')
        update(pct=100, stage='Done', done=True, output=path)
    elif cmd == 'fail':
        update(stage='Stopped: ' + ' '.join(argv[1:]), failed=True)
    else:
        sys.exit(__doc__)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
