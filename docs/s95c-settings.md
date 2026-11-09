# Samsung S95C privacy pass (2023, Tizen 7)

1. **Record your current values first**
   - Where: Take a photo of each screen below before changing it
   - Do: These photos are your undo. Nothing here has a factory 'restore' for privacy toggles.
2. **Viewing Information Services (ACR) -> Off**
   - Where: Settings > All Settings > General & Privacy > Terms & Privacy
   - Do: Turn off Viewing Information Services. This is the content-recognition that fingerprints what is on screen, including HDMI inputs.
3. **Interest-Based Advertisement -> Off**
   - Where: Settings > All Settings > General & Privacy > Terms & Privacy
   - Do: Turn off Interest-Based Advertisement.
4. **Reset the advertising ID (PSID)**
   - Where: Settings > All Settings > General & Privacy > Terms & Privacy
   - Do: Use Reset PSID if offered, after turning ads off, so the old profile is orphaned.
5. **Voice Recognition Services -> Off (if present)**
   - Where: Settings > All Settings > General & Privacy > Terms & Privacy
   - Do: Turn off. Some regions/firmwares do not show this entry.
6. **Voice Wake-up -> Off (if present)**
   - Where: Settings > All Settings > General & Privacy > Voice
   - Do: Turn off always-listening wake word. Push-to-talk on the remote still works.
7. **Start screen behaviour**
   - Where: Settings > All Settings > General & Privacy > Start Screen Option
   - Do: Optional: 'Start with Smart Hub Home' off and 'Autorun Last App' on boots into your last input/app instead of the ad-carrying home row. Also turn off any 'Autorun Samsung TV Plus' toggle. The Home button will still open Samsung Home.
8. **Leave Software Update on**
   - Where: Settings > Support > Software Update > Auto Update
   - Do: Keep ON. Firmware updates carry security fixes and can reset the toggles above, so re-run this pass after an update instead of freezing firmware.
9. **Remove this tool's pairing when done**
   - Where: Settings > All Settings > Connection > External Device Manager > Device Connection Manager > Device List
   - Do: Delete 'cleantizen' if you do not plan to use the remote again.


> These are where the settings should be on 2023 firmware. Nobody has verified them on an S95C yet. If an entry is missing or has moved, look under **Settings > Support > Terms & Privacy**, then fix the path in `tools/tizen.py` and regenerate this file with `python3 tools/tizen.py checklist`.
