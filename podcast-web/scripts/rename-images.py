#!/usr/bin/env python3
"""
Scan all episode folders and rename images to the standard convention:
  {PREFIX}{NNN}B.ext  - Blog cover
  {PREFIX}{NNN}S.ext  - Spotify/Podcast cover
  {PREFIX}{NNN}Y.ext  - YouTube cover

Usage:
  python rename-images.py          # dry run (shows what would be renamed)
  python rename-images.py --apply  # actually rename files
"""

from __future__ import annotations
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

PODCASTS = {
    "Filosofia": "F",
    "Historia": "H",
    "Libros": "L",
    "Mitologia": "M",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

def get_episode_number(folder_name: str) -> str | None:
    match = re.match(r"^(\d+)", folder_name)
    if match:
        return match.group(1).zfill(3)
    return None

def classify_image(filename: str, prefix: str, num: str) -> str | None:
    """Return 'B', 'S', or 'Y' based on filename patterns, or None if unclassifiable."""
    name_lower = filename.lower()
    stem = Path(filename).stem.lower()

    # Skip thumbnails, window images, hash-named files, and template resources
    if "thumbnail" in name_lower:
        return None
    if "windowimage" in name_lower:
        return None
    if re.match(r"^[a-f0-9]{40,}", stem):
        return None
    if "cover base" in name_lower:
        return None

    # Skip files that have "2" suffix (old versions like F003S2, F004_YT2, F005_YT2)
    pnum = f"{prefix}{num}".lower()
    if re.match(rf"^{re.escape(pnum)}[bsy]2", stem):
        return None
    # Also skip F203S (typo file)
    if stem.startswith(f"{prefix.lower()}203"):
        return None

    # Already correctly named - skip
    if re.match(rf"^{re.escape(pnum)}b$", stem):
        return "ALREADY_B"
    if re.match(rf"^{re.escape(pnum)}s$", stem):
        return "ALREADY_S"
    if re.match(rf"^{re.escape(pnum)}y$", stem):
        return "ALREADY_Y"

    # Blog patterns
    blog_patterns = [
        r"cover\s*blog",
        r"coverblog",
        rf"{re.escape(pnum)}-?cover\s*blog",
        rf"{re.escape(prefix.lower())}\d{{3}}-?coverblog",
    ]
    for pat in blog_patterns:
        if re.search(pat, name_lower):
            return "B"

    # Spotify/Podcast patterns
    spotify_patterns = [
        r"cover\s*spotify",
        r"coverspotify",
        r"cover\s*podcast",
        r"spotify\s*cover",
        rf"{re.escape(pnum)}-?spotify",
        rf"{re.escape(pnum)}-?s\b",
        rf"{re.escape(pnum)}_?s\b",
        rf"{re.escape(pnum)}-?cover\s*spotify",
        rf"{re.escape(prefix.lower())}\d{{3}}-?coverspotify",
        r"cover\s*spori?ty",  # typos
        r"cover\s*spoity",
    ]
    for pat in spotify_patterns:
        if re.search(pat, name_lower):
            return "S"

    # YouTube patterns
    yt_patterns = [
        r"cover\s*y\s*t",
        r"cover\s*youtube",
        r"coveryt",
        rf"{re.escape(pnum)}[-_]?\s*yt",
        rf"{re.escape(pnum)}-?cover\s*yt",
        rf"{re.escape(prefix.lower())}\d{{3}}-?coveryt",
        rf"{re.escape(pnum)}[-_]?yt",
    ]
    for pat in yt_patterns:
        if re.search(pat, name_lower):
            return "Y"

    # Libros: "Cover.jpg" or "Cover.png" (without qualifier) in early episodes = Spotify
    if re.match(r"^cover(\s|$)", stem) and not any(
        x in name_lower for x in ["blog", "spotify", "podcast", "yt", "youtube"]
    ):
        # "Cover" alone (in Libros) is typically Spotify
        if prefix == "L":
            return "S"

    # {PREFIX}{NNN}-Spotify patterns (F010-Spotify, etc.)
    if re.search(rf"{re.escape(prefix.lower())}\d{{3}}-?spotify", name_lower):
        return "S"

    return None


def scan_and_plan():
    renames = []
    skipped = []
    already_correct = []

    for podcast_folder, prefix in PODCASTS.items():
        podcast_path = REPO_ROOT / podcast_folder
        if not podcast_path.exists():
            continue

        for entry in sorted(podcast_path.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith("000") or entry.name.startswith("_") or entry.name.startswith("."):
                continue

            num = get_episode_number(entry.name)
            if not num:
                continue

            # Track what target names already exist or are planned
            planned_targets = {}

            for img_file in sorted(entry.iterdir()):
                if not img_file.is_file():
                    continue
                if img_file.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue

                classification = classify_image(img_file.name, prefix, num)

                if classification is None:
                    skipped.append(str(img_file.relative_to(REPO_ROOT)))
                    continue

                if classification.startswith("ALREADY_"):
                    already_correct.append(str(img_file.relative_to(REPO_ROOT)))
                    continue

                target_name = f"{prefix}{num}{classification}{img_file.suffix.lower()}"
                target_path = entry / target_name

                # Check for conflicts
                if classification in planned_targets:
                    skipped.append(
                        f"{img_file.relative_to(REPO_ROOT)} (CONFLICT: {classification} already mapped)"
                    )
                    continue

                if target_path.exists() and target_path != img_file:
                    skipped.append(
                        f"{img_file.relative_to(REPO_ROOT)} (TARGET EXISTS: {target_name})"
                    )
                    continue

                planned_targets[classification] = True
                renames.append((img_file, target_path))

    return renames, skipped, already_correct


def main():
    apply = "--apply" in sys.argv

    renames, skipped, already_correct = scan_and_plan()

    print(f"\n{'=' * 60}")
    print(f"  IMAGE RENAME {'(DRY RUN)' if not apply else '(APPLYING)'}")
    print(f"{'=' * 60}\n")

    print(f"Already correct: {len(already_correct)} files")
    print(f"To rename: {len(renames)} files")
    print(f"Skipped (unclassifiable/conflicts): {len(skipped)} files\n")

    if renames:
        print("-" * 60)
        print("RENAMES:")
        print("-" * 60)
        for src, dst in renames:
            src_rel = src.relative_to(REPO_ROOT)
            dst_name = dst.name
            print(f"  {src_rel}")
            print(f"    -> {dst_name}")
            print()

    if skipped:
        print("-" * 60)
        print("SKIPPED:")
        print("-" * 60)
        for s in skipped:
            print(f"  {s}")
        print()

    if apply:
        print("-" * 60)
        print("APPLYING RENAMES...")
        print("-" * 60)
        for src, dst in renames:
            os.rename(src, dst)
            print(f"  RENAMED: {src.name} -> {dst.name}")
        print(f"\nDone! {len(renames)} files renamed.")
    else:
        print("-" * 60)
        print("This was a DRY RUN. Run with --apply to actually rename files.")
        print("-" * 60)


if __name__ == "__main__":
    main()
