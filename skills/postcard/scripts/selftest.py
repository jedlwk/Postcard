#!/usr/bin/env python3
"""Self-test for the toolchain. Run it after changing anything here.

    python3 scripts/selftest.py            # offline checks only
    python3 scripts/selftest.py --network  # also hits the Commons API

Offline tests cover the pure logic: nesting walks, block replacement, ranking,
encoding, entity handling, exit codes. Network tests confirm the Commons calls
and the two User-Agents still work, which is the part most likely to rot.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import commons                                                     # noqa: E402
import htmltool                                                    # noqa: E402

PASS, FAIL = [], []


def check(name, fn):
    try:
        ok, note = fn()
    except Exception as e:
        ok, note = False, f'{type(e).__name__}: {e}'
    (PASS if ok else FAIL).append(name)
    print(f'{"PASS" if ok else "FAIL"}  {name}' + (f'  [{note}]' if note else ''))


def run(*args):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True)


def stub(score=0, **kw):
    row = {'title': 'x.jpg', 'w': 2000, 'h': 1333, 'mo': 7, 'yr': '2020',
           'desc': '', 'cats': [], 'lic': 'CC BY-SA 4.0', 'thumb': None, 'url': None}
    row.update(kw)
    return row


# ----------------------------------------------------------------- offline

def t_find_close():
    s = '<div class="a"><div><div></div></div></div>TAIL'
    return htmltool.find_close(s, 0) == s.index('TAIL'), 'walks depth'


def t_replace_block():
    s = 'BEFORE<div class="x"><div>deep</div></div>AFTER'
    out = htmltool.replace_block(s, s.index('<div class="x"'), '<div class="x">NEW</div>')
    return out == 'BEFORE<div class="x">NEW</div>AFTER', None


def t_unbalanced_raises():
    try:
        htmltool.find_close('<div><div></div>', 0)
        return False, 'should have raised'
    except ValueError:
        return True, None


def t_rank_portrait_and_banner():
    rows = [stub(title='portrait.jpg', w=1200, h=1600),
            stub(title='banner.jpg', w=4000, h=400),
            stub(title='small.jpg', w=600, h=400),
            stub(title='good.jpg', w=2000, h=1333)]
    out = commons.usable(rows)
    return [r['title'] for r in out] == ['good.jpg'], 'drops portrait/banner/small'


def t_rank_uses_categories():
    """The whole point: score bare filenames via their own categories."""
    rows = [stub(title='IMG_4821.jpg', cats=['Great Buddha Hall']),
            stub(title='DSC_0001.jpg', cats=['Interior of somewhere'])]
    out = commons.usable(rows, prefer=['great buddha hall'])
    return out[0]['title'] == 'IMG_4821.jpg' and out[0]['score'] == 1, 'category match wins'


def t_rank_avoid_and_season():
    rows = [stub(title='a.jpg', mo=1, cats=['Torii']),
            stub(title='b.jpg', mo=7, cats=['Torii']),
            stub(title='c.jpg', mo=7, cats=['Torii', 'Interior'])]
    out = commons.usable(rows, months=[6, 7, 8], prefer=['torii'], avoid=['interior'])
    return [r['title'] for r in out] == ['b.jpg', 'a.jpg', 'c.jpg'], 'subject > season > size'


def t_boilerplate_stripped():
    noise = ['CC-BY-SA-4.0', 'Photographs taken on 2019-04-01', 'Self-published work',
             'Media lacking a description', 'Taken with Nikon D750']
    return all(commons.BOILERPLATE.match(c) for c in noise), 'licence/upload cats ignored'


def t_boilerplate_keeps_real():
    real = ['Great Buddha Hall', 'Deer in Nara', 'Towers in Japan', 'Inari fox statues']
    return not any(commons.BOILERPLATE.match(c) for c in real), 'real subjects kept'


def t_encode_normalises(tmp):
    from PIL import Image
    src = os.path.join(tmp, 'p.jpg')
    # Noise, not a flat colour: a solid image compresses below the 8KB floor
    # that `check` uses to catch UA-rejected error pages, and would trip it.
    Image.frombytes('RGB', (900, 1400),
                    os.urandom(900 * 1400 * 3)).save(src)   # portrait input
    dst = os.path.join(tmp, 'o.jpg')
    subprocess.run([sys.executable, f'{HERE}/imageprep.py',
                    _plan(tmp, src), os.path.join(tmp, 'out'),
                    '--manifest', os.path.join(tmp, 'm.json')],
                   capture_output=True, text=True)
    w, h = Image.open(os.path.join(tmp, 'out', 'g00.jpg')).size
    return (w, h) == (820, 547), f'{w}x{h}'


def _plan(tmp, src):
    path = os.path.join(tmp, 'plan.json')
    json.dump({'g': [{'src': src, 'what': 'A &amp; B', 'where': 'Somewhere',
                      'credit': 'Someone, CC BY-SA 4.0'}]}, open(path, 'w'))
    return path


def t_gallery_roundtrip(tmp):
    """Inject, then confirm entities decode in alt and unicode survives."""
    import re
    man = os.path.join(tmp, 'm.json')
    data = json.load(open(man))
    data['g'][0].update(what='Torii gates &amp; the path to 伏見稲荷',
                        where='Fushimi Inari, 京都', credit='Æ, CC BY-SA 4.0')
    json.dump(data, open(man, 'w'))
    doc = os.path.join(tmp, 'doc.html')
    open(doc, 'w', encoding='utf-8').write(
        '<html><head><meta charset="UTF-8"></head><body><div class="page">'
        '<div class="gallery-hint">Kyoto &middot; 0 photos &middot; scroll &rarr;</div>'
        '<div class="gallery-scroll"><div class="gallery-slide">old</div></div>'
        '</div></body></html>')
    r = run(f'{HERE}/htmltool.py', 'gallery', doc, man, '--labels', 'g=Kyoto')
    out = open(doc, encoding='utf-8').read()
    alt = re.search(r'<img [^>]*alt="([^"]*)"', out).group(1)
    ok = (r.returncode == 0 and '伏見稲荷' in out and '京都' in out and 'Æ' in out
          and '&amp;' in alt and '"' not in alt and '1 photos' in out)
    return ok, f'alt={alt[:34]!r}'


def t_gallery_rerunnable(tmp):
    r = run(f'{HERE}/htmltool.py', 'gallery', os.path.join(tmp, 'doc.html'),
            os.path.join(tmp, 'm.json'), '--labels', 'g=Kyoto')
    return r.returncode == 0, 'count regex, not literal'


def t_gallery_refuses_bad_label(tmp):
    r = run(f'{HERE}/htmltool.py', 'gallery', os.path.join(tmp, 'doc.html'),
            os.path.join(tmp, 'm.json'), '--labels', 'g=Nowhere')
    return r.returncode != 0 and 'matched 0' in r.stdout + r.stderr, 'fails loudly'


def t_check_exit_codes(tmp):
    doc = os.path.join(tmp, 'doc.html')
    clean = run(f'{HERE}/htmltool.py', 'check', doc)
    broken = os.path.join(tmp, 'broken.html')
    s = open(doc, encoding='utf-8').read()
    s = s.replace('</div></body>', '</body>', 1)              # unclosed div
    s = s.replace('<body>', '<body>{{HERO}}', 1)              # placeholder
    s = s.replace('<img ', '<img loading="lazy" ', 1)         # lazy trap
    open(broken, 'w', encoding='utf-8').write(s)
    bad = run(f'{HERE}/htmltool.py', 'check', broken)
    caught = all(k in bad.stdout for k in ('UNCLOSED', 'placeholders: 1', 'lazy'))
    return clean.returncode == 0 and bad.returncode == 1 and caught, 'catches all three'


def t_lite(tmp):
    doc, out = os.path.join(tmp, 'doc.html'), os.path.join(tmp, 'lite.html')
    run(f'{HERE}/htmltool.py', 'lite', doc, out)
    full, small = open(doc, encoding='utf-8').read(), open(out, encoding='utf-8').read()
    return ('base64' not in small and len(small) < len(full) / 5
            and small.count('<div') == full.count('<div')), f'{len(full)}B -> {len(small)}B'


def t_contactsheet_missing_frame(tmp):
    d = os.path.join(tmp, 'cand')
    os.makedirs(d, exist_ok=True)
    shutil.copy(os.path.join(tmp, 'out', 'g00.jpg'), os.path.join(d, 'k_0.jpg'))
    sheet = os.path.join(tmp, 'sheet.jpg')                    # k_1 deliberately absent
    r = run(f'{HERE}/contactsheet.py', sheet, '--dir', d, '--keys', 'k',
            '--per-key', '2', '--cell', '200x140')
    return r.returncode == 0 and os.path.exists(sheet), 'gap does not abort'


# ----------------------------------------------------------------- network

def t_find_cat():
    out = commons.find_cat('Todai-ji')
    return 'Tōdai-ji' in out, 'resolves diacritics'


def t_subcats():
    out = commons.subcats('Tōdai-ji')
    return 'Buildings of Tōdai-ji' in out, f'{len(out)} sub-categories'


def t_container_needs_deep():
    """The bug this fix exists for: a container category looks empty."""
    shallow = commons.usable(commons.list_cat('Buildings of Tōdai-ji'))
    deep = commons.usable(commons.list_deep('Buildings of Tōdai-ji', depth=2))
    return len(shallow) == 0 and len(deep) > 50, f'{len(shallow)} shallow -> {len(deep)} deep'


def t_file_categories_present():
    rows = commons.list_cat('Deer in Nara')
    return any(r['cats'] for r in rows), 'per-file categories fetched'


def t_fetch_ua(tmp):
    """Confirms the browser UA still works against the file host."""
    rows = commons.usable(commons.list_cat('Deer in Nara'))[:1]
    picks = os.path.join(tmp, 'picks.json')
    json.dump({'k': rows}, open(picks, 'w'))
    n = commons.fetch(picks, os.path.join(tmp, 'dl'), delay=0.3)
    return n == 1, 'file host accepted UA_FILES'


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--network', action='store_true', help='also test the Commons API')
    a = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix='ti-selftest-')
    try:
        print('offline')
        for name, fn in [
            ('find_close walks nesting', t_find_close),
            ('replace_block keeps surroundings', t_replace_block),
            ('find_close raises on unbalanced input', t_unbalanced_raises),
            ('ranking drops portrait / banner / small', t_rank_portrait_and_banner),
            ('ranking scores via file categories', t_rank_uses_categories),
            ('ranking order: subject > season > size', t_rank_avoid_and_season),
            ('boilerplate categories stripped', t_boilerplate_stripped),
            ('real subject categories kept', t_boilerplate_keeps_real),
        ]:
            check(name, fn)
        for name, fn in [
            ('imageprep normalises portrait to 820x547', t_encode_normalises),
            ('gallery: unicode + entities round-trip', t_gallery_roundtrip),
            ('gallery re-runs on an injected doc', t_gallery_rerunnable),
            ('gallery refuses an unmatched label', t_gallery_refuses_bad_label),
            ('check exits 0 clean / 1 broken', t_check_exit_codes),
            ('lite strips base64, keeps structure', t_lite),
            ('contactsheet survives a missing frame', t_contactsheet_missing_frame),
        ]:
            check(name, lambda fn=fn: fn(tmp))

        if a.network:
            print('\nnetwork')
            for name, fn in [
                ('find-cat resolves diacritics', t_find_cat),
                ('subcats lists sub-categories', t_subcats),
                ('container category needs --deep', t_container_needs_deep),
                ('per-file categories are fetched', t_file_categories_present),
            ]:
                check(name, fn)
            check('fetch works against the file host', lambda: t_fetch_ua(tmp))
        else:
            print('\n(skipping network tests; pass --network to include them)')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f'\n{len(PASS)}/{len(PASS) + len(FAIL)} passed')
    if FAIL:
        print('failed: ' + ', '.join(FAIL))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
