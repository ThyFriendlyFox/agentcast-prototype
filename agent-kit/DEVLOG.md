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
