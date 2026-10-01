"""Generate placeholder images for the sample plan (so tests need no downloads)."""
import os, sys
from PIL import Image, ImageDraw

def make(folder):
    os.makedirs(folder, exist_ok=True)
    spec = {'hero': (1600, 900, (31, 93, 79)), 'a1': (1200, 800, (200, 140, 90)), 'a2': (1200, 800, (90, 140, 170)), 'a3': (1200, 800, (150, 120, 190)),
            'b1': (1200, 800, (110, 160, 110)), 'b2': (1200, 800, (190, 90, 90)), 'map': (900, 700, (225, 230, 215))}
    for k, (w, h, c) in spec.items():
        im = Image.new('RGB', (w, h), c); d = ImageDraw.Draw(im)
        for i in range(0, w, 80):
            d.line([(i, 0), (w - i, h)], fill=tuple(min(255, v + 25) for v in c), width=6)
        d.text((40, 40), k, fill=(255, 255, 255))
        im.save(os.path.join(folder, k + '.jpg'), quality=85)

if __name__ == '__main__':
    make(sys.argv[1])
