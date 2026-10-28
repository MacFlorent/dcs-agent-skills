# Ideas

Prospective work. An idea taken up leaves this file in the commit that opens its spec; a dropped
idea stays, with its reason.

## Reference missions checked in DCS

The tests compare two builds (`test/fixtures/*/expected.miz`) with their recipes, but neither
mission has been opened in the Mission Editor or flown. Check them in DCS, fix what is wrong, and
build further test missions for what the helpers write and nothing checks yet, so the reference
is a mission known to work.

## Templates for other maps

`building-dcs-missions` ships only `caucasus.miz`. Each map needs an empty mission saved by the
Mission Editor on it.

## DCS behaviour met by Skynet-IADS's in-sim suite

Seen while building that suite's scenarios, each confirmed in a run; worth a line in the skills
where it would have saved the search.

- **A waypoint task starts when the waypoint is reached.** `building-dcs-missions` says an attack
  task on an air-started group's first waypoint is ignored and goes on waypoint 2. If waypoint 2 is
  the end of the route, the attack starts only there: an F-16 told to fire a HARM from 70 km flew
  the whole route with both missiles on. Put waypoint 2 just after the start, carrying the task, and
  the route on to a third. Belongs in `writing-dcs-scripts` too: a group spawned by
  `coalition.addGroup` takes the same route table.
- **What the AI fires a HARM at.** At an SA-6's radar and a P-19, not at a 1L13 EWR, and never at a
  radar that is off (the SkynetMunitionTests campaign, confirmed again there).
- **`SetInvisible` hides from sensors, not from scripts.** An invisible aircraft is in no radar's
  detections, but `coalition.getGroups` still lists it: a script that reacts to any hostile aircraft
  nearby, seen or not, still reacts to it.
- **An EW radar far from a munition does not report it.** A 1L13 35 km and more away reported no bomb
  and no Maverick; a 55G6 2 km away reported every one within a second of release. A scenario
  measuring a reaction to munitions puts the EW radar beside the target.

