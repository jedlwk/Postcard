#!/usr/bin/env python3
"""Crop and re-encode the chosen photos to one uniform size, and report payload.

    imageprep.py plan.json final/ --manifest manifest.json

plan.json maps each chapter to its ordered photos:

    {"kyo": [{"src":    "th/kyo_inari_0.jpg",
              "what":   "The vermilion tunnel of votive gates",
              "where":  "Senbon Torii, Fushimi Inari-taisha",
              "credit": "Luka Peternel, CC BY-SA 4.0"}, ...]}

`credit` is a licence condition, not decoration -- most Commons files are CC BY
or BY-SA.

Sizing is the whole budget conversation. At 820x547 / quality 58, eighty photos
came to 5.6MB on disk and ~7.5MB base64, landing a complete document at 8.6MB.
The same document with only fifty photos at 880px/q60 was 10.9MB, so uniform
re-encoding bought thirty extra photos and still saved 2MB.

Don't feed this multi-megabyte originals. Commons' 900px thumbnail is already
larger than the final crop.

Needs Pillow.
"""
import argparse
import json
import os

from PIL import Image, ImageOps

BASE64_OVERHEAD = 4 / 3
WARN_BYTES = 12e6


def encode(src, dst, size, quality):
    """Center-crop to the exact target ratio and save. Returns bytes written."""
    img = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
    # Cropping to the display ratio here leaves the browser's object-fit:cover
    # almost nothing to trim, and keeps the file smaller than shipping the
    # uncropped frame.
    img = ImageOps.fit(img, size, Image.LANCZOS, centering=(0.5, 0.5))
    img.save(dst, 'JPEG', quality=quality, optimize=True, progressive=True)
    return os.path.getsize(dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plan')
    ap.add_argument('outdir')
    ap.add_argument('--size', default='820x547')
    ap.add_argument('--quality', type=int, default=58)
    ap.add_argument('--manifest', default='manifest.json')
    a = ap.parse_args()

    size = tuple(int(v) for v in a.size.split('x'))
    os.makedirs(a.outdir, exist_ok=True)

    manifest, total = {}, 0
    for group, items in json.load(open(a.plan)).items():
        rows = []
        for i, item in enumerate(items):
            dst = os.path.join(a.outdir, f'{group}{i:02d}.jpg')
            written = encode(item['src'], dst, size, a.quality)
            total += written
            rows.append({'f': dst, 'what': item['what'], 'where': item['where'],
                         'credit': item['credit'], 'kb': written // 1024})
        manifest[group] = rows
        print(f'{group:6s} {len(rows):3d} photos')

    json.dump(manifest, open(a.manifest, 'w'), indent=1)
    count = sum(len(v) for v in manifest.values())
    encoded = total * BASE64_OVERHEAD
    print(f'\n{count} photos  {total // 1024}KB on disk  ~{int(encoded) // 1024}KB as base64')
    if encoded > WARN_BYTES:
        print('WARNING: over ~12MB encoded. Lower --quality or --size.')


if __name__ == '__main__':
    main()
