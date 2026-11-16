# Game data update (Covens of Umbra, 3.30)

These scripts add new-league items and stats to `renderer/public/data/*/items.ndjson` and `stats.ndjson`. They work from [RePoE](https://github.com/repoe-fork/repoe-fork.github.io) exports instead of the game files.

## How it works

`update_330.py` compares two RePoE exports, an older one and a newer one. It adds anything new to the app's data in all four languages (en, ru, ko, cmn-Hant):

- new currency, fragments, jewels, Viscera, gems and uniques
- renamed items (the app's existing trade tag is kept)
- new stats, with official trade stat IDs from `stat_translations.json`

`statgen.py` converts RePoE stat translations into the app's stat format. When tested against existing entries, it matched about 97% of matchers exactly.

## Run it

1. From the RePoE repo, export these files from two commits (an older export and a newer one):
   - `base_items.json`, `uniques.json` and `gems.json` from `data/` and from `data/<Language>/` for Korean, Russian and Traditional Chinese
   - `stat_translations.json` from `data/` and from `data/<Language>/` for the same three languages
2. Run:

   ```sh
   python3 tools/update-data/update_330.py <old-export-dir> <new-export-dir> renderer/public/data
   ```

3. Check `git diff`, then build the renderer. The build regenerates the search indexes.

## Limitations

- RePoE doesn't include unique base types. Add them to `UNIQUE_BASES` before running.
- The trade site can't be reached from the build environment, so trade tags for new exchange items are guessed as the lowercase item name with dashes (e.g. `abyss-thread`). Fix any tag whose bulk search fails.
- New items use static `web.poecdn.com/image/...` icons. New uniques have no disenchant value.
