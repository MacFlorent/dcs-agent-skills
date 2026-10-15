# Measured, not in the wiki

Behaviour measured in a live mission, DCS 2.9 (2.9.30 where a section or line says so). A DCS
update may change it: when a result contradicts a line here, say so rather than trusting the line.

## Observing a munition

- Follow `e.weapon` from the shot event (`S_EVENT_SHOT`; guns: `S_EVENT_SHOOTING_START`), and poll
  `Object.isExist(weapon)` for its end.
- Its height above ground when it disappears tells an interception (hundreds of metres) from an
  impact.
- A weapon's `getName()` is `""`; its id is `weapon.id_`.

## Weapon descriptors (2.9.30)

- `Weapon.getDescByName` does not exist. A launcher spawned with the weapon gives its descriptor
  without firing: `unit:getAmmo()[i].desc`.
- `missileCategory` does not mark cruise missiles reliably: the Kh-65 reports 5 (cruise), the
  AGM-84H SLAM-ER 6, like the Maverick and the HARM.
- The AGM-154 JSOW, a glide bomb, is a missile to DCS (`category` 1): an attack task limited to
  guided-bomb weapon flags never releases it.

## Ground units and radars (2.9.30)

- Every unit controller of a group returns the same `getDetectedTargets` list: it cannot tell
  which of the group's radars holds the track.
- With "Evasion of ARM" on, only the targeted unit reacts: its radar goes dark 10–20 s after it
  detects the missile, and a mobile single vehicle drives 250–400 m away.

## Rearming ground units

- A stationary unit within about 30 m of an ammo truck of its side (`Ural-375`, `Ural-4320-31`)
  rearms **if its AI is on**: a unit switched off with `controller:setOnOff(false)` is never
  rearmed, and starts rearming within about 30 s of `setOnOff(true)` (2.9.30).
- The rearm starts 30–60 s after the unit stops firing, not after the truck appears. An empty unit
  and a partly loaded one rearm alike; emission off (`enableEmission(false)`) does not stop it
  (2.9.30).
- Rates measured: IRIS-T one missile per ~15 s, C-RAM ~68 rounds per 15 s, Tor M2 (`CHAP_TorM2`)
  about 4 missiles per 15 s.
- A unit out of ammunition does not rearm on its own: without a truck nearby it stays empty.

## AI attacks, observed (2.9.30)

Seen on repeated runs, not explained; another geometry or target may give another result.

- The AI fires a HARM at a P-19 radar but not at a 1L13 EWR, not at a unit whose radar is off, and
  never at a Tunguska or a Gepard themselves.
- An AI AH-64D never fired a Hellfire at an IRIS-T SLM unit, nor at a 55G6 EWR 2 km from one.
- An AI Tu-22M3 never releases the Kh-22N at a ground target.
- A missile that strays or comes down short (seen with the SLAM-ER) usually flies right when
  launched again from a bearing turned by 45°.
