import os
import shutil
import re
import argparse
import time
from datetime import datetime
from collections import defaultdict, Counter

###############################################################################
# Language definitions
###############################################################################
LANGUAGE_PATTERNS = {
    "en": [
        r"\b(USA|U)\b",
        r"\b(En|Eng|English)\b",
        r"\b(Europe)\b.*\b(En|Eng|English)\b",
        r"\b(World)\b",
        r"\b(USA,\s?Europe)\b.*\b(En)\b",
    ],
    "jp": [r"\b(JPN|Japan|J)\b", r"日本語", r"日文"],
    "fr": [r"\b(Fr|FRA|French|Francais|Français)\b"],
    "de": [r"\b(De|Ger|German|Deutsch)\b"],
    "es": [r"\b(ES|Spa|Spanish|Español|Espanol|Castellano)\b"],
    "it": [r"\b(ITA|It|Italian|Italiano)\b"],
    "pt": [r"\b(PT|Portugu[eê]s|Brazil|BR)\b"],
    "ru": [r"\b(RU|Rus|Russian|Русский)\b"],
    "ko": [r"\b(KOR|Korea|Korean)\b", r"한국어", r"한글"],
    "zh": [r"\b(CHN|China|Chinese)\b", r"中文版", r"中文", r"汉化"],
    "multi": [r"\b(Multi\s?[\d]+|M[0-9]+)\b"],
    "eu": [r"\b(EUR|Europe|EU)\b(?!.*\b(En|Eng|English)\b)"],
}

# Broad ROM extension coverage for MiSTer FPGA-era and beyond
ROM_EXTENSIONS = {
    # Atari / early consoles
    ".a26", ".a52", ".a78",
    # Nintendo family (home + handheld)
    ".nes", ".fds", ".sfc", ".smc", ".gb", ".gbc", ".gba",
    ".nds", ".dsi", ".3ds", ".cia",
    ".n64", ".z64", ".v64",
    # Sega family
    ".sms", ".gg", ".sg", ".sgx",
    ".md", ".smd", ".gen", ".32x", ".meg", ".bin", ".rom",
    # PC Engine / TurboGrafx / SuperGrafx
    ".pce",
    # SNK / Neo Geo, etc.
    ".neo", ".ngp", ".ngc", ".ngpc",
    # Optical / disc-based systems
    ".cue", ".iso", ".chd", ".gdi", ".cdi",
    ".mdf", ".mds", ".nrg",
    ".cso", ".pbp",
    # PSP / Vita / modern-ish handhelds
    ".vpk", ".psv", ".psvita",
    # Switch-style formats
    ".nsp", ".xci",
    # Arcade / MAME style / compressed sets
    ".zip", ".7z", ".7zip", ".rar",
    # 8/16-bit computer + tape/disk images
    ".adf", ".d64", ".tap", ".tzx",
}

###############################################################################
# Language detection helpers
###############################################################################

def detect_languages(filename_no_ext):
    """
    Returns a set of language codes detected in the filename (no extension).
    Can return more than one (like 'multi').
    """
    detected = set()
    for lang_code, patterns in LANGUAGE_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, filename_no_ext, flags=re.IGNORECASE):
                detected.add(lang_code)
                break
    return detected


def should_keep(detected_langs, keep_langs):
    """
    SORT decision:
      - If any detected language is in keep_langs -> KEEP
      - If file has no detected languages:
            If 'en' in keep_langs, assume keep
            Otherwise keep (conservative: don't shove unknowns)
    """
    if detected_langs:
        return any(lang in keep_langs for lang in detected_langs)
    if "en" in keep_langs:
        return True
    return True


###############################################################################
# Filesystem helpers
###############################################################################

def collect_roms(root_dir, include_moved=True):
    """
    Yield (abs_path, rel_path_from_root) of every file with a known ROM extension.

    If include_moved=False, skip anything already under "Moved ROMS/".
    """
    moved_root_abs = os.path.abspath(os.path.join(root_dir, "Moved ROMS"))

    for base, dirs, files in os.walk(root_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ROM_EXTENSIONS:
                abs_path = os.path.join(base, f)
                rel_path = os.path.relpath(abs_path, root_dir)

                if not include_moved:
                    # skip stuff already in Moved ROMS/
                    if os.path.commonpath(
                        [os.path.abspath(abs_path), moved_root_abs]
                    ) == moved_root_abs:
                        continue

                yield abs_path, rel_path


def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)


def unique_destination_path(dest_full_path):
    """
    Make sure we don't overwrite existing files.
    Only used in live move mode.
    """
    if not os.path.exists(dest_full_path):
        return dest_full_path
    base_no_ext, ext = os.path.splitext(dest_full_path)
    counter = 1
    candidate = f"{base_no_ext} ({counter}){ext}"
    while os.path.exists(candidate):
        counter += 1
        candidate = f"{base_no_ext} ({counter}){ext}"
    return candidate


def plan_dest_paths_for_sort(root_dir, rel_path):
    """
    For SORT mode:
      "Moved ROMS/<original/subpath/file>"
    Return (logical_rel_dest, physical_abs_dest)
    """
    logical_rel_dest = os.path.join("Moved ROMS", rel_path)
    physical_abs_dest = os.path.join(root_dir, logical_rel_dest)
    return logical_rel_dest, physical_abs_dest


def plan_dest_paths_for_remerge(root_dir, rel_from_moved):
    """
    For REMERGE mode:
      put file back at "<root>/<rel_from_moved>"
    Return (logical_rel_dest, physical_abs_dest)
    """
    logical_rel_dest = rel_from_moved
    physical_abs_dest = os.path.join(root_dir, rel_from_moved)
    return logical_rel_dest, physical_abs_dest


###############################################################################
# Core modes: sort, remerge, langs-report, cleanup
###############################################################################

def do_sort(root_dir, keep_langs, do_move, log_lines):
    """
    SORT MODE:
    - Walk all ROMs except ones already in Moved ROMS/
    - Decide KEEP or MOVE
    - If do_move=True, move non-kept ROMs into "Moved ROMS/<original/subpath>"
    """
    moved_count = 0
    kept_count = 0
    move_entries = []
    keep_entries = []

    for abs_path, rel_path in collect_roms(root_dir, include_moved=False):
        filename = os.path.basename(abs_path)
        name_no_ext, _ = os.path.splitext(filename)

        langs = detect_languages(name_no_ext)
        keep_it = should_keep(langs, keep_langs)

        if keep_it:
            kept_count += 1
            keep_entries.append(
                f"[KEEP] {rel_path}  (detected={sorted(list(langs))})"
            )
        else:
            moved_count += 1
            logical_rel_dest, physical_abs_dest = plan_dest_paths_for_sort(
                root_dir, rel_path
            )

            move_entries.append(
                f"[MOVE] {rel_path}  ->  {logical_rel_dest} "
                f"(detected={sorted(list(langs))})"
            )

            if do_move:
                ensure_parent_dir(physical_abs_dest)
                final_abs_dest = unique_destination_path(physical_abs_dest)
                shutil.move(abs_path, final_abs_dest)

    log_lines.append("---- KEPT FILES ----")
    log_lines.extend(keep_entries)
    log_lines.append("")
    log_lines.append("---- MOVED (or WOULD MOVE) FILES ----")
    log_lines.extend(move_entries)
    log_lines.append("")
    log_lines.append("---- SORT SUMMARY ----")
    log_lines.append(f"Total kept: {kept_count}")
    log_lines.append(f"Total moved (or would move): {moved_count}")


def do_remerge(root_dir, keep_langs, do_move, log_lines):
    """
    REMERGE MODE:
    - Look inside 'Moved ROMS/'
    - Bring files back to original folder path if allowed by keep_langs
    """
    moved_root = os.path.join(root_dir, "Moved ROMS")

    moved_back_count = 0
    skipped_count = 0
    remerge_entries = []
    skip_entries = []

    if not os.path.isdir(moved_root):
        log_lines.append("[INFO] No 'Moved ROMS' folder found, nothing to remerge.")
        log_lines.append("---- REMERGE SUMMARY ----")
        log_lines.append("Total moved back: 0")
        log_lines.append("Total skipped: 0")
        return

    for base, dirs, files in os.walk(moved_root):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in ROM_EXTENSIONS:
                continue

            abs_path = os.path.join(base, f)
            rel_from_moved = os.path.relpath(abs_path, moved_root)

            logical_rel_dest, physical_abs_dest = plan_dest_paths_for_remerge(
                root_dir, rel_from_moved
            )

            name_no_ext, _ = os.path.splitext(f)
            langs = detect_languages(name_no_ext)

            # remerge logic:
            # - if keep_langs is empty set() in remerge mode => ALL languages can come back
            # - else only bring back files that match keep_langs
            # - no detected langs? treat as English if 'en' is being restored
            if len(keep_langs) == 0:
                allow_back = True
            else:
                if langs:
                    allow_back = any(lang in keep_langs for lang in langs)
                else:
                    allow_back = "en" in keep_langs

            if allow_back:
                remerge_entries.append(
                    f"[REMERGE] Moved ROMS/{rel_from_moved} -> {logical_rel_dest} "
                    f"(detected={sorted(list(langs))})"
                )
                if do_move:
                    ensure_parent_dir(physical_abs_dest)
                    final_abs_dest = unique_destination_path(physical_abs_dest)
                    shutil.move(abs_path, final_abs_dest)
                moved_back_count += 1
            else:
                skip_entries.append(
                    f"[SKIP] Moved ROMS/{rel_from_moved} "
                    f"(detected={sorted(list(langs))})"
                )
                skipped_count += 1

    log_lines.append("---- REMERGE MOVED (or WOULD MOVE) ----")
    log_lines.extend(remerge_entries)
    log_lines.append("")
    log_lines.append("---- REMERGE SKIPPED ----")
    log_lines.extend(skip_entries)
    log_lines.append("")
    log_lines.append("---- REMERGE SUMMARY ----")
    log_lines.append(f"Total moved back (or would move): {moved_back_count}")
    log_lines.append(f"Total skipped: {skipped_count}")


def do_langs_report(root_dir, log_lines):
    """
    LANGS MODE:
    - Scan all ROMs except ones already in Moved ROMS/
    - Count per-folder language distribution + global totals
    - A ROM can increment multiple languages
    - ROMs with no detectable language are counted as 'unknown'
    """
    folder_lang_counts = defaultdict(Counter)
    total_counts = Counter()

    for abs_path, rel_path in collect_roms(root_dir, include_moved=False):
        parts = rel_path.split(os.sep)
        folder_bucket = parts[0] if len(parts) > 1 else ""  # top-level folder or root

        filename = os.path.basename(abs_path)
        name_no_ext, _ = os.path.splitext(filename)

        langs = detect_languages(name_no_ext)

        if not langs:
            folder_lang_counts[folder_bucket]["unknown"] += 1
            total_counts["unknown"] += 1
        else:
            for lang in langs:
                folder_lang_counts[folder_bucket][lang] += 1
                total_counts[lang] += 1

    log_lines.append("=== LANGUAGE SUMMARY ===")

    if folder_lang_counts:
        for folder, counter in sorted(folder_lang_counts.items()):
            folder_label = folder if folder else "(root)"
            log_lines.append(f"Folder: {folder_label}")
            for lang_code, count in counter.most_common():
                log_lines.append(f"  {lang_code.upper()}: {count}")
            log_lines.append("")
    else:
        log_lines.append("No ROMs found to analyze.")
        log_lines.append("")

    log_lines.append("TOTALS:")
    if total_counts:
        for lang_code, count in total_counts.most_common():
            log_lines.append(f"  {lang_code.upper()}: {count}")
    else:
        log_lines.append("  (none)")
    log_lines.append("")


def cleanup_empty_dirs(root):
    """
    After remerge, clean up empty folders under 'Moved ROMS/'.
    Only removes directories that are actually empty.
    Returns list of removed directory paths.
    """
    removed = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        if not dirnames and not filenames:
            try:
                os.rmdir(dirpath)
                removed.append(dirpath)
            except Exception:
                pass
    return removed


###############################################################################
# main()
###############################################################################

def main():
    parser = argparse.ArgumentParser(
        description=(
            "ROMuLess: sort, remerge, and analyze multi-system ROM libraries by language.\n\n"
            "Default mode (no flags): SORT REPORT ONLY (dry run), keeping English.\n"
            "  --move        actually moves excluded ROMs into 'Moved ROMS/'.\n"
            "  --remerge     undo: move ROMs back out of 'Moved ROMS/'.\n"
            "  --langs       language stats only (no moves, no sorting).\n"
            "  --cleanup     with --remerge: after moving back, remove any empty subfolders\n"
            "                left inside 'Moved ROMS/'.\n"
        )
    )

    parser.add_argument(
        "--keep",
        nargs="*",
        default=["en"],
        help=(
            "Languages to KEEP (sort mode) or RESTORE (remerge mode).\n"
            "Examples:\n"
            "  --keep en it     keep/restore English + Italian\n"
            "  --keep jp de     keep/restore Japanese + German\n\n"
            "SORT MODE:\n"
            "  Files with these langs stay; everything else can be moved to 'Moved ROMS/'.\n"
            "  Default is ['en'].\n\n"
            "REMERGE MODE:\n"
            "  Only these langs get restored out of 'Moved ROMS/'.\n"
            "  If you pass `--keep` with nothing after it in remerge mode, that means ALL languages.\n\n"
            "IGNORED in --langs mode."
        )
    )

    parser.add_argument(
        "--move",
        action="store_true",
        help="Actually move files / perform changes. Without this, it's all dry-run."
    )

    parser.add_argument(
        "--remerge",
        action="store_true",
        help="Undo sort: move ROMs from 'Moved ROMS' back into original folders. "
             "Combine with --keep to selectively restore only certain languages."
    )

    parser.add_argument(
        "--langs",
        action="store_true",
        help="Report language counts per folder and in total. No moving, no sorting."
    )

    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="(Only relevant with --remerge.) After remerge, delete any empty folders "
             "left in 'Moved ROMS/'. Only empty folders are removed. "
             "If you're running without --move (dry run), this just reports intent."
    )

    parser.add_argument(
        "--log",
        default="rom_sort_log.txt",
        help="Log filename (default: rom_sort_log.txt)"
    )

    args = parser.parse_args()

    root_dir = os.path.dirname(os.path.abspath(__file__))

    # figure out mode
    mode_langs = args.langs
    mode_remerge = (args.remerge and not mode_langs)
    mode_sort = (not mode_langs and not mode_remerge)

    # figure out keep_langs based on mode
    explicit_keep_empty = (args.keep == [])

    if mode_langs:
        # --langs ignores keep_langs behaviorally, but we'll record it in logs anyway
        keep_langs = (
            set()
            if explicit_keep_empty
            else {lang.lower() for lang in args.keep}
        )
    elif mode_remerge:
        # remerge: empty keep list => ALL languages
        if explicit_keep_empty:
            keep_langs = set()
        else:
            keep_langs = {lang.lower() for lang in args.keep}
    else:
        # sort mode: empty keep list is probably accidental, assume English
        if explicit_keep_empty:
            keep_langs = {"en"}
        else:
            keep_langs = {lang.lower() for lang in args.keep}

    t_start = time.time()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_lines = []
    log_lines.append("=== ROMuLess Report ===")
    log_lines.append(f"Run at: {now_str}")
    log_lines.append(f"Root dir: {root_dir}")
    log_lines.append(f"Moved ROMS dir: {os.path.join(root_dir, 'Moved ROMS')}")
    log_lines.append(
        f"Mode: {'LANGS' if mode_langs else ('REMERGE' if mode_remerge else 'SORT')}"
    )

    if mode_langs:
        log_lines.append("Keep languages: (n/a for --langs)")
        log_lines.append("Action: REPORT ONLY (LANGS STATS)")
    else:
        log_lines.append(
            f"Keep languages: {sorted(list(keep_langs)) if keep_langs else 'ALL (remerge mode)'}"
        )
        if mode_remerge:
            action_desc = "REMERGE " + ("(MOVE FILES)" if args.move else "(DRY RUN)")
        else:
            action_desc = "SORT " + ("(MOVE FILES)" if args.move else "(DRY RUN)")
        log_lines.append(f"Action: {action_desc}")
        if args.cleanup and mode_remerge:
            log_lines.append("Cleanup requested: yes")
        else:
            log_lines.append("Cleanup requested: no")
    log_lines.append("")

    # run the mode
    if mode_langs:
        do_langs_report(root_dir, log_lines)

    elif mode_remerge:
        do_remerge(root_dir, keep_langs, args.move, log_lines)

        # cleanup handling under Moved ROMS/
        if args.cleanup:
            moved_root = os.path.join(root_dir, "Moved ROMS")
            if os.path.isdir(moved_root):
                if args.move:
                    removed_dirs = cleanup_empty_dirs(moved_root)
                    log_lines.append("")
                    log_lines.append("---- CLEANUP ----")
                    if removed_dirs:
                        log_lines.append(f"Removed {len(removed_dirs)} empty directories:")
                        for d in removed_dirs:
                            log_lines.append(f"  {d}")
                    else:
                        log_lines.append("No empty directories were removed; none were empty.")
                else:
                    # dry-run cleanup preview
                    log_lines.append("")
                    log_lines.append("---- CLEANUP (DRY RUN) ----")
                    log_lines.append("Would remove any now-empty folders inside 'Moved ROMS/' "
                                     "after remerge completes with --move.")
            else:
                log_lines.append("")
                log_lines.append("[INFO] No 'Moved ROMS' folder found to clean.")

    else:
        do_sort(root_dir, keep_langs, args.move, log_lines)

    elapsed = time.time() - t_start
    log_lines.append("---- RUNTIME ----")
    log_lines.append(f"Time elapsed: {elapsed:.2f} seconds")
    log_lines.append("====================================")

    # write the log
    log_path = os.path.join(root_dir, args.log)
    with open(log_path, "w", encoding="utf-8") as f:
        for line in log_lines:
            f.write(line + "\n")

    # console also
    print("\n".join(log_lines))
    print(f"\nLog written to: {log_path}")


if __name__ == "__main__":
    main()
