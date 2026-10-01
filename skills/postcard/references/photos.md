# Photos

## Contents
- Source and licence
- The workflow
- Rules that matter
- Size and credits

## Source and licence

Wikimedia Commons only: public domain or CC licensed. Credit every photo (photographer and licence) because attribution is a licence condition. Never caption a substitute as the real place. If a place has no usable photo, use a nearby one and caption what it really shows.

## The workflow

Run the scripts in `scripts/`, in this order:

1. `commons.py find-cat "<place>"` resolves a category name.
2. `commons.py subcats "<category>"` lists sub-categories. **This step is not optional.** A broad category returns close-ups and oddities. A sub-category returns the icon (for example `Deer in Nara`, not `Nara Park`).
3. `commons.py list-cat "<sub-category>" --months 7,8 --prefer a,b --avoid x,y --json picks.json` ranks the files. Add `--deep 2` when the category only holds sub-categories. `--months` ranks nature and foliage by the travel season.
4. `commons.py fetch picks.json <trip>/photos/` downloads the 900 px thumbnails, one at a time.
5. `contactsheet.py sheet.jpg --dir <trip>/photos/ --keys <names>` makes a labelled grid. **Look at it.** Metadata cannot tell you a "wildflower meadow" is full of snow.
6. Reference the chosen files straight from `photos/` in `plan.json` (no copying). `render_guide.py` crops and encodes them (820 by 547). Unused files are ignored.

## Rules that matter

- **Season.** Match the trip's season for nature, gardens and foliage. Do not filter city architecture by month, because it shrinks the pool onto engravings and prints.
- **Avoid** plans, engravings, lithographs, postcards, paintings, models, maps and inscriptions. They win on file size.
- **Two hosts, two User-Agents.** The API needs a descriptive bot UA with contact info. `upload.wikimedia.org` needs a browser UA and rejects the bot one. `commons.py` handles both.
- **Download serially**, about 1.3 seconds apart. Parallel downloads get rate limited.
- **Never use `loading="lazy"`** on inline base64 images.
- **Maps** must be real published maps (NPS, Wikivoyage, Commons). Never draw one.

## Size and credits

About 4 to 5 photos per night: 2 nights is 12, 3 nights is 16. At most 2 photos of one place. At 820 by 547 and quality 58, 80 photos is about 8.6 MB. Keep the whole file under about 12 MB.
