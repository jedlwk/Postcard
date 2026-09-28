#!/usr/bin/env python3
"""Build a labelled contact sheet so photos are judged by eye, not by filename.

    # candidates, one row per subject, from files named <key>_<n>.jpg
    contactsheet.py sheet.jpg --dir th --keys kyo_inari,nar_todaiji

    # the final set, from an imageprep manifest
    contactsheet.py sheet.jpg --manifest manifest.json --group kyo

This is the step that catches what metadata cannot: a "wildflower meadow" with
snow and no flowers, an October-red garden in a summer document, six near
identical frames of one sunset, or a category that is secretly about skiing.

Then look at the output image. Repeat until every frame is right.

Needs Pillow.
"""
import argparse
import json
import os

from PIL import Image, ImageDraw

LABEL_H = 18


def rows_from_dir(dirname, keys, per_key):
    """One row per key, reading <dirname>/<key>_<n>.jpg."""
    rows = []
    for key in keys:
        paths = [os.path.join(dirname, f'{key}_{i}.jpg') for i in range(per_key)]
        rows.append([(p, f'{key} #{i}') for i, p in enumerate(paths) if os.path.exists(p)])
    return rows


def rows_from_manifest(path, group, cols):
    """Wrap one manifest group into rows of `cols`, labelled with its place."""
    data = json.load(open(path))
    items = data[group] if group else next(iter(data.values()))
    cells = [(x['f'], f'{i}: {x.get("where", "")}') for i, x in enumerate(items)]
    return [cells[i:i + cols] for i in range(0, len(cells), cols)]


def build(rows, out, cell):
    width, height = cell
    cols = max(len(r) for r in rows)
    sheet = Image.new('RGB', (cols * width, len(rows) * (height + LABEL_H)), 'white')
    draw = ImageDraw.Draw(sheet)

    for r, row in enumerate(rows):
        for c, (path, label) in enumerate(row):
            x, y = c * width, r * (height + LABEL_H)
            try:
                img = Image.open(path).convert('RGB').resize((width, height))
                sheet.paste(img, (x, y + LABEL_H))
            except Exception as e:
                # A missing or corrupt frame should be visible in the sheet,
                # not abort the whole audit.
                draw.text((x + 4, y + LABEL_H + 4), f'UNREADABLE\n{e}'[:60], fill='red')
            draw.text((x + 4, y + 3), label[:int(width / 5.6)], fill='black')

    sheet.save(out, quality=80)
    print(f'{out}  {sheet.size[0]}x{sheet.size[1]}  {sum(len(r) for r in rows)} frames')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out')
    ap.add_argument('--dir', help='directory of <key>_<n>.jpg candidates')
    ap.add_argument('--keys', help='comma-separated subject keys, one row each')
    ap.add_argument('--per-key', type=int, default=6)
    ap.add_argument('--manifest', help='imageprep manifest instead of --dir')
    ap.add_argument('--group', help='which manifest group to show')
    ap.add_argument('--cols', type=int, default=4)
    ap.add_argument('--cell', default='300x200')
    a = ap.parse_args()

    if a.dir:
        rows = rows_from_dir(a.dir, a.keys.split(','), a.per_key)
    elif a.manifest:
        rows = rows_from_manifest(a.manifest, a.group, a.cols)
    else:
        ap.error('need --dir or --manifest')

    build(rows, a.out, tuple(int(v) for v in a.cell.split('x')))


if __name__ == '__main__':
    main()
