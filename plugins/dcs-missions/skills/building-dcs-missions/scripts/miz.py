"""miz.py -- build, unpack and pack DCS .miz files. Python 3 standard library only.

  python miz.py build TEMPLATE.miz RECIPE.lua OUT.miz [--dcs DCS_INSTALL] [--lua LUA]
      Unpack TEMPLATE, run RECIPE through mizedit.lua (next to this file), check every unit
      type and country against the DCS install, pack OUT. Nothing is written when a check fails.
  python miz.py find TEXT [--lines N] [--max M] [--dcs DCS_INSTALL]
      List the missions shipped with DCS whose `mission` table contains TEXT (a unit type, a task
      id such as "SetInvisible", a field name), with the matching line and the N lines after it:
      known-good examples written by the Mission Editor.
  python miz.py countries [--dcs DCS_INSTALL]
      Country ids and names, numbered from Scripts/Database/db_countries.lua the way DCS does
      (one id per country:add, in order; country:next() skips one).
  python miz.py unpack IN.miz DIR
  python miz.py pack DIR OUT.miz

A .miz is a zip of Lua tables: mission, options, warehouses, theatre, l10n/DEFAULT/dictionary,
l10n/DEFAULT/mapResource, plus embedded files under l10n/DEFAULT/.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LUA_CANDIDATES = ["lua5.1", "lua", r"C:\Program Files (x86)\Lua\5.1\lua.exe"]
DCS_CANDIDATES = [r"E:\DCS World", r"C:\Program Files\Eagle Dynamics\DCS World",
                  r"D:\DCS World", r"C:\Program Files\Eagle Dynamics\DCS World OpenBeta"]
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


def find_lua(explicit):
    for cand in ([explicit] if explicit else LUA_CANDIDATES):
        exe = shutil.which(cand) or (cand if Path(cand).is_file() else None)
        if exe:
            return exe
    sys.exit("no Lua 5.1 found; pass --lua")


def find_dcs(explicit):
    for cand in ([explicit] if explicit else DCS_CANDIDATES):
        if cand and (Path(cand) / "Scripts" / "Database").is_dir():
            return Path(cand)
    return None


def need_dcs(explicit):
    return find_dcs(explicit) or sys.exit("DCS install not found; pass --dcs")


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


def build(args):
    lua = find_lua(args.lua)
    with tempfile.TemporaryDirectory() as tmp:
        unpack(args.template, tmp)
        run = subprocess.run([lua, str(HERE / "mizedit.lua"), tmp, args.recipe],
                             capture_output=True, text=True)
        if run.returncode != 0:
            sys.exit(run.stderr.strip())
        # TYPE <type> <country id> <country name> <category> <group>
        units = [line.split("\t")[1:] for line in run.stdout.splitlines()
                 if line.startswith("TYPE\t")]
        dcs = find_dcs(args.dcs)
        if dcs is None:
            print("WARNING: DCS install not found (--dcs); unit types and countries NOT checked")
        else:
            types = known_types(dcs)
            unknown = sorted({u[0] for u in units if u[0] not in types})
            if unknown:
                sys.exit("not written: unknown unit types (check spelling against "
                         "Scripts/Database/db_countries.lua): " + ", ".join(unknown))
            ids = countries(dcs)
            wrong = sorted({f"id {u[1]} is {ids.get(int(u[1]), 'no country')}, not {u[2]}"
                            for u in units if ids.get(int(u[1])) != u[2]})
            if wrong:
                sys.exit("not written: country id and name disagree "
                         "(python miz.py countries): " + "; ".join(wrong))
            print(f"unit types and countries checked against {dcs}")
        pack(tmp, args.out)
    print(f"wrote {args.out}: {len(units)} units")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("template")
    b.add_argument("recipe")
    b.add_argument("out")
    b.add_argument("--dcs")
    b.add_argument("--lua")
    f = sub.add_parser("find")
    f.add_argument("text")
    f.add_argument("--lines", type=int, default=0)
    f.add_argument("--max", type=int, default=5)
    f.add_argument("--dcs")
    c = sub.add_parser("countries")
    c.add_argument("--dcs")
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
