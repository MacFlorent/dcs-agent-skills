M.gameMaster(1, 1)
M.addGroup(side="red", country={"id": 0, "name": "Russia"}, category="vehicle",
           name="SAM-SA6", x=25732, y=454671, tasks=[M.immortal()], units=[
               {"type": "Kub 1S91 str"}, {"type": "Kub 2P25 ln", "dx": 100}, {"type": "Kub 2P25 ln", "dy": 100}])
gbu = {"CLSID": "{GBU-38}"}
M.addGroup(side="blue", country={"id": 2, "name": "USA"}, category="plane", name="MQ9",
           x=-14268, y=454671, alt=5000, speed=80, task="Ground Attack", tasks=[M.invisible(), M.immortal()],
           units=[{"type": "MQ-9 Reaper", "payload": {"pylons": [gbu, gbu, gbu, gbu], "fuel": 1300,
                                                      "flare": 0, "chaff": 0, "gun": 100}}],
           route=[{"x": 15000, "y": 454671, "tasks": [M.bombing(23732, 454671, 14)]}])
M.onStart("scripts", [M.doScriptFile(M.embedFile("Scripts/my-script.lua")),
                      M.doScript('env.info("mission start")')])
