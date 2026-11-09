# DNS blocking for the S95C

There are two ways to do this. The evidence on setting DNS directly on the TV is mixed:

- **On the TV (simplest).** On a 2023 Q70C, Glass Home set
  **Settings > All Settings > Connection > Network > Network Status > IP Settings > DNS Setting >
  Enter manually** to Control D's free "HaGeZi Light" filter (`76.76.2.37`, backup `76.76.10.37`).
  The setting stayed, and YouTube, Netflix, Prime Video, Disney+ and Samsung TV Plus all still
  worked. Use the on-screen keypad; number keys on the remote didn't fill the boxes. The catch: the
  TV accepts only one DNS server, so if that service goes down, the TV has no internet. If that
  happens, set DNS Setting back to **Get automatically** first.
- **On the router or a LAN resolver (sturdier).** A 2023 CU7700 reverted a manual DNS server to
  automatic, so blocking at the router also covers TVs that don't keep the setting. It also lets you
  check the query log. The steps below use this route with `samsung-ads.txt`.

After setting DNS on the TV, check that the setting stuck. Then check that `samsungads.com` no
longer loads in the TV's browser.

## Setup

1. Run AdGuard Home or Pi-hole v6+ on something that's always on (a Raspberry Pi or a NAS).
2. Add `samsung-ads.txt` as a blocklist. Point the resolver at the raw file URL in this repo, or
   paste the rules in as custom filtering rules.
3. Give the TV that resolver. Either make it the DNS server the router's DHCP hands out, or set a
   static lease for the TV with that resolver as its DNS.
4. Reboot the TV (hold Power until it restarts) so it picks up the new DHCP lease.

## Verify instead of assuming

- In the resolver's query log, filter by the TV's IP address. You should see `samsungads.com`,
  `samsungacr.com` and so on marked as blocked.
- The TV's built-in browser shouldn't load `samsungads.com`.
- Netflix, YouTube and the Samsung app store should still work. If something breaks, find the
  blocked domain in the log and remove that one rule. Don't turn the whole list off.

## Growing the list

Leave the TV idle on the home screen for 24 hours with logging on, then sort the TV's queries by
count. Block a candidate domain only if it's clearly analytics, logging or ads, and only after one
full day of normal use shows nothing broke. Firmware updates run on Samsung's own servers, so
never block a domain you can't identify. Leaving security fixes switched off is worse than a few
telemetry pings.

## Limits

- **Smart TVs can bypass your DNS.** If the TV is ever seen using a hardcoded resolver such as
  `8.8.8.8`, block outbound port 53 from the TV's IP at the router.
- **In-app ads aren't affected.** YouTube and Netflix serve ads from the same domains as the video,
  so DNS can't remove them.
