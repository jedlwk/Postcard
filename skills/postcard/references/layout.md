# Layout

## Contents
- What the renderer builds
- Design rules
- Editing a guide
- Verifying in a browser

## What the renderer builds

`scripts/render_guide.py plan.json` writes one self-contained HTML file (fonts and photos embedded, no scripts) plus a calendar file. The CSS and fonts live in `templates/`. Do not hand-write markup. Change the plan or the template.

- **Top:** cover photo, route strip, then a sticky tab bar.
- **Overview tab:** day-by-day table (each row opens its stop), a dated "book and check" list with a calendar link, weather, risks, sources, and a banner if the guide is not fully verified.
- **One tab per stop:** header, photos with the map beside them, "Day by day" next to a side column (where to stay, know before you go, festivals, fun fact), hikes, an optional shortlist, and the longer places list folded into a block.
- **Extra tabs:** layover, logistics or anything else, as cards.
- **Print:** every tab prints, the tab bar and carousels are hidden.

## Design rules

- Warm paper palette, one accent colour per stop (`s1` to `s8`), a separate colour per place category, and a confidence tag for dates.
- Light and dark mode come from the template. If you add a colour token, add it to the light root and both dark blocks.
- Tabs are CSS only: radio inputs, labels and `:checked` rules. Panels and radios must stay siblings of the tab bar. Day rows in the Overview are labels for the same radios.
- Write short, specific text. Few dashes, no filler, no notes about how the guide was made.

## Editing a guide

- **A guide with a `plan.json`:** edit the plan and re-render. Never edit the HTML.
- **An older guide without one:** `htmltool.py lite guide.html lite.html` strips the base64 so you can read it. Edit with a script that asserts each target appears exactly once, and write the file only at the end. Find a block's end with `htmltool.find_close`, never a regex.

## Verifying in a browser

- Run `validate_guide.py guide.html --plan plan.json` first. It must pass.
- Pages over about 8 MB screenshot blank. Check with script instead: every tab shows its panel, 0 broken images, no horizontal scroll at 375 px. For a visual look, render a copy with tiny placeholder images.
- Simulated clicks do not fire `:target` or `<details>`. Test those by hand or set `open` in script.
