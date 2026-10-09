---
name: writing-dcs-scripts
description: Use when writing Lua that runs inside a DCS World mission — spawning groups with coalition.addGroup, tasking AI, setting commands and options, handling events, observing weapons, scheduling with timer, checking ground for a unit — or when DCS scripting behaves unexpectedly (a task ignored, a spawn without weapons, a missing module).
---

# Writing DCS scripts

Lua inside a mission: trigger actions, embedded scripts, code run in a live mission. The API is
large and recalled details are often wrong: look each call up. To write the `.miz` itself
(groups, triggers, embedded files), use `building-dcs-missions`.

## The API: Hoggit wiki

| Need | Page |
|---|---|
| Index of singletons, classes, enums, tasks, events | https://wiki.hoggitworld.com/view/Simulator_Scripting_Engine_Documentation |
| Spawning (`coalition.addGroup`): group table, payload, route | https://wiki.hoggitworld.com/view/DCS_func_addGroup |
| Tasks, such as Bombing | https://wiki.hoggitworld.com/view/Category:Tasks, https://wiki.hoggitworld.com/view/DCS_task_bombing |
| Commands (`setCommand`), such as SetImmortal | https://wiki.hoggitworld.com/view/DCS_command_setImmortal |
| AI options (`setOption`): ROE, REACTION_ON_THREAT | https://wiki.hoggitworld.com/view/DCS_func_setOption, https://wiki.hoggitworld.com/view/DCS_enum_AI |
| Weapon flags (`weaponType`) | https://wiki.hoggitworld.com/view/DCS_enum_weapon_flag |
| Shot event (`S_EVENT_SHOT`; guns use `S_EVENT_SHOOTING_START`) | https://wiki.hoggitworld.com/view/DCS_event_shot |

The wiki lags DCS updates: when it and the DCS install disagree on a name or field, the install
wins (`building-dcs-missions` lists where the install spells them).

## Spawning

`coalition.addGroup(countryId, Group.Category.GROUND | AIRPLANE | HELICOPTER | SHIP, group)` takes
the group table the Mission Editor writes, minus what it computes: `groupId` and `unitId` are
optional, and `x`/`y`, `route` points, `task`, `payload`, `alt`, `speed` mean the same.

- **A name already in use replaces that group or unit** (a way to respawn, and a way to destroy
  one by accident): make names unique.
- **A fresh group's controller is not ready at once.** Wait before giving it a task, command or
  option (`timer.scheduleFunction`, a second has been enough); the wiki warns that doing it at once
  can crash the game.
- **Task tables differ from the `.miz` form**: the file's Bombing task has `x`, `y`;
  `controller:setTask` wants `point = { x = ..., y = ... }`. Copy a runtime task from the wiki page
  of that task, not from a `.miz`.
- Commands and options set on a waypoint in the editor are available at runtime:
  `group:getController():setCommand({ id = "SetImmortal", params = { value = true } })`.

## Tasking air groups

**A task on waypoint 1 of an air-started group is ignored**: the aircraft flies the route and
never attacks; Weapon Free does not fix it (it then attacks whatever it sees, late). The same task
on waypoint 2, or pushed with `controller:pushTask` after the spawn delay, executes.

## Payloads, flags and type names

Recalled CLSIDs, weapon flags and unit type names may be wrong, and fail silently: a jet spawns
unarmed, a unit is skipped. Look them up — the install files `building-dcs-missions` lists, the
wiki for flags, or `list_payloads` / `list_unit_types` when the veaf-mission-editor MCP server is
connected — and check `unit:getAmmo()` after spawning.

## Events, timers and cleanup

- Remove event handlers (`world.removeEventHandler`) and spawned groups on every exit path,
  timeouts included.
- Keep the id `timer.scheduleFunction` returns, and `timer.removeFunction` it when the work it
  guards ends another way.

## The environment

- Stock **Lua 5.1**: no yield across `pcall`.
- `MissionScripting.lua` (in the DCS install) removes `io`, `lfs`, `os`, `require` and `package`
  from the mission. The usual edit unlocks `io` and `lfs` only: no clock, no file rename or delete.
  It is install-wide, affects every mission including multiplayer, and DCS updates revert it.
- A mission loads Lua at start through trigger actions: DO SCRIPT (text) and DO SCRIPT FILE (a file
  embedded in the `.miz`). `dofile` names a chunk with the plain path, no `@`.
- F10 menus (`missionCommands`) show at most 10 entries per level and do not page; a 13th entry
  breaks the menu.
- `dcs.log` (`Saved Games\DCS\Logs`) timestamps are UTC.

## Measured behaviour

[facts.md](facts.md): what the wiki does not say, measured in DCS — observing a munition in
flight, how ground units rearm. Read it before measuring weapons or engagements.

## Checking ground for a unit

`scripts/placement-check.lua` (in this skill's folder) returns a function; load it in the running
mission and call `check(points, radius)`. For each point it reports surface types, height spread
and buildings in the radius. Trees are invisible to the scripting engine: it cannot see a forest.
