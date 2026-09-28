#!/usr/bin/env python3
"""Safe structural edits and verification for a multi-megabyte HTML document.

    check   doc.html                 nesting, placeholders, images, charset
    lite    doc.html lite.html       strip base64 so the file is greppable
    gallery doc.html manifest.json --labels oly="Olympic National Park"

You cannot Read a 9MB HTML file into context, and you cannot regex your way to
a block's closing tag. Both have caused real, user-visible bugs. `find_close`
and `replace_block` are importable for any other block swap.

Stdlib only.
"""
import argparse
import base64
import hashlib
import html as html_
import json
import os
import re
import sys

B64_ANY = re.compile(r'data:image/[a-z]+;base64,[A-Za-z0-9+/=]+')
B64_SRC = re.compile(r'src="data:image/[a-z]+;base64,([A-Za-z0-9+/=]+)"')


# ------------------------------------------------------------ block editing

def find_close(text, start, tag='div'):
    """Index just past the </tag> that closes the <tag> beginning at `start`.

    Counting tags is not the same as tracking nesting. A document can have
    perfectly balanced <div>/</div> counts while an entire chapter sits nested
    inside its neighbour, so walk the depth.
    """
    depth = 0
    for m in re.finditer(rf'<{tag}\b|</{tag}>', text[start:]):
        depth += -1 if m.group(0).startswith('</') else 1
        if depth == 0:
            return start + m.end()
    raise ValueError(f'unbalanced <{tag}> from offset {start}')


def replace_block(text, start, new, tag='div'):
    """Swap the element starting at `start` for `new`, keeping everything else."""
    return text[:start] + new + text[find_close(text, start, tag):]


# ---------------------------------------------------------------- verification

def check(path):
    """Report every structural problem found. Returns a non-zero issue count."""
    doc = open(path, encoding='utf-8').read()
    issues = 0
    print(f'size {len(doc) / 1e6:.2f}MB')

    # Nesting. Start after the stylesheet so CSS braces are out of the way.
    body = doc[doc.find('</style>'):] if '</style>' in doc else doc
    stack = []
    for m in re.finditer(r'<(/?)(div|section|main|article|figure)\b[^>]*>', body):
        tag = m.group(2)
        if m.group(1):                                   # a closing tag
            if not stack:
                print(f'  EXTRA CLOSE </{tag}> at {m.start()}')
                issues += 1
            elif stack[-1][0] != tag:
                opened, pos = stack.pop()
                print(f'  MISMATCH <{opened}> at {pos} closed by </{tag}> at {m.start()}')
                issues += 1
            else:
                stack.pop()
        elif not m.group(0).endswith('/>'):
            stack.append((tag, m.start()))
    if stack:
        print(f'  UNCLOSED at EOF: {stack[:5]}')
        issues += len(stack)
    print(f'nesting: {"OK" if not issues else f"{issues} error(s)"}')

    left = re.findall(r'\{\{[A-Z0-9_]+\}\}', doc)
    print(f'placeholders: {len(left)}' + (f'  {sorted(set(left))}' if left else ''))
    issues += len(left)

    payloads = B64_SRC.findall(doc)
    external = [s for s in re.findall(r'<img[^>]+src="([^"]{0,60})', doc)
                if not s.startswith('data:')]
    dupes = len(payloads) - len({hashlib.md5(p.encode()).hexdigest() for p in payloads})
    tiny = sum(1 for p in payloads
               if len(base64.b64decode(p + '==', validate=False)) < 8000)
    print(f'images: {len(payloads)} embedded, {dupes} duplicate, {tiny} tiny, '
          f'{len(external)} external')
    if external:
        print(f'  external srcs break offline/CSP: {external[:3]}')
    issues += dupes + tiny + len(external)

    # loading="lazy" on an inline data URI defers nothing, and makes every
    # off-screen image report complete===false / naturalWidth===0 -- which reads
    # as "50 of 51 images broken" in a browser check.
    lazy = doc.count('loading="lazy"')
    if lazy:
        print(f'  {lazy} loading="lazy" on inline base64, remove them')
        issues += lazy

    if 'charset' not in doc[:1200].lower():
        print('  missing <meta charset="UTF-8">, expect mojibake in em-dashes')
        issues += 1

    print(f'\n{"PASS" if not issues else f"{issues} issue(s)"}')
    return issues


def lite(src, dst):
    """Write a copy with base64 payloads replaced by 'IMG', for grepping."""
    doc = open(src, encoding='utf-8').read()
    out = B64_ANY.sub('IMG', doc)
    open(dst, 'w', encoding='utf-8').write(out)
    print(f'{len(doc) / 1e6:.2f}MB -> {len(out) / 1024:.0f}KB   {dst}')


# ------------------------------------------------------------------- galleries

def _slide(entry, imgdir):
    """One .gallery-slide: the photo plus its what / where / credit caption."""
    data = base64.b64encode(open(os.path.join(imgdir, entry['f']), 'rb').read()).decode()
    # Captions are authored with HTML entities (&mdash;, &amp;). Decode them to
    # real characters, then re-escape for an attribute -- deleting them instead
    # leaves gaps like "Torii gates  the path".
    alt = html_.escape(html_.unescape(entry['what']), quote=True)
    return ('<div class="gallery-slide">'
            f'<img src="data:image/jpeg;base64,{data}" alt="{alt}">'
            '<div class="gallery-cap">'
            f'<span class="gc-what">{entry["what"]}</span>'
            f'<span class="gc-where">{entry["where"]}</span>'
            f'<span class="gc-credit">{entry["credit"]}</span>'
            '</div></div>')


def gallery(path, manifest_path, labels, imgdir=''):
    """Replace each .gallery-scroll block with the manifest's photos.

    Anchors on the '<label> - N photos - scroll' hint line, whose count is
    rewritten too, so this stays re-runnable on an already-injected document.
    """
    doc = open(path, encoding='utf-8').read()
    before = len(doc)
    manifest = json.load(open(manifest_path))

    for group, label in labels.items():
        items = manifest[group]
        hint = re.compile(rf'<div class="gallery-hint">{re.escape(label)} '
                          r'&middot; \d+ photos &middot; scroll &rarr;</div>')
        found = hint.findall(doc)
        if len(found) != 1:
            sys.exit(f'gallery-hint for "{label}" matched {len(found)}, expected 1')

        m = hint.search(doc)
        doc = (doc[:m.start()]
               + f'<div class="gallery-hint">{label} &middot; {len(items)} photos '
                 '&middot; scroll &rarr;</div>'
               + doc[m.end():])
        block = ('<div class="gallery-scroll">\n    '
                 + '\n    '.join(_slide(x, imgdir) for x in items) + '\n    </div>')
        doc = replace_block(doc, doc.index('<div class="gallery-scroll">', m.start()), block)
        print(f'{group:6s} -> {len(items)} slides')

    open(path, 'w', encoding='utf-8').write(doc)
    print(f'{before / 1e6:.2f}MB -> {len(doc) / 1e6:.2f}MB')


# ------------------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('check').add_argument('html')

    p = sub.add_parser('lite')
    p.add_argument('html')
    p.add_argument('out')

    p = sub.add_parser('gallery')
    p.add_argument('html')
    p.add_argument('manifest')
    p.add_argument('--labels', nargs='+', required=True,
                   help='group=Label pairs matching the gallery-hint text')
    p.add_argument('--imgdir', default='')

    a = ap.parse_args()
    if a.cmd == 'check':
        sys.exit(1 if check(a.html) else 0)
    if a.cmd == 'lite':
        return lite(a.html, a.out)
    return gallery(a.html, a.manifest, dict(p.split('=', 1) for p in a.labels), a.imgdir)


if __name__ == '__main__':
    main()
