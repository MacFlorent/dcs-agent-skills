"""miz.py -- build, unpack and pack DCS .miz files. Python 3 standard library only.

  python miz.py build TEMPLATE.miz RECIPE.py OUT.miz --dcs INSTALL
      Run the Python RECIPE on TEMPLATE's tables (mizedit.py, next to this file), check every
      unit type and country against the DCS install, write OUT. Nothing is written when a check
      fails. Only the tables the recipe changed are rewritten; the rest of TEMPLATE is copied.
  python miz.py find TEXT [--lines N] [--max M] --dcs INSTALL
      List the missions shipped with DCS whose `mission` table contains TEXT (a unit type, a task
      id such as "SetInvisible", a field name), with the matching line and the N lines after it:
      known-good examples written by the Mission Editor.
  python miz.py countries --dcs INSTALL
      Country ids and names, numbered from Scripts/Database/db_countries.lua the way DCS does
      (one id per country:add, in order; country:next() skips one).
  python miz.py unpack IN.miz DIR
  python miz.py pack DIR OUT.miz

A .miz is a zip of Lua tables: mission, options, warehouses, theatre, l10n/DEFAULT/dictionary,
l10n/DEFAULT/mapResource, plus embedded files under l10n/DEFAULT/.

INSTALL is the DCS World folder, the one holding Scripts/Database. The scripts never look for it:
the caller passes it.
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mizedit  # noqa: E402
from luatable import FormatError  # noqa: E402

HERE = Path(__file__).resolve().parent
COUNTRY_LINE = re.compile(
    r"""^country:next\(\)|^country:add\(\s*'[^']+'\s*,\s*_\("[^"]*"\)\s*,\s*"([^"]+)\"""", re.M)


def unpack(miz, folder):
    with zipfile.ZipFile(miz) as z:
        z.extractall(folder)


def pack(folder, miz):
    folder = Path(folder)
    with zipfile.ZipFile(miz, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(folder.rglob("*")):
            if path.is_file():   # files only, forward slashes: as the Mission Editor writes them
                z.write(path, path.relative_to(folder).as_posix())


def is_dcs(path):
    return (Path(path) / "Scripts" / "Database").is_dir()


def need_dcs(path):
    if not is_dcs(path):
        sys.exit(f"not a DCS install (no Scripts/Database): {path}")
    return Path(path)


def countries(dcs):
    """{id: name}: one id per country:add, in file order; a bare country:next() skips one."""
    text = (dcs / "Scripts" / "Database" / "db_countries.lua").read_text("utf-8", "ignore")
    ids = {}
    for idx, m in enumerate(COUNTRY_LINE.finditer(text)):
        if m.group(1):
            ids[idx] = m.group(1)
    return ids


def known_types(dcs):
    """Every quoted string in the unit databases: core units, aircraft modules, and mods."""
    roots = [dcs / "Scripts" / "Database", dcs / "CoreMods", dcs / "Mods" / "aircraft",
             dcs / "Mods" / "tech", Path.home() / "Saved Games" / "DCS" / "Mods"]
    found = set()
    for root in roots:
        for path in root.rglob("*.lua") if root.is_dir() else []:
            try:
                found.update(re.findall(r'"([^"\n]{2,60})"', path.read_text("utf-8", "ignore")))
            except OSError:
                pass
    return found


def find(args):
    dcs = need_dcs(args.dcs)
    shown = 0
    for miz in sorted(dcs.glob("Mods/**/Missions/**/*.miz")) + sorted(dcs.glob("Missions/**/*.miz")):
        try:
            with zipfile.ZipFile(miz) as z:
                text = z.read("mission").decode("utf-8", "ignore")
        except (zipfile.BadZipFile, KeyError, OSError):
            continue
        at = text.find(args.text)
        if at >= 0:
            lines = text[text.rfind("\n", 0, at) + 1:].split("\n")[:args.lines + 1]
            print(miz.relative_to(dcs))
            for line in lines:
                print("    " + line.rstrip())
            shown += 1
            if shown >= args.max:
                break
    if shown == 0:
        print("no shipped mission contains", repr(args.text))


def check_units(units, types, country_ids):
    """Problems with the units' types and countries, against the DCS install's names."""
    problems = []
    unknown = sorted({u.type for u in units if u.type not in types})
    if unknown:
        problems.append("unknown unit types (check spelling against Scripts/Database/db_countries.lua): "
                        + ", ".join(unknown))
    wrong = sorted({f"id {u.country_id} is {country_ids.get(u.country_id, 'no country')}, not {u.country_name}"
                    for u in units if country_ids.get(u.country_id) != u.country_name})
    if wrong:
        problems.append("country id and name disagree (python miz.py countries): " + "; ".join(wrong))
    return problems


def build(args):
    try:
        b = mizedit.build(args.template, args.recipe)
    except (mizedit.RecipeError, FormatError) as e:
        sys.exit(str(e))
    dcs = need_dcs(args.dcs)
    problems = check_units(b.units, known_types(dcs), countries(dcs))
    if problems:
        sys.exit("not written: " + "\n  ".join(problems))
    print(f"unit types and countries checked against {dcs}")
    b.write(args.out)
    print(f"wrote {args.out}: {len(b.units)} units")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("template")
    b.add_argument("recipe")
    b.add_argument("out")
    b.add_argument("--dcs", required=True)
    f = sub.add_parser("find")
    f.add_argument("text")
    f.add_argument("--lines", type=int, default=0)
    f.add_argument("--max", type=int, default=5)
    f.add_argument("--dcs", required=True)
    c = sub.add_parser("countries")
    c.add_argument("--dcs", required=True)
    u = sub.add_parser("unpack")
    u.add_argument("miz")
    u.add_argument("folder")
    k = sub.add_parser("pack")
    k.add_argument("folder")
    k.add_argument("miz")
    args = p.parse_args()
    if args.cmd == "build":
        build(args)
    elif args.cmd == "find":
        find(args)
    elif args.cmd == "countries":
        for i, name in countries(need_dcs(args.dcs)).items():
            print(i, name)
    elif args.cmd == "unpack":
        unpack(args.miz, args.folder)
    else:
        pack(args.folder, args.miz)


if __name__ == "__main__":
    main()
