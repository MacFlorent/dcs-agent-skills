# Reference

## Files in a .miz

| File | Holds |
|---|---|
| `mission` | coalitions and groups, triggers, weather, date, Game Master roles |
| `options`, `warehouses` | copied from the template; `warehouses` also sets airbase coalitions |
| `theatre` | the map name, one line |
| `l10n/DEFAULT/dictionary` | strings the editor keys as `DictKey_*` (briefing texts) |
| `l10n/DEFAULT/mapResource` | `ResKey_*` → file name of each embedded file |
| `l10n/DEFAULT/<file>` | embedded files: scripts, sounds, images |

`mission.coalitions.<side>` lists the country ids allowed on each side;
`mission.coalition.<side>.country[]` holds the groups, by category (`vehicle`, `plane`,
`helicopter`, `ship`, `static`). Group and unit ids are unique across the mission; unit names too.

## Triggers

Two halves that must agree, index for index:

- `mission.trigrules[n]` — what the editor shows: `predicate` (`triggerStart` = MISSION START,
  `triggerOnce`, `triggerContinious`), `rules` (conditions), `actions`
  (`{ predicate = "a_do_script", text = ... }`, `{ predicate = "a_do_script_file", file = <ResKey> }`).
- `mission.trig` — what DCS runs: `actions[n]` and `conditions[n]` as Lua source, `flag[n] = true`,
  and `funcStartup[n]` (MISSION START) or `func[n]` (the others) calling them.

`M.onStart` writes both for a MISSION START trigger. For another kind, copy one from a shipped
mission (`miz.py find '"triggerOnce"'`).

## Game Master

`mission.groundControl.roles.instructor.<side>` = number of Game Master slots.
`artillery_commander`, `forward_observer` and `observer` are the other Combined Arms roles.

## Air groups

- Air start: first waypoint `type = "Turning Point"`, with `alt`, `speed`; the unit carries the
  same `alt`, `speed`, `heading` and `psi = -heading`.
- `payload.pylons[<station number>] = { CLSID = ... }`; `fuel` in kg (internal max in `entry.lua`,
  `M_fuel_max`).
- Main task (`task`) matches what the waypoint tasks do: `Ground Attack` for Bombing,
  `CAS`, `SEAD`, `CAP`, `Nothing`…
