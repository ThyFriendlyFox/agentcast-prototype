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
