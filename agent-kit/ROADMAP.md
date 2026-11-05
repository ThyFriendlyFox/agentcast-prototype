# ROADMAP.md — the source of all work

**This file is not optional.** Every feature the agent builds flows down
from here. If it isn't on this roadmap, it doesn't get built; if it needs
building, it gets added here first. One item ships per weekly cycle
(see `WEEKLY.md`).

## North star

Agentcast is the cheapest way to give a cloud agent ears and a big screen
in any room: a small HDMI dongle with a far-field mic array that any team
can plug into a TV and use in minutes.

## Feature Queue — ordered; top unblocked item ships next

provisional: true (set by the agent at setup; the human re-orders)

### 1. v0.1 bring-up on the bench
- **Promise:** A CM5 on a v0.1 main board boots, shows a desktop on a TV over HDMI, and records 4 channels from the mic bar with `arecord`.
- **Evidence:** a photo of the TV and a 4-channel WAV in `hardware/v0.1/bringup/`.
- **Use case:** UC-1 (team room).
- **Scope guard:** no enclosure, no cloud agent, no echo cancellation.
- **Status:** blocked on ordering v0.1 boards (open item 1: CM5 socket positions).

### 2. v0.2 HDMI +5V load switch and main board SIM deck
- **Promise:** HDMI pin 18 holds at least 4.8 V at 55 mA with USB-C at 4.75 V, proven by an ngspice deck with sourced models.
- **Evidence:** `workcenter gates` GREEN on v0.2 main with the deck passing.
- **Use case:** UC-1.
- **Scope guard:** no other main board change.
- **Status:** ready

### 3. Echo reference: measure HDMI audio vs I2S clock drift
- **Promise:** A test plays a tone over HDMI and records it on the mic bar, and reports the drift between the two clocks in ppm.
- **Evidence:** the script and its output in `hardware/v0.1/bringup/`.
- **Use case:** UC-2 (agent speaks, people interrupt).
- **Scope guard:** measurement only; no canceller.
- **Status:** blocked on item 1.

## Later — candidates, not yet specced

- 8-mic bar on all 4 I2S0 lanes — better direction finding.
- Wired Ethernet on the main board — offices that block Wi-Fi devices.
- Enclosure and mic bar bracket — the bar must stand facing the room.

## Shipped

<!-- Move queue items here when done, newest first, with the release tag
     and the evidence link. This is the project's real history of intent. -->

| Week | Feature | Release | Evidence |
|---|---|---|---|
| 2026-11-05 | v0.1 boards designed | - | `workcenter gates` GREEN on main and micbar |

## Explicitly not doing

- A camera in v0.x — the spec keeps the device audio-only for trust until decided.

## Queue changes

<!-- Any reorder, insertion above position 3, or item removal gets one
     line here: date, what changed, why. -->
