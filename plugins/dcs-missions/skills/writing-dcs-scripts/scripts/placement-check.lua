--[[
placement-check.lua -- is the ground at a map point fit for a ground group? Runs inside DCS.
The file returns a function; load it in the running mission, then call it:

  local check = dofile("<path>/placement-check.lua")
  return check({ { x = 25732, y = 454671 }, { x = -65000, y = 825000 } }, 150)

For each point (map metres, x north, y east) and a radius in metres, returns the surface type at
the centre and at 8 points on the circle, the height spread across them, and the buildings and
other scenery objects inside the circle. Trees are not scenery objects to the scripting engine:
a forest is invisible here, so look at the spot on the F10 map as well.
]]

local SURFACE = { [1] = "land", [2] = "shallow water", [3] = "water", [4] = "road", [5] = "runway" }

local function probe(x, y, radius)
  local lowest, highest, surfaces = math.huge, -math.huge, {}
  for i = 0, 8 do
    local px, py = x, y
    if i > 0 then
      local a = (i - 1) * math.pi / 4
      px, py = x + radius * math.cos(a), y + radius * math.sin(a)
    end
    local h = land.getHeight({ x = px, y = py })
    lowest, highest = math.min(lowest, h), math.max(highest, h)
    local s = SURFACE[land.getSurfaceType({ x = px, y = py })] or "unknown"
    surfaces[s] = (surfaces[s] or 0) + 1
  end

  local scenery = {}
  world.searchObjects(Object.Category.SCENERY,
    { id = world.VolumeType.SPHERE,
      params = { point = { x = x, y = (lowest + highest) / 2, z = y }, radius = radius } },
    function(obj)
      local name = obj:getTypeName() or "?"
      scenery[name] = (scenery[name] or 0) + 1
      return true
    end)

  local clear = surfaces.land == 9 and next(scenery) == nil and highest - lowest < radius / 10
  return { x = x, y = y, clear = clear, surfaces = surfaces,
           heightSpread = math.floor(highest - lowest + 0.5), groundHeight = math.floor(lowest),
           scenery = scenery }
end

return function(points, radius)
  local results = {}
  for i, p in ipairs(points) do results[i] = probe(p.x, p.y, radius or 150) end
  return results
end
