#!/usr/bin/env python3
"""
For episodes 024+ in all podcasts: normalize cover assets (PREFIXnnnB|S|Y) to
1920x1080 JPG with letterboxing, matching make-video static-image behavior.

Prefers PNG > WEBP > JPEG as source when multiple files share the same stem.

Usage:
  python normalize_cover_images.py           # dry run
  python normalize_cover_images.py --apply # run ffmpeg, replace/delete sources
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

PODCASTS = {
    "Filosofia": "F",
    "Historia": "H",
    "Libros": "L",
    "Mitologia": "M",
}

IMAGE_SUFFIXES = ".png", ".jpg", ".jpeg", ".webp"

# Source preference when both F024B.png and F024B.jpg exist (lower = better).
SOURCE_RANK = {".png": 0, ".webp": 1, ".jpeg": 2, ".jpg": 3}

MIN_EPISODE = 24
OUT_W, OUT_H = 1920, 1080
VF = (
    f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=decrease,"
    f"pad={OUT_W}:{OUT_H}:(ow-iw)/2:(oh-ih)/2"
)


def episode_num(folder_name: str) -> int:
    m = re.match(r"^(\d+)", folder_name)
    return int(m.group(1)) if m else 0


def collect_groups() -> list[tuple[Path, str, list[Path]]]:
    """Return (episode_dir, canonical_stem like F024B, [source paths])."""
    groups: dict[tuple[Path, str], list[Path]] = {}

    for podcast_folder, prefix in PODCASTS.items():
        root = REPO_ROOT / podcast_folder
        if not root.is_dir():
            continue

        for ep in sorted(root.iterdir()):
            if not ep.is_dir() or ep.name.startswith(("000", "_", ".")):
                continue
            if episode_num(ep.name) < MIN_EPISODE:
                continue

            n = episode_num(ep.name)
            ns = f"{n:03d}"
            rx = re.compile(
                rf"^({re.escape(prefix)}{ns}[BSY])(?P<ext>\.[a-z0-9]+)$", re.I
            )

            for f in ep.iterdir():
                if not f.is_file():
                    continue
                m = rx.match(f.name)
                if not m:
                    continue
                if f.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                canonical = m.group(1).upper()
                key = (ep, canonical)
                groups.setdefault(key, []).append(f)

    return [
        (ep_dir, canon, sorted(files))
        for (ep_dir, canon), files in sorted(groups.items())
    ]


def pick_sources(files: list[Path]) -> tuple[Path, list[Path]]:
    ordered = sorted(files, key=lambda p: (SOURCE_RANK.get(p.suffix.lower(), 99), p.name))
    return ordered[0], ordered[1:]


def ffprobe_size(path: Path) -> str | None:
    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0:s=x",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return r.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def run_ffmpeg(src: Path, dst: Path) -> None:
    # Must end in .jpg so ffmpeg picks the right muxer (not .jpg.tmp).
    tmp = dst.parent / f"{dst.stem}.tmp_normalize.jpg"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(src),
        "-vf",
        VF,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(tmp),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        if tmp.exists():
            tmp.unlink()
        raise
    tmp.replace(dst)


def main() -> None:
    apply = "--apply" in sys.argv
    groups = collect_groups()

    print(f"\n{'=' * 60}")
    print(f"  NORMALIZE COVERS (ep >= {MIN_EPISODE}) → {OUT_W}x{OUT_H} JPG")
    print(f"  {'APPLY' if apply else 'DRY RUN'}")
    print(f"{'=' * 60}\n")

    n_convert = 0
    for ep_dir, canonical, files in groups:
        main_src, extras = pick_sources(files)
        dst = ep_dir / f"{canonical}.jpg"
        dim = ffprobe_size(main_src)
        extra_note = f" (+{len(extras)} alt)" if extras else ""
        print(f"{main_src.relative_to(REPO_ROOT)}  [{dim or '?'}]{extra_note}")
        print(f"  → {dst.relative_to(REPO_ROOT)}")

        if extras:
            for e in extras:
                print(f"  (alt source: {e.name})")

        if apply:
            tmp_dst = dst
            try:
                run_ffmpeg(main_src, tmp_dst)
            except subprocess.CalledProcessError as exc:
                err = exc.stderr.decode() if exc.stderr else str(exc)
                print(f"  ERROR: ffmpeg failed:\n{err[:2000]}")
                continue
            for p in [main_src, *extras]:
                if p.resolve() == dst.resolve():
                    continue
                try:
                    p.unlink()
                except OSError as e:
                    print(f"  WARN: could not remove {p.name}: {e}")
            n_convert += 1
            print("  OK")

    print()
    if apply:
        print(f"Converted {n_convert} cover(s).")
    else:
        print("Dry run only. Pass --apply to write JPGs and remove PNG/WebP/extra JPEGs.")


if __name__ == "__main__":
    main()
