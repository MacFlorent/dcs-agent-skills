# Measured, not in the wiki

Behaviour measured in a live mission, DCS 2.9. A DCS update may change it: when a result
contradicts a line here, say so rather than trusting the line.

## Observing a munition

- Follow `e.weapon` from the shot event (`S_EVENT_SHOT`; guns: `S_EVENT_SHOOTING_START`), and poll
  `Object.isExist(weapon)` for its end.
- Its height above ground when it disappears tells an interception (hundreds of metres) from an
  impact.
- A weapon's `getName()` is `""`; its id is `weapon.id_`.

## Rearming ground units

- A stationary unit within about 30 m of an ammo truck of its side (`Ural-375`, `Ural-4320-31`)
  rearms, starting about 50 s after the truck appears.
- Rates measured: IRIS-T one missile per ~15 s, C-RAM ~68 rounds per 15 s.
- A unit out of ammunition does not rearm on its own: without a truck nearby it stays empty.
