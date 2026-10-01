#!/usr/bin/env python3
"""Check a finished guide. Exit code 1 if anything is wrong.

    validate_guide.py guide.html [--plan plan.json]

Checks: structure (nesting), every tab has a radio and a panel, every in-page
link resolves, images decode, weekday + date pairs agree, file size, banned
phrases and dash punctuation in the visible text, placeholder text, credits
on photos and maps, and (with --plan) that verification and sources are honest.
Errors fail the run. Warnings are things to look at.
"""
import argparse, base64, collections, datetime as dt, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BANNED = ['genuinely', 'leverage', 'seamless', 'delve', 'tapestry', 'testament', 'robust', 'pivotal', 'transformative', 'unlock', 'it is worth noting',
          "it's worth noting", 'single most', 'hidden gem', 'must-visit destination']
MONTHS = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}
WD = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}


def visible_text(doc):
    doc = re.sub(r'<style.*?</style>', ' ', doc, flags=re.S)
    doc = re.sub(r'data:[^"\')]+', '', doc)
    doc = re.sub(r'<[^>]+>', ' ', doc)
    return html.unescape(re.sub(r'\s+', ' ', doc))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('html'); ap.add_argument('--plan')
    a = ap.parse_args()
    doc = open(a.html, encoding='utf-8').read()
    errs, warns = [], []

    # structure
    try:
        import htmltool
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            n = htmltool.check(a.html)
        if n:
            errs.append('structure check failed:\n    ' + buf.getvalue().strip().replace('\n', '\n    '))
    except Exception as e:  # pragma: no cover
        warns.append(f'could not run the structure check: {e}')

    # tabs
    radios = re.findall(r'<input type="radio" name="tab" class="tabradio" id="(t-[^"]+)"', doc)
    labels = set(re.findall(r'<label for="(t-[^"]+)"', doc))
    panels = re.findall(r'<section class="panel" id="p-([^"]+)"', doc)
    if not radios:
        errs.append('no tab radios found')
    for r in radios:
        if 'p-' + r[2:] not in ['p-' + p for p in panels]:
            errs.append(f'tab {r} has no panel')
    for l in labels - set(radios):
        errs.append(f'a label points at {l}, which is not a tab')
    if len(radios) != len(panels):
        errs.append(f'{len(radios)} tab radios but {len(panels)} panels')
    if 'id="p-overview"' not in doc:
        errs.append('no Overview panel')

    # in-page links
    ids = collections.Counter(re.findall(r'\sid="([^"]+)"', doc))
    for k, v in ids.items():
        if v > 1:
            errs.append(f'duplicate id "{k}"')
    for h in set(re.findall(r'href="#([^"]+)"', doc)):
        if h not in ids:
            errs.append(f'link to #{h} has no target')

    # images
    imgs = re.findall(r'<img src="([^"]*)"', doc)
    bad = 0
    for src in imgs:
        if not src.startswith('data:image/'):
            errs.append('external image (the file must be self-contained): ' + src[:60]); continue
        try:
            raw = base64.b64decode(src.split(',', 1)[1], validate=False)
            if len(raw) < 2000:
                bad += 1
        except Exception:
            bad += 1
    if bad:
        errs.append(f'{bad} image(s) are empty or undecodable')
    if re.search(r'(src|href)="https?://[^"]+\.(woff2?|css|js)"', doc) or '<script' in doc:
        errs.append('external fonts/styles/scripts or a <script> tag found')
    for fig in re.findall(r'<figure class="route-map".*?</figure>', doc, re.S):
        if 'map-credit' not in fig:
            errs.append('a map has no credit')
    for slide in re.findall(r'<div class="gallery-slide">.*?</div></div>', doc, re.S):
        if 'gc-credit"></span>' in slide:
            errs.append('a photo has an empty credit')
    size = len(doc.encode()) / 1e6
    if size > 14:
        errs.append(f'file is {size:.1f} MB; over about 12 MB is painful to open')
    elif size > 11:
        warns.append(f'file is {size:.1f} MB')

    text = visible_text(doc)
    low = text.lower()

    # placeholders and phrases
    for ph in ('lorem ipsum', 'todo', 'tbd', 'xxx', '[insert', 'placeholder'):
        if re.search(r'\b' + re.escape(ph), low) and 'test data' not in low:
            errs.append(f'placeholder text: "{ph}"')
    for b in BANNED:
        if b in low:
            warns.append(f'phrase to cut: "{b}"')
    dashes = len(re.findall(r'\u2014|\s\u2013\s|\s-\s|--', text))
    if dashes:
        warns.append(f'{dashes} em/en dash(es) in the visible text (use full stops, commas or colons)')

    # weekday + date
    title_year = re.search(r'\b(20\d\d)\b', text)
    year = int(title_year.group(1)) if title_year else None
    if a.plan and os.path.isfile(a.plan):
        try:
            year = int(json.load(open(a.plan))['start'][:4])
        except Exception:
            pass
    if year:
        pats = [r'\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\.?,?\s+(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b',
                r'\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\.?,?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})\b']
        seen = set()
        for pi, pat in enumerate(pats):
            for m in re.finditer(pat, text):
                before, after = text[max(0, m.start() - 2):m.start()], text[m.end():m.end() + 3]
                if re.search(r'[\u2013-]\s*$', before) or re.match(r'\s*[\u2013-]\s*\d', after):
                    continue                      # part of a range such as Fri-Sun, Oct 8-10
                wd, x, y = m.group(1), m.group(2), m.group(3)
                day, mon = (int(x), y) if pi == 0 else (int(y), x)
                try:
                    d = dt.date(year, MONTHS[mon[:3].lower()], day)
                except ValueError:
                    continue
                if d.weekday() != WD[wd[:3].lower()] and m.group(0) not in seen:
                    seen.add(m.group(0))
                    warns.append(f'weekday mismatch for {year}: "{m.group(0)}" is a {d.strftime("%A")}. Ignore if it is a past year')

    # plan honesty
    if a.plan and os.path.isfile(a.plan):
        plan = json.load(open(a.plan))
        v = plan.get('verification') or {}
        banner = 'Not fully fact-checked' in doc
        if v.get('status') == 'verified' and banner:
            errs.append('plan says verified but the page shows the not-fact-checked banner')
        if v.get('status') != 'verified' and not banner:
            errs.append('guide is not verified but has no banner')
        if v.get('status') == 'verified' and len(plan.get('sources') or []) < 5:
            warns.append('verified, but fewer than 5 sources listed')
        n_days = sum(len(s.get('days', [])) for s in plan.get('stops', []))
        shown = doc.count('class="day-item"')
        if n_days and shown != n_days:
            errs.append(f'plan has {n_days} days but the page shows {shown}')

    for w in warns:
        print('warning:', w)
    for e in errs:
        print('ERROR:', e)
    print(f'\n{len(imgs)} images, {len(radios)} tabs, {size:.1f} MB')
    print('PASS' if not errs else f'FAIL ({len(errs)} error(s))')
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
