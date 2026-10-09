-- luacheck configuration, read by scripts/lint.sh, locally and in CI.
std = "lua51"
max_line_length = 120

-- test/fixtures/ keeps the Lua recipes the golden missions were built from, and stand-in scripts.
exclude_files = { "test/fixtures/**" }

-- Runs inside a DCS mission.
files["plugins/dcs-missions/skills/writing-dcs-scripts/scripts/placement-check.lua"] = {
  read_globals = { "land", "world", "Object" },
}
