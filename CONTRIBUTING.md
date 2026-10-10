# Contributing

dcs-agent-skills holds agent skills for DCS World and is the Claude Code marketplace they install
from. This file holds every rule for changing it; `CLAUDE.md` only points here.

## What you need

- **Claude Code**, for `claude plugin validate` and to try a skill in a session.
- **Python 3**, to run the skills' scripts and the tests (standard library only).
- **A Bash shell** (Git Bash on Windows) and `curl`, for `scripts/lint.sh`, which fetches luacheck
  itself.
- **DCS World**, for checks only the simulator can answer.

## Layout

| Path | What it is |
|---|---|
| `.claude-plugin/marketplace.json` | the marketplace: one entry per plugin, here or in another repository |
| `plugins/<plugin>/` | one plugin: `.claude-plugin/plugin.json` and `skills/` |
| `plugins/<plugin>/skills/<skill>/` | one skill: `SKILL.md`, files it loads on demand, `scripts/`, `templates/` |
| `scripts/lint.sh` | luacheck at a pinned version, downloaded into `.tools/` (git-ignored) |
| `test/` | the tests of the skills' scripts, Python `unittest`; `test/fixtures/` holds the missions they build from |
| `.tracker/` | work in progress and work done, and `IDEAS.md` — see *Tracking work* |
| `.drafts/` | local working space, git-ignored |

A new skill goes into an existing plugin. A new plugin is worth it only when its skills must be
installable apart from the others, for example because they need a dependency the others do not.

## Running the checks

What a change must pass before its pull request:

```
claude plugin validate .                      # validate the marketplace and each plugin
python -m unittest discover -s test          # test the skills' scripts
bash scripts/lint.sh                          # luacheck on the Lua scripts, as CI runs it
claude --plugin-dir plugins/dcs-missions      # a session with the working tree's plugin loaded
```

After changing the `.miz` reader or writer, also run the round trip over every mission that comes
with DCS World. It takes about a minute and a half, so it runs only when `test/dcs-install.txt`
names your DCS install: copy `test/dcs-install.example.txt` to it and follow its comment. The copy
is git-ignored; comment its line out to skip the round trip again. Then run the tests as above.

## Writing skills

A skill is read by an agent in the middle of a task, so it says what to do and where facts are,
not how it came to be known.

- **General DCS knowledge only**: what is true of DCS for any mission, wherever it was found. What
  holds only for one mission or one external script stays with it.
- **No runner.** No skill mentions dcs-hotload or any other way to run Lua in a live mission; where
  a step needs one, it says "in the running mission". The agent combines the skill with whatever
  runner it has.
- **One home per fact.** Before adding a fact, search every skill for it. Skills of the same plugin
  may point to each other by skill name, since they are installed together; they may route an
  out-of-scope case to another skill but never depend on one.
- **Facts from the install, not from memory.** Unit types, CLSIDs, task fields and flags are read
  from the DCS install or the Hoggit wiki, and a skill says where. A fact measured in DCS says so
  and names the DCS version.
- **The description says when to load the skill**, in the user's words ("Use when …"), never what
  the skill contains: an agent decides from the description alone.
- **`SKILL.md` stays short**; detail goes into a file it names, saying what it holds and when to
  read it: the agent opens no file `SKILL.md` does not send it to.

Change a script, change its tests. `test/` checks the `.miz` reader and writer, the recipe helpers
against reference missions (`test/fixtures/*/expected.miz`, built from the recipe next to each),
and that `SKILL.md` shows the example the tests build. The `.miz` reader and writer must give back
the text they read for any mission they do not change.

To check a skill, start a fresh session with the working tree's plugin loaded (see *Running the
checks*) and give it a task the skill should handle, without naming the skill: the skill must load
from its description, and the agent must follow it. Then a task close to it that it should not
handle.

## How a change is made

These steps are mandatory, whatever tools you work with.

1. **Check what is already known** before adding or changing advice: search `plugins/` and
   `.tracker/`, its archive and `IDEAS.md` included.
2. **Open the work**, if it needs a spec — see *Tracking work*: commit
   `.tracker/<type>-<slug>/spec.md` straight to `main` with `Status: in-progress`, then branch from
   that commit. The idea the work takes up, if any, leaves `IDEAS.md` in the same commit.
3. **Branch** from an up-to-date `main`, named as *Git flow* says.
4. **Run the checks** — see *Running the checks*. `claude plugin validate .` warns that `version`
   is missing: expected, see *Versioning*; any other warning is fixed. Run a script you changed.
   Check a skill you changed as *Writing skills* says.
5. **Commit** as *Git flow* says.
6. **Open a pull request to `main`.** Its description says what changed and why, and how it was
   checked — including "not tried in DCS" when it was not. Amendments to the spec ride with the
   pull request, down to `Status: done`, set by the last pull request of the work.
7. **Merging is a maintainer's call.**
8. **Archive** the work's folder, at your discretion, once its last pull request has merged or it
   has been dropped.

## Tracking work

`.tracker/` records work in progress and work done. It is not a backlog: what might be done some
day is an entry in `.tracker/IDEAS.md`, or a GitHub issue when it comes from outside.

```
.tracker/
  IDEAS.md                           prospective work
  <type>-<slug>/                     one piece of work, named like its branch <type>/<slug>
    spec.md                          the only required file
  archive/
    YYYY-MM-DD-<type>-<slug>/        merged or dropped
```

**A spec is worth writing** when there is something to decide before writing, or when the work
spans several pull requests; otherwise a branch and a pull request are enough. A suggested shape:
the problem, what to build, the decisions with the alternatives turned down, what is out of scope,
discussion under `## Comments`. A spec is kept true while the work is under way and is not edited
once its pull request has merged.

What is strict is what a search relies on:

- **The location**: a folder directly under `.tracker/`, with `spec.md` at its root.
- **The `Status:` line**, the first line after the title:

  | Status | Meaning |
  |---|---|
  | `open` | written, not started |
  | `in-progress` | taken on; carried by the branch `<type>/<slug>` |
  | `blocked` | waiting — the line says on what, and who is expected to act |
  | `paused` | deliberately set aside — the line says what would restart it |
  | `done` | complete; set in the pull request itself |
  | `dropped` | decided against — the line or the spec says why |

  What is under way is found by search: `grep -l "Status: in-progress" .tracker/*/spec.md`.
- **The archive**: a folder moves as it is to `archive/YYYY-MM-DD-<type>-<slug>/`, dated the day its
  last pull request merged or the work was dropped. The state is never part of a file name.
- **`IDEAS.md`** is a free list. An idea taken up leaves it in the commit that opens its spec; a
  dropped idea stays, with its reason.

## Git flow

- `main` is the only long-lived branch and the target of every pull request.
- Branch from `main` as `<type>/<slug>`: `<type>` is one of `feat`, `fix`, `docs`, `chore`,
  `refactor`, `test`; `<slug>` is lowercase kebab.
- Never commit directly to `main`, with one exception: a change confined to `.tracker/` (opening a
  piece of work, a status change, an idea, archiving). Anything else goes through a pull request,
  guidance files included.
- [Conventional Commits](https://www.conventionalcommits.org/), in English. A commit does one thing.
- Pull requests are merged with a merge commit, so their commits stay readable apart.

## Versioning

The plugins of this repository have no version: `version` is set neither in their `plugin.json`
nor in their marketplace entry. Claude Code then versions them by commit, so **every merge to
`main` is a release** that users receive on their next `/plugin marketplace update`, or at once with
auto-update on. Hence `main` is always installable, and there is no changelog: the pull requests
are the history.

A marketplace entry for a plugin of another repository is pinned to one of its release tags
(`"ref": "v<x.y.z>"`), so users only get a released version; moving the pin is a pull request here.
It names the repository by its HTTPS URL (`"source": "url"`), not as `owner/repo` (`"source":
"github"`): for the latter Claude Code may clone over SSH, which fails for anyone without a GitHub
SSH key, even on a public repository.

## Writing guidance

The guidance files are `README.md`, this file and `CLAUDE.md`. Skills follow *Writing skills*.

- **A rule is stated once**; other files point at it. A command may be repeated. A reason, when
  one is worth giving, is given with the rule and nowhere else.
- **A rule stands on its own.** It never cites a spec, a piece of work, a commit, a person or a
  date to justify itself; that history is in `.tracker/` and the pull requests.
- **Point as little as possible.** A pointer into the repository names a file, or a heading in
  prose (*like this*); never a Markdown link. Links to outside sources are fine.
- **`CLAUDE.md` is read in every agent session**, so each of its lines must prevent a mistake.
- Everything written in the repository is in English.
