# dcs-agent-skills — Claude Code instructions

> Agent skills for DCS World, published as a Claude Code plugin marketplace. Every merge to `main`
> reaches users on their next update; nothing is built.

**`CONTRIBUTING.md` is the guide, and its steps for a change are mandatory.** Read them before
starting a change, and again after a context compaction: this file is the only one that stays
loaded.

## Never

- **Mention dcs-hotload, or any other way of running Lua in a live mission, under `plugins/`.**
  Skills describe DCS; the agent brings its own runner. CI fails on the word `hotload`.
- **Put a fact in two skills.** Each fact has one home; other skills point to it by skill name.
- **Write a unit type, CLSID, task field or flag from memory** into a skill or an example: read it
  from the DCS install or the Hoggit wiki.
- **Add project findings** (one test series, one library such as Skynet) to a skill: only what is
  true of DCS for any mission belongs here.
- **Set `version`** in `plugin.json` or `marketplace.json` for a plugin of this repository.
- **Commit directly to `main`**, except a change confined to `.tracker/`. Branch as `<type>/<slug>`.
- **Merge a pull request** unless asked to.

## Commands

```
claude plugin validate .                # the marketplace and each plugin, as CI runs it
bash scripts/lint.sh                    # luacheck at its pinned version, as CI runs it
```

## Workflow

- When only DCS can show whether a skill's advice is right, stop and ask the user to try it.
- Specs and plans written while planning go to `.drafts/` (git-ignored). What is worth keeping
  becomes a spec in `.tracker/`.

## Before you do these, read

| About to… | Read |
|---|---|
| add, change or move a skill, or a fact inside one | `CONTRIBUTING.md` — writing skills |
| add a plugin or a marketplace entry | `CONTRIBUTING.md` — layout, versioning |
| open a pull request, or open, update or archive a piece of work | `CONTRIBUTING.md` |
| edit a guidance file | `CONTRIBUTING.md` — how guidance is written |
