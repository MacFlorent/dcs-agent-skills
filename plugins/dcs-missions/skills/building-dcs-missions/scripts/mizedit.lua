--[[
mizedit.lua -- edit an unpacked .miz with a Lua recipe, then write its tables back.
Usage (normally through miz.py build): lua mizedit.lua <unpacked dir> <recipe.lua>

The recipe runs with these globals:
  mission, mapResource, dictionary, options, warehouses   the mission's own tables, edit freely
  M                                                       the helpers below
Plain Lua 5.1, no DCS. Helpers fill the fields the Mission Editor writes, so a recipe only gives
what matters: types, positions, tasks.
]]

local DIR, RECIPE = arg[1], arg[2]
assert(DIR and RECIPE, "usage: lua mizedit.lua <unpacked dir> <recipe.lua>")

local TABLES = {
  mission = "mission", options = "options", warehouses = "warehouses",
  dictionary = "l10n/DEFAULT/dictionary", mapResource = "l10n/DEFAULT/mapResource",
}

local function load(name)
  local chunk = assert(loadfile(DIR .. "/" .. TABLES[name]))
  local env = {}
  setfenv(chunk, env)
  chunk()
  return assert(env[name], name .. " is missing from its file")
end

-- ── Serializer, Mission Editor style ───────────────────────────────────────────────────────

local function serialize(value, indent, out)
  local kind = type(value)
  if kind == "table" then
    local keys = {}
    for k in pairs(value) do keys[#keys + 1] = k end
    if #keys == 0 then out[#out + 1] = "{}" return end
    table.sort(keys, function(a, b)
      if type(a) == type(b) then return a < b end
      return type(a) == "number"
    end)
    out[#out + 1] = "\n" .. indent .. "{\n"
    for _, k in ipairs(keys) do
      local key = type(k) == "number" and ("[" .. k .. "]") or ("[" .. string.format("%q", k) .. "]")
      out[#out + 1] = indent .. "\t" .. key .. " = "
      serialize(value[k], indent .. "\t", out)
      out[#out + 1] = ",\n"
    end
    out[#out + 1] = indent .. "}"
  elseif kind == "string" then
    out[#out + 1] = string.format("%q", value)
  elseif kind == "number" then
    if value == math.floor(value) and math.abs(value) < 2^53 then
      out[#out + 1] = string.format("%.0f", value)   -- %d is 32-bit in Lua 5.1 on Windows
    else
      out[#out + 1] = string.format("%.17g", value)
    end
  elseif kind == "boolean" then
    out[#out + 1] = tostring(value)
  else
    error("cannot write a " .. kind)
  end
end

local function save(name, value)
  local out = { name .. " = " }
  serialize(value, "", out)
  out[#out + 1] = " -- end of " .. name .. "\n"
  local f = assert(io.open(DIR .. "/" .. TABLES[name], "wb"))
  f:write(table.concat(out))
  f:close()
end

-- ── The mission's tables ────────────────────────────────────────────────────────────────────

mission = load("mission")
options = load("options")
warehouses = load("warehouses")
dictionary = load("dictionary")
mapResource = load("mapResource")

M = {}

local function eachGroup(fn)
  for side, coal in pairs(mission.coalition) do
    for _, country in ipairs(coal.country or {}) do
      for _, category in ipairs({ "vehicle", "plane", "helicopter", "ship", "static" }) do
        for _, group in ipairs((country[category] or {}).group or {}) do
          fn(group, category, country, side)
        end
      end
    end
  end
end

local function nextIds()
  local g, u = 0, 0
  eachGroup(function(group)
    g = math.max(g, group.groupId or 0)
    for _, unit in ipairs(group.units or {}) do u = math.max(u, unit.unitId or 0) end
  end)
  return g + 1, u + 1
end

-- ── Tasks ───────────────────────────────────────────────────────────────────────────────────

--- A waypoint task that runs a command or sets an option, e.g.
--- M.wrapped{ id = "SetInvisible", params = { value = true } }.
function M.wrapped(action)
  return { id = "WrappedAction", enabled = true, auto = false, params = { action = action } }
end

M.invisible = function() return M.wrapped({ id = "SetInvisible", params = { value = true } }) end
M.immortal = function() return M.wrapped({ id = "SetImmortal", params = { value = true } }) end

--- An AI option on the first waypoint: name is the numeric option id, as in AI.Option.<Air|Ground>.id
--- (Hoggit wiki, "DCS func setOption"). Ground ROE is id 0: value 2 open fire, 4 weapon hold.
function M.option(name, value)
  return M.wrapped({ id = "Option", params = { name = name, value = value } })
end

--- Attack a map point. weaponType (MissionEditor/modules/me_action_db.lua, weaponTable):
--- 4294967295 all, 14 guided bombs, 240 iron bombs, 2032 any bomb, 4161536 any air-to-surface
--- missile, 2097152 cruise missile, 32768 anti-radiation.
function M.bombing(x, y, weaponType, expend)
  return { id = "Bombing", enabled = true, auto = false, params = {
    x = x, y = y, weaponType = weaponType or 4294967295, expend = expend or "All",
    attackQtyLimit = false, attackQty = 1, groupAttack = false,
    direction = 0, directionEnabled = false, altitude = 2000, altitudeEnabled = false,
  } }
end

local function combo(tasks)
  for i, t in ipairs(tasks or {}) do t.number = i end
  return { id = "ComboTask", params = { tasks = tasks or {} } }
end

-- ── Groups ──────────────────────────────────────────────────────────────────────────────────

local function countryOf(side, countryId, countryName)
  local coal = assert(mission.coalition[side], "no coalition " .. tostring(side))
  local allowed = false
  for _, id in ipairs(mission.coalitions[side] or {}) do
    if id == countryId then allowed = true end
  end
  assert(allowed, string.format("country %d is not on the %s side in this mission", countryId, side))
  coal.country = coal.country or {}
  for _, c in ipairs(coal.country) do
    if c.id == countryId then return c end
  end
  local c = { id = countryId, name = countryName }
  coal.country[#coal.country + 1] = c
  return c
end

--- Add a group. spec:
---   side = "red"|"blue"|"neutrals", country = { id, name }  (ids: DCS `country.id`, e.g. 0 Russia, 2 USA)
---   category = "vehicle"|"plane"|"helicopter"|"ship"
---   name, x, y                                group name and anchor (map metres, x north, y east)
---   units = { { type, dx, dy, heading, name, payload, skill }, ... }   offsets from x, y
---   tasks = { ... }                           tasks on the first waypoint (M.invisible() ...)
---   route = { { x, y, alt, speed, tasks }, ... }   extra waypoints (air and moving ground)
---   alt, speed, task                          air only: start altitude (m), speed (m/s), main task
---   lateActivation, hidden, uncontrollable
--- Returns the group table, already in the mission.
function M.addGroup(spec)
  local air = spec.category == "plane" or spec.category == "helicopter"
  local groupId, unitId = nextIds()
  local alt, speed = spec.alt or (air and 3000 or 0), spec.speed or (air and 150 or 0)

  local first = {
    x = spec.x, y = spec.y, alt = alt, alt_type = "BARO", speed = speed,
    type = "Turning Point", action = air and "Turning Point" or "Off Road",
    ETA = 0, ETA_locked = true, speed_locked = true, formation_template = "", name = "",
    task = combo(spec.tasks),
  }
  local points = { first }
  for _, p in ipairs(spec.route or {}) do
    points[#points + 1] = {
      x = p.x, y = p.y, alt = p.alt or alt, alt_type = "BARO", speed = p.speed or speed,
      type = "Turning Point", action = air and "Turning Point" or (p.action or "Off Road"),
      ETA = 0, ETA_locked = false, speed_locked = true, formation_template = "", name = "",
      task = combo(p.tasks),
    }
  end

  local group = {
    groupId = groupId, name = assert(spec.name, "a group needs a name"),
    x = spec.x, y = spec.y, start_time = 0,
    task = spec.task or (air and "Nothing" or "Ground Nothing"),
    taskSelected = true, tasks = {}, visible = false, hidden = spec.hidden or false,
    hiddenOnPlanner = false, lateActivation = spec.lateActivation or false,
    uncontrollable = spec.uncontrollable or false,
    route = { points = points, spans = {} },
    units = {},
  }
  if air then
    group.frequency, group.modulation, group.communication = 251, 0, true
    group.uncontrolled, group.radioSet = false, false
  end

  for i, u in ipairs(spec.units) do
    local unit = {
      unitId = unitId + i - 1, type = assert(u.type, "a unit needs a type"),
      name = u.name or string.format("%s-%d", spec.name, i),
      x = spec.x + (u.dx or 0), y = spec.y + (u.dy or 0),
      heading = u.heading or 0, skill = u.skill or "Excellent",
    }
    if air then
      unit.alt, unit.alt_type, unit.speed, unit.psi = alt, "BARO", speed, -(u.heading or 0)
      unit.onboard_num = string.format("%03d", unit.unitId)
      unit.callsign = { 1, 1, i, name = "Enfield1" .. i }
      unit.payload = u.payload or { pylons = {}, fuel = 0, flare = 0, chaff = 0, gun = 100 }
    else
      unit.playerCanDrive, unit.coldAtStart = false, false
      unit.transportable = { randomTransportable = false }
    end
    group.units[i] = unit
  end

  local country = countryOf(spec.side, spec.country.id, spec.country.name)
  country[spec.category] = country[spec.category] or { group = {} }
  local list = country[spec.category].group
  list[#list + 1] = group
  return group
end

--- Game Master (the "instructor" role) slots per side.
function M.gameMaster(blue, red)
  mission.groundControl.roles.instructor.blue = blue or 1
  mission.groundControl.roles.instructor.red = red or 1
end

-- ── Scripts and triggers ────────────────────────────────────────────────────────────────────

local RECIPE_DIR = RECIPE:match("^(.*)[/\\]") or "."

--- Embed a file in l10n/DEFAULT and register it. Returns its resource key. A relative path is
--- read from the recipe's folder.
function M.embedFile(path)
  if not (path:match("^%a:") or path:match("^[/\\]")) then
    path = RECIPE_DIR .. "/" .. path
  end
  local name = path:match("([^/\\]+)$")
  local src = assert(io.open(path, "rb"), "cannot read " .. path)
  local data = src:read("*a")
  src:close()
  local dst = assert(io.open(DIR .. "/l10n/DEFAULT/" .. name, "wb"))
  dst:write(data)
  dst:close()
  mission.maxDictId = (mission.maxDictId or 0) + 1
  local key = "ResKey_Action_" .. mission.maxDictId
  mapResource[key] = name
  return key
end

function M.doScriptFile(key)
  return { rule = { predicate = "a_do_script_file", file = key },
           code = string.format("a_do_script_file(getValueResourceByKey(%q));", key) }
end

function M.doScript(text)
  return { rule = { predicate = "a_do_script", text = text },
           code = string.format("a_do_script(%q);", text) }
end

--- A MISSION START trigger running the actions in order. Writes both halves the way the Mission
--- Editor does: trigrules (what the editor shows) and trig (what DCS runs).
function M.onStart(comment, actions)
  mission.trigrules = mission.trigrules or {}
  local trig = mission.trig
  local n = #mission.trigrules + 1
  local rules, code = {}, {}
  for i, a in ipairs(actions) do rules[i], code[i] = a.rule, a.code end
  mission.trigrules[n] = { comment = comment, predicate = "triggerStart", eventlist = "",
                           colorItem = "0x00ffffff", rules = {}, actions = rules }
  trig.actions[n] = table.concat(code)
  trig.conditions[n] = "return(true)"
  trig.flag[n] = true
  trig.funcStartup[n] = string.format(
    "if mission.trig.conditions[%d]() then mission.trig.actions[%d]() end", n, n)
end

-- ── Run the recipe, check, write ────────────────────────────────────────────────────────────

local recipe = assert(loadfile(RECIPE))
recipe()

local problems = {}
local groupIds, unitIds, names = {}, {}, {}
eachGroup(function(group, category, country)
  if groupIds[group.groupId] then problems[#problems + 1] = "duplicate groupId " .. group.groupId end
  groupIds[group.groupId] = true
  for _, unit in ipairs(group.units or {}) do
    if unitIds[unit.unitId] then problems[#problems + 1] = "duplicate unitId " .. unit.unitId end
    if names[unit.name] then problems[#problems + 1] = "duplicate unit name " .. unit.name end
    unitIds[unit.unitId], names[unit.name] = true, true
    print(string.format("TYPE\t%s\t%d\t%s\t%s\t%s", unit.type, country.id, country.name, category,
      group.name))
  end
end)
local function count(t) local n = 0 for _ in pairs(t or {}) do n = n + 1 end return n end
if count(mission.trigrules) ~= count(mission.trig.funcStartup) + count(mission.trig.func) then
  problems[#problems + 1] = "trigrules and trig have different trigger counts"
end
for key, file in pairs(mapResource) do
  local f = io.open(DIR .. "/l10n/DEFAULT/" .. file, "rb")
  if f then f:close() else problems[#problems + 1] = key .. " names a missing file " .. file end
end
if #problems > 0 then
  io.stderr:write("not written:\n  " .. table.concat(problems, "\n  ") .. "\n")
  os.exit(1)
end

for name in pairs(TABLES) do save(name, _G[name]) end
print("OK")
