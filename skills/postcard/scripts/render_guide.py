#!/usr/bin/env python3
"""Render a Postcard guide from plan.json.

    render_guide.py plan.json                 -> <plan folder>/<title>.html (+ .ics)
    render_guide.py plan.json --check         -> validate the plan only
    render_guide.py plan.json -o out.html

The agent writes content into plan.json (see references/plan-schema.md).
This script owns the layout: markup, tabs, colours, weekday labels, photo
encoding, calendar link, print styles. Same plan, same page, every time.

Inline text markup used in plan strings:
    **bold**  *italic*  [label](https://url)
    {must}  {book}  {michelin:star|bib|rec}  {car}
Everything else is HTML-escaped.
"""
import argparse, base64, datetime as dt, html, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(os.path.dirname(HERE), 'templates')
sys.path.insert(0, HERE)

CATS = [('Food', 'Food &amp; Drink', 'food'), ('Markets', 'Markets &amp; Shopping', 'market'), ('Nature', 'Nature &amp; Views', 'nature'),
        ('Culture', 'History &amp; Culture', 'culture'), ('Nightlife', 'Nightlife &amp; Vibes', 'night'), ('Festivals', 'Festivals &amp; Events', 'fest')]
DAY_CAT = {'festival': 'fest', 'nature': 'nature', 'travel': 'culture', 'arrival': 'culture', 'culture': 'culture', 'scenic': 'market',
           'food': 'food', 'market': 'market', 'nightlife': 'night', 'rest': 'night'}
TAG_CLASS = {'high': 'fixed', 'fixed': 'fixed', 'likely': 'likely', 'uncertain': 'uncertain', 'risk': 'uncertain'}
TAG_LABEL = {'high': 'HIGH CONFIDENCE', 'fixed': 'HIGH CONFIDENCE', 'likely': 'LIKELY', 'uncertain': 'UNCERTAIN', 'risk': 'AT RISK'}
TIER = {'must': ('Must-do', 't-must'), 'high': ('Highly recommended', 't-high'), 'good': ('Good to have', 't-good')}
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


# ------------------------------------------------------------------ text
def esc(s):
    """HTML-escape, but leave entities the author already wrote (&ndash; &amp;) alone."""
    t = html.escape(str(s if s is not None else ''), quote=True)
    return re.sub(r'&amp;(#?\w+;)', r'&\1', t)


def md(s):
    """Escape, then apply the small inline markup."""
    t = esc(s)
    t = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])', r'<em>\1</em>', t)
    t = t.replace('{must}', '<span class="must-see">MUST-SEE</span>').replace('{book}', '<span class="book-tag">BOOK AHEAD</span>')
    t = t.replace('{car}', '<span class="car">car</span>')
    t = re.sub(r'\{michelin:(star|bib|rec)\}', lambda m: {'star': '<span class="michelin-tag mstar">MICHELIN 1 Star</span>',
               'bib': '<span class="michelin-tag mbib">MICHELIN Bib Gourmand</span>', 'rec': '<span class="michelin-tag mrec">MICHELIN Recommended</span>'}[m.group(1)], t)
    return t


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', str(s).lower()).strip('-') or 'x'


def pdate(s):
    return dt.date.fromisoformat(s)


def dlabel(d):
    return f'{WD[d.weekday()]} {d.day} {MONTHS[d.month - 1]}'


def color(c):
    return c if re.fullmatch(r's[1-8]', str(c or '')) else 's1'


# ------------------------------------------------------------------ images
_cache = {}


def img_uri(path, base, kind='photo'):
    try:
        from PIL import Image
    except ImportError:
        import tripstate
        tripstate.ensure_pillow()
        from PIL import Image
    p = path if os.path.isabs(path) else os.path.join(base, path)
    key = (p, kind)
    if key in _cache:
        return _cache[key]
    im = Image.open(p).convert('RGB')
    w, h = im.size
    if kind == 'photo':
        t = 820 / 547
        if w / h > t:
            nw = int(h * t); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:
            nh = int(w / t); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
        im = im.resize((820, 547), Image.LANCZOS); q = 58
    elif kind == 'hero':
        if w > 1600:
            im = im.resize((1600, round(h * 1600 / w)), Image.LANCZOS)
        q = 60
    else:  # map
        if w > 1000:
            im = im.resize((1000, round(h * 1000 / w)), Image.LANCZOS)
        q = 72
    b = io.BytesIO(); im.save(b, 'JPEG', quality=q, optimize=True)
    uri = 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
    _cache[key] = uri
    return uri


# ------------------------------------------------------------------ plan check
def check_plan(plan, base):
    errs, warns = [], []
    need = lambda c, m: errs.append(m) if not c else None
    need(plan.get('title'), 'title is required')
    need(plan.get('headline'), 'headline is required')
    try:
        s, e = pdate(plan['start']), pdate(plan['end'])
        need(e >= s, 'end is before start')
    except Exception:
        s = e = None; errs.append('start and end must be ISO dates (YYYY-MM-DD)')
    stops = plan.get('stops') or []
    need(stops, 'at least one stop is required')
    ids = set()
    for i, st in enumerate(stops, 1):
        w = f'stop {i} ({st.get("name", "?")})'
        for k in ('id', 'name', 'dates', 'days'):
            need(st.get(k), f'{w}: "{k}" is required')
        if st.get('id') in ids:
            errs.append(f'{w}: duplicate id')
        ids.add(st.get('id'))
        if not st.get('photos'):
            warns.append(f'{w}: no photos')
        for ph in st.get('photos', []):
            for k in ('file', 'what', 'where', 'credit'):
                if not ph.get(k):
                    errs.append(f'{w}: photo missing "{k}"')
            if ph.get('file') and not os.path.isfile(ph['file'] if os.path.isabs(ph['file']) else os.path.join(base, ph['file'])):
                errs.append(f'{w}: photo file not found: {ph["file"]}')
        m = st.get('map')
        if m:
            if not (m.get('credit') and m.get('source_url')):
                errs.append(f'{w}: map needs credit and source_url (real published maps only)')
            if m.get('file') and not os.path.isfile(m['file'] if os.path.isabs(m['file']) else os.path.join(base, m['file'])):
                errs.append(f'{w}: map file not found')
        for d in st.get('days', []):
            try:
                dd = pdate(d['date'])
                if s and e and not (s <= dd <= e):
                    warns.append(f'{w}: day {d["date"]} is outside the trip dates')
            except Exception:
                errs.append(f'{w}: day has a bad date: {d.get("date")}')
            need(d.get('lead'), f'{w}: day {d.get("date")} needs a lead line')
    h = plan.get('hero') or {}
    need(h.get('image'), 'hero.image is required')
    if h.get('image') and not os.path.isfile(h['image'] if os.path.isabs(h['image']) else os.path.join(base, h['image'])):
        errs.append('hero image not found')
    need(h.get('credit'), 'hero.credit is required (credit every photo)')
    v = plan.get('verification') or {}
    if v.get('status') == 'verified':
        if not (plan.get('sources') or []):
            errs.append('verification.status is "verified" but sources is empty')
        if not v.get('second_pass'):
            warns.append('verified without a second pass (verification.second_pass)')
    elif not v.get('status'):
        warns.append('verification.status missing; the guide will say it is not fact-checked')
    return errs, warns


# ------------------------------------------------------------------ blocks
def li(items):
    return ''.join(f'<li>{md(x)}</li>' for x in items)


def info_card(title, items, cls=''):
    return f'<div class="info-card{" " + cls if cls else ""}"><h4>{esc(title)}</h4><ul>{li(items)}</ul></div>'


def transit_card(c, accent=None):
    st = f' style="border-left:4px solid var(--{color(accent)})"' if accent else ''
    kick = f'<div class="t-detail mono">{esc(c["kicker"])}</div>' if c.get('kicker') else ''
    return f'<div class="transit-card"{st}><div class="t-route">{md(c["title"])}</div>{kick}<ul>{li(c.get("items", []))}</ul></div>'


def section(tag, title, sub, cards, cls='logistics', sid=''):
    ida = f' id="{sid}"' if sid else ''
    sb = f'<p class="section-sub">{md(sub)}</p>' if sub else ''
    return (f'<section{ida} class="{cls}"><div class="section-head"><span class="section-tag">{esc(tag)}</span><h2>{esc(title)}</h2></div>{sb}'
            f'<div class="transit-strip">{"".join(transit_card(c) for c in cards)}</div></section>')


def weather(w):
    rows = []
    lo_s, hi_s = -5, 40
    pos = lambda v: max(0, min(100, (v - lo_s) / (hi_s - lo_s) * 100))
    for r in w.get('rows', []):
        c = color(r.get('color'))
        a, b = pos(r['lo']), pos(r['hi'])
        fl = ''
        if 'feels_lo' in r and 'feels_hi' in r:
            fl = f'<div class="wx-comfort" style="left:{pos(r["feels_lo"]):.1f}%;right:{100 - pos(r["feels_hi"]):.1f}%" title="Feels like {r["feels_lo"]}&ndash;{r["feels_hi"]}&deg;C"></div>'
        feels = f'<span class="wx-feels">feels {r["feels_lo"]}&ndash;{r["feels_hi"]}&deg;C</span>' if fl else ''
        rows.append(f'<div class="wx-row"><div class="wx-label">{esc(r["label"])}<span class="wx-sub mono">{esc(r.get("sub", ""))}</span></div>'
                    f'<div class="wx-track">{fl}<div class="wx-range" style="left:{a:.1f}%; width:{b - a:.1f}%; background:var(--{c}-tint); border:1px solid var(--{c})"></div>'
                    f'<div class="wx-dot" style="left:{a:.1f}%; background:var(--{c})">{r["lo"]}</div><div class="wx-dot" style="left:{b:.1f}%; background:var(--{c})">{r["hi"]}</div></div>'
                    f'<div class="wx-cond">{feels}<span>{esc(r.get("rain", ""))}</span><span class="wx-wind">{esc(r.get("wind", ""))}</span></div></div>')
    ticks = ''.join(f'<span style="left:{pos(v):.1f}%">{v}&deg;{"C" if v == 40 else ""}</span>' for v in (-5, 5, 15, 25, 35, 40))
    notes = ''.join(f'<p class="wx-note">{md(n)}</p>' for n in w.get('notes', []))
    return (f'<section class="section"><div class="section-head"><span class="section-tag">Weather across the route</span><h2>{esc(w.get("title", "What the weather will feel like"))}</h2></div>'
            f'<p class="section-sub">{md(w.get("intro", ""))}</p><div class="weather-strip">{"".join(rows)}<div class="wx-scale"><div></div><div class="ticks mono">{ticks}</div></div></div>'
            f'<p class="wx-legend"><span class="wx-swatch"></span><span><strong>Shaded band: what it feels like.</strong> Wind chill on cold mornings, humidex on warm afternoons. The solid bar is the average low to high.</span></p>{notes}</section>')


def gallery(st, base, sid):
    slides = ''.join(
        f'<div class="gallery-slide"><img src="{img_uri(p["file"], base)}" alt="{esc(p["what"])}"><div class="gallery-cap"><span class="gc-what">{esc(p["what"])}</span>'
        f'<span class="gc-where">{esc(p["where"])}</span><span class="gc-credit">{esc(p["credit"])}</span></div></div>' for p in st.get('photos', []))
    gal = (f'<div class="gallery-hint">{esc(st["name"])} &middot; {len(st.get("photos", []))} photos &middot; scroll &rarr;</div><div class="gallery-scroll">{slides}</div>')
    m = st.get('map')
    if not m or not m.get('file'):
        return f'<div class="media-solo">{gal}</div>'
    mid = f'map-{sid}'
    return (f'<div class="media-row"><div class="media-gallery">{gal}</div><div class="media-map"><span class="map-anchor" id="{mid}-back"></span>'
            f'<figure class="route-map" id="{mid}"><a class="map-open" href="#{mid}" title="Enlarge"><img src="{img_uri(m["file"], base, "map")}" alt="{esc(m.get("alt", st["name"] + " map"))}">'
            f'<span class="map-zoom mono">&#8853; enlarge</span></a><a class="map-close" href="#{mid}-back" aria-label="Close">&times;</a>'
            f'<figcaption>{md(m.get("caption", ""))} <span class="map-credit">Map: {esc(m["credit"])} &middot; <a href="{esc(m["source_url"])}" target="_blank" rel="noopener">source</a></span></figcaption></figure></div></div>')


def day_item(d):
    dd = pdate(d['date'])
    cat = DAY_CAT.get(str(d.get('cat', 'nature')).lower(), 'nature')
    bullets = f'<ul class="day-highlights">{li(d.get("bullets", []))}</ul>' if d.get('bullets') else ''
    return (f'<div class="day-item"><div class="day-tag"><span class="mono">{dlabel(dd)}</span><span class="day-cat" style="background:var(--cat-{cat}-tint); color:var(--cat-{cat})">{esc(d.get("cat", ""))}</span></div>'
            f'<div class="day-text"><span class="day-lead">{md(d["lead"])}</span>{bullets}</div></div>')


def stay_card(s, c):
    pick = (f'<p class="stay-pick"><span class="book-tag">{esc(s["pick"].get("tag", "BOOK THIS"))}</span> <strong>{md(s["pick"]["name"])}</strong>: {md(s["pick"]["text"])}</p>' if s.get('pick') else '')
    alts = ''.join(f'<p class="stay-alt"><strong>{esc(a["label"])}:</strong> {md(a["text"])}</p>' for a in s.get('alts', []))
    links = ''.join(f'<a href="{esc(l["url"])}" target="_blank" rel="noopener">&#8599; {esc(l["label"])}</a>' for l in s.get('links', []))
    links = f'<div class="stay-links">{links}</div>' if links else ''
    return (f'<div class="stay-card" style="border-left-color:var(--{c})"><div class="stay-nights mono">{esc(s["nights"])}</div><div class="stay-base">{md(s["base"])}</div>'
            f'<p class="stay-why">{md(s.get("why", ""))}</p>{pick}{alts}{links}</div>')


def hikes(h):
    cards = []
    for x in h['items']:
        tl, tc = TIER.get(x.get('tier', 'good'), TIER['good'])
        stats = ''.join(f'<span>{esc(v)}</span>' for v in x.get('stats', []))
        diff = f'<span class="hs-diff">{esc(x["diff"])}</span>' if x.get('diff') else ''
        link = f'<a class="alltrails-link" href="{esc(x["url"])}" target="_blank" rel="noopener">&#8599; {esc(x.get("url_label", "AllTrails"))}</a>' if x.get('url') else ''
        trait = f'<span class="hike-trait">{esc(x["trait"])}</span>' if x.get('trait') else ''
        cards.append(f'<div class="hike-card{" is-must" if x.get("tier") == "must" else ""}"><h5>{esc(x["name"])}</h5><div class="hike-badges"><span class="hike-tier {tc}">{tl}</span>{trait}</div>'
                     f'<div class="hike-stats">{stats}{diff}</div><p class="hike-where">{md(x.get("where", ""))}</p>{link}</div>')
    sub = f'<p class="blk-sub">{md(h["sub"])}</p>' if h.get('sub') else ''
    return f'<div class="blk"><h3 class="blk-h">Hikes</h3>{sub}<div class="hike-grid">{"".join(cards)}</div></div>'


def shortlist(sl):
    out = []
    for g in sl['groups']:
        spots = []
        for sp in g['spots']:
            name = f'<a href="{esc(sp["url"])}" target="_blank" rel="noopener">{esc(sp["name"])}</a>' if sp.get('url') else esc(sp['name'])
            must = '<span class="must-see">MUST-SEE</span>' if sp.get('must') else ''
            meta = ''.join(f'<span>{esc(m)}</span>' for m in sp.get('meta', []))
            car = '<span class="car">car</span>' if sp.get('car') else ''
            spots.append(f'<div class="spot-card{" is-must" if sp.get("must") else ""}"><div class="spot-name">{name}{must}</div><div class="spot-meta">{car}{meta}</div><p class="spot-why">{md(sp.get("why", ""))}</p></div>')
        out.append(f'<div class="spot-group">{esc(g["name"])}</div><div class="spot-grid">{"".join(spots)}</div>')
    sub = f'<p class="blk-sub">{md(sl["sub"])}</p>' if sl.get('sub') else ''
    return f'<div class="blk"><div class="vanlist"><h3 class="blk-h">{esc(sl.get("title", "The shortlist"))}</h3>{sub}{"".join(out)}</div></div>'


def more_item(x):
    why = ': ' + md(x['why']) if x.get('why') else ''
    area = '<span class="cat-area">' + esc(x['area']) + '</span>' if x.get('area') else ''
    return '<li><strong>' + md(x['name']) + '</strong>' + why + area + '</li>'


def src_row(s):
    link = ' &middot; <a href="' + esc(s['url']) + '" target="_blank" rel="noopener">source</a>' if s.get('url') else ''
    return '<div class="src-row"><span>' + md(s['claim']) + link + '</span><time>' + esc(s.get('checked', '')) + '</time></div>'


def more_block(st, sid):
    more = st.get('more') or {}
    reading = st.get('reading') or []
    if not more and not reading:
        return ''
    n = sum(len(more.get(k, [])) for k, _, _ in CATS if k in more)
    radios, labels, panels = [], [], []
    for i, (key, label, _) in enumerate(CATS, 1):
        items = more.get(key, [])
        radios.append(f'<input type="radio" name="tabs-{sid}" id="tabs-{sid}-{i}" class="tab-radio"{" checked" if i == 1 else ""}>')
        hide = '' if items else ' style="display:none"'
        labels.append(f'<label class="tab-label" for="tabs-{sid}-{i}"{hide}>{label}<span class="count mono">({len(items)})</span></label>')
        lis = ''.join(more_item(x) for x in items)
        panels.append(f'<ul class="cat-list tab-panel-content">{lis}</ul>')
    sub = f'<p class="explore-sub">{md(more.get("_sub", ""))}</p>' if more.get('_sub') else ''
    exp = (f'<div class="explore-more">{sub}<div class="explore-tabs">{"".join(radios)}<div class="tabs-layout"><div class="tabs-sidebar">{"".join(labels)}</div>'
           f'<div class="tabs-panel">{"".join(panels)}</div></div></div></div>') if more else ''
    fr = ''
    if reading:
        rows = ''.join(f'<a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["label"])}<span class="fr-src">{esc(r.get("src", ""))}</span></a>' for r in reading)
        fr = f'<div class="info-card fr-box"><h4>Further Reading</h4><div class="further-reading">{rows}</div></div>'
    note = f'{n} places, sorted by type' if n else 'reading'
    return f'<details class="more"><summary><span>More places and reading</span><span class="more-n mono">{note}</span></summary>{exp}{fr}</details>'


def stop_panel(st, i, nxt, base):
    sid = slug(st['id']); c = color(st.get('color'))
    b = st.get('badges') or {}
    badges = ''
    if b:
        dots = ''.join(f'<span class="dot{" filled" if k < int(b.get("intensity", 2)) else ""}"></span>' for k in range(3))
        inten = {1: 'Low', 2: 'Medium', 3: 'High'}.get(int(b.get('intensity', 2)), 'Medium')
        vibes = ''.join(f'<span class="badge-vibe">{esc(v)}</span>' for v in b.get('vibes', []))
        cat = f'<span class="badge-category" style="background:var(--{c}-tint); color:var(--{c})">{esc(b["category"])}</span>' if b.get('category') else ''
        badges = f'<div class="trip-badges">{cat}<span class="badge-intensity" style="color:var(--{c})"><span class="dots">{dots}</span>{inten}</span>{vibes}</div>'
    ml = st.get('maps_link')
    mlink = f'<a class="maps-link" href="{esc(ml["url"])}" target="_blank" rel="noopener">&#8599; {esc(ml.get("label", "View this drive on Google Maps"))}</a>' if ml else ''
    al = st.get('alert')
    alert = f'<div class="smoke-note"><span class="sn-label">&#9888; {esc(al["label"])}</span>{md(al["text"])}</div>' if al else ''
    days = ''.join(day_item(d) for d in st['days'])
    stays = st.get('stays') or []
    side = ''
    if stays:
        side += f'<div class="info-card stay-box"><h4>Where to stay</h4>{"".join(stay_card(s, c) for s in stays)}</div>'
    for card in st.get('cards', []):
        side += info_card(card['title'], card['items'])
    if st.get('know'):
        side += info_card('Know before you go', st['know'])
    if st.get('festivals'):
        fl = ''.join(f'<li><span class="tag {TAG_CLASS.get(f.get("tag", "likely"), "likely")}">{esc(f.get("label") or TAG_LABEL.get(f.get("tag", "likely"), ""))}</span>{md(f["text"])}</li>' for f in st['festivals'])
        side += f'<div class="info-card"><h4>Festivals &amp; Events</h4><ul class="fest-list">{fl}</ul></div>'
    if st.get('fun_fact'):
        side += f'<div class="info-card funfact"><h4>Fun Fact</h4><p>{md(st["fun_fact"])}</p></div>'
    nx = f'<a class="p-next" href="#top"><label for="t-{nxt[0]}">Next: {esc(nxt[1])} &rarr;</label></a>' if nxt else ''
    return (f'<section class="panel" id="p-{sid}"><div class="p-head"><div class="chapter-head"><span class="chapter-tag" style="color:var(--{c})">Stop {i}</span><h2>{esc(st["name"])}</h2></div>'
            f'<div class="chapter-dates">{esc(st["dates"])}</div><div class="p-meta">{badges}{mlink}</div></div>{alert}{gallery(st, base, sid)}'
            f'<div class="p-grid"><div class="p-main"><h3 class="blk-h">Day by day</h3><div class="day-list">{days}</div></div><aside class="p-side">{side}</aside></div>'
            f'{hikes(st["hikes"]) if st.get("hikes") else ""}{shortlist(st["shortlist"]) if st.get("shortlist") else ""}{more_block(st, sid)}{nx}</section>')


# ------------------------------------------------------------------ calendar
def ics_text(plan):
    def esc_i(s):
        return re.sub(r'<[^>]+>', '', str(s)).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')
    stamp = dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    ev = []

    def add(uid, start, summary, desc='', allday=True, end=None):
        s = start.replace('-', '').replace(':', '')
        lines = ['BEGIN:VEVENT', f'UID:{uid}@postcard', f'DTSTAMP:{stamp}']
        if allday:
            lines.append(f'DTSTART;VALUE=DATE:{s[:8]}')
        else:
            lines.append(f'DTSTART:{s}')
            if end:
                lines.append(f'DTEND:{end.replace("-", "").replace(":", "")}')
        lines.append(f'SUMMARY:{esc_i(summary)}')
        if desc:
            lines.append(f'DESCRIPTION:{esc_i(desc)}')
        lines.append('END:VEVENT'); ev.append('\r\n'.join(lines))
    for st in plan.get('stops', []):
        for d in st.get('days', []):
            add(f'day-{d["date"]}-{slug(st["id"])}', d['date'], f'{st["name"]}: {re.sub(r"[*{}]", "", d["lead"])}', '\n'.join(re.sub(r'[*{}]', '', b) for b in d.get('bullets', [])))
    for n, f in enumerate(plan.get('flights', [])):
        if f.get('start'):
            add(f'flight-{n}', f['start'], f['label'], f.get('note', ''), allday=False, end=f.get('end'))
    for n, b in enumerate(plan.get('book_check', [])):
        if b.get('date'):
            add(f'book-{n}', b['date'], 'Postcard: ' + re.sub(r'[*{}]', '', b['text']), b.get('when', ''))
    return 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Postcard//EN\r\nCALSCALE:GREGORIAN\r\n' + '\r\n'.join(ev) + '\r\nEND:VCALENDAR\r\n'


# ------------------------------------------------------------------ page
def render(plan, base):
    stops = plan['stops']
    extras = plan.get('extras') or []
    tabs = [('overview', 'Overview', 'ink', f'{dlabel(pdate(plan["start"]))} to {dlabel(pdate(plan["end"]))}')]
    for st in stops:
        tabs.append((slug(st['id']), st.get('tab', st['name'].split(',')[0]), color(st.get('color')), st.get('tab_sub', '')))
    for ex in extras:
        tabs.append((slug(ex['id']), ex['name'], color(ex.get('color', 's7')), ex.get('sub', '')))
    hero = plan['hero']
    eyebrow = plan.get('eyebrow') or ' &middot; '.join(esc(s['name'].split(',')[0].upper()) for s in stops)
    # route strip
    route = plan.get('route')
    if not route:
        route = [{'type': 'stop', 'city': s['name'].split(',')[0], 'nights': s.get('tab_sub', ''), 'color': s.get('color')} for s in stops]
    rs = []
    for r in route:
        t = r.get('type')
        if t == 'home':
            rs.append(f'<div class="route-home"><div class="rn-city">{esc(r["city"])}</div><div class="rn-nights mono">{esc(r.get("sub", "Home"))}</div></div>')
        elif t == 'fly':
            rs.append(f'<div class="route-fly"><div class="rf-mode">Fly</div><div class="rf-detail mono">{"<br>".join(esc(x) for x in str(r["detail"]).split("|"))}</div></div>')
        elif t == 'drive':
            rs.append(f'<div class="route-via"><div class="rv-label mono">{esc(r["label"])}</div><div class="rv-mode">{esc(r.get("mode", "DRIVE"))}</div></div>')
        else:
            rs.append(f'<div class="route-node"><div class="rn-dot" style="background:var(--{color(r.get("color"))})"></div><div class="rn-city">{esc(r["city"])}</div><div class="rn-nights mono">{esc(r.get("nights", ""))}</div></div>')
    # overview
    rows = []
    for si, st in enumerate(stops):
        c = color(st.get('color'))
        for d in st['days']:
            rows.append((d['date'], c, slug(st['id']), re.sub(r'[*{}]', '', d['lead']), d.get('sleep') or st.get('sleep', '')))
    rows.sort(key=lambda r: r[0])
    glance = ('<div class="glance"><div class="gl-head mono"><span>Date</span><span></span><span>Plan</span><span>Sleep</span></div>' + ''.join(
        f'<label class="gl-row" for="t-{sid}"><span class="gl-d mono">{dlabel(pdate(d))}</span><span class="gl-dot" style="background:var(--{c})"></span><span class="gl-what">{esc(w)}</span><span class="gl-sleep mono">{esc(sl)}</span></label>'
        for d, c, sid, w, sl in rows) + '</div>')
    ics = ics_text(plan)
    cal = f'<a class="cal-link" download="{slug(plan["title"])}.ics" href="data:text/calendar;base64,{base64.b64encode(ics.encode()).decode()}">Add the plan and deadlines to your calendar</a>'
    bc = plan.get('book_check') or []
    todo = ''
    if bc:
        lis = ''.join(f'<li><span class="when mono">{esc(b.get("when", ""))}</span>{md(b["text"])}</li>' for b in bc)
        todo = f'<div class="info-card todo"><h4>Book and check, in order</h4><ol class="todo-list">{lis}</ol>{cal}</div>'
    else:
        todo = f'<div class="info-card todo"><h4>Calendar</h4>{cal}</div>'
    v = plan.get('verification') or {}
    banner = ''
    if v.get('status') != 'verified':
        why = {'partial': 'Some details were checked and some were not.', 'unchecked': 'Nothing here was checked against a live source.'}.get(v.get('status'), 'This guide was not fact-checked.')
        banner = f'<div class="smoke-note"><span class="sn-label">&#9888; Not fully fact-checked</span>{esc(why)} Confirm hours, prices, closures and dates before you book.</div>'
    srcs = plan.get('sources') or []
    src_html = ''
    if srcs:
        rows_s = ''.join(src_row(x) for x in srcs)
        src_html = f'<details class="more src"><summary><span>Sources and recheck dates</span><span class="more-n mono">{len(srcs)} sources</span></summary><div class="src-list">{rows_s}</div></details>'
    w = plan.get('weather')
    r = plan.get('risks')
    overview = (f'<section class="panel" id="p-overview">{banner}<div class="ov-grid"><div><h3 class="blk-h">The trip, day by day</h3><p class="blk-sub">Tap a row to open that stop.</p>{glance}</div>'
                f'<aside class="p-side">{todo}</aside></div>{weather(w) if w else ""}'
                f'{section(r.get("tag", "Risks"), r["title"], r.get("intro", ""), r["cards"], sid="risks") if r else ""}{src_html}'
                f'<a class="p-next" href="#top"><label for="t-{tabs[1][0]}">Start: {esc(tabs[1][1])} &rarr;</label></a></section>')
    panels = [overview]
    for i, st in enumerate(stops, 1):
        nxt = (tabs[i + 1][0], tabs[i + 1][1]) if i + 1 < len(tabs) else None
        panels.append(stop_panel(st, i, nxt, base))
    for j, ex in enumerate(extras):
        k = len(stops) + 1 + j
        nxt = f'<a class="p-next" href="#top"><label for="t-{tabs[k + 1][0]}">Next: {esc(tabs[k + 1][1])} &rarr;</label></a>' if k + 1 < len(tabs) else ''
        panels.append(f'<section class="panel" id="p-{slug(ex["id"])}">{section(ex.get("tag", ex["name"]), ex.get("title", ex["name"]), ex.get("intro", ""), ex["cards"])}{nxt}</section>')
    radios = ''.join(f'<input type="radio" name="tab" class="tabradio" id="t-{k}"{" checked" if n == 0 else ""}>' for n, (k, _, _, _) in enumerate(tabs))
    bar = '<span id="top" class="tabs-anchor"></span><nav class="tabbar" aria-label="Sections">' + ''.join(
        f'<label for="t-{k}" style="--c:var(--{c if c != "ink" else "ink"})"><span class="tb-name">{esc(n)}</span><span class="tb-sub mono">{esc(s)}</span></label>' for k, n, c, s in tabs) + '</nav>'
    tabcss = ''.join(f'#t-{k}:checked ~ .panels #p-{k}{{display:block}}#t-{k}:checked ~ .tabbar label[for=t-{k}]{{background:var(--paper-raised);border-color:var(--c);box-shadow:inset 0 -3px 0 var(--c)}}' for k, _, _, _ in tabs)
    ncol = len(tabs)
    tabcss += f'.tabbar{{grid-template-columns:repeat({ncol},minmax(0,1fr))}}'
    foot = f'<div class="foot-note"><p>{md(plan["footnote"])}</p></div>' if plan.get('footnote') else ''
    lede = f'<p class="lede">{md(plan.get("lede", ""))}</p>' if plan.get('lede') else ''
    hero_html = (f'<div class="hero"><img src="{img_uri(hero["image"], base, "hero")}" alt="{esc(hero.get("alt", ""))}"><div class="hero-scrim"></div>'
                 f'<div class="hero-content"><div class="hero-eyebrow">{eyebrow}</div><h1>{esc(plan["headline"])}</h1>{lede}</div></div>')
    css = open(os.path.join(TPL, 'fonts.css')).read() + open(os.path.join(TPL, 'guide.css')).read() + tabcss
    return (f'<!doctype html>\n<html lang="{esc(plan.get("lang", "en"))}"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{esc(plan["title"])}</title><style>{css}</style></head><body><div class="page">{hero_html}<div class="route-strip">{"".join(rs)}</div>'
            f'{radios}{bar}<div class="panels">{"".join(panels)}</div>{foot}'
            f'<p class="hero-credit" style="font-size:11px;color:var(--ink-faint);margin:18px 0 0">Cover photo: {esc(hero["credit"])}</p></div></body></html>')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plan'); ap.add_argument('-o', '--out'); ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    base = os.path.dirname(os.path.abspath(a.plan))
    plan = json.load(open(a.plan, encoding='utf-8'))
    errs, warns = check_plan(plan, base)
    for w in warns:
        print('warning:', w)
    for e in errs:
        print('ERROR:', e)
    if errs:
        sys.exit(1)
    if a.check:
        print('plan ok'); return
    out = a.out or os.path.join(base, plan['title'].strip().replace('/', '-') + '.html')
    page = render(plan, base)
    open(out, 'w', encoding='utf-8').write(page)
    open(os.path.splitext(out)[0] + '.ics', 'w').write(ics_text(plan))
    print(f'wrote {out} ({len(page) / 1e6:.1f} MB) and .ics')


if __name__ == '__main__':
    main()
