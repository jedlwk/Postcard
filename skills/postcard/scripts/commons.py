#!/usr/bin/env python3
"""Wikimedia Commons photo sourcing.

    find-cat "Todai-ji"            which categories exist for this place
    subcats  "Todai-ji"            drill down: sub-categories, most useful first
    list-cat "Gates of Todaiji"    usable files, ranked by subject then season
    search   "sequim lavender"     full-text fallback (last resort, see below)
    fetch    picks.json out/       serial download with backoff

Typical run:

    find-cat "Todai-ji"                          # -> "Tōdai-ji"
    subcats  "Tōdai-ji"                          # -> "Buildings of Tōdai-ji"
    list-cat "Buildings of Tōdai-ji" \\
             --months 10,11 --prefer daibutsuden,hall --json picks.json
    fetch    picks.json th/

Prefer categories over `search`. Full-text search crosses continents without
warning: "Blue Lake" returns Mount Gambier (Australia), "Rainy Lake" returns
Minnesota, "Queen Elizabeth Park" returns lions in Uganda.

Stdlib only.
"""
import argparse
import html as html_
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# The two Wikimedia hosts want DIFFERENT User-Agents and each 403s the other's.
#   the API   -> a descriptive bot UA with contact info. A generic or absent UA
#                returns a ~2KB HTML error page, which a naive size check
#                mistakes for a successful download.
#   the files -> a real browser UA. The descriptive bot UA gets a flat 403.
# Verified empirically. Do not merge these into one constant.
UA_API = ('TripInfographicBuilder/1.0 '
          '(personal trip planning document; contact: set-your-email@example.com)')
UA_FILES = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
API = 'https://commons.wikimedia.org/w/api.php'

# Every Commons file carries licence/upload bookkeeping categories. They say
# nothing about the subject and would pollute keyword scoring, so drop them.
BOILERPLATE = re.compile(
    r'^(CC-|PD-|GFDL|Self-published|Media lacking|Photographs taken on|'
    r'Japan photographs taken on|Taken with|Uploaded with|Panoramio|'
    r'Photos from Panoramio|Images from Panoramio|Files from|Media from|'
    r'Images by|Photographs by|Flickr images|Author died)', re.I)

SKIP_EXT = ('.tif', '.tiff', '.webm', '.svg', '.gif', '.ogv', '.ogg', '.pdf', '.xcf')


# ---------------------------------------------------------------- API plumbing

def _get(params, tries=4):
    """One API call, with retries on transient failure."""
    url = API + '?' + urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': '2'})
    req = urllib.request.Request(url, headers={'User-Agent': UA_API})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 + 2 * attempt)


def _text(extmeta, key):
    """Pull a plain-text field out of the API's HTML-bearing extmetadata."""
    raw = extmeta.get(key, {}).get('value', '')
    return html_.unescape(re.sub(r'<[^>]+>', '', raw)).strip() if raw else ''


def _row(page):
    """One API page -> the flat record the rest of this script uses."""
    info = (page.get('imageinfo') or [{}])[0]
    meta = info.get('extmetadata', {})
    date = _text(meta, 'DateTimeOriginal') or _text(meta, 'DateTime')
    m = re.search(r'(\d{4})[-:](\d{2})[-:](\d{2})', date)
    return {
        'title': page['title'].replace('File:', ''),
        'w': info.get('width'), 'h': info.get('height'),
        'url': info.get('url'), 'thumb': info.get('thumburl'),
        'yr': m.group(1) if m else '', 'mo': int(m.group(2)) if m else 0,
        'lic': _text(meta, 'LicenseShortName'), 'artist': _text(meta, 'Artist')[:80],
        'desc': _text(meta, 'ImageDescription')[:200],
        'cats': [c['title'].replace('Category:', '')
                 for c in page.get('categories', [])
                 if not BOILERPLATE.match(c['title'].replace('Category:', ''))],
    }


# ------------------------------------------------------------------- discovery

def find_cat(query, n=12, near=None):
    """Category names matching a place. Commons spelling is often not yours
    ("Todai-ji" -> "Tōdai-ji", "Lago di Braies" -> "Pragser Wildsee"), so always
    resolve before listing.

    `near` guards against same-name places elsewhere. Commons disambiguates with
    a parenthetical, so "Roman forum (Brescia)", "Spanish Steps (Washington,
    D.C.)" and "Santa Croce (Caltanissetta)" all look like plausible hits for a
    Rome or Dolomites trip. Passing near='Rome' drops any candidate whose
    parenthetical names somewhere else. Candidates with no parenthetical are
    kept -- that is where the useful local-language names live.
    """
    d = _get({'action': 'query', 'list': 'search', 'srsearch': query,
              'srnamespace': '14', 'srlimit': str(n)})
    names = [x['title'].replace('Category:', '') for x in d['query']['search']]
    if not near:
        return names

    near = near.lower()
    keep = []
    for name in names:
        qualifier = re.search(r'\(([^)]+)\)', name)
        if qualifier and near not in qualifier.group(1).lower():
            continue
        keep.append(name)
    return keep


def subcats(cat, n=60):
    """Sub-categories of a broad category.

    This is the highest-leverage step in photo sourcing. A broad category holds
    whatever a few prolific uploaders shot, which skews to close-ups: plain
    "Arashiyama" yields maple-leaf details, "Nara Park" yields seed pods, and
    "Tōdai-ji" yields ceiling shots. The sub-categories are semantic and name
    the thing you actually want -- "Buildings of Tōdai-ji", "Gates of Todaiji",
    "Remote views of Tōdai-ji", "Deer in Nara", "Sagano Bamboo forest".

    Enumerate them instead of guessing a narrower name.
    """
    d = _get({'action': 'query', 'list': 'categorymembers', 'cmtitle': 'Category:' + cat,
              'cmtype': 'subcat', 'cmlimit': str(n)})
    return [x['title'].replace('Category:', '') for x in d['query']['categorymembers']]


def list_deep(cat, depth=2, cap=400):
    """Files in a category plus its sub-categories, `depth` levels down.

    Commons often nests: "Tōdai-ji" -> "Buildings of Tōdai-ji" -> "Golden Hall,
    Todaiji". The middle levels are pure containers holding no files at all, so
    a plain list-cat on one returns nothing and looks like a dead end. Walking
    down pools the leaves.
    """
    pool, seen_cat, queue = {}, set(), [(cat, 0)]
    while queue and len(pool) < cap:
        name, level = queue.pop(0)
        if name in seen_cat:
            continue
        seen_cat.add(name)
        for row in list_cat(name, cap):
            pool.setdefault(row['title'], row)
        if level < depth:
            queue += [(c, level + 1) for c in subcats(name)]
            time.sleep(0.2)
    return list(pool.values())


def list_cat(cat, cap=400):
    """Every file in a category, with its own categories attached.

    Per-file categories are the thing that rescues bare filenames. A file called
    "- panoramio - ESU.jpg" with no description still sits in "Towers in Japan";
    "Fox0290.jpg" sits in "Inari fox statues". Without them, keyword scoring has
    nothing to work with on exactly the files that need it most.

    Paging note: asking for imageinfo and categories together means the API can
    continue on either axis, so merge by title rather than appending -- a naive
    `out += pages` duplicates rows whenever it continues on categories.
    """
    merged, cont = {}, {}
    while True:
        d = _get({'action': 'query', 'generator': 'categorymembers',
                  'gcmtitle': 'Category:' + cat, 'gcmtype': 'file', 'gcmlimit': '200',
                  'prop': 'imageinfo|categories',
                  'iiprop': 'url|size|extmetadata', 'iiurlwidth': '900',
                  'clshow': '!hidden', 'cllimit': 'max', **cont})
        for page in d.get('query', {}).get('pages', []):
            row = _row(page)
            if row['title'] in merged:
                merged[row['title']]['cats'] += row['cats']
            else:
                merged[row['title']] = row
        if 'continue' in d and len(merged) < cap:
            cont = d['continue']
            time.sleep(0.4)
        else:
            return list(merged.values())


def search(term, n=30):
    """Full-text fallback. Only when a category genuinely does not exist."""
    d = _get({'action': 'query', 'generator': 'search', 'gsrsearch': f'filetype:bitmap {term}',
              'gsrnamespace': '6', 'gsrlimit': str(n), 'prop': 'imageinfo',
              'iiprop': 'url|size|extmetadata', 'iiurlwidth': '900'})
    return [_row(p) for p in d.get('query', {}).get('pages', [])]


# --------------------------------------------------------------------- ranking

def usable(rows, min_width=1100, months=None, prefer=(), avoid=()):
    """Drop unusable files, then rank by subject match, season, resolution.

    Scoring reads title + description + the file's own categories, so it still
    works on files whose filename is a camera serial number.
    """
    prefer = [w.lower() for w in prefer]
    avoid = [w.lower() for w in avoid]
    months = set(months or ())
    out, seen = [], set()

    for x in rows:
        if x['title'] in seen or not x['w'] or not x['h']:
            continue
        seen.add(x['title'])
        ratio = x['w'] / x['h']
        # Portrait crops badly into a landscape frame; anything wider than 3:1 is
        # a page banner or a scanned scroll, not a photo.
        if x['w'] < min_width or ratio < 1.0 or ratio > 3.0:
            continue
        if x['title'].lower().endswith(SKIP_EXT):
            continue
        hay = ' '.join([x['title'], x['desc'], ' '.join(x['cats'])]).lower()
        x['inseason'] = x['mo'] in months
        x['score'] = sum(w in hay for w in prefer) - 3 * sum(w in hay for w in avoid)
        out.append(x)

    out.sort(key=lambda x: (-x['score'], not x['inseason'], -x['w']))
    return out


# -------------------------------------------------------------------- download

def fetch(picks_path, outdir, delay=1.3, min_bytes=8000):
    """Download every thumbnail in picks.json to outdir/<key>_<n>.jpg.

    Serial on purpose: a 4-thread fetch trips HTTP 429 after ~13 files and then
    fails everything after it. Re-running skips files already on disk.
    """
    picks = json.load(open(picks_path))
    os.makedirs(outdir, exist_ok=True)
    jobs = [(os.path.join(outdir, f'{key}_{i}.jpg'), row.get('thumb') or row.get('url'))
            for key, rows in picks.items() for i, row in enumerate(rows)]
    jobs = [(p, u) for p, u in jobs
            if u and (not os.path.exists(p) or os.path.getsize(p) < min_bytes)]

    ok = 0
    for path, url in jobs:
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': UA_FILES})
                data = urllib.request.urlopen(req, timeout=45).read()
                if len(data) < min_bytes:
                    raise ValueError(f'only {len(data)}B - UA rejected?')
                open(path, 'wb').write(data)
                ok += 1
                break
            except urllib.error.HTTPError as e:
                # 403 means the User-Agent is wrong, not that the host is busy.
                # Retrying burns minutes for nothing.
                if e.code == 403:
                    print(f'FAIL {path}: 403, file host rejected the User-Agent', flush=True)
                    break
                if attempt == 3:
                    print(f'FAIL {path}: {e}', flush=True)
                else:
                    time.sleep(4 * (attempt + 1))
            except Exception as e:
                if attempt == 3:
                    print(f'FAIL {path}: {e}', flush=True)
                else:
                    time.sleep(4 * (attempt + 1))
        time.sleep(delay)

    print(f'requested {len(jobs)}  ok {ok}', flush=True)
    return ok


# ------------------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('find-cat')
    p.add_argument('query')
    p.add_argument('--near', help='city/region; drops same-name places elsewhere')
    sub.add_parser('subcats').add_argument('query')

    for name in ('list-cat', 'search'):
        p = sub.add_parser(name)
        p.add_argument('query')
        p.add_argument('--months', default='', help='e.g. 6,7,8,9 - rank these first')
        p.add_argument('--prefer', default='', help='subject keywords to rank up')
        p.add_argument('--avoid', default='', help='keywords to rank down')
        p.add_argument('--min-width', type=int, default=1100)
        p.add_argument('--deep', type=int, default=0, metavar='N',
                       help='also pull files from sub-categories, N levels down')
        p.add_argument('--limit', type=int, default=20)
        p.add_argument('--json', help='write the ranked list here (feeds fetch)')

    p = sub.add_parser('fetch')
    p.add_argument('picks')
    p.add_argument('outdir')
    p.add_argument('--delay', type=float, default=1.3)

    a = ap.parse_args()

    if a.cmd == 'fetch':
        return fetch(a.picks, a.outdir, a.delay)
    if a.cmd == 'find-cat':
        print('\n'.join(find_cat(a.query, near=getattr(a, 'near', None))))
        return
    if a.cmd == 'subcats':
        found = subcats(a.query)
        print('\n'.join(found) if found else '(no sub-categories)')
        return

    csv = lambda v: [w.strip() for w in v.split(',') if w.strip()]
    if a.cmd == 'search':
        rows = search(a.query)
    elif a.deep:
        rows = list_deep(a.query, a.deep)
    else:
        rows = list_cat(a.query)
    rows = usable(rows, a.min_width, [int(m) for m in csv(a.months)],
                  csv(a.prefer), csv(a.avoid))

    print(f'# {len(rows)} usable in "{a.query}"', file=sys.stderr)
    if not rows and a.cmd == 'list-cat' and not a.deep:
        # Almost always a container category. Say so instead of looking dead.
        kids = subcats(a.query)
        if kids:
            print(f'# no direct files; {len(kids)} sub-categories -- retry with '
                  f'--deep 2, or pick one:\n#   ' + '\n#   '.join(kids[:12]),
                  file=sys.stderr)
    for i, x in enumerate(rows[:a.limit]):
        print(f'{i:3d} {"S" if x["inseason"] else "."} +{x["score"]:<2} '
              f'{x["mo"] or "--"}/{x["yr"] or "----"} {x["w"]}x{x["h"]:<5} '
              f'{x["lic"][:12]:12s} {x["title"][:58]}')
    if a.json:
        json.dump(rows, open(a.json, 'w'))


if __name__ == '__main__':
    main()
