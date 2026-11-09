# Clean up a Samsung S95C TV

A Samsung Tizen counterpart to [cleanyourtv](https://github.com/Gathin23/cleanyourtv), which only
supports Android TV. This **isn't a replacement OS**. The S95C only runs firmware signed by Samsung,
has secure boot and a locked bootloader, and offers no shell on retail firmware. Trying to flash
anything else would brick the TV. What a Tizen TV *does* let you control is covered by three
pieces here:

| Piece | What it does | Where |
|---|---|---|
| Settings pass | Turns off content recognition (ACR), interest-based ads, voice data and the Smart Hub autorun | [`docs/s95c-settings.md`](docs/s95c-settings.md) |
| DNS blocklist | Blocks Samsung's ad and ACR domains at the router | [`dns/`](dns/README.md) |
| `tools/tizen.py` | Remote control from a computer on the LAN: probe, pair, send keys, launch apps, and a guided walk through the settings pass | below |

## The strongest option: use the TV as a screen only

To get a home screen you control and no Samsung tracking at all, **take the TV off the network**
and plug in an Android TV or Google TV box (such as an Nvidia Shield or Google TV Streamer). Then run
the original cleanyourtv on that box. The S95C's panel and picture processing work the same without
a network connection. Everything below is for keeping the TV's own apps.

## Your own home screen: Glass Home

[Glass Home](https://github.com/victaphu/glass-home-samsung-tv) is a minimal home screen for
Tizen TVs. It shows a photo backdrop and a dock of apps and HDMI inputs, and it doesn't track you.
It's been reported working on Samsung TVs from 2018 to 2025, including a 2022 S95B and a 2023
Q70C. That's as close to "my own OS" as a Samsung TV allows without unsupported hacks:

- You install it in Developer Mode with a free Samsung certificate made for your TV's DUID (its
  device ID). Expect about an hour the first time. Turn Developer Mode off afterwards.
- The TV starts in Glass Home if you turn **Start with Smart Hub Home** off and **Autorun Last App**
  on (step 6 of the settings pass). The Home button still opens Smart Hub.
- A major Tizen upgrade (such as One UI Tizen) can delete sideloaded apps, so keep your build and
  certificate files to reinstall it.
- Its photo website runs over plain HTTP on port 8090. Set `photoService: false` if you don't want
  that open on your network.

Projects that change what the Home button opens (CleanFrame, Arn0) do it by rewriting undocumented
settings. Each was tested on a single TV, and a firmware update can break them. Avoid them on a
$2,000 panel unless you accept that risk.

## tools/tizen.py

Needs Python 3.9 or newer and nothing else. The computer has to be on the same network as the TV.
It only connects to private LAN addresses.

```sh
python3 tools/tizen.py probe 192.168.1.50      # read-only: ports + model info, identifiers redacted
python3 tools/tizen.py pair 192.168.1.50       # accept "Allow" on the TV; token saved to ~/.cleantizen/
python3 tools/tizen.py guide 192.168.1.50      # walk the settings pass, steering the TV from the keyboard
python3 tools/tizen.py key 192.168.1.50 HOME
python3 tools/tizen.py app 192.168.1.50 netflix --launch
python3 tools/tizen.py checklist               # print the settings pass
```

**Why `guide` doesn't change settings automatically.** Tizen offers no way to read what's on the
screen, and menu order changes between model year, region and firmware version. In the reference
project's tests, sending a fixed sequence of key presses without watching the screen ended up in the
wrong menu, two rows away from a channel retune. So `guide` shows the step and where to find it,
and you press each key while watching the TV. It never sends OK unless you type it.

## Status: untested on an S95C

Steps marked **[verified]** in the settings pass were confirmed on a 2023 Q70C (Tizen 8) by Glass
Home. Nobody has confirmed any of them on an S95C. Glass Home's `tools/` folder has a similar remote
(`tvremote.py`). It also has `phonecam.py`, which streams an iPhone camera pointed at the TV so a
script can see the screen, the one thing this tool can't do. The WebSocket client has only been tested against a fake TV server, not a real set.
If a step is wrong on your TV, correct `CHECKLIST` in `tools/tizen.py` and regenerate the doc:

```sh
python3 tools/tizen.py checklist > docs/s95c-settings.md   # then re-add the footer note
python3 -m unittest discover -s tests
```

## What this can't do

- **Remove or disable Samsung's built-in apps.** Tizen has no equivalent of Android's
  `pm disable-user`.
- **Replace the Home button.** Glass Home gets close by opening at power-on, but the Home button
  still opens Samsung Home. The reference project's
  [Tizen notes](https://github.com/Gathin23/cleanyourtv/blob/main/docs/devices/samsung-tizen.md)
  cover this.
- **Remove ads inside YouTube, Netflix and similar apps.**
- **Keep settings through firmware updates.** Updates can reset these toggles, so run the settings
  pass again after each update. Leave auto-update on.
