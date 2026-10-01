# Pitfalls

Bugs already hit, and the fix. Read before debugging.

## Contents
- Photos
- Verification
- Legacy HTML guides
- Browser checks

## Photos

- **Two Wikimedia hosts want different User-Agents.** The API wants a descriptive bot UA with contact info. `upload.wikimedia.org` wants a browser UA and returns 403 to the bot one.
- **Download serially**, about 1.3 seconds apart. Parallel downloads trip 429.
- **Full-text search crosses continents.** Resolve a category first.
- **A broad category returns details, not the icon.** Always run `subcats` and drill down.
- **A category with zero files is usually a container.** Use `--deep 2`.
- **A season filter on city architecture starves the pool.** Apply it to nature and foliage only.
- **Non-photographic files outrank photos on size.** Keep a standing avoid-list (plans, engravings, postcards, paintings, maps).
- **Keyword scoring needs the file's own categories.** Bare filenames carry no subject.
- **Over-eager `--avoid` demotes the good photo.** Look at the contact sheet.
- **Metadata is not enough.** Look at every photo for subject and season.
- **Some places have no usable photo.** Substitute honestly and caption what it shows.
- **Never use `loading="lazy"`** on inline base64 images.

## Verification

- **Content bugs hide in prose.** After any itinerary change, sweep the text for stale numbers: nights, days, "five parks", a drive time.
- **Check every dependent reference when something is dropped.** A removed stop leaves links, tabs and sentences behind.
- **An unconfirmed event is flagged, not removed.**
- **A claim copied from a past year is the most common error.** Re-check anything dated.

## Legacy HTML guides

Only for older guides with no `plan.json`.

- **Balanced tag counts do not prove correct nesting.** Use `htmltool.py check`, which walks depth.
- **Never regex for a closing tag.** Use `htmltool.find_close`.
- **Assert before you replace.** `assert html.count(anchor) == 1`, and write the file only at the end.
- **Keep a backup before structural surgery.**
- **A lightbox wrapper must be a `<div>`, never an `<a>`**, and hidden anchors need to be out of the grid.
- **Grid tracks need `minmax(0, 1fr)`** or a wide child blows the layout out.
- **`:nth-of-type` tab mapping needs real `id` and `for` pairs.**
- **Equal CSS specificity is decided by source order.** A later patch block wins.

## Browser checks

- **Screenshots go blank on pages over about 8 MB.** Check with script, or render a copy with placeholder images.
- **Simulated clicks do not fire `:target` or `<details>`.** Set `open` in script, or test by hand.
