# Python recipes, without Lua

Status: in-progress

## Problem

`building-dcs-missions` builds a `.miz` by running a Lua recipe through `scripts/mizedit.lua`, which
loads the mission's tables and writes them all back. Two costs:

- **The whole mission is rewritten, not only what the recipe adds.** The writer sorts every key and
  writes every non-integer number with `%.17g`, so parts of the template the recipe never touched
  come back as different text, and floats such as headings can change in their last digits.
- **Lua 5.1 is required** next to Python, only for this.

dcs-hotload 1.1.0 solved the same problem for its setup script: a reader and writer of the Mission
Editor's table format, in Python, that keep the file's order, style and numbers, exact on all 951
missions DCS ships. This work brings that approach here, as planned when hotload adopted it.

## What to build

- **`scripts/luatable.py`**: the table reader and writer, taken from dcs-hotload's
  `hotload-setup.py` (same author; it becomes this repository's own code, no shared dependency).
- **`scripts/mizedit.py`**: the recipe helpers, ported from `mizedit.lua` with the same names and
  spec fields (`M.addGroup`, `M.onStart`, `M.doScript`, `M.doScriptFile`, `M.embedFile`,
  `M.bombing`, `M.wrapped`, `M.invisible`, `M.immortal`, `M.option`, `M.gameMaster`) and the same
  checks (duplicate ids and unit names, `trig` and `trigrules` counts, files a trigger names).
- **Recipes are Python files**, run with the mission's tables as globals (`mission`, `options`,
  `warehouses`, `dictionary`, `mapResource`) and `M`. A Lua table becomes a dict, a Lua array a
  list: `M.addGroup{ name = "SAM", units = { { type = "X" } } }` becomes
  `M.addGroup(name="SAM", units=[{"type": "X"}])`.
- **`miz.py build TEMPLATE.miz recipe.py OUT.miz`** runs it in Python: no Lua, no `--lua`. Each
  table is written back only when the recipe changed it, in the style of the file it came from;
  every other entry of the zip is copied unchanged.
- `mizedit.lua` is deleted. The skill's docs, the README and CONTRIBUTING lose Lua 5.1 as a
  requirement for the scripts (luacheck still lints `placement-check.lua`, which runs in DCS).

## Tests

This repository has none yet; they go to `test/`, Python `unittest`, run by CI.

- **Golden builds**: two recipes built by the Lua path before it is deleted — the example of
  `SKILL.md`, and an SA-10 site with an EWR and two embedded scripts — are kept as fixtures. The
  Python build of the same recipes must give the same tables (numbers compared as numbers).
- **Untouched means unchanged**: an empty recipe gives back every entry of the template byte for
  byte; a recipe that adds a group leaves `options`, `warehouses` and `dictionary` byte for byte.
- **The table format**: exact round trip on every table of the template; on request
  (`DCS_AGENT_SKILLS_TEST_SHIPPED_MISSIONS=1`), on every mission DCS ships.
- **The checks**: duplicate unit names, a country not on its side, a trigger naming a missing file.

## Decisions

- **Recipes in Python.** Turned down: Lua recipes with Python reading and writing (recipes would
  stay in the language of runtime scripts, so group tables copy between a recipe and
  `coalition.addGroup` code, but Lua 5.1 stays required and the build spans two languages); both
  languages, Lua as legacy (two build paths to maintain).
- **Same helper names and fields as `mizedit.lua`**, camelCase included, so a Lua recipe ports
  line by line and the skill's text changes little.

## Out of scope

- Porting the recipes of missions that use this skill: the SkynetMunitionTests recipe stays on its
  own copy of the old skill until that project moves to the plugin.
- Sharing the table code with dcs-hotload as a package.
