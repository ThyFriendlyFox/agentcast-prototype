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

### 1. v0.5 bring-up on the bench
- **Promise:** A v0.5 stick plugged into a TV boots its ESP32-P4, joins Wi-Fi through the C6, shows a test image over HDMI,, shows a desktop on a TV over HDMI, and records from the on-board mic and from a USB mic on J6 with `arecord`.
- **Evidence:** a photo of the TV and two WAV files in `hardware/v0.3/bringup/`.
- **Use case:** UC-1 (team room).
- **Scope guard:** no enclosure, no cloud agent, no echo cancellation.
- **Status:** blocked on firmware (ESP-IDF, ESP-Hosted, LT8912B driver) and the LT8912B crystal value.

### 2. Speaker labels from voice on the dongle's audio
- **Promise:** A recording from the v0.2 mic of 3 people talking in turn gets 3 speaker labels from a voice-based diarizer with under 15 % diarization error.
- **Evidence:** the script, the recording and the score in `hardware/v0.3/bringup/`.
- **Use case:** UC-4 (standup).
- **Scope guard:** offline test; no live pipeline.
- **Status:** blocked on item 1.

### 3. Echo reference: measure HDMI audio vs I2S clock drift
- **Promise:** A test plays a tone over HDMI and records it on the on-board mic, and reports the drift between the two clocks in ppm.
- **Evidence:** the script and its output in `hardware/v0.1/bringup/`.
- **Use case:** UC-2 (agent speaks, people interrupt).
- **Scope guard:** measurement only; no canceller.
- **Status:** blocked on item 1.

## Later — candidates, not yet specced

- Parts under the module (taller CM5 sockets) — a smaller board.
- Wired Ethernet on the main board — offices that block Wi-Fi devices.
- Enclosure — the dongle hangs behind a TV; the mic needs an opening.

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
