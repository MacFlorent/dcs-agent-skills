-- luacheck configuration. CI runs `luacheck .` from the repository root.
std = "lua51"
max_line_length = 120

-- Runs in plain Lua 5.1 and hands the mission's tables to the recipe as globals. Its section
-- rulers are box-drawing characters, three bytes each, which a byte count takes for long lines.
files["plugins/dcs-missions/skills/building-dcs-missions/scripts/mizedit.lua"] = {
  globals = { "mission", "options", "warehouses", "dictionary", "mapResource", "M" },
  max_comment_line_length = false,
}

-- Runs inside a DCS mission.
files["plugins/dcs-missions/skills/writing-dcs-scripts/scripts/placement-check.lua"] = {
  read_globals = { "land", "world", "Object" },
}
