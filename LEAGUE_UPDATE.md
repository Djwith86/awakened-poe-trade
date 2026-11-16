# New-league update guide

This is the checklist for updating this fork when a new Path of Exile league launches. It was first done for **3.30 Covens of Umbra** in November 2026.

## What this fork is

- An unofficial fork of [SnosMe/awakened-poe-trade](https://github.com/SnosMe/awakened-poe-trade), with league data added before the official app updates.
- Windows only. Releases are built and published automatically by GitHub Actions (`.github/workflows/release.yml`).
- The app updates itself from **this repo's** releases, not the official repo's (`main/electron-builder.yml` → `publish`).

## 1. Update the game data

The scripts in `tools/update-data/` generate item and stat data from [RePoE](https://github.com/repoe-fork/repoe-fork.github.io) exports. See its README for details.

1. Wait for RePoE to publish an export for the new patch. Its commit messages look like `Export 3.31.0.x`.
2. Export `base_items.json`, `uniques.json`, `gems.json` and `stat_translations.json` from the last old-league commit and the new commit. Each export needs `data/` plus `data/Korean`, `data/Russian` and `data/Traditional Chinese`.
3. Update `UNIQUE_BASES` in `update_330.py`. RePoE doesn't include unique base types, so look them up in league patch notes and item listings.
4. Run:

   ```sh
   python3 tools/update-data/update_330.py <old-export> <new-export> renderer/public/data
   ```

5. Review the printed report: renamed items, new items, gems, uniques and stats.

## 2. Check what the scripts can't know

- **Trade tags for new currency** are guessed as the lowercase item name with dashes (`abyss-thread`). Renamed items keep their old tag. If bulk search fails for an item, its tag is wrong.
- **New item types that copy differently from the game.** Paste the item's Ctrl+Alt+C text and test it. In 3.30, Wickerman Viscera had no `Rarity:` line and had Lesser/Greater tier prefixes, which needed parser changes (`findVisceraByTieredName` in `Parser.ts`). They're searched with the trade site's free-text `term`, because the trade site doesn't list tiered names as base types.
- **poe.ninja categories** for new item types (`renderer/src/web/background/Prices.ts`).
- **Map text changes**, such as `MAP_MORE_SCARABS` in `client_strings.js`.

## 3. Version number (important)

pathofexile.com's Cloudflare **blocked builds versioned `3.30.x`**, while the official `3.29.108` and our `3.29.x` builds were allowed. GGG seems to treat unknown versions as suspicious.

- Keep the version in the same major.minor as the latest official release, with a patch number upstream won't use (we used `3.29.2xx`).
- Every release must have a **higher** version than the last one, or the auto-updater ignores it.
- Don't use pre-release suffixes like `-covens.1`. They make the updater look for a different update file.

If the app shows "Sorry, you have been blocked", check pathofexile.com/trade in a normal browser. If the site works there, the version number is the likely cause.

## 4. Release

1. Bump `version` in `main/package.json`.
2. Update the installer link in `README.md`: `.../releases/download/v<version>/Awakened.PoE.Trade.Setup.<version>.exe`
3. Commit and push to `master`.

GitHub Actions builds the installer and publishes release `v<version>` with the installer, the `.blockmap` and `latest.yml`. Installed apps update on their next check and install the update when you quit.

- The installer is named `Awakened.PoE.Trade.Setup.<version>.exe` (with dots) so it matches what `latest.yml` points to.
- If a run fails, open it under **Actions** to see the log. If a release was created by hand or left partly uploaded, re-running the workflow fills in the missing files.

## 5. Pull in official updates

When SnosMe releases a new version, merge `SnosMe/awakened-poe-trade` `master` into this fork. Expect conflicts in `renderer/public/data/*`; the official data is usually the better choice once it covers the league. Keep this fork's changes to `main/electron-builder.yml`, `release.yml`, the About links and the README download section.
