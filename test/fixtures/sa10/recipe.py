# SA-10 site and an EWR on Caucasus, run by Skynet IADS.
# Positions are those of "Mozdok SA10" and "Sarmakovo EW Site" in the shipped mission
# A-10CII_IA_CAUC_Roka Whack-a-Tank.miz.
russia = {"id": 0, "name": "Russia"}

M.gameMaster(1, 1)

# EWR: Skynet finds early-warning radars by unit name ("EW" prefix).
M.addGroup(side="red", country=russia, category="vehicle", name="EW-Sarmakovo",
           x=-103728.8, y=714246.7, units=[
               {"type": "1L13 EWR", "heading": 4.765, "name": "EW-Sarmakovo-1L13"}])

# SA-10: Skynet finds SAM sites by group name ("SAM" prefix). Offsets from the 40B6M track radar.
x0, y0 = -109929.6, 825787.4


def at(type, x, y, heading):
    return {"type": type, "dx": x - x0, "dy": y - y0, "heading": heading}


M.addGroup(side="red", country=russia, category="vehicle", name="SAM-SA10-Mozdok",
           x=x0, y=y0, units=[
               at("S-300PS 40B6M tr", -109929.6, 825787.4, 3.281),
               at("S-300PS 64H6E sr", -109714.2, 825818.6, 4.939),
               at("S-300PS 40B6MD sr", -109408.9, 825817.2, 3.142),
               at("S-300PS 54K6 cp", -109634.7, 825738.2, 5.725),
               at("S-300PS 5P85D ln", -109862.3, 825871.9, 1.798),
               at("S-300PS 5P85C ln", -109852.0, 825870.7, 1.798),
               at("S-300PS 5P85D ln", -109837.6, 825866.5, 1.798),
               at("S-300PS 5P85C ln", -109828.0, 825865.7, 1.798),
               at("S-300PS 5P85D ln", -109833.1, 825732.6, 4.939),
               at("S-300PS 5P85C ln", -109825.0, 825738.6, 4.939),
               at("S-300PS 5P85D ln", -109811.9, 825747.5, 4.939),
               at("S-300PS 5P85C ln", -109803.3, 825753.6, 4.939)])

M.onStart("Skynet IADS", [
    M.doScriptFile(M.embedFile("Scripts/skynet-iads-compiled.lua")),
    M.doScriptFile(M.embedFile("Scripts/iads-setup.lua"))])
