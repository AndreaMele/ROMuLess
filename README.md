# 🕹️ ROMuLess  
> ⚠️ **Important Note:** ROMuLess is designed for **single-file ROMs** only.  
> It is **not compatible with folder-based ROM structures**, such as PlayStation Vita, Wii, or other formats  
> where each game is stored as a directory containing multiple files.

**“Sort smarter, not harder.”**

ROMuLess is a Python utility that helps you **organize**, **remerge**, and **analyze** massive ROM collections by language — ideal for MiSTerFPGA sets, multi-region fullsets, handheld dumps, and optical disc libraries.

It looks at filenames (like `(USA)`, `(JPN)`, `(ITA)`, `(Multi5)`) and can:
- quarantine ROMs that aren't in your chosen languages,
- undo that quarantine,
- report language distribution per system folder,
- log everything it does.

No scraping external DBs, no hashing — just filenames.

---

## 🚀 Features

- **Automatic Language Detection**  
  Detects tags like `(USA)`, `(Europe)`, `(ITA)`, `(GER)`, `(JPN)`, `(Spanish)`, `(Multi5)`, `(World)`.

- **Smart Sorting (Quarantine)**  
  Moves ROMs that don’t match your allowed languages into `Moved ROMS/`, preserving folder/subfolder structure.

- **Safe by Default**  
  Without `--move`, ROMuLess does a dry run. It will NOT touch files or even create folders.

- **Full Undo ("Remerge")**  
  Use `--remerge` to put ROMs back from `Moved ROMS/` to where they originally lived.

- **Selective Restore by Language**  
  You can choose exactly which languages to bring back.

- **Language Census (`--langs`)**  
  Get per-folder and total counts for each detected language. Great for auditing collections.

- **Cleanup (`--cleanup`)**  
  After you remerge, automatically remove any now-empty leftover folders in `Moved ROMS/`.

- **Detailed Logging**  
  Every run writes `rom_sort_log.txt` with actions, stats, and runtime.

---

## 🧩 How It Works

> Run ROMuLess from the root of your ROM collection.  
> (Put `ROMuLess.py` in the same folder as your system subfolders like `NES`, `SNES`, `PSX`, etc.)

### 1. Sort / Quarantine

Dry run:
```bash
python ROMuLess.py --keep en it
```
- Keeps English + Italian in place.
- Shows which ROMs would be moved.
- No changes are made.

Actually move excluded languages into `Moved ROMS/`:
```bash
python ROMuLess.py --keep en it --move
```

Result:
- Things tagged as English (`en`) or Italian (`it`) stay.
- Everything else moves under:
  `Moved ROMS/<original/sub/folder/...>`.

---

### 2. Remerge (Undo)

Restore files from `Moved ROMS/` back into their original folders.

Restore **everything**:
```bash
python ROMuLess.py --remerge --keep --move
```

- `--remerge` = undo sorting  
- `--keep` with nothing after it = all languages are allowed to come back  
- `--move` = do it for real

Preview first (no changes yet):
```bash
python ROMuLess.py --remerge --keep
```

Restore only specific languages (German + Japanese only):
```bash
python ROMuLess.py --remerge --keep de jp --move
```

---

### 3. Cleanup after Remerge

After remerge, `Moved ROMS/` might still have empty folders. Clean them up:

```bash
python ROMuLess.py --remerge --keep --move --cleanup
```

`--cleanup`:
- Only deletes empty folders.
- Only touches folders inside `Moved ROMS/`.
- If you run without `--move`, it will just *say* what it would have cleaned after a real run.

---

### 4. Language Stats Mode

Just want to know what languages you have?

```bash
python ROMuLess.py --langs
```

Example output:

```text
=== LANGUAGE SUMMARY ===
Folder: NES
  EN: 52
  JP: 7
  DE: 4
  UNKNOWN: 3

Folder: PSX
  EN: 120
  FR: 6
  DE: 1

TOTALS:
  EN: 172
  JP: 7
  FR: 6
  DE: 5
  UNKNOWN: 3

Time elapsed: 1.73 seconds
```

This does not move or rename anything.

---

## ⚙️ Command Reference

| Flag            | Description |
|-----------------|-------------|
| `--keep [langs]` | Which languages you allow. In sort mode: only these stay, everything else gets moved. In remerge mode: only these get restored. If you pass `--keep` with nothing after it *in remerge mode*, that means “ALL languages may come back.” Default is `en` (English). |
| `--move`        | Actually move files / perform changes. Without this, ROMuLess only reports (dry run). |
| `--remerge`     | Undo sorting by moving ROMs back out of `Moved ROMS/`. Combine with `--keep` to restore only certain languages. |
| `--cleanup`     | After remerge, delete any empty folders in `Moved ROMS/`. Safe. No effect in sort mode or `--langs` mode. |
| `--langs`       | Show per-folder and global language counts. Read-only. Ignores `--move`. |
| `--log <file>`  | Override log filename (default: `rom_sort_log.txt`). |

---

## 🌍 Language Codes

Use these with `--keep`:

| Code     | Language                       | Example filename tags detected |
|----------|--------------------------------|--------------------------------|
| `en`     | English                        | `(USA)`, `(U)`, `(En)`, `(English)`, `(World)` |
| `jp`     | Japanese                       | `(JPN)`, `(Japan)`, `日本語` |
| `fr`     | French                         | `(FRA)`, `(French)`, `(Français)` |
| `de`     | German                         | `(GER)`, `(German)`, `(Deutsch)` |
| `it`     | Italian                        | `(ITA)`, `(Italiano)` |
| `es`     | Spanish / Castilian            | `(ESP)`, `(Spanish)`, `(Castellano)` |
| `pt`     | Portuguese / Brazil            | `(PT)`, `(BR)`, `(Português)` |
| `ru`     | Russian                        | `(RUS)`, `(Русский)` |
| `ko`     | Korean                         | `(KOR)`, `(Korean)`, `한국어` |
| `zh`     | Chinese                        | `(CHN)`, `(中文)`, `(中文版)` |
| `multi`  | Multi-language dump            | `Multi3`, `Multi5` |
| `eu`     | Generic Europe tag (no explicit English) | `(EUR)`, `(Europe)` |
| `unknown`| No recognizable language tag   | Untagged filename |

A single ROM can match multiple languages (for example, “(Multi5)” dumps).

---

## 🗂 Supported ROM File Types

ROMuLess recognizes a ROM / game image by extension.

### Cartridge / tape / disk style
- `.a26`, `.a52`, `.a78` (Atari)
- `.nes`, `.fds` (NES / Famicom Disk System)
- `.sfc`, `.smc` (SNES / Super Famicom)
- `.gb`, `.gbc`, `.gba` (Game Boy / Color / Advance)
- `.nds`, `.dsi` (Nintendo DS / DSi)
- `.3ds`, `.cia` (Nintendo 3DS content)
- `.n64`, `.z64`, `.v64` (Nintendo 64)
- `.sms`, `.gg`, `.sg`, `.sgx` (Master System / Game Gear / SG-1000 / SuperGrafx)
- `.md`, `.smd`, `.gen`, `.32x`, `.meg`, `.bin`, `.rom` (Genesis / Mega Drive / 32X / etc.)
- `.pce` (PC Engine / TurboGrafx-16)
- `.neo`, `.ngp`, `.ngc`, `.ngpc` (Neo Geo / Neo Geo Pocket/Color)
- `.adf`, `.d64`, `.tap`, `.tzx` (Amiga / C64 / Spectrum-style images)

### Optical / disc-based formats
- `.cue`, `.iso`, `.chd`, `.gdi`, `.cdi`, `.mdf`, `.mds`, `.nrg`, `.cso`, `.pbp`  
  (PS1, Saturn, Sega CD, Dreamcast, PS2, PSP, etc.)

### Handheld / later formats
- `.vpk`, `.psv`, `.psvita` (Vita-style dumps/homebrew)
- `.nsp`, `.xci` (Switch-style)

### Arcade / compressed sets
- `.zip`, `.7z`, `.7zip`, `.rar` (MAME / arcade, per-ROM archives)

You can edit `ROM_EXTENSIONS` in the script to match how you store ROMs.

---

## 🧠 Requirements

- Python 3.8+
- No external dependencies (just standard library).

---

## 📜 License

MIT License  
© 2025 Andrea Mele
