"""luatable.py -- read and write the Lua tables of a .miz the way the Mission Editor does. Python 3.

A table file is `name = { ... }`: `mission`, `options`, `warehouses`, `l10n/DEFAULT/dictionary`,
`l10n/DEFAULT/mapResource`. Tables read as dicts in file order, keys as str or int; numbers read
as Num, which keeps the text the file wrote; strings and booleans as themselves.

The writer follows the style of the file it read (tabs or four spaces, `{}` or an open pair for an
empty table), so a table it does not change comes back as the same text. Python values written in
are Lua values: int and float as numbers (a whole float without its .0, as the editor writes it),
bool as true/false, dict as a table. A list is not a Lua value: convert it with lua().
"""
import re


class FormatError(Exception):
    pass


class Num(str):
    """A number as the file wrote it: kept as text, so writing it back changes nothing."""


class Style:
    """How a file is laid out: the indent unit, whether an empty table is written `{}`, and whether
    the file's own table is, when it is empty (editors that write `{}` inside may not at the top)."""

    def __init__(self, indent, compact_empty, compact_top=None):
        self.indent, self.compact_empty = indent, compact_empty
        self.compact_top = compact_empty if compact_top is None else compact_top

    @classmethod
    def of(cls, text):
        m = re.search(r"\n([ \t]+)\S", text)
        indent = m.group(1) if m else "\t"
        if re.search(r"= \{\},", text):
            compact = True
        elif re.search(r"= \n[ \t]*\{\n[ \t]*\}, -- end of", text):
            compact = False
        else:
            compact = indent == "\t"
        if re.match(r"\w+ = \{\}\s*$", text):
            top = True
        elif re.match(r"\w+ = \n\{\n\}", text):
            top = False
        else:
            top = None
        return cls(indent, compact, top)


ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "a": "\a", "b": "\b", "f": "\f", "v": "\v",
           "\\": "\\", '"': '"', "'": "'", "\n": "\n"}
NUMBER = re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
SPACE = re.compile(r"\s*")
NAME = re.compile(r"[A-Za-z_]\w*")
INT = re.compile(r"-?\d+")
DIGITS = re.compile(r"\d{1,3}")


class Parser:
    def __init__(self, text):
        self.text, self.pos = text, 0

    def fail(self, what):
        line = self.text.count("\n", 0, self.pos) + 1
        raise FormatError(f"line {line}: {what}")

    def skip(self):
        while True:
            self.pos = SPACE.match(self.text, self.pos).end()
            if self.text.startswith("--", self.pos):
                end = self.text.find("\n", self.pos)
                self.pos = len(self.text) if end < 0 else end
            else:
                return

    def expect(self, token):
        self.skip()
        if not self.text.startswith(token, self.pos):
            self.fail(f"expected {token!r}")
        self.pos += len(token)

    def peek(self):
        self.skip()
        return self.text[self.pos:self.pos + 1]

    def name(self):
        self.skip()
        m = NAME.match(self.text, self.pos)
        if not m:
            self.fail("expected a name")
        self.pos = m.end()
        return m.group()

    def string(self):
        quote = self.text[self.pos]
        self.pos += 1
        out = []
        while True:
            if self.pos >= len(self.text):
                self.fail("unfinished string")
            c = self.text[self.pos]
            if c == quote:
                self.pos += 1
                return "".join(out)
            if c == "\\":
                e = self.text[self.pos + 1:self.pos + 2]
                if e in ESCAPES:
                    out.append(ESCAPES[e])
                    self.pos += 2
                elif e.isdigit():
                    m = DIGITS.match(self.text, self.pos + 1)
                    code = int(m.group())
                    if code > 127:
                        self.fail("a byte escape above 127")
                    out.append(chr(code))
                    self.pos = m.end()
                else:
                    self.fail(f"unknown escape \\{e}")
            elif c == "\n":
                self.fail("unfinished string")
            else:
                out.append(c)
                self.pos += 1

    def value(self):
        c = self.peek()
        if c == "{":
            return self.table()
        if c in "\"'":
            return self.string()
        m = NUMBER.match(self.text, self.pos)
        if m:
            self.pos = m.end()
            return Num(m.group())
        for word, value in (("true", True), ("false", False)):
            if re.compile(word + r"\b").match(self.text, self.pos):
                self.pos += len(word)
                return value
        self.fail("expected a value")

    def table(self):
        self.expect("{")
        table = {}
        while self.peek() != "}":
            self.expect("[")
            if self.peek() in "\"'":
                key = self.string()
            else:
                m = INT.match(self.text, self.pos)
                if not m:
                    self.fail("expected a string or integer key")
                self.pos = m.end()
                key = int(m.group())
            self.expect("]")
            self.expect("=")
            table[key] = self.value()
            if self.peek() == ",":
                self.pos += 1
        self.pos += 1
        return table


def lua_load(text):
    """`name = { ... }` → (name, table)."""
    p = Parser(text)
    name = p.name()
    p.expect("=")
    if p.peek() != "{":
        p.fail("expected a table")
    value = p.table()
    p.skip()
    if p.pos != len(text):
        p.fail("unexpected text after the table")
    return name, value


def lua_quote(s):
    """A string as Lua 5.1's %q writes it, which is how the Mission Editor writes strings."""
    return '"' + (s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\\n")
                  .replace("\r", "\\r").replace("\0", "\\000")) + '"'


def lua_key(key):
    return f"[{key}]" if isinstance(key, int) else f"[{lua_quote(key)}]"


def lua_scalar(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, Num):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() and abs(value) < 2 ** 53 else repr(value)
    if isinstance(value, str):
        return lua_quote(value)
    raise FormatError(f"cannot write a {type(value).__name__} as a Lua value: {value!r}")


def lua_dump(name, value, style):
    """Writes `name = { ... }` the way the Mission Editor does, in the given style."""
    if not value and style.compact_top:
        return f"{name} = {{}}\n"
    out = [f"{name} = \n{{\n"]

    def entries(table, depth):
        pad = style.indent * depth
        for key, v in table.items():
            k = lua_key(key)
            if not isinstance(v, dict):
                out.append(f"{pad}{k} = {lua_scalar(v)},\n")
            elif not v and style.compact_empty:
                out.append(f"{pad}{k} = {{}},\n")
            else:
                out.append(f"{pad}{k} = \n{pad}{{\n")
                entries(v, depth + 1)
                out.append(f"{pad}}}, -- end of {k}\n")

    entries(value, 1)
    out.append(f"}} -- end of {name}\n")
    return "".join(out)


def lua(value):
    """A Python value as a Lua table value: lists and tuples become arrays ({1: ..., 2: ...}), dicts
    are copied, recursively. A table used twice is written twice, as Lua does."""
    if isinstance(value, (list, tuple)):
        return {i + 1: lua(v) for i, v in enumerate(value)}
    if isinstance(value, dict):
        return {k: lua(v) for k, v in value.items()}
    return value


def num(value):
    """A number read from a file (Num) or written by a recipe, as int or float."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    f = float(value)
    return int(f) if f.is_integer() else f


def array(table):
    """The values of a Lua array (keys 1..n) in order."""
    return [table[k] for k in sorted(k for k in table if isinstance(k, int))]


def append(table, value):
    """Adds a value at the end of a Lua array, returning its index."""
    n = max([k for k in table if isinstance(k, int)] + [0]) + 1
    table[n] = value
    return n
