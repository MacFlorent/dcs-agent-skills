"""mizedit.py -- run a Python recipe on a mission. Normally through `miz.py build`.

The recipe is a Python file run with these globals:
  mission, options, warehouses, dictionary, mapResource   the mission's own tables, edit freely
  M                                                       the helpers below
  luatable                                                Num, num(), lua() for direct edits
Tables are dicts: a Lua array is a dict keyed 1..n (luatable.lua() converts a list). Helpers take
lists and fill the fields the Mission Editor writes, so a recipe only gives what matters: types,
positions, tasks.

A table is written back only when the recipe changed it, in the style of the file it came from;
every other entry of the .miz is copied unchanged.
"""
import copy
import os
import tempfile
import time
import traceback
import zipfile
from collections import namedtuple
from pathlib import Path

import luatable
from luatable import FormatError, Style, append, array, lua, lua_dump, lua_load, lua_quote, num

TABLES = {"mission": "mission", "options": "options", "warehouses": "warehouses",
          "dictionary": "l10n/DEFAULT/dictionary", "mapResource": "l10n/DEFAULT/mapResource"}
CATEGORIES = ("vehicle", "plane", "helicopter", "ship", "static")

Unit = namedtuple("Unit", "type country_id country_name category group")


class RecipeError(Exception):
    pass


def combo(tasks):
    tasks = lua(tasks or [])
    for i, t in tasks.items():
        t["number"] = i
    return {"id": "ComboTask", "params": {"tasks": tasks}}


class Helpers:
    """The `M` of a recipe."""

    def __init__(self, build, recipe_dir):
        self._build, self._dir = build, recipe_dir

    @property
    def _mission(self):
        return self._build.tables["mission"]

    # ── Tasks ───────────────────────────────────────────────────────────────────────────────────

    def wrapped(self, action):
        """A waypoint task that runs a command or sets an option, e.g.
        M.wrapped({"id": "SetInvisible", "params": {"value": True}})."""
        return {"id": "WrappedAction", "enabled": True, "auto": False, "params": {"action": lua(action)}}

    def invisible(self):
        return self.wrapped({"id": "SetInvisible", "params": {"value": True}})

    def immortal(self):
        return self.wrapped({"id": "SetImmortal", "params": {"value": True}})

    def option(self, name, value):
        """An AI option on the first waypoint: name is the numeric option id, as in
        AI.Option.<Air|Ground>.id (Hoggit wiki, "DCS func setOption"). Ground ROE is id 0: value 2
        open fire, 4 weapon hold."""
        return self.wrapped({"id": "Option", "params": {"name": name, "value": value}})

    def bombing(self, x, y, weaponType=4294967295, expend="All"):
        """Attack a map point. weaponType (MissionEditor/modules/me_action_db.lua, weaponTable):
        4294967295 all, 14 guided bombs, 240 iron bombs, 2032 any bomb, 4161536 any air-to-surface
        missile, 2097152 cruise missile, 32768 anti-radiation."""
        return {"id": "Bombing", "enabled": True, "auto": False, "params": {
            "x": x, "y": y, "weaponType": weaponType, "expend": expend,
            "attackQtyLimit": False, "attackQty": 1, "groupAttack": False,
            "direction": 0, "directionEnabled": False, "altitude": 2000, "altitudeEnabled": False}}

    # ── Groups ──────────────────────────────────────────────────────────────────────────────────

    def _country(self, side, country_id, country_name):
        mission = self._mission
        coal = mission["coalition"].get(side)
        if coal is None:
            raise RecipeError(f"no coalition {side!r}")
        if not any(num(i) == country_id for i in array(mission["coalitions"].get(side, {}))):
            raise RecipeError(f"country {country_id} is not on the {side} side in this mission")
        countries = coal.setdefault("country", {})
        for c in array(countries):
            if num(c["id"]) == country_id:
                return c
        c = {"id": country_id, "name": country_name}
        append(countries, c)
        return c

    def addGroup(self, side, country, category, name, x, y, units, tasks=None, route=None, alt=None,
                 speed=None, task=None, lateActivation=False, hidden=False, uncontrollable=False):
        """Add a group:
          side = "red"|"blue"|"neutrals", country = {"id", "name"}  (ids: DCS country.id, e.g. 0 Russia, 2 USA)
          category = "vehicle"|"plane"|"helicopter"|"ship"
          name, x, y                     group name and anchor (map metres, x north, y east)
          units = [{type, dx, dy, heading, name, payload, skill}, ...]   offsets from x, y
          tasks = [...]                  tasks on the first waypoint (M.invisible() ...)
          route = [{x, y, alt, speed, tasks}, ...]   extra waypoints (air and moving ground)
          alt, speed, task               air only: start altitude (m), speed (m/s), main task
          lateActivation, hidden, uncontrollable
        Returns the group table, already in the mission."""
        air = category in ("plane", "helicopter")
        group_id, unit_id = self._build.next_ids()
        alt = alt if alt is not None else (3000 if air else 0)
        speed = speed if speed is not None else (150 if air else 0)

        points = [{
            "x": x, "y": y, "alt": alt, "alt_type": "BARO", "speed": speed,
            "type": "Turning Point", "action": "Turning Point" if air else "Off Road",
            "ETA": 0, "ETA_locked": True, "speed_locked": True, "formation_template": "", "name": "",
            "task": combo(tasks)}]
        for p in route or []:
            points.append({
                "x": p["x"], "y": p["y"], "alt": p.get("alt", alt), "alt_type": "BARO",
                "speed": p.get("speed", speed), "type": "Turning Point",
                "action": "Turning Point" if air else p.get("action", "Off Road"),
                "ETA": 0, "ETA_locked": False, "speed_locked": True, "formation_template": "", "name": "",
                "task": combo(p.get("tasks"))})

        group = {
            "groupId": group_id, "name": name, "x": x, "y": y, "start_time": 0,
            "task": task or ("Nothing" if air else "Ground Nothing"),
            "taskSelected": True, "tasks": {}, "visible": False, "hidden": hidden,
            "hiddenOnPlanner": False, "lateActivation": lateActivation, "uncontrollable": uncontrollable,
            "route": {"points": lua(points), "spans": {}},
            "units": {},
        }
        if air:
            group.update(frequency=251, modulation=0, communication=True, uncontrolled=False, radioSet=False)

        for i, u in enumerate(units, start=1):
            if "type" not in u:
                raise RecipeError(f"unit {i} of {name} has no type")
            heading = u.get("heading", 0)
            unit = {
                "unitId": unit_id + i - 1, "type": u["type"], "name": u.get("name", f"{name}-{i}"),
                "x": x + u.get("dx", 0), "y": y + u.get("dy", 0),
                "heading": heading, "skill": u.get("skill", "Excellent"),
            }
            if air:
                unit.update(alt=alt, alt_type="BARO", speed=speed, psi=-heading,
                            onboard_num=f"{unit_id + i - 1:03d}",
                            callsign={1: 1, 2: 1, 3: i, "name": f"Enfield1{i}"},
                            payload=lua(u.get("payload") or
                                        {"pylons": {}, "fuel": 0, "flare": 0, "chaff": 0, "gun": 100}))
            else:
                unit.update(playerCanDrive=False, coldAtStart=False,
                            transportable={"randomTransportable": False})
            group["units"][i] = unit

        c = self._country(side, country["id"], country["name"])
        c.setdefault(category, {"group": {}})
        append(c[category].setdefault("group", {}), group)
        return group

    def gameMaster(self, blue=1, red=1):
        """Game Master (the "instructor" role) slots per side."""
        instructor = self._mission["groundControl"]["roles"]["instructor"]
        instructor["blue"], instructor["red"] = blue, red

    # ── Scripts and triggers ────────────────────────────────────────────────────────────────────

    def embedFile(self, path):
        """Embed a file in l10n/DEFAULT and register it. Returns its resource key. A relative path
        is read from the recipe's folder."""
        path = Path(path)
        if not path.is_absolute():
            path = self._dir / path
        try:
            data = path.read_bytes()
        except OSError:
            raise RecipeError(f"cannot read {path}") from None
        self._build.entries["l10n/DEFAULT/" + path.name] = data
        mission = self._mission
        mission["maxDictId"] = num(mission.get("maxDictId", 0)) + 1
        key = f"ResKey_Action_{mission['maxDictId']}"
        self._build.tables["mapResource"][key] = path.name
        return key

    def doScriptFile(self, key):
        return {"rule": {"predicate": "a_do_script_file", "file": key},
                "code": f"a_do_script_file(getValueResourceByKey({lua_quote(key)}));"}

    def doScript(self, text):
        return {"rule": {"predicate": "a_do_script", "text": text},
                "code": f"a_do_script({lua_quote(text)});"}

    def onStart(self, comment, actions):
        """A MISSION START trigger running the actions in order. Writes both halves the way the
        Mission Editor does: trigrules (what the editor shows) and trig (what DCS runs)."""
        mission = self._mission
        rules = mission.setdefault("trigrules", {})
        trig = mission["trig"]
        n = append(rules, {"comment": comment, "predicate": "triggerStart", "eventlist": "",
                           "colorItem": "0x00ffffff", "rules": {},
                           "actions": lua([a["rule"] for a in actions])})
        trig.setdefault("actions", {})[n] = "".join(a["code"] for a in actions)
        trig.setdefault("conditions", {})[n] = "return(true)"
        trig.setdefault("flag", {})[n] = True
        trig.setdefault("funcStartup", {})[n] = \
            f"if mission.trig.conditions[{n}]() then mission.trig.actions[{n}]() end"


class Build:
    """A template with a recipe applied: write() it once the checks pass."""

    def __init__(self, template):
        with zipfile.ZipFile(template) as z:
            self.infos = {i.filename: i for i in z.infolist()}
            self.entries = {name: z.read(name) for name in self.infos}
        self.tables, self.styles, self.originals = {}, {}, {}
        for name, entry in TABLES.items():
            text = self.entries[entry].decode("utf-8")
            file_name, self.tables[name] = lua_load(text)
            if file_name != name:
                raise FormatError(f"{entry} defines {file_name!r}, not {name!r}")
            self.styles[name] = Style.of(text)
            self.originals[name] = copy.deepcopy(self.tables[name])
        self.units = []

    def groups(self):
        """(group, category, country) for every group of the mission."""
        for coal in self.tables["mission"]["coalition"].values():
            for country in array(coal.get("country", {})):
                for category in CATEGORIES:
                    for group in array(country.get(category, {}).get("group", {})):
                        yield group, category, country

    def next_ids(self):
        g, u = 0, 0
        for group, _, _ in self.groups():
            g = max(g, num(group.get("groupId", 0)))
            for unit in array(group.get("units", {})):
                u = max(u, num(unit.get("unitId", 0)))
        return g + 1, u + 1

    def check(self):
        problems = []
        group_ids, unit_ids, names = set(), set(), set()
        self.units = []
        for group, category, country in self.groups():
            gid = num(group["groupId"])
            if gid in group_ids:
                problems.append(f"duplicate groupId {gid}")
            group_ids.add(gid)
            for unit in array(group.get("units", {})):
                uid = num(unit["unitId"])
                if uid in unit_ids:
                    problems.append(f"duplicate unitId {uid}")
                if unit["name"] in names:
                    problems.append(f"duplicate unit name {unit['name']}")
                unit_ids.add(uid)
                names.add(unit["name"])
                self.units.append(Unit(unit["type"], num(country["id"]), country["name"], category,
                                       group["name"]))
        mission = self.tables["mission"]
        trig = mission.get("trig", {})
        if len(mission.get("trigrules", {})) != len(trig.get("funcStartup", {})) + len(trig.get("func", {})):
            problems.append("trigrules and trig have different trigger counts")
        for key, file in self.tables["mapResource"].items():
            if "l10n/DEFAULT/" + file not in self.entries:
                problems.append(f"{key} names a missing file {file}")
        if problems:
            raise RecipeError("not written:\n  " + "\n  ".join(problems))

    def write(self, out):
        for name, entry in TABLES.items():
            if self.tables[name] != self.originals[name]:
                text = lua_dump(name, self.tables[name], self.styles[name])
                lua_load(text)   # what is written must read back
                self.entries[entry] = text.encode("utf-8")
        out = Path(out)
        fd, tmp = tempfile.mkstemp(dir=out.parent, suffix=".miz")
        os.close(fd)
        try:
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
                for name, data in self.entries.items():
                    info = self.infos.get(name)
                    if info is None:
                        info = zipfile.ZipInfo(name, time.localtime()[:6])
                        info.compress_type = zipfile.ZIP_DEFLATED
                    z.writestr(info, data)
            os.replace(tmp, out)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


def build(template, recipe):
    """Applies the recipe to the template and checks the result. Raises RecipeError."""
    recipe = Path(recipe).resolve()
    b = Build(template)
    scope = {"__name__": "__recipe__", "__file__": str(recipe), "M": Helpers(b, recipe.parent),
             "luatable": luatable, **b.tables}
    try:
        code = compile(recipe.read_text(encoding="utf-8"), str(recipe), "exec")
        exec(code, scope)
    except RecipeError as e:
        raise RecipeError(f"{recipe.name}: {e}") from None
    except Exception as e:
        lines = [f.lineno for f in traceback.extract_tb(e.__traceback__) if f.filename == str(recipe)]
        where = f"{recipe.name}, line {lines[-1]}" if lines else recipe.name
        raise RecipeError(f"{where}: {type(e).__name__}: {e}") from None
    for name in TABLES:
        b.tables[name] = scope[name]
    b.check()
    return b
