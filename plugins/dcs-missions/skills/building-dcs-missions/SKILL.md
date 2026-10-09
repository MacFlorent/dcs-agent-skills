---
name: building-dcs-missions
description: Use when creating or editing a DCS World .miz file without the Mission Editor or VEAF tools — placing SAM sites, EW radars, aircraft with payloads, ships, Game Master slots, mission-start triggers, embedded scripts — or when writing group tables for coalition.addGroup, or choosing where on the map to put ground units.
---

# Building DCS missions

A `.miz` is a zip of Lua tables. Build it from a mission the Mission Editor saved, with a Lua
recipe run by `scripts/miz.py`; take every format and name from the DCS install, never from
memory.

For VEAF missions (a `mission.yaml`, VEAF aliases, combat zones), use `veaf-mission-authoring`.

## Build

```bash
python scripts/miz.py build TEMPLATE.miz recipe.lua OUT.miz     # checks, then writes
python scripts/miz.py find '"SetInvisible"' --lines 8           # shipped examples of anything
python scripts/miz.py countries                                 # country ids
python scripts/miz.py unpack OUT.miz dir                        # read what was written
```

**Template**: a mission saved empty by the Mission Editor on the right map. `templates/` holds
`caucasus.miz` (saved by DCS 2.9.30). Another map needs its own: `warehouses` lists that map's
airfields, so a template cannot be relabelled. Ask the user to save an empty mission on that map
(New, pick the map, Save) and add it to `templates/` as `<map>.miz`.

**Recipe** (helpers in `scripts/mizedit.lua`, documented at each function):

```lua
M.gameMaster(1, 1)
M.addGroup{ side = "red", country = { id = 0, name = "Russia" }, category = "vehicle",
  name = "SAM-SA6", x = 25732, y = 454671, tasks = { M.immortal() }, units = {
    { type = "Kub 1S91 str" }, { type = "Kub 2P25 ln", dx = 100 }, { type = "Kub 2P25 ln", dy = 100 } } }
local gbu = { CLSID = "{GBU-38}" }
M.addGroup{ side = "blue", country = { id = 2, name = "USA" }, category = "plane", name = "MQ9",
  x = -14268, y = 454671, alt = 5000, speed = 80, task = "Ground Attack", tasks = { M.invisible(), M.immortal() },
  units = { { type = "MQ-9 Reaper", payload = { pylons = { gbu, gbu, gbu, gbu }, fuel = 1300,
    flare = 0, chaff = 0, gun = 100 } } },
  route = { { x = 15000, y = 454671, tasks = { M.bombing(23732, 454671, 14) } } } }
M.onStart("scripts", { M.doScriptFile(M.embedFile("Scripts/skynet-iads-compiled.lua")),
  M.doScript([==[dofile([[D:\path\dcs-hotload\dcs-hotload.lua]])]==]) })
```

Map metres: `x` north, `y` east; headings in radians from north. `M.embedFile` reads a relative
path from the recipe's folder. The build refuses duplicate ids or unit names, unknown unit types,
a country id that does not match its name, and triggers naming missing files.

## Where the facts are

| Need | Source |
|---|---|
| Unit type names per country | `Scripts/Database/db_countries.lua` (`cnt_unit` lines under the country) |
| Aircraft type, pylons, CLSIDs | `CoreMods/aircraft/<type>/entry.lua`; loadouts in `MissionEditor/data/scripts/UnitPayloads/<type>.lua` and `CoreMods/aircraft/*/UnitPayloads/` |
| Task and option fields | `miz.py find '"<task id>"'`, then unpack that mission |
| Weapon-type numbers | `MissionEditor/modules/me_action_db.lua`, `weaponTable` |
| Country ids | `miz.py countries` (not the line count: DCS skips ids) |

**Published documentation** says what things *do*; the install says how the file *spells* them.
On the Hoggit wiki: the [scripting engine](https://wiki.hoggitworld.com/view/Simulator_Scripting_Engine_Documentation)
(runtime API), [tasks](https://wiki.hoggitworld.com/view/Category:Tasks) such as
[Bombing](https://wiki.hoggitworld.com/view/DCS_task_bombing), commands such as
[SetImmortal](https://wiki.hoggitworld.com/view/DCS_command_setImmortal), AI options from
[setOption](https://wiki.hoggitworld.com/view/DCS_func_setOption),
[addGroup](https://wiki.hoggitworld.com/view/DCS_func_addGroup), and the
[mission editor](https://wiki.hoggitworld.com/view/DCS_mission_editor) pages for trigger and AI
behaviour. The wiki does not describe the `.miz` file, and lags DCS updates: when it and the
install disagree on a name or field, the install wins.

## Placement

No file holds trees or buildings. In order of preference:

1. A spot already flown (a group of an earlier mission that stood there).
2. A spot checked in the running mission: copy `scripts/placement-check.lua` into
   `dcs-hotload/user-lib/` and run it through hotload (**REQUIRED SUB-SKILL:**
   `piloting-dcs-hotload`). It reports surface, slope and buildings, not forests.
3. When DCS is not running: build anyway, and list each unchecked position (group, x, y) in the
   report for the user to check on the Mission Editor map.

## Runtime spawns

`coalition.addGroup(country.id.X, Group.Category.GROUND, group)` takes the same group table as
`M.addGroup` writes (see `reference.md`). Give a spawned group a few seconds before tasking it.

## Common mistakes

| Mistake | Effect | Instead |
|---|---|---|
| Attack task on the first waypoint of an air-started group | not flown | put it on waypoint 2 (`route[1].tasks`) |
| Unit type, CLSID or task field from memory | ME drops the unit or task silently | read it from the sources above |
| Ground units on a guessed spot | units in a forest or on a slope | a flown spot, or `placement-check` |
| `weaponType = 2032` for iron bombs | any bomb | 240 iron, 14 guided (`weaponTable`) |
| Editing `trigrules` without `trig` (or the reverse) | ME shows one thing, DCS runs another | `M.onStart` writes both |
| A rebuilt mission restarted from DCS | the old copy runs (Restart replays the temp copy) | re-open the `.miz` from disk |

## Before saying it works

The build proves the tables load and are consistent. Say what is still unproven: the user opens
it in the Mission Editor (it complains about missing fields), then flies it — units on the
ground, aircraft flying their tasks, scripts loading in `dcs.log`.
