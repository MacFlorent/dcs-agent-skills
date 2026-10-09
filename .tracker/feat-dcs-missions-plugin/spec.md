# The dcs-missions plugin and the marketplace

Status: done

Builds this repository's first content: the `dcs-missions` plugin, from skills that lived
untracked in the SkynetMunitionTests mission (`.claude/skills/`), and the marketplace that lists it.
The rules the plugin follows are in `CONTRIBUTING.md`; this spec says what moves where.
Companion work: dcs-hotload ships its own plugin, specified in that repository.

## Goal

One repository that holds general DCS World knowledge for agents and is the marketplace to
install from:

- the `dcs-missions` plugin: building `.miz` files, and writing Lua that runs inside a mission;
- an entry for the `dcs-hotload` plugin, which lives in its own repository.

`/plugin marketplace add MacFlorent/dcs-agent-skills` once, then install either or both.

## Principles

- **General DCS knowledge only.** What is true of DCS for any mission. Findings tied to one
  project (a test series, a library like Skynet) stay in that project.
- **No mention of dcs-hotload, or of any way to run Lua in a live mission.** Skills describe DCS;
  the agent combines them with whatever runner it has. Where a step needs a live mission, say
  "run this in the running mission".
- **No overlap between skills.** Each fact has one home. Skills of the same plugin may point to
  each other by name (they are always installed together). Routing to another skill for an
  out-of-scope case is fine (`veaf-mission-authoring` for VEAF missions); depending on one is not.
- **Facts from the install, not from memory.** Both skills keep the current rule: unit types,
  CLSIDs, task fields and flags are read from the DCS install or the Hoggit wiki.

## Repository layout

```
.claude-plugin/
  marketplace.json
plugins/
  dcs-missions/
    .claude-plugin/plugin.json
    skills/
      building-dcs-missions/
        SKILL.md
        reference.md
        scripts/miz.py
        scripts/mizedit.lua
        templates/caucasus.miz
      writing-dcs-scripts/
        SKILL.md
        facts.md          measured behaviour, loaded on demand
        scripts/placement-check.lua
README.md                 what is here, how to install, how to add a skill
LICENSE.md
```

`marketplace.json`:

```json
{
  "name": "dcs-agent-skills",
  "owner": { "name": "MacFlorent" },
  "plugins": [
    { "name": "dcs-missions", "source": "./plugins/dcs-missions",
      "description": "Build DCS World .miz files and write mission Lua" },
    { "name": "dcs-hotload",
      "source": { "source": "github", "repo": "MacFlorent/dcs-hotload", "ref": "<release tag>" },
      "description": "Run Lua in a live DCS mission (tool + skill)" }
  ]
}
```

Add the `dcs-hotload` entry once hotload has a release containing `.claude-plugin/plugin.json`.
Pin it to a release tag so the installed skill always matches a released tool; bump the tag when
hotload releases.

Versioning of `dcs-missions`: Claude Code sends users a new copy only when the plugin's computed
version changes (`plugin.json` `version`, else the entry's, else the commit SHA). These skills
have no release pipeline, so **omit `version` in both places**: users then track commits on the
default branch, and every push is an update. Switch to explicit versions only if a stable/latest
split is ever needed. Updates reach users through `/plugin marketplace update dcs-agent-skills`, or
automatically once they enable auto-update for the marketplace in `/plugin` (off by default).

Plugin layout: one plugin for now. Split only when a part should be installable alone (for
example a skill needing a dependency others do not).

## Source material

Everything comes from SkynetMunitionTests `.claude/skills/`:

- `building-dcs-missions/` (SKILL.md, reference.md, scripts, templates)
- `piloting-dcs-hotload/dcs-scripting-facts.md` and the "Writing Lua for a live mission" section of
  `piloting-dcs-hotload/SKILL.md`

Start the repository from a copy (no history to keep: these files are untracked).

## Skill: `building-dcs-missions`

Scope unchanged: editing `.miz` files without the Mission Editor. Changes:

| Change | Detail |
|---|---|
| Recipe example | replace the `dofile(...dcs-hotload.lua)` line with a neutral `M.doScript([==[env.info("mission start")]==])` |
| Placement step 2 | "run `scripts/placement-check.lua` from `writing-dcs-scripts` in the running mission"; drop `dcs-hotload/user-lib/` and the REQUIRED SUB-SKILL line |
| Hoggit wiki paragraph in "Where the facts are" | move to `writing-dcs-scripts`; keep the install-file table here (it is about `.miz` spelling) and point to `writing-dcs-scripts` for runtime API |
| "Runtime spawns" section | move to `writing-dcs-scripts`; keep one line: "the group table `M.addGroup` writes is the one `coalition.addGroup` takes, see `writing-dcs-scripts`" |
| Common mistakes: waypoint-1 row | keep: it is about where a recipe puts the task (`route[1].tasks`). The explanation of the behaviour lives in `writing-dcs-scripts` |
| Common mistakes: restart row | keep: "Restart replays `%TEMP%\DCS\tempMission.miz`; re-open a rebuilt `.miz` from the Mission menu". This is its one home |
| `reference.md` "Group tables at runtime" | move to `writing-dcs-scripts` (runtime API) |
| `reference.md` "For the munition tests" | remove; stays in SkynetMunitionTests |
| `miz.py` DCS install candidates | keep, add `--dcs` / an env variable in the docs since paths differ per machine |

Description unchanged except dropping "or when writing group tables for coalition.addGroup"
(now `writing-dcs-scripts`).

## Skill: `writing-dcs-scripts` (new)

Lua that runs inside a DCS mission: triggers, embedded scripts, scripts run in a live mission.

Description:

> Use when writing Lua that runs inside a DCS World mission — spawning groups with
> coalition.addGroup, tasking AI, setting options, handling events, observing weapons, scheduling
> with timer — or when DCS scripting behaves unexpectedly (a task ignored, a spawn without
> weapons, a missing module).

### SKILL.md

- **The API is on the Hoggit wiki; look it up, do not recall it.** The link table from
  `dcs-scripting-facts.md` (index, addGroup, bombing task, weapon flags, AI options, shot event),
  plus the links now in `building-dcs-missions` (tasks category, setCommand, setOption). The wiki
  lags DCS updates; the install wins on names.
- **Spawning**: same group table as the editor writes (from `reference.md` "Group tables at
  runtime"); a name already in use replaces that group; wait about a second
  (`timer.scheduleFunction`) before giving a fresh group's controller a task, command or option.
  Runtime task tables differ from the `.miz` form (`point = {x, y}` vs `x`, `y`).
- **Tasking air groups**: a task on waypoint 1 of an air-started group is ignored; put it on
  waypoint 2 or `pushTask` it after the spawn delay. Weapon Free does not fix it.
- **Payloads and flags**: CLSIDs, weapon flags and type names from memory fail silently (a jet
  spawns unarmed). Look them up (install files, wiki, `list_payloads` / `list_unit_types` when the
  veaf-mission-editor MCP server is connected) and check `unit:getAmmo()` after spawning.
- **Cleanup**: remove event handlers and spawned groups on every exit path, timeouts included.
- **The environment**: Lua 5.1 (no yield across `pcall`); `io` and `lfs` exist only when
  `MissionScripting.lua` is edited, `os`, `require` and `package` never; `dofile` names a chunk
  with the plain path (no `@`); F10 menus show at most 10 entries per level, no paging; `dcs.log`
  timestamps are UTC.
- `doScript` / `doScriptFile`: how a mission loads Lua at start (trigger actions, embedded files);
  the `.miz` side is in `building-dcs-missions`.

### facts.md (measured, not in the wiki; DCS 2.9)

- **Observing a munition**: follow `e.weapon` from `S_EVENT_SHOT` (guns:
  `S_EVENT_SHOOTING_START`); poll `Object.isExist(weapon)`; height above ground when it disappears
  separates interception (hundreds of metres) from impact; a weapon's `getName()` is `""`, its id
  is `weapon.id_`.
- **Rearming**: a stationary unit within ~30 m of an ammo truck of its side (`Ural-375`,
  `Ural-4320-31`) rearms from about 50 s after the truck appears; measured: IRIS-T one missile per
  ~15 s, C-RAM ~68 rounds per 15 s.
- **A bombing combination proven to release** is project data (stays in SkynetMunitionTests);
  only keep the general rules above.

### scripts/placement-check.lua

Moved from `building-dcs-missions`. Rewrite the header so it does not assume a runner: "returns a
function; `dofile` it or load it however you run Lua in the mission, then call
`check(points, radius)`".

## Not migrated (stays in SkynetMunitionTests)

Skynet behaviour (last line of defence ignores invisibility, out-of-ammo sites stay dark, IADS in
a guarded global), the GBU-38 release recipe, "one engagement at a time" (DCS froze once with
C-RAM and IRIS-T engaging together), `reference.md` "For the munition tests". They become a
project skill or `CLAUDE.md` section there; handled in that repository, not here.

## README

What the plugins do, install commands, the two principles a new skill must follow (general DCS
only; no runner-specific content), and where a new skill goes (into `dcs-missions` unless it
needs to install alone).

## Acceptance

- `grep -ri hotload plugins/` finds nothing.
- No fact appears in both skills (check the Hoggit links, waypoint-1, spawn delay, restart).
- Each skill loads from its description in a fresh session with the plugin installed:
  "build a mission with an SA-6 site on Caucasus" → `building-dcs-missions`; "write a script
  that spawns an F-16 and makes it bomb a point" → `writing-dcs-scripts`.
- `python miz.py build templates/caucasus.miz <recipe> out.miz` works from the plugin's install
  path (no path left pointing at SkynetMunitionTests).
- With both plugins installed in a mission folder, "check that ground at x, y is fit for a SAM
  site" runs `placement-check.lua` through hotload without either skill naming the other.

## Comments

Decided while building:

- **The `dcs-hotload` marketplace entry is not part of this work.** It needs a hotload release that
  contains the plugin; it is an idea in `IDEAS.md` until then.
- **Validation runs without `--strict`.** Strict mode turns the missing-version warning into an
  error, and the plugins have no version on purpose. CI fails on any other warning.
- **`miz.py` also reads `DCS_INSTALL`**, so a machine with DCS elsewhere sets it once instead of
  passing `--dcs` to every command.
- **The license file is `LICENSE.md`**, as in dcs-hotload.
- **luacheck is fetched by `scripts/lint.sh`**, taken from Skynet-IADS: a pinned binary, the same
  locally and in CI, with nothing to install.
- **`facts.md` gained one line**, from the munition-test notes left behind: a unit out of
  ammunition stays empty without a truck nearby. It is true of any mission.

Checked: the recipe example in `building-dcs-missions` builds against DCS 2.9 from the plugin's
folder; `claude plugin validate .` passes with only the version warning; no `hotload` under
`plugins/`; in fresh headless sessions with the plugin loaded, a spawning-and-bombing script task
picks `writing-dcs-scripts`, an SA-6 mission task picks `building-dcs-missions`, and an unrelated
Python task picks neither. `scripts/lint.sh` (luacheck 1.2.0)
is clean. Not checked: the placement check through a runner, anything in DCS beyond the build.
