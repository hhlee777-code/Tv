# Samsung S95C privacy pass (2023 models)

1. **Record your current values first**
   - Where: Take a photo of each screen below before changing it
   - Do: These photos are your undo; most toggles can be flipped back, PSID reset cannot.
2. **Viewing Information Services (ACR) and Interest-Based Ads -> Off  [verified]**
   - Where: Settings > Privacy Choices (left menu) > Terms & Conditions, Privacy Policy
   - Do: Untick Viewing Information Services and Interest-Based Advertisements, then move down to OK. Leave 'I agree to all' unticked. VIS fingerprints what is on screen, HDMI inputs included.
3. **Reset the advertising ID (PSID)  [verified]**
   - Where: Settings > All Settings > General & Privacy > Terms & Privacy > Reset PSID
   - Do: Reset, after turning ads off, so the old profile is orphaned. Cannot be undone; nothing depends on it.
4. **Samsung promotional pop-ups -> Off  [verified]**
   - Where: Settings > Notification (just above All Settings) > gear icon
   - Do: Untick Samsung Promotion, then OK.
5. **Voice data -> Off (if present)  [unverified]**
   - Where: Settings > All Settings > General & Privacy > Terms & Privacy / Voice
   - Do: Turn off Voice Recognition Services and Voice Wake-up if listed. Some firmwares show neither.
6. **Don't open Smart Hub at power-on  [verified]**
   - Where: Settings > All Settings > General & Privacy > Start Screen Options (on Tizen 9 / One UI: Advanced Features > Start Screen Options)
   - Do: 'Start with Smart Hub Home' off. With a home-screen app like Glass Home, also turn 'Autorun Last App' on. The Home button still opens Samsung Home.
   - **Careful:** Factory data reset is the item just below Start Screen Options. Do not press OK there.
7. **Mute Home-screen previews  [verified]**
   - Where: Home > For You tab > scroll to the very bottom > Media Options > Autoplay Sound
   - Do: Press OK to switch autoplay sound off.
8. **Leave Software Update on  [unverified path]**
   - Where: Settings > Support > Software Update > Auto Update
   - Do: Keep ON. Updates carry security fixes and can reset the toggles above, so re-run this pass after one instead of freezing firmware.
   - **Careful:** Avoid Support > Device Care > Reset Smart Hub: it signs you out and removes downloaded apps.
9. **Remove this tool's pairing when done  [unverified path]**
   - Where: Settings > All Settings > Connection > External Device Manager > Device Connection Manager > Device List
   - Do: Delete 'cleantizen' if you do not plan to use the remote again.


> Steps marked [verified] were confirmed on a 2023 Q70C running Tizen 8 by [Glass Home](https://github.com/victaphu/glass-home-samsung-tv/blob/main/docs/SAMSUNG-SETTINGS.md). That is the same model year as the S95C but a different model. Steps marked [unverified] are where the setting should be. If an entry has moved on your TV, fix `CHECKLIST` in `tools/tizen.py` and regenerate this file with `python3 tools/tizen.py checklist`.
