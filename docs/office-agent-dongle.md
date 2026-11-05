# Office Agent Dongle

Nov 5, 2026 · @thyfriendlyfox

## Summary

The Office Agent Dongle is a small HDMI device with a far-field microphone array. You plug it into any TV. People in the room talk normally, and a cloud agent hears them, does the work, and shows the results on the TV.

The device does very little work itself. It captures clean audio, sends it to the cloud, and shows a live dashboard. The agent, its tools, and its per-user desktop VM run in the cloud.

No product does this today. TVs and streaming boxes have microphones, but they keep them for their own assistants.

## Problem and origin

On Nov 4, 2026, Sharif Shameem posted an idea he called "The Office of the Future." It is a normal office with microphones and cameras everywhere. People talk all day, agents get the transcripts, and agents do the tasks and show results on big TV screens. The idea also fits our goal of offices without desks, where people stand and work in groups.

The hard part is the hardware. Every room needs a good microphone and a screen, and both must connect to the agent. Today the options all fail:

| Platform | Screen | Microphone | Why it fails |
| --- | --- | --- | --- |
| [Roku TV](https://developer.roku.com/dev/docs/dev-environment) | Yes | Remote only | Apps run in a BrightScript sandbox. The mic works only while the user holds OK ([source](https://medium.com/float-left-insights/speech-recognition-on-roku-using-google-cloud-speech-to-text-api-ac79bb944986)). |
| Samsung TV (Tizen) | Yes | Built in, or borrowed from a soundbar | Samsung keeps the mic for Bixby and its own data collection ([source](https://runtimewire.com/article/scoop-samsung-s-tizen-tv-api-can-find-and-enable-connected-microphones)). |
| [Fire TV Cube](https://developer.amazon.com/docs/fire-tv/voice-enable-your-app-and-content.html) | Yes | 8 far-field mics | Apps get Alexa voice commands, not raw audio. |
| Laptop in each room | Small | Yes | Poor far-field pickup. People must set it up every time. |

The Samsung case is useful proof. In Oct 2026, a researcher (log4j) reported that a Samsung TV runs an on-board model that classifies room sounds, and can use the mic on a connected soundbar ([source](https://cybernews.com/privacy/samsung-smart-tv-spying-microphones-ai/)). So the TV makers already treat the TV as a room microphone. They just do not let you use it.

## Product

The user experience has three steps: plug in, sign in once, and talk.

1. Plug the dongle into a TV HDMI port and a USB-C power supply.
2. Scan a QR code on the TV with a phone. Sign in and pick a workspace.
3. Talk. The TV shows what the agent hears, what it is doing, and what it made.

The TV screen shows only the work: the live transcript, the agent's current task, and the results (code diffs, documents, test runs, previews). No settings menus show on the TV.

**Use cases:**

- **Team room.** A team stands at the TV and plans a feature. The agent writes tickets and starts the code while they talk.
- **Standup.** Each person says what they did. The agent updates the tracker and lists the blockers on screen.
- **Solo desk.** A builder talks through a bug at home. The agent runs the code and shows the fix on the TV.
- **Client meeting.** The agent captures action items and drafts the follow-up email. Everyone in the room gives consent first.

## How it works

The idea has two parts: a device in the room and an agent in the cloud.

- **The device.** A small dongle plugs into the TV's HDMI port. It has a far-field microphone array, so it hears everyone in the room. It shows the agent's work on the TV.
- **The agent.** It runs in the cloud on its own computer. It turns what people say into tasks, does the tasks, and sends the results back to the screen.

The dongle can be cheap because it does very little work. The value is in the agent. Any TV in any room becomes a place where an agent listens and works.

## Foreseen issues and required features

These are requirements for the design, not solutions. Each issue below needs a feature in the device or the service.

### Echo cancellation

Echo cancellation is the most important audio feature. Without it, the agent hears itself and the TV, and it cannot tell those sounds from people.

The TV shows only what the dongle sends, like a Chromecast. So every sound from the TV speakers comes from the dongle: the agent's voice, video sound, and alerts. The device always has an exact copy of what plays, and it can subtract that copy from the microphone signal. These problems remain:

- **TV delay.** The TV processes sound before it plays it. The delay changes with the TV model, picture mode, and sound mode. The device must measure the delay at setup, for example with a short test sound, and keep tracking it, because people change TV settings.
- **The TV changes the sound.** TV speakers and settings such as bass boost, virtual surround, and dialogue enhancement change the sound. The echo that reaches the mics is not an exact match of the copy. The cancellation must adapt to each room and TV.
- **Soundbars and receivers.** The TV can pass the sound to a soundbar over HDMI ARC. This adds more delay and moves the sound source to a different place in the room.
- **Loud TV, quiet person.** At high volume, the echo is much louder than a person speaking from across the room. The device must remove a strong echo without removing the speech under it.
- **Interruptions (barge-in).** A person must be able to talk over the agent and stop it. The cancellation must work while the agent speaks, so both sides can talk at the same time.

Sound that does not come from the dongle, such as a laptop video or people in the hallway, cannot be cancelled this way. It needs noise suppression instead.

### Speaker identification

The agent must know who said what. Otherwise it assigns tasks to the wrong person and mixes up decisions.

**Two separate jobs:**

1. **Diarization ("who spoke when").** The software splits the audio into turns and groups the turns by voice. The output uses anonymous labels such as Speaker 1 and Speaker 2. It cannot find real names by itself ([source](https://www.recall.ai/blog/speaker-labels-and-names-explained)).
2. **Identification ("who is Speaker 1").** The software matches each group to a real person.

**Ways to identify people** (products combine these):

- **Voice enrollment.** Each person records a short, clean voice sample once. pyannote uses a clip of up to 30 seconds with one voice only ([source](https://www.pyannote.ai/blog/speaker-identification-system-recurring-meetings)). People who did not enroll stay anonymous.
- **Learning from corrections.** A user names a speaker once, and the system recognizes that voice in later meetings ([ClovaNote](https://help.worksmobile.com/en/use-guides/clovanote/view/speaker-identification/)).
- **Context.** People often say their names at the start of a meeting. The software can catch those names in the transcript.
- **Who is in the room.** QR sign-in and calendar invites tell the system which people to expect. This narrows the possible matches.

**How others do it.** For virtual meetings, tools like Read AI get names from the meeting platform. For in-person meetings, Read AI records on a phone and detects each unique speaker ([App Store](https://apps.apple.com/app/id6575345796)). The closest product to this idea is [Microsoft Teams Intelligent Speakers](https://support.microsoft.com/office/use-teams-intelligent-speakers-to-identify-in-room-participants-in-meeting-transcription-a075d6c0-30b3-44b9-b218-556a87fadc00): an in-room device where people enroll their voice, others can correct a label, and the identified person can reject it. It turns off voice identification for meetings with more than 20 invitees.

**The advantage of a mic array: direction.** A phone hears one channel. An array also hears where each voice comes from. Research shows that combining direction with voiceprints beats single-channel diarization, mostly when people talk over each other ([source](https://arxiv.org/abs/2506.16228v1)). Direction alone fails when people walk around, so the system needs both.

**Foreseen problems:**

- **Overlapping speech.** Two people talk at once. Standard diarization gives the segment to one person. The system needs overlap detection, and direction helps separate the voices.
- **Live labels versus final labels.** Live labels use only the audio so far. A later pass regroups the voices with the full recording. The agent may act on a wrong live label, so it needs a rule: wait for a confident ID before it assigns a task to a person.
- **Guests.** Clients, visitors, and new hires have no voiceprint. The system needs a guest mode that does not store their voice by default.
- **Similar or changing voices.** Colleagues with similar voices, a cold, or a person who moves across the room all cause errors. The UI must make corrections fast.
- **The agent's own voice.** Leftover echo of the agent must never become a speaker label.
- **Voiceprints are biometric data.** Some states, such as Illinois, regulate voiceprints under biometric privacy law. This is separate from recording consent. Enrollment needs its own opt-in, a stated retention period, and a way to delete the voiceprint.

**What the device must provide** (requirements for the EE):

- **All mic channels, not only one cleaned channel.** Most voice chips output a single processed channel and discard the direction information. The device must also deliver every mic channel, or several beam outputs, to the software.
- **A fixed, known mic layout.** The software needs exact mic positions. Wider spacing gives better direction cues, because the cues get weaker when mics sit close together ([source](https://web3.arxiv.org/pdf/2506.16228)). This conflicts with a small dongle body.
- **One shared clock.** All mic channels and the playback copy need sample-aligned timestamps. Echo cancellation and direction finding both depend on this.
- **Direction and voice activity per frame.** The device should report direction of arrival and speech detection with the audio. The heavy models can run in the cloud.

### Hearing the room

The agent is only as good as what it hears. A missed word can change a task, and a whole missed sentence loses a decision.

**Foreseen problems:**

- **Mics behind the TV.** A dongle hangs behind the TV, like a Chromecast. The TV body blocks sound and creates echoes off the wall. The mics cannot sit in the dongle body.
- **Wall-mounted TVs.** TVs often hang high on a wall or above a cabinet. The mics then point at the ceiling or the far side of the room.
- **Distance.** People stand or sit anywhere in a meeting room, often 3 to 6 m away. Speech from far away is quiet and mixed with room echo.
- **People spread around the room.** The mics must hear every direction. People also face away from the TV when they talk to each other.
- **Room echo (reverberation).** Glass walls, hard floors, and bare walls make speech smear. Speech recognition gets worse as reverberation grows.
- **Steady noise.** HVAC, projectors, fans, and street noise sit under the speech all day.
- **Sudden noise.** Doors, chairs, coffee machines, and typing cause short loud sounds that can cut off words.
- **Other sound sources.** A laptop plays a video, or a phone rings. These sounds do not come from the dongle, so echo cancellation cannot remove them.
- **Whispers and side talk.** Two people talk quietly in a corner. The system must decide if that speech is part of the meeting.

**What the device must provide:**

- **A mic unit separate from the dongle body.** It sits on top of or below the TV and faces the room. A cable connects it to the dongle. Portal TV used this form: a bar on the TV ([source](https://higlo.co/shared-space/the-history-of-the-meta-portal-tv-the-right-product-from-the-wrong-company)).
- **360° far-field pickup** across a full meeting room.
- **Beamforming** that follows the active speaker, and can follow more than one speaker at a time.
- **Noise suppression and de-reverberation** that remove noise without cutting speech. Too much suppression damages the audio that speech recognition and speaker ID need. So the device should also keep a lightly processed version for those models.
- **Automatic gain control** so near and far voices reach the same level.
- **A room check at setup.** The device measures noise and reverberation and tells the user if the room or the mic position is bad.

### Many devices and rooms

The idea puts a device in every room. Many devices in one office create problems that one device does not have.

**Foreseen problems:**

- **One conversation, two devices.** In open offices or rooms with thin walls, two devices hear the same speech. Both agents could act on it, so a task could be done twice.
- **The wrong room acts.** A loud person in the next room gives a command, and this room's agent does it.
- **People move between rooms.** A conversation starts in one room and continues in another. The agent must keep the context.
- **Two agents talk at once.** Two devices in one big space speak results over each other.
- **Shared spaces versus private rooms.** A lobby TV and a private office need different rules about what the agent shows and does.

**What the system must provide:**

- **Room boundaries.** Each device belongs to one room. The devices compare what they hear, detect duplicate speech, and agree on which device acts.
- **A loudness and direction test** so a device ignores faint speech from outside its room.
- **Context that follows people.** The workspace keeps one shared memory, so a person can continue in another room.
- **Room types.** Admins mark each room as shared or private, and the agent follows that room's rules.

### Consent, privacy and trust

A microphone in every room is the idea's biggest strength and its biggest risk. People will not use it unless they trust it, and the law limits it.

**Foreseen problems:**

- **All-party consent.** Florida requires consent from every person in a recorded conversation, including at work ([source](https://recordinglaw.com/party-two-party-consent-states/florida-recording-laws/)). A visitor who walks into the room has not consented.
- **People do not know the state.** People must always know if the device is off, waiting, listening, or recording.
- **Fear of a hidden "on" state.** After the Samsung story, people will ask if software can turn the mics on in secret ([source](https://cybernews.com/privacy/samsung-smart-tv-spying-microphones-ai/)).
- **Private talk in a work room.** People say personal things near the TV. Storing everything forever is a liability.
- **Sensitive meetings.** HR, legal, and client meetings need the device fully off.
- **Who can see the data.** A manager reading every transcript of every room is a trust problem, even when it is legal.
- **Voiceprints.** See speaker identification: biometric laws apply.

**What the system must provide:**

- **Clear listening states** that people can see from anywhere in the room: off, waiting for a wake word, and active. The TV screen and a light on the device both show the state.
- **An optional on-device wake word.** In this mode, no audio leaves the room until someone activates the agent.
- **A physical mute** that disconnects the microphones. Its indicator must be tied to the mic power, so software cannot show "off" while the mics are on.
- **A consent flow** at sign-in for every user, and a visible notice for visitors.
- **A private mode** for one meeting: one tap or one spoken command turns off listening until the meeting ends.
- **Retention rules.** Delete raw audio after transcription by default. Admins set how long transcripts are kept.
- **Access rules.** Each person can see what the device captured about them. Admins see audit logs, not every transcript by default.
- **No ads and no data sale**, stated in plain words. The business earns from the subscription only.

### Getting results in front of people

The TV is the agent's face. If the screen is off, unreadable, or silent, the agent's work is lost.

**Foreseen problems:**

- **The TV is off or on another input.** The agent finishes a task, but the TV sleeps or shows a cable box on another HDMI port.
- **TV volume is low or muted.** The agent's voice plays through the TV speakers, so the TV remote controls it. The dongle cannot see the TV volume.
- **HDMI-CEC is not reliable.** CEC lets a device turn the TV on, switch inputs, and change volume. TV brands support it in different ways, and some turn it off by default.
- **Text too small.** People read the TV from several meters away.
- **Many TV types.** Resolutions, aspect ratios, and overscan differ. Some TVs cut off the screen edges.
- **Burn-in.** A dashboard that stays the same for hours can burn into OLED TVs.
- **Screen privacy.** Glass-walled rooms let people outside read the TV. A private document on screen is visible to everyone who walks by.
- **Wrong time to speak.** The agent talks while someone presents, or reads out a private result to the room.

**What the system must provide:**

- **TV control over HDMI-CEC** to wake the TV, switch to the dongle's input, and set the volume. It needs a fallback when CEC fails, such as a prompt on the user's phone.
- **A backup voice path.** A small speaker on the device, or on-screen captions, for when the TV is muted.
- **A layout made for distance viewing:** large text, high contrast, and safe margins for overscan.
- **Burn-in protection:** the layout moves slightly over time, and the screen dims when the room is idle.
- **Display rules:** private results go to the person's phone, not the room screen.
- **Speaking rules:** the agent waits for a pause, speaks only when asked or for urgent items, and uses the screen for everything else.

### Power, network and setup

The device must work in any office with no IT help. Setup must take minutes, and the device must recover from problems by itself.

**Foreseen problems:**

- **Weak power from the TV.** Many TV USB ports supply too little power, and some turn off when the TV sleeps. The device would then go deaf when the TV is off.
- **Heat behind the TV.** The space behind a TV is hot and has little airflow.
- **Office Wi-Fi.** Offices use captive portals, enterprise sign-in, or networks that block devices they do not know.
- **Firewalls.** Some offices block the streaming connections that live audio needs.
- **Network drops.** The agent runs in the cloud. A short drop can lose speech, and a long drop makes the device useless.
- **Latency.** A slow round trip makes the agent feel slow and makes interruptions awkward.
- **No keyboard.** A TV has no easy way to type a password or a sign-in.
- **Moving the device.** People unplug it and take it to another room or home.

**What the system must provide:**

- **A separate power supply.** The device must not depend on the TV's USB port.
- **Heat tolerance** for the space behind a TV.
- **Wired Ethernet as an option**, and support for enterprise Wi-Fi.
- **Network needs that IT can approve:** a short, documented list of the connections the device uses.
- **A buffer** that holds recent audio during short drops and sends it when the network returns, plus a clear offline state on screen.
- **Low-latency streaming** for live audio.
- **Phone pairing.** The TV shows a QR code, and the user signs in and picks the room on a phone.
- **Room reassignment** when the device moves, so it does not act with the wrong room's rules.

### Security and updates

This device hears private conversations and controls an agent that takes real actions. That makes it a target for attackers, and some attacks need only sound.

**Foreseen problems:**

- **Spoken commands from the wrong source.** A video, a phone call, or a person in the hallway says a command, and the agent acts on it.
- **Commands inside the dongle's own media.** The dongle plays a video that contains words aimed at the agent. Echo cancellation removes most of it, but not always all of it.
- **Voice spoofing.** A recording or an AI clone of a manager's voice asks for a risky action.
- **Prompt injection by voice.** Someone speaks instructions that try to change the agent's rules.
- **Risky actions by voice.** A spoken "deploy it" or "delete that" is easy to say by mistake or misunderstand.
- **Stolen or lost device.** The device holds sign-in tokens for the workspace.
- **Network attacks.** Someone intercepts the audio stream or pushes fake firmware.
- **Old firmware.** Devices that never update keep known security holes.

**What the system must provide:**

- **Never treat the dongle's own playback as a command.** The system knows what it played, so it must ignore speech that matches its own output.
- **Permissions per action.** Low-risk actions run from voice. High-risk actions, such as deploys, deletions, payments, and outside emails, need confirmation on the person's phone.
- **Voice is not authentication.** A voiceprint helps label speakers, but it must never be the only proof of who gave a command.
- **Encrypted audio** from the device to the cloud.
- **Secure boot and signed firmware**, so the device runs only firmware from the maker.
- **Automatic updates**, with a way to roll back a bad update.
- **Remote lock and wipe** from the admin console, and short-lived sign-in tokens on the device.

## Market and competitors

The closest competitor is Vibe Bot, an AI meeting-room device from CES 2026. It and the other products in this space record and summarize meetings. None of them acts as a live agent that does the work and shows it on the room TV.

| Product | What it is | Gap for this idea |
| --- | --- | --- |
| [Vibe Bot](https://vibe.us/blog/meeting-owl-alternatives/) | All-in-one meeting-room device with its own OS, notes, cross-meeting memory, and MCP-compatible tool links | Notes and memory, not a live work agent. Expensive room hardware, not a $150 dongle. |
| [Kandao Meeting Pro 2](https://vibe.us/blog/meeting-owl-alternatives/) | 360° conference camera with on-device transcription (May 2026) | Video calls and summaries only |
| [AI notetaker pins and recorders](https://techcrunch.com/2026/03/20/ai-notetaker-hardware-devices-pins-pendants-record-transcribe/) | Wearables and desk recorders, about $89 to $200 | Personal, no screen, no agent |
| [Fire TV Cube](https://developer.amazon.com/docs/fire-tv/voice-enable-your-app-and-content.html) | Streaming box with 8 far-field mics | Mics serve Alexa only |
| [Meta Portal TV](https://en.wikipedia.org/wiki/Meta_Portal) | Camera and mic bar for a TV, $99, discontinued in 2022 | Proves the form factor. Failed on trust in Facebook and thin app support. |

Two lessons come from Portal TV. First, a TV-attached mic device can ship at a low price. Second, buyers judge the maker before they trust a microphone in their room ([source](https://higlo.co/shared-space/the-history-of-the-meta-portal-tv-the-right-product-from-the-wrong-company)).

**Our position:** the cheapest way to give a cloud agent ears and a big screen in any room. The agent is the product. The dongle is how it enters the room.

## Business model and go-to-market

Sell the dongle near cost and earn on the agent. The hardware is the way in. The subscription is the business.

**Revenue (proposed):**

- **Hardware.** One-time sale, priced close to parts plus assembly. A low price lets a team put one in every room.
- **Subscription.** Monthly fee per workspace, plus usage credits for agent time and VM hours. This uses the same billing model as the voice agent: credits plus a monthly plan through Stripe.
- **Rooms add up.** A company pays once per seat or workspace. More dongles in more rooms raise usage, not new contracts.

**Go-to-market:**

1. **Use it ourselves first.** Put dongles in Reagent rooms and Developer Day sessions. This follows the rule "do it ourselves first, so Reagent knows how to help others."
2. **Demo video.** A team talks at a TV, and the agent ships a feature on screen. This one clip carries the whole pitch. It can reply to posts like Sharif's.
3. **Small teams first.** Target startups and agencies of 5 to 50 people that already pay for coding agents. They buy fast and have no IT review.
4. **Automated outbound.** Use automated AI cold email to engineering leads at those teams, so distribution does not depend on personal content creation.

Enterprise sales come later. Enterprise rooms need security reviews, SOC 2, and device management.

## Risks

The biggest risk is legal, not technical. Florida and about a dozen other states require consent from every person before a conversation is recorded.

| Risk | Why it matters |
| --- | --- |
| Recording consent law | Florida requires all-party consent under Fla. Stat. § 934.03. Recording without it is a third-degree felony, with civil damages too ([source](https://recordinglaw.com/party-two-party-consent-states/florida-recording-laws/)). The rule applies in the workplace. Always-on listening may not be legal without clear consent from every person in the room. |
| Trust | The Samsung story and Portal TV show that buyers fear room microphones. The maker's reputation decides whether people accept the device. |
| Competition | Vibe Bot and others already sell AI room devices. The idea must win on price and on a live agent, not on meeting notes. |
| Cloud cost | An agent that listens and works all day uses a lot of compute. The price must cover it. |

## Open questions

- [ ] Always-on listening or wake word? Always-on fits Sharif's vision but raises the consent risk.
- [ ] One agent per room, or one agent per person?
- [ ] Add a camera later, or stay audio-only for trust?
- [ ] Which Reagent subsidiary owns this idea?
- [ ] What price for the device and the subscription?

## Sources

- [Roku developer environment overview](https://developer.roku.com/dev/docs/dev-environment)
- [Speech recognition on Roku (Medium)](https://medium.com/float-left-insights/speech-recognition-on-roku-using-google-cloud-speech-to-text-api-ac79bb944986)
- [Runtime Wire: Tizen can enable connected microphones](https://runtimewire.com/article/scoop-samsung-s-tizen-tv-api-can-find-and-enable-connected-microphones)
- [Cybernews: Samsung TV data collection claims](https://cybernews.com/privacy/samsung-smart-tv-spying-microphones-ai/)
- [Amazon Developer: Voice-enabling apps on Fire TV](https://developer.amazon.com/docs/fire-tv/voice-enable-your-app-and-content.html)
- [Vibe: Meeting Owl alternatives](https://vibe.us/blog/meeting-owl-alternatives/)
- [Meta Portal (Wikipedia)](https://en.wikipedia.org/wiki/Meta_Portal)
- [Higlo: history of Portal TV](https://higlo.co/shared-space/the-history-of-the-meta-portal-tv-the-right-product-from-the-wrong-company)
- [Florida recording laws](https://recordinglaw.com/party-two-party-consent-states/florida-recording-laws/)

* [Recall.ai: speaker labels and names explained](https://www.recall.ai/blog/speaker-labels-and-names-explained)
* [pyannoteAI: speaker identification for recurring meetings](https://www.pyannote.ai/blog/speaker-identification-system-recurring-meetings)
* [ClovaNote: auto speaker identification](https://help.worksmobile.com/en/use-guides/clovanote/view/speaker-identification/)
* [Read AI on the App Store](https://apps.apple.com/app/id6575345796)
* [Microsoft Teams Intelligent Speakers](https://support.microsoft.com/office/use-teams-intelligent-speakers-to-identify-in-room-participants-in-meeting-transcription-a075d6c0-30b3-44b9-b218-556a87fadc00)
* [Spatio-spectral diarization of meetings (arXiv 2506.16228)](https://arxiv.org/abs/2506.16228v1)
