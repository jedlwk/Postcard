#!/usr/bin/env python3
"""Grade a finished guide against an eval.

    python3 tests/grade.py <guide.html> tests/evals/rockies-6d.json [--plan plan.json]

Each eval holds a brief to give the agent and what the result must satisfy.
Run it by feeding the brief to Postcard (any model), then grading the output.
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'skills', 'postcard', 'scripts'))
from validate_guide import visible_text


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    guide, ev = a[0], json.load(open(a[1]))
    plan = a[a.index('--plan') + 1] if '--plan' in a else None
    cmd = [sys.executable, os.path.join(ROOT, 'skills', 'postcard', 'scripts', 'validate_guide.py'), guide] + (['--plan', plan] if plan else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    doc = open(guide, encoding='utf-8').read()
    text = visible_text(doc).lower()
    ex = ev['expect']; fails = []
    if r.returncode:
        fails.append('validate_guide failed:\n' + r.stdout)
    tabs = len(re.findall(r'class="tabradio"', doc)); days = doc.count('class="day-item"')
    if tabs < ex.get('min_tabs', 0):
        fails.append(f'{tabs} tabs, wanted at least {ex["min_tabs"]}')
    if not ex.get('min_days', 0) <= days <= ex.get('max_days', 99):
        fails.append(f'{days} days, wanted {ex.get("min_days", 0)} to {ex.get("max_days", 99)}')
    for w in ex.get('must_mention', []):
        if w.lower() not in text:
            fails.append(f'never mentions "{w}"')
    for w in ex.get('must_not_mention', []):
        if w.lower() in text:
            fails.append(f'mentions "{w}"')
    if len(doc.encode()) / 1e6 > ex.get('max_mb', 12):
        fails.append('file too large')
    if ex.get('verified') and 'Not fully fact-checked' in doc:
        fails.append('expected a verified guide')
    for f in fails:
        print('FAIL:', f)
    print(f'{ev["name"]}: ' + ('PASS' if not fails else f'{len(fails)} problem(s)'))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
