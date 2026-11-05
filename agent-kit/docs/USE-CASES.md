# Use cases

<!-- The user-facing answer to "what do I do with this?". Each case has
     the same shape — pick the verbs that fit the product and keep them
     identical across every case. For a tool the shape might be
     Record/Play/Undo; for a library, Setup/Call/Result; for a service,
     Trigger/Action/Outcome. Cases are written in the repo's STYLE.md
     voice: short sentences, active voice, no marketing words.

     This file is load-bearing for the roadmap: every Feature Queue item
     in ROADMAP.md should trace to a use case here (or add one). A
     feature that serves no use case is a side quest. -->

Each case has the same shape: **Plug** (what the room sets up), **Talk**
(what people say), **See** (what the TV shows).

## UC-1 Team room

**Plug.** A team plugs the dongle into the room TV and sets the mic bar on top.
**Talk.** They plan a feature standing at the TV.
**See.** The TV shows the transcript, the tickets the agent wrote, and its first code diff.

## UC-2 Interrupt the agent

**Plug.** The dongle plays the agent's voice through the TV speakers.
**Talk.** A person talks over the agent to stop it.
**See.** The agent stops; the transcript shows the person's words, not the agent's echo.

## UC-3 Mute for a private meeting

**Plug.** The dongle is on and listening.
**Talk.** Someone slides the mute switch on the mic bar.
**See.** The green LED goes out and the red LED lights; the TV shows "muted".

## UC-4 Standup

**Plug.** The dongle is already in the room.
**Talk.** Each person says what they did and what blocks them.
**See.** The TV lists the updates and the blockers per person.

## UC-5 Solo desk

**Plug.** A builder plugs the dongle into a TV at home.
**Talk.** They talk through a bug.
**See.** The agent runs the code and shows the fix on the TV.
