# DEVLOG.md — the live devlog

The plain history of this project. A person who knows nothing about the
code reads this file and knows what happened, in order, with no jargon.
Append only. Never rewrite an old entry — a wrong entry gets a
correction entry, not an edit.

Write every entry in the voice of `TONE.md`.

## Entry shape

Every entry has the same shape:

```
## YYYY-MM-DD — <one line: what happened>

<What we did. What worked. What broke. What we learned.
3–10 short sentences. Plain words. Past tense for what happened,
present tense for how things now stand.>

Evidence: <commit / tag / gate run / screenshot>
```

## When to write

- Every WEEKLY.md cycle writes one entry at step 5 (before merge).
- A failed or abandoned attempt gets an entry too. The devlog records
  what happened, not what succeeded. A week with no shipped feature
  still gets its entry.
- Out-of-band work (security patch, gate repair, big triage) gets one.
- SETUP.md writes the first entry: "Installed the agent kit."

## What does not go here

- Code detail that belongs in commit messages.
- Promises about the future — that is ROADMAP.md.
- State claims — that is STATUS.md. The devlog is the story; STATUS is
  the snapshot.

---

<!-- Entries below, newest first. -->

## 2026-11-05 — Installed the agent kit and designed hardware v0.1

I installed the agent kit and filled its placeholders. The repo holds the
Agentcast dongle hardware. I designed v0.1 as two boards with the Via EE
Workcenter. The main board carries a Raspberry Pi CM5 with an HDMI-A port
and USB-C power. The mic bar has 4 I2S mics and a hardware mute switch. I
drew the 4 HDMI pairs by hand; FreeRouting routed the rest. Both boards
pass ERC, DRC and export. The CM5 socket positions come from an approximate
datasheet figure and need a check before ordering.

Evidence: `workcenter gates` GREEN on `hardware/v0.1/main` and `hardware/v0.1/micbar`.

## 2026-11-05 — v0.2: one board with an on-board mic

The human found v0.1 too big and asked for one board. Speaker labels come
from voices, not directions, so the 4-mic bar went. v0.2 is one 57 x 50.4 mm
board under the CM5. It has one I2S mic, a USB-C port for an external mic,
and the mute switch, which now also cuts the external port's power. Small
parts moved to the bottom face. The HDMI +5V now runs through a switch, not a
diode. The board passes ERC, DRC, SIM and export. v0.1 is archived.

Evidence: `workcenter gates` GREEN on `hardware/v0.2/dongle`.

## 2026-11-05 — v0.3: the dongle becomes a stick

The human asked for a slimmer, stick-shaped board and could not see a USB port
in the v0.2 pictures. The v0.2 USB-C parts had no 3D body in KiCad and drew as
black boxes; v0.3 uses the GCT USB4085, which has one, and `render --strict`
now passes. v0.3 is 67 x 46 mm with HDMI out of the end and the two USB-C ports
out of the sides. I checked the CM5 sockets and holes against Raspberry Pi's
CM5 3D model: they match. The HDMI pairs now run 60 to 66 mm in nested lanes,
matched to 0.000 mm within each pair. The router cut the +5V pour into pieces
twice, so In2.Cu is now a plane with nothing else on it. No board-mount HDMI
plug with a drawing turned up, so the stick still needs an adapter.

Evidence: `workcenter gates` GREEN on `hardware/v0.3/dongle`.

## 2026-11-05 — v0.4: a male HDMI plug on the stick

The human pointed out that a TV dongle needs a male HDMI plug. v0.4 clamps a
male HDMI Type-A plug on the board's near edge: odd contacts on the top face,
even on the bottom. KiCad has no such footprint, so the library script draws
one from the HDMI Type-A contact layout. Two HDMI pairs now drop through a via
pair to the bottom contacts; all four stay matched within each pair. The part's
drawing (XUNPU HDMI-003) would not download here, so its pad size, clamp tabs,
odd-row face and board thickness are still to confirm. Gates are GREEN.

Evidence: `workcenter gates` GREEN on `hardware/v0.4/dongle`.

## 2026-11-06 — v0.5: our own computer on a Chromecast-sized stick

The human asked for a stick like a Roku or Chromecast, narrower than the CM5
allows, and sent the XUNPU HDMI-003 plug drawing. The dongle does not need
Linux: it streams audio up and shows what the cloud renders. v0.5 uses an
ESP32-P4 with in-package PSRAM, an LT8912B DSI-to-HDMI bridge with HDMI
audio, and an ESP32-C6 module for Wi-Fi, on a 72 x 26 mm board. The plug
footprint now follows the manufacturer drawing: even pins on top, odd below,
and two slots cut in the board edge. The LT8912B crystal value is not in its
datasheet and stays open.

## 2026-11-07 — v0.5: six layers, hand-drawn DSI, a fanout that leaves lanes

The P4's 0.35 mm pitch would not route on four layers: every FreeRouting run
left 20 to 38 connections open. The board went to six layers (JLC06161H-2313,
two ground planes), and the pairs shrank to suit its 0.1 mm prepreg. The DSI
pairs are drawn by hand; to keep them from crossing, D0 and D1 have P and N
swapped, which the LT8912B allows and its driver must undo. Before routing,
each P4 and LT8912B pad gets a via on a short stub, placed so that a pad
without one still has a straight lane out; the QFN ground pads tie into the
exposed pad instead of taking a via outside. Via's stitching and its router
model ignore the 0.25 mm hole clearance, so this board keeps 0.15 mm copper
clearance, which puts a via's hole at 0.25 mm.

## 2026-11-07 — v0.5: 30 mm wide, eight layers

Six layers still left 28 connections open around the P4, and widening the
board from 26 to 30 mm (the human's call) only took it to 26. The human
asked why not more layers; the board went to eight (JLC081611-2116: ground
planes on In1 and In6, four inner routing layers). Its 0.109 mm outer
prepreg is close enough to the six-layer board's 0.1 mm that the pair
widths stay: about 104 ohm TMDS and 102 ohm DSI.

## 2026-11-08 — v0.5: GREEN at 80 x 30 mm

Eight layers did not finish it either: the router kept leaving 15-25
connections at the P4, every one a pin its neighbours' vias boxed in. The
human allowed a longer board; at 80 mm the mic moved off the P4's bottom
row. The rest came from the pins, not the router: movable GPIOs spread to
every other free pin, the flash moved to the top face with its bus drawn
by hand, pins boxed in outside take a via between the pad ring and the
exposed pad, and one HDMI pair runs 0.6 mm further to free a via spot. Two
fanout bugs fell out on the way (a lane check that refused every via once
one lane had closed, and a fan pass that forgot vias already placed).
What FreeRouting still leaves, finish.py routes: a grid search that may
move another net only if that net then rejoins, and undoes the move
otherwise. A rip-up that kept its moves regardless went from 23 open to
150; the careful one cannot make a board worse. Gates GREEN, make verify
GREEN.
