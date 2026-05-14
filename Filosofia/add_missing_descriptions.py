#!/usr/bin/env python3
"""
Crea descriptions.json en carpetas de Filosofía que aún no lo tengan.

Origen del texto: Blog.md si existe; si no, Script.md (limpio, tono lectura);
si no hay .md, usa el título del episodio en episodes.json.

Uso: python3 Filosofia/add_missing_descriptions.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EPISODES_JSON = REPO_ROOT / "podcast-web" / "data" / "episodes.json"


def load_gen():
    spec = importlib.util.spec_from_file_location(
        "generate_blogs_from_scripts",
        REPO_ROOT / "Filosofia" / "generate_blogs_from_scripts.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def excerpt_from_blog(text: str, gen) -> str:
    return gen.extract_excerpt(text)


def excerpt_from_script(path: Path, gen) -> str:
    raw = path.read_text(encoding="utf-8")
    body = gen.strip_podcast_lines(raw)
    body = gen.listen_to_read(body)
    body = gen.blockquote_to_pull(body)
    body = gen.normalize_headings(body)
    return gen.extract_excerpt(body)


def fallback_description(title: str, max_chars: int = 248) -> str:
    t = title.strip().rstrip(".")
    base = f"{t}: ideas y contexto en formato extenso para leer con calma."
    if len(base) > max_chars:
        base = base[: max_chars - 3].rsplit(" ", 1)[0] + "..."
    return base


def main() -> None:
    gen = load_gen()
    data = json.loads(EPISODES_JSON.read_text(encoding="utf-8"))
    updated = 0
    for ep in data.get("filosofia", []):
        folder = gen.resolve_episode_folder(ep["folder"])
        num = ep.get("number")
        title = (ep.get("title") or "").strip()
        if not folder.is_dir():
            print(f"[{num}] skip: sin carpeta {folder}", file=sys.stderr)
            continue
        desc_path = folder / "descriptions.json"
        if desc_path.is_file():
            continue
        blog = folder / "Blog.md"
        try:
            if blog.is_file():
                excerpt = excerpt_from_blog(blog.read_text(encoding="utf-8"), gen)
            else:
                script = gen.find_script(folder)
                excerpt = excerpt_from_script(script, gen)
        except (FileNotFoundError, OSError):
            excerpt = fallback_description(title)

        if not excerpt or excerpt == "Reflexión en clave de texto a partir del guion del programa.":
            excerpt = fallback_description(title)

        gen.write_description(folder, excerpt)
        ep["hasDescriptions"] = True
        updated += 1
        print(f"[{num}] OK -> {folder.name}")

    if updated:
        EPISODES_JSON.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"Listo: {updated} descriptions.json nuevos.")


if __name__ == "__main__":
    main()
