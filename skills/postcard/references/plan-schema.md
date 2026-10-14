# plan.json

The agent writes the content here. `render_guide.py` owns the layout. Complete examples are `tests/samples/sample-lean-plan.json` (lean, with a swap) and `tests/samples/sample-plan.json` (full depth). Run `render_guide.py plan.json --check` to validate a plan without rendering.

## Contents
- Inline text
- Top level
- A stop
- Swaps
- Word budgets
- Overview and extra tabs
- Paths

## Inline text

Plain strings. These markers work anywhere in text:

| Write | Shows |
|---|---|
| `**bold**`, `*italic*` | bold, italic |
| `[label](https://url)` | a link |
| `{must}` | MUST-SEE tag |
| `{book}` | BOOK AHEAD tag |
| `{car}` | car tag |
| `{michelin:star}`, `{michelin:bib}`, `{michelin:rec}` | Michelin tags |

Entities such as `&ndash;` and `&amp;` are kept as written. Everything else is escaped.

## Top level

| Field | Notes |
|---|---|
| `title`, `headline`, `lede` | page title, hero headline, a lede of up to 35 words |
| `eyebrow` | optional small line above the headline (defaults to the stop names) |
| `start`, `end` | ISO dates. Weekday labels are computed from these |
| `hero` | `image`, `alt`, `credit` (required) |
| `route` | optional list of `home`, `fly`, `drive`, `stop` nodes. Built from the stops if missing |
| `flights` | `label`, `start`, `end` (local ISO date-times), `note`. Go into the calendar file |
| `book_check` | `when`, `text`, optional `date` (ISO). Items with a date become calendar events |
| `weather` | `title`, `intro`, `rows` (`label`, `sub`, `lo`, `hi`, `feels_lo`, `feels_hi`, `rain`, `wind`, `color`), `notes` |
| `risks` | `tag`, `title`, `intro`, `cards` (`title`, `kicker`, `items`) |
| `sources` | list of `claim`, `url`, `checked`. Every price, hour, closure and date goes here |
| `verification` | `status` (`verified`, `partial`, `unchecked`), `checked` (date), `second_pass` (true once done). Anything but `verified` shows a banner |
| `stops` | list of stops, in order |
| `extras` | extra tabs: `id`, `name`, `sub`, `title`, `intro`, `cards` |
| `footnote` | closing note, shown under the tabs |
| `stage` | `researched`, `photos` or `built`. Lets a stopped build resume |
| `depth` | leave out for a lean guide. `"full"` lifts the word budgets and allows `shortlist`, `more` and `reading` |
| `swaps` | groups of alternative versions (see Swaps) |

## A stop

| Field | Notes |
|---|---|
| `id`, `name`, `tab`, `tab_sub` | `tab` is the short tab name, `tab_sub` something like "3 nights" |
| `color` | `s1` to `s8` |
| `dates` | display line, for example `Sat&ndash;Tue, Jul 17&ndash;20, 2027 &middot; 3 nights` |
| `sleep` | default place to sleep, shown in the Overview table (a day can override with its own `sleep`) |
| `badges` | `category`, `intensity` (1 to 3), `vibes` |
| `maps_link` | `url`, `label` |
| `alert` | `label`, `text`: a risk that lands on these dates |
| `photos` | each: `file`, `what`, `where`, `credit` |
| `map` | `file`, `caption`, `credit`, `source_url` (a real published map) |
| `days` | each: `date` (ISO), `cat` (one or up to three of Arrival, Travel, Food, Nature, Culture, Festival, Scenic, Market, as a string or a list: a day is often a mix), `lead`, `bullets`, optional `drive_h` (hours), `sleep`, `swap` |
| `stays` | each: `nights`, `base`, `why`, `pick` (`name`, `text`, optional `tag`), `alts` (`label`, `text`), `links`, optional `swap` |
| `know`, `cards` | plain lists for the side column (`cards` have a `title`) |
| `festivals` | each: `tag` (`high`, `likely`, `uncertain`, `risk`), `text` |
| `fun_fact` | one verified fact |
| `hikes` | `sub`, `items` (`name`, `tier` must/high/good, `trait`, `stats`, `diff`, `where`, `url`) |
| `shortlist` | `groups` of `spots` (`name`, `url`, `must`, `car`, `meta`, `why`) |
| `more` | `Food`, `Markets`, `Nature`, `Culture`, `Nightlife`, `Festivals`, each a list of `name`, `why`, `area` |
| `reading` | list of `label`, `src`, `url` |

## Swaps

A swap lets the reader pick between whole versions of the trip. The first option is the default. The usual use is the order of the middle stops.

```json
"swaps": [{"id": "order", "label": "Order of the two big blocks", "options": [
  {"id": "olympic-first", "name": "Olympic, then Rainier", "note": "Starts with the lavender festival",
   "tabs": ["olympic", "rainier", "seattle"]},
  {"id": "rainier-first", "name": "Rainier, then Olympic", "note": "Misses the festival",
   "tabs": ["rainier", "olympic", "seattle"]}]}]
```

- **`tabs`** (optional) lists every stop id once, in that order. It reorders the tabs, the "Next" links and the Start link.
- **`swap`** on a day, stay or route item: `"order:rainier-first"` (a list tags several groups). Untagged items always show.
- **`dates` and `tab_sub`** of a stop can be a string, or an object keyed by tag: `{"order:olympic-first": "Sat to Mon", "order:rainier-first": "Tue to Fri"}`.
- **`route`** nodes take `swap` too, so the strip shows the route for the chosen order. Author both routes.
- Each option shows its total driving, summed from `drive_h` on the days it tags. The calendar file uses the first option only.
- Stop numbers ("Stop 1") are left off when an order can change.

## Word budgets

Checked by `render_guide.py --check` unless `depth` is `full`. Counts are visible words.

| Where | Limit |
|---|---|
| `lede` | 35 words |
| a day `lead` | 12 words |
| `bullets` | 4 a day, 18 words each |
| a stay `why`, `pick.text`, `alts` | 20, 22 words, 1 alt of 20 |
| `know` | 3 items of 18 words |
| `festivals` | 3 items of 20 words |
| `hikes` | 3 items |
| `cards`, `fun_fact` | 1 card, 20 words |
| `risks` | 4 cards, 3 items each, 20 words each |
| `book_check` | 8 items of 18 words |
| a swap option `note` | 14 words |

## Overview and extra tabs

The Overview table is built from every stop's `days`. Extra tabs are lists of `cards`: a `title`, an optional `kicker`, and `items`.

## Paths

Image paths are relative to the plan's folder. Keep the layout `<trip>/plan.json`, `<trip>/photos/`, and the guide is written beside the plan.
