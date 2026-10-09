# Ideas

Prospective work. An idea taken up leaves this file in the commit that opens its spec; a dropped
idea stays, with its reason.

## List dcs-hotload in the marketplace

Once a dcs-hotload release ships its own plugin (`.claude-plugin/plugin.json`), add its entry,
pinned to that release tag:
`{ "name": "dcs-hotload", "source": { "source": "github", "repo": "MacFlorent/dcs-hotload",
"ref": "v<x.y.z>" } }`. Each later hotload release moves the pin.

## Templates for other maps

`building-dcs-missions` ships only `caucasus.miz`. Each map needs an empty mission saved by the
Mission Editor on it.

