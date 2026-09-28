# Pitfalls

Every entry here is a bug that actually shipped and had to be diagnosed. Read
this before debugging — the cause is probably already written down.

---

## Structure

### Tag COUNT balance does not prove correct NESTING

This one bit twice, and cost the most time both times.

A stray `</div>` left behind when deleting a block made an entire chapter a
*child* of the previous chapter, while document-wide `<div>`/`</div>` counts
stayed perfectly balanced (367/367). The count check passed clean for several
rounds. The browser's error-recovery parser folded everything after the fault
inside the unclosed chapter, rendering it outside the page's `max-width`
container at full browser width. The user reported it as "Mount Rainier is
hyper extended to the ends of the page."

Worse: the first fix attempt — *adding* a closing tag — was wrong. It just moved
the imbalance and prematurely closed `.page`.

**When counts are balanced but nesting is wrong, the bug is a pair**: a missing
close in one place and a stray close in another. Fix both halves.

Use `htmltool.py check`, which walks a stack and reports byte offsets. Also
confirm in a browser that every chapter's `parentElement` is the page container
and not another chapter.

### Never regex for a closing tag

`re.search(r'<div class="gallery-scroll">.*?</div>', ...)` stops at the first
nested close. Use `htmltool.find_close()`, which tracks depth.

### Assert before you replace

`assert html.count(anchor) == 1` before every string replacement. On a 9MB file
you are editing blind; a silent 0-match or 2-match replacement is worse than a
crash. Write the file only at the end of the script so a failed assertion
corrupts nothing.

### Keep a backup before structural surgery

Copy the file to a scratch directory first. An 8MB file full of embedded base64
cannot be cheaply regenerated.

---

## Images

### The two Wikimedia hosts want different User-Agents

- `commons.wikimedia.org/w/api.php` — needs a **descriptive bot UA** with contact
  info. A generic or absent UA returns a ~2KB HTML error page, which a naive
  file-size check mistakes for a successful download.
- `upload.wikimedia.org` (the actual files) — needs a **real browser UA**. A
  descriptive bot UA gets a flat `403 Forbidden`.

Each host rejects the other's UA. `commons.py` keeps them as two constants;
don't merge them. A 403 is not transient — don't retry it, surface it.

### Download serially

A 4-thread parallel fetch tripped HTTP 429 after ~13 files and failed the
remaining 70. Serial with a ~1.3s delay and exponential backoff completes 100%.
Run it in the background and poll for the process to exit.

### Never put `loading="lazy"` on an inline base64 image

It defers nothing — there is no network fetch. Worse, off-screen lazy images
report `complete === false` and `naturalWidth === 0`, so a browser check screams
"50 of 51 images broken" when everything is fine. `htmltool.py check` flags these.

### Full-text search crosses continents

Real results: "Blue Lake" → Mount Gambier, Australia. "Rainy Lake" → Minnesota.
"Queen Elizabeth Park" → lions in Uganda. "Chihuly Garden and Glass" → Kew
Gardens, London. "Reflection Lakes" → Toronto City Hall. Resolve a category
first with `find-cat`, and fall back to search only for thin categories.

### A broad category returns details, not the icon

"Widest, in-season" is not "representative". Ranking a broad category by
resolution and date produced a **cat** as the top Fushimi Inari result, **no
deer** anywhere in Nara Park, and four interior ceiling shots for Tōdai-ji.

Fix: `subcats` the broad category and pick a specific one. Don't guess the
narrower name — Commons' sub-category names are semantic and enumerating them
takes one call.

### A season filter on city architecture starves the pool

Constraining Milan/Venice/Florence/Rome to Sep–Nov on an October trip shrank each
candidate list so hard that the ranking fell through to an engraving for San
Miniato, an albumen print for the Colosseum, a mosaic lunette for the Florence
Duomo and a porcelain dinner service. Season is invisible in a cathedral facade —
apply the month filter to nature and gardens only.

### Non-photographic files outrank photos on size

Plans, engravings, postcards, paintings, models and maps are often the largest
files in a category, so a size tiebreak hands them the top slot. Keep a standing
avoid-list, and note that the terms have to match the actual title: `--avoid
carousel,kiosk,playground` did nothing against a file called
`Baby Karts - Villa Borghese`.

### Converting a lightbox doc to galleries orphans the surviving links

Removing the `.lightbox` modals leaves any `<a href="#lb-...">` that wrapped a
photo you kept — the anchor still renders as clickable and now jumps nowhere.
Sweep for `href="#lb-` after the conversion and unwrap them. Also check for
`<figure class="chapter-hero">`-style extras that only some chapters had; with a
full gallery per chapter they are both redundant and inconsistent.

### Shared CSS rules hide inside dead-code sweeps

Deleting `.gallery figure, .info-card { transition: ... }` as part of removing the
old `.gallery` grid would silently strip the transition from every info card.
Rewrite shared selectors rather than deleting them.

### A category with zero files is usually a container, not a dead end

`Buildings of Tōdai-ji` and `Gates of Todaiji` each return zero files. They hold
only further sub-categories; the photos live one level down. `--deep 2` pools the
leaves and turned that same query into 262 usable files with Daibutsuden
exteriors ranked first. `list-cat` now prints the sub-category list when a
category comes back empty, so this is visible rather than mystifying.

### Keyword scoring needs the file's own categories

Scoring on title and description alone fails on exactly the files that need it
most — the ones named `IMG_4821.jpg` or `- panoramio - ESU.jpg`. Those files
still carry real categories ("Towers in Japan", "Inari fox statues"), so fold
them into the haystack. Strip licence and upload bookkeeping categories
("CC-BY-4.0", "Photographs taken on 2019-04-01", "Self-published work") first,
or they add noise and can match a keyword by accident.

### Over-eager `--avoid` demotes the good photo

`--avoid fox` on Fushimi Inari knocked out the votive-torii-with-fox-guardians
shot and promoted one with overhead power lines through the frame. Avoid terms
are a blunt −3; use them for whole wrong subjects (`interior`, `map`,
`woodblock`), not for incidental details.

None of this substitutes for the contact sheet.

### Metadata is not enough — look at the photos

Capture-date filtering gets you most of the way. Only a contact sheet caught: a
Hurricane Ridge "wildflower meadow" with snow-covered peaks and zero flowers, an
October-red Japanese garden, autumn huckleberry at Nisqually Vista, and a
"Cutthroat Lake" category that is really about backcountry *skiing*.

### Some places have no usable photo — substitute honestly

Blue Lake (WA) has only deep-snow April shots. Marymere Falls has essentially
nothing. Caption the substitute for what it actually shows, and tell the user.

### Watch for a lost data URI prefix when swapping an image

Dropping `data:image/jpeg;base64,` during a replacement produces a silently
broken image. `htmltool.py check` catches it as an external src.

---

## CSS

### Equal specificity is decided by source order

Hit twice.

1. A bare `.tab-panel-content { display: none; }` ties with `.cat-list
   { display: flex; }` — both single-class. `.cat-list` is declared later, so it
   wins and every panel stays visible. Fix: scope to
   `.explore-tabs .tab-panel-content` (two classes).
2. A `position: sticky` override inside a media query must come **after** the base
   rule in source order, not before.

Never use inline `style="display:none"` as a "safety default" — inline beats
every class rule including the `:checked` toggle, so it can never be un-hidden.

### `:nth-of-type` tab mapping needs real `id`/`for` pairs

Labels with no `for` attribute do nothing when clicked. The positional selector
pattern is otherwise ID-free and applies to every location's tab block unchanged.

### The lightbox wrapper must be a `<div>`, never an `<a>`

HTML forbids nested anchors. Wrapping the modal in `<a>` so the close button is
"just another anchor inside" makes the browser auto-close the outer anchor at the
inner one — the image and caption fall out of the container and render as
always-visible content stacked at the bottom of the page. `:target` works fine on
a plain `<div>`.

### A negative-margin bleed needs its parent's padding to cancel

`.hero { margin: 0 -24px; }` only works if `.hero` is genuinely *inside* the
padded page container. As a sibling, it pushes the page 24px past the viewport on
each side. Invisible on macOS (scrollbars hide at rest) but visible as clipped
text in a real screenshot. The check that catches it:
`document.documentElement.scrollWidth > window.innerWidth`. Run it whenever a
user says the layout looks "off".

### Grid tracks need `minmax(0,1fr)`

A bare `1fr` won't shrink below its content's min-content width. Also set
`min-width: 0` on flex children holding text.

### Port CSS when you port markup

A `.fest-list` class was used in every chapter of one document but its CSS was
only ever added to the sibling document. It rendered as an unstyled `<ul>` and
looked merely plain rather than broken. Grep the `<style>` region for the class,
don't just confirm the markup copied.

---

## Verification

### Screenshots go blank on heavy pages

Above roughly 8MB, preview tools render a solid blank even though the DOM and CSS
are correct, and `window.innerWidth` can report 0. Trust JS state checks —
`naturalWidth`, `getComputedStyle`, element counts. To eyeball a new component,
extract it plus the `<style>` block into a small standalone file and screenshot
that instead.

### Simulated clicks don't fire `:target` or `<details>`

Set `location.hash` or `element.open` directly instead of concluding the pattern
is broken.

### Content bugs hide in prose

A hero lede still read "Four nights at Olympic" long after the split changed to
three. The route strip and chapter headers were both correct, so nothing else
surfaced it. When a number changes, grep the prose too.

### Sweep for every dependent reference when something is dropped

Removing one festival touched: the hero lede, route strip, weather heading, six
chapters' date lines, day lists, sidebar cards, prose, fun facts, further
reading, a shared tab panel, a photo caption, a rental-car sentence, and a
closure caveat. After the main edits, grep broadly for the dropped term and
assume the first pass missed something.
