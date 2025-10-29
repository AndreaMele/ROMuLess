# ROMuLess Changelog

All notable changes to ROMuLess are documented here.

---

## [0.4.0] - Cleanup + Language Stats
### Added
- `--cleanup` flag:
  - When used with `--remerge`, automatically removes any **empty** directories left under `Moved ROMS/`.
  - Safe: only deletes empty folders.
  - In dry run (no `--move`), it just logs what would have been deleted.

- `--langs` mode:
  - Scans your ROM collection (excluding `Moved ROMS/`).
  - Counts how many ROMs match each language per top-level folder (NES, SNES, PSX, etc.).
  - Also prints global totals.
  - Writes the report to console and `rom_sort_log.txt`.
  - Read-only; does not move or delete anything.

### Changed
- README updated with `--cleanup` and `--langs`.
- Runtime, mode, and intent are now logged consistently.

---

## [0.3.0] - Remerge Mode / Undo Support
### Added
- `--remerge` mode:
  - Restores ROMs from `Moved ROMS/` back to their original locations.
  - Respects `--keep` to only restore chosen languages.

### Behavior
- `--remerge --keep en it --move`: restore only English + Italian.
- `--remerge --keep --move`: restore ALL languages (empty `--keep` in remerge mode means “all allowed back”).

### Safety
- Without `--move`, `--remerge` is a dry run. No file operations occur.

---

## [0.2.0] - Keep Rules, Safe Moves, Structure Preservation
### Added
- `--keep` flag in sort mode:
  - Only ROMs in those languages stay in place.
  - Everything else is considered “moveable.”

- Quarantine folder renamed to **`Moved ROMS/`**.
  - Non-kept ROMs go there.
  - Original subfolder layout is preserved (`NES/...`, `SNES/...`, etc.).

- Logging:
  - `rom_sort_log.txt` records KEEP vs MOVE decisions, detected language(s), total counts, and runtime.

### Behavior changes
- Dry run is the default:
  - The script will NOT create folders or move any files unless `--move` is provided.
- Collision-safe moves:
  - If a destination filename already exists, ROMuLess appends `(<number>)` instead of overwriting.

---

## [0.1.0] - Initial Version
### Added
- Core sorting logic using filename region/language tags:
  - `(USA)`, `(JPN)`, `(ITA)`, `(Spanish)`, `Multi5`, etc.
- Recursive scan of all subdirectories under the script location.
- Timing and summary output.
- Basic English-only filtering.
- Early quarantine folder was called `Non English/`.
- Project later renamed to **ROMuLess**.
