"""Tests of the building-dcs-missions scripts: the table format, recipes, the build.

    python -m unittest discover -s test

The round trip over every mission shipped with DCS takes about a minute and a half, so it runs only
when test/dcs-install.txt names a DCS install (a copy of test/dcs-install.example.txt). Run it
after changing the table reader or writer.
"""
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins" / "dcs-missions" / "skills" / "building-dcs-missions"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
TEMPLATE = SKILL / "templates" / "caucasus.miz"
sys.path.insert(0, str(SKILL / "scripts"))

import luatable  # noqa: E402
import mizedit  # noqa: E402
import miz  # noqa: E402


def entries(path):
    with zipfile.ZipFile(path) as z:
        return {i.filename: z.read(i.filename) for i in z.infolist()}


def table(path, entry):
    return luatable.lua_load(entries(path)[entry].decode("utf-8"))[1]


def normal(value):
    """Tables compared as values: numbers as floats, whatever their spelling."""
    if isinstance(value, dict):
        return {(float(k) if isinstance(k, int) else k): normal(v) for k, v in value.items()}
    if isinstance(value, luatable.Num) or (isinstance(value, (int, float)) and not isinstance(value, bool)):
        return float(value)
    return value


class Scratch(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dcs-agent-skills-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def recipe(self, text, name="recipe.py"):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def build(self, recipe):
        out = self.dir / "out.miz"
        mizedit.build(TEMPLATE, recipe).write(out)
        return out


# ── The Mission Editor's table format ───────────────────────────────────────────────────────────

SPACES = '''mission =
{
    ["trig"] =
    {
        ["actions"] =
        {
            [1] = "a_do_script(\\"x\\");",
        }, -- end of ["actions"]
        ["flag"] =
        {
        }, -- end of ["flag"]
    }, -- end of ["trig"]
    ["x"] = -0.0051662641880086,
    ["big"] = 1e+20,
    ["on"] = true,
} -- end of mission
'''.replace(" =" + chr(10), " = " + chr(10))   # the Mission Editor writes "= " before a table


class TableFormat(unittest.TestCase):
    def test_every_table_of_the_template_reads_and_writes_back_unchanged(self):
        for name, data in entries(TEMPLATE).items():
            if name == "theatre":
                continue
            text = data.decode("utf-8")
            with self.subTest(entry=name):
                table_name, value = luatable.lua_load(text)
                self.assertEqual(luatable.lua_dump(table_name, value, luatable.Style.of(text)), text)

    def test_spaces_and_open_empty_tables(self):
        name, value = luatable.lua_load(SPACES)
        self.assertEqual(luatable.lua_dump(name, value, luatable.Style.of(SPACES)), SPACES)
        self.assertIsInstance(value["x"], luatable.Num)
        self.assertEqual(value["trig"]["actions"][1], 'a_do_script("x");')

    def test_empty_file_tables_in_both_styles(self):
        for text in ("mapResource = {}\n", "mapResource = \n{\n} -- end of mapResource\n"):
            with self.subTest(text=text):
                name, value = luatable.lua_load(text)
                self.assertEqual(luatable.lua_dump(name, value, luatable.Style.of(text)), text)

    def test_escapes(self):
        value = {1: 'q" b\\ nl\nend \r \0'}
        out = luatable.lua_dump("x", value, luatable.Style("\t", True))
        self.assertIn('[1] = "q\\" b\\\\ nl\\\nend \\r \\000",', out)
        self.assertEqual(luatable.lua_load(out)[1], value)

    def test_python_values(self):
        out = luatable.lua_dump("x", {"i": 5, "f": 2.5, "whole": 3.0, "b": False,
                                      "l": {1: "a"}}, luatable.Style("\t", True))
        self.assertIn('["i"] = 5,', out)
        self.assertIn('["f"] = 2.5,', out)
        self.assertIn('["whole"] = 3,', out)
        self.assertIn('["b"] = false,', out)

    def test_refuses_what_it_cannot_read(self):
        with self.assertRaises(luatable.FormatError):
            luatable.lua_load("mission = { [1] = some_function() }")


def dcs_install():
    """The first line of test/dcs-install.txt that is neither blank nor a # comment, else None."""
    config = Path(__file__).resolve().parent / "dcs-install.txt"
    lines = config.read_text(encoding="utf-8").splitlines() if config.is_file() else []
    return next((s for s in map(str.strip, lines) if s and not s.startswith("#")), None)


DCS_INSTALL = dcs_install()


@unittest.skipUnless(DCS_INSTALL, "no DCS install in test/dcs-install.txt")
class ShippedMissions(unittest.TestCase):
    """Every table a build may rewrite, in every mission DCS ships, reads and writes back unchanged.

    A few dictionaries were edited by hand after the Mission Editor (`["key"]= "x"`, no space): the
    writer gives those lines the editor's spacing, so for them only the values must match."""

    def test_every_table_a_build_may_rewrite(self):
        failures, count, tables_seen, hand_edited = [], 0, 0, 0
        self.assertTrue(miz.is_dcs(DCS_INSTALL), f"test/dcs-install.txt: not a DCS install: {DCS_INSTALL}")
        for path in sorted(Path(DCS_INSTALL).rglob("*.miz")):
            try:
                tables = {n: d.decode("utf-8") for n, d in entries(path).items() if n in mizedit.TABLES.values()}
            except (zipfile.BadZipFile, UnicodeDecodeError, OSError):
                continue
            count += 1
            for name, text in tables.items():
                tables_seen += 1
                try:
                    t, value = luatable.lua_load(text)
                    out = luatable.lua_dump(t, value, luatable.Style.of(text))
                    if out == text:
                        continue
                    if "]= " in text and luatable.lua_load(out)[1] == value:
                        hand_edited += 1
                        continue
                    failures.append(f"{path} {name}: text differs")
                except luatable.FormatError as e:
                    failures.append(f"{path} {name}: {e}")
        self.assertGreater(count, 0)
        self.assertEqual(failures, [], f"{len(failures)} of {tables_seen} tables, in {count} missions")
        print(f"{count} shipped missions, {tables_seen} tables: written back unchanged "
              f"({hand_edited} hand-edited, same values)")


# ── Recipes ─────────────────────────────────────────────────────────────────────────────────────

class ReferenceBuilds(Scratch):
    """Each fixture's recipe.py builds the same tables as its expected.miz. Not checked in DCS.
    When a helper changes on purpose, rebuild it:
    miz.py build templates/caucasus.miz recipe.py expected.miz --dcs DCS."""

    def check(self, fixture):
        out = self.build(FIXTURES / fixture / "recipe.py")
        reference = FIXTURES / fixture / "expected.miz"
        for entry in ("mission", "l10n/DEFAULT/mapResource"):
            with self.subTest(entry=entry):
                self.assertEqual(normal(table(out, entry)), normal(table(reference, entry)))
        built, expected = entries(out), entries(reference)
        self.assertEqual(sorted(built), sorted(expected))
        for name in expected:
            if name.endswith(".lua"):
                self.assertEqual(built[name], expected[name], name)

    def test_the_skill_example(self):
        self.check("example")

    def test_the_skill_shows_the_tested_example(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        shown = text.split("```python\n", 1)[1].split("```", 1)[0]
        self.assertEqual(shown, (FIXTURES / "example" / "recipe.py").read_text(encoding="utf-8"))

    def test_a_recipe_can_edit_tables_directly(self):
        out = self.build(self.recipe(
            'mission["descriptionText"] = "Briefing"\n'
            'mission["maxDictId"] = luatable.num(mission["maxDictId"]) + 1\n'))
        mission = table(out, "mission")
        self.assertEqual(mission["descriptionText"], "Briefing")

    def test_an_sa10_site_with_scripts(self):
        self.check("sa10")


class Untouched(Scratch):
    def test_an_empty_recipe_gives_back_the_template(self):
        out = self.build(self.recipe("# nothing\n"))
        self.assertEqual(entries(out), entries(TEMPLATE))

    def test_a_group_changes_only_the_mission(self):
        out = self.build(self.recipe(
            'M.addGroup(side="red", country={"id": 0, "name": "Russia"}, category="vehicle", name="G", '
            'x=0, y=0, units=[{"type": "T-72B"}])\n'))
        before, after = entries(TEMPLATE), entries(out)
        self.assertEqual(list(after), list(before))
        for name in before:
            if name != "mission":
                self.assertEqual(after[name], before[name], name)

    def test_untouched_parts_of_the_mission_keep_their_text(self):
        template = entries(TEMPLATE)["mission"].decode("utf-8")
        out = self.build(self.recipe('M.gameMaster(2, 3)\n'))
        text = entries(out)["mission"].decode("utf-8")
        self.assertEqual(len(text.splitlines()), len(template.splitlines()))
        changed = [(a, b) for a, b in zip(template.splitlines(), text.splitlines()) if a != b]
        self.assertEqual(len(changed), 2, changed)


class Helpers(Scratch):
    def test_lists_become_lua_arrays(self):
        out = self.build(self.recipe(
            'M.addGroup(side="blue", country={"id": 2, "name": "USA"}, category="plane", name="P", '
            'x=0, y=0, units=[{"type": "F-16C_50", "payload": {"pylons": [{"CLSID": "A"}, {"CLSID": "B"}]}}])\n'))
        country = table(out, "mission")["coalition"]["blue"]["country"]
        usa = next(c for c in country.values() if float(c["id"]) == 2)
        unit = usa["plane"]["group"][1]["units"][1]
        self.assertEqual(unit["payload"]["pylons"], {1: {"CLSID": "A"}, 2: {"CLSID": "B"}})
        self.assertEqual(unit["callsign"][3], luatable.Num("1"))

    def test_an_aircraft_psi_is_minus_its_heading(self):
        out = self.build(self.recipe(
            'M.addGroup(side="blue", country={"id": 2, "name": "USA"}, category="plane", name="P", '
            'x=0, y=0, units=[{"type": "F-16C_50", "heading": 1.5}])\n'))
        usa = next(c for c in table(out, "mission")["coalition"]["blue"]["country"].values()
                   if float(c["id"]) == 2)
        unit = usa["plane"]["group"][1]["units"][1]
        self.assertEqual((float(unit["heading"]), float(unit["psi"])), (1.5, -1.5))

    def test_ids_follow_those_in_the_mission(self):
        b = mizedit.build(TEMPLATE, self.recipe(
            'a = M.addGroup(side="red", country={"id": 0, "name": "Russia"}, category="vehicle", name="A", '
            'x=0, y=0, units=[{"type": "T-72B"}, {"type": "T-72B"}])\n'
            'b = M.addGroup(side="red", country={"id": 0, "name": "Russia"}, category="vehicle", name="B", '
            'x=0, y=0, units=[{"type": "T-72B"}])\n'
            'assert b["groupId"] == a["groupId"] + 1 and b["units"][1]["unitId"] == a["units"][2]["unitId"] + 1\n'))
        self.assertEqual([u.group for u in b.units], ["A", "A", "B"])

    def test_on_start_writes_trig_and_trigrules_index_for_index(self):
        out = self.build(self.recipe('M.onStart("a", [M.doScript("x = 1")])\n'
                                     'M.onStart("b", [M.doScript("y = 2")])\n'))
        mission = table(out, "mission")
        self.assertEqual(mission["trigrules"][2]["actions"][1]["text"], "y = 2")
        self.assertEqual(mission["trig"]["actions"][2], 'a_do_script("y = 2");')
        self.assertEqual(mission["trig"]["funcStartup"][2],
                         "if mission.trig.conditions[2]() then mission.trig.actions[2]() end")

    def test_embed_file_reads_from_the_recipe_folder(self):
        (self.dir / "s.lua").write_text("return 1", encoding="utf-8")
        out = self.build(self.recipe('M.onStart("s", [M.doScriptFile(M.embedFile("s.lua"))])\n'))
        self.assertEqual(entries(out)["l10n/DEFAULT/s.lua"], b"return 1")


class Checks(Scratch):
    def refused(self, text, message):
        with self.assertRaises(mizedit.RecipeError) as e:
            mizedit.build(TEMPLATE, self.recipe(text))
        self.assertIn(message, str(e.exception))

    def test_duplicate_unit_names(self):
        self.refused(
            'for g in ("A", "B"):\n'
            '    M.addGroup(side="red", country={"id": 0, "name": "Russia"}, category="vehicle", name=g, '
            'x=0, y=0, units=[{"type": "T-72B", "name": "same"}])\n', "duplicate unit name same")

    def test_a_country_not_on_its_side(self):
        self.refused('M.addGroup(side="blue", country={"id": 0, "name": "Russia"}, category="vehicle", '
                     'name="G", x=0, y=0, units=[{"type": "T-72B"}])\n', "not on the blue side")

    def test_a_trigger_naming_a_missing_file(self):
        self.refused('mapResource["ResKey_X"] = "missing.lua"\n', "missing.lua")

    def test_an_error_in_the_recipe_names_the_recipe(self):
        self.refused('undefined_name\n', "recipe.py")


class Command(Scratch):
    def test_build_command_writes_nothing_on_unknown_types(self):
        recipe = self.recipe('M.addGroup(side="red", country={"id": 0, "name": "Russia"}, category="vehicle", '
                             'name="G", x=0, y=0, units=[{"type": "No Such Tank"}])\n')
        out = self.dir / "out.miz"
        problems = miz.check_units(mizedit.build(TEMPLATE, recipe).units,
                                   types={"T-72B"}, country_ids={0: "Russia"})
        self.assertTrue(any("No Such Tank" in p for p in problems))
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
