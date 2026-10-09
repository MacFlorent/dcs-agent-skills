# dcs-agent-skills

Agent skills for DCS World: what an agent needs to know to build missions and write the Lua that
runs inside them, loaded when a task calls for it. Published as a Claude Code plugin marketplace.

## Plugins

### dcs-missions

| Skill | Loads when the agent… |
|---|---|
| `building-dcs-missions` | creates or edits a `.miz` without the Mission Editor: groups, payloads, triggers, embedded scripts, where to put ground units |
| `writing-dcs-scripts` | writes Lua that runs in a mission: spawning, tasking, options, events, timers, observing weapons |

The skills read names and formats from your DCS install rather than from memory, and say where
the Hoggit wiki documents the scripting API. They do not run anything in DCS: to act on a live
mission, the agent needs a way to run Lua there, which these skills leave to you: `dcs-hotload`,
below, is one.

The scripts of `building-dcs-missions` need **Python 3** only: recipes are Python, and the `.miz`
is read and written without Lua, keeping what a recipe does not change as it was. They find the
DCS install in its usual places, or through the `DCS_INSTALL` environment variable.

### dcs-hotload

The Claude Code plugin of [dcs-hotload](https://github.com/MacFlorent/dcs-hotload), a tool that
runs Lua inside a live DCS mission through a file mailbox. Its skill sets the tool up in a mission
folder (deploys it, checks `MissionScripting.lua`, adds the boot trigger to the `.miz`, asking
before each change outside the mission folder) and drives a running mission through it. It needs
Python 3 and Git Bash.

The plugin lives in its own repository and is listed here pinned to a release tag: it installs
the released tool, and moves to a new release with a pull request here.

## Install

In Claude Code:

```
/plugin marketplace add MacFlorent/dcs-agent-skills
/plugin install dcs-missions@dcs-agent-skills
/plugin install dcs-hotload@dcs-agent-skills
```

Install either or both.

Updates arrive with `/plugin marketplace update dcs-agent-skills`, or by themselves once
auto-update is turned on for the marketplace in `/plugin` → Marketplaces.

## Contributing

`CONTRIBUTING.md`: how a skill is written, checked and proposed.

## License

Apache License 2.0, in `LICENSE.md`.
