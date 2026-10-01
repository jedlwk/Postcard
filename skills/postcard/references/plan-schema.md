# plan.json

The agent writes the content here. `render_guide.py` owns the layout. A complete example is `tests/samples/sample-plan.json`. Run `render_guide.py plan.json --check` to validate a plan without rendering.

## Contents
- Inline text
- Top level
- A stop
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
| `title`, `headline`, `lede` | page title, hero headline, one short paragraph |
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
| `days` | each: `date` (ISO), `cat` (Arrival, Travel, Food, Nature, Culture, Festival, Scenic), `lead`, `bullets` |
| `stays` | each: `nights`, `base`, `why`, `pick` (`name`, `text`), `alts` (`label`, `text`), `links` |
| `know`, `cards` | plain lists for the side column (`cards` have a `title`) |
| `festivals` | each: `tag` (`high`, `likely`, `uncertain`, `risk`), `text` |
| `fun_fact` | one verified fact |
| `hikes` | `sub`, `items` (`name`, `tier` must/high/good, `trait`, `stats`, `diff`, `where`, `url`) |
| `shortlist` | `groups` of `spots` (`name`, `url`, `must`, `car`, `meta`, `why`) |
| `more` | `Food`, `Markets`, `Nature`, `Culture`, `Nightlife`, `Festivals`, each a list of `name`, `why`, `area` |
| `reading` | list of `label`, `src`, `url` |

## Overview and extra tabs

The Overview table is built from every stop's `days`. Extra tabs are lists of `cards`: a `title`, an optional `kicker`, and `items`.

## Paths

Image paths are relative to the plan's folder. Keep the layout `<trip>/plan.json`, `<trip>/photos/`, and the guide is written beside the plan.
