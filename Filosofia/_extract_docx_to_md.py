#!/usr/bin/env python3
"""Extrae Script.md y Blog.md desde .docx en Filosofia (fuentes con Tab 1 / Blog o Tab 2)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from docx import Document
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent

SKIP_PATH_MARKERS = ("/.claude/", "/_Resources/", "/000 Recursos comunes/")


def should_skip(path: Path) -> bool:
    s = path.as_posix()
    return any(m in s for m in SKIP_PATH_MARKERS)


def is_script_tab_title(text: str) -> bool:
    t = (text or "").strip()
    return t in ("Tab 1", "Guion Podcast")


def is_blog_split_title(style_name: str, text: str) -> bool:
    if style_name != "Title":
        return False
    raw = (text or "").strip().lower()
    return raw in ("blog", "tab 2") or raw.startswith("blog ")


def paragraph_to_md(p: Paragraph) -> str | None:
    text = (p.text or "").strip()
    if not text:
        return None
    name = p.style.name if p.style else "normal"
    if name == "Heading 1":
        return f"# {text}\n"
    if name == "Heading 2":
        return f"## {text}\n"
    if name == "Heading 3":
        return f"### {text}\n"
    return f"{text}\n"


def paragraphs_to_md(paras: list[Paragraph]) -> str:
    chunks: list[str] = []
    for p in paras:
        line = paragraph_to_md(p)
        if line:
            chunks.append(line)
    return "\n".join(chunks).rstrip() + "\n"


def split_docx(doc_path: Path) -> tuple[str, str | None]:
    doc = Document(doc_path)
    paras = list(doc.paragraphs)
    if not paras:
        return "", None

    start = 0
    if paras[0].style and paras[0].style.name == "Title" and is_script_tab_title(
        paras[0].text or ""
    ):
        start = 1

    split_i: int | None = None
    for i in range(start + 1, len(paras)):
        p = paras[i]
        sn = p.style.name if p.style else ""
        if is_blog_split_title(sn, p.text or ""):
            split_i = i
            break

    if split_i is None:
        script_paras = paras[start:]
        return paragraphs_to_md(script_paras), None

    script_paras = paras[start:split_i]
    # Tras el título Blog/Tab 2 suele repetirse el H1 del episodio: incluirlo en blog
    blog_paras = paras[split_i + 1 :]
    return paragraphs_to_md(script_paras), paragraphs_to_md(blog_paras)


LEGACY_MD_NAMES = re.compile(
    r"^(\d{3})[-–].*\.md$|^\d{3}-Script\.md$|^00\d.*\.md$"
)


def legacy_md_to_remove(ep_dir: Path, kept_names: set[str]) -> list[Path]:
    out: list[Path] = []
    for p in ep_dir.iterdir():
        if not p.is_file() or p.suffix.lower() != ".md":
            continue
        if p.name in kept_names:
            continue
        if p.name == "Blog.md":
            continue
        if LEGACY_MD_NAMES.match(p.name) or p.name.endswith("-Script.md"):
            out.append(p)
    return out


def main() -> None:
    docx_files = sorted(
        p
        for p in ROOT.rglob("*.docx")
        if p.is_file() and not should_skip(p)
    )
    if not docx_files:
        print("No se encontraron .docx (colocalos en la carpeta del episodio y volvé a ejecutar).")
        return

    for docx_path in docx_files:
        ep_dir = docx_path.parent
        rel = docx_path.relative_to(ROOT)
        print(f"· {rel}")

        script_md, blog_md = split_docx(docx_path)
        (ep_dir / "Script.md").write_text(script_md, encoding="utf-8")
        if blog_md and blog_md.strip():
            (ep_dir / "Blog.md").write_text(blog_md, encoding="utf-8")
        else:
            blog_file = ep_dir / "Blog.md"
            if blog_file.exists():
                blog_file.unlink()

        fuente = ep_dir / "Fuente.docx"
        if docx_path.name != "Fuente.docx":
            if fuente.exists() and fuente.resolve() != docx_path.resolve():
                print(
                    f"  advertencia: ya existe {fuente.name}, no renombro {docx_path.name!r}"
                )
            else:
                if fuente.exists() and fuente.samefile(docx_path):
                    pass
                else:
                    if fuente.exists():
                        fuente.unlink()
                    shutil.move(str(docx_path), str(fuente))
                    print(f"  → renombrado a Fuente.docx")

        kept = {"Script.md"}
        if (ep_dir / "Blog.md").exists():
            kept.add("Blog.md")
        for old in legacy_md_to_remove(ep_dir, kept):
            print(f"  elimina obsoleto: {old.name}")
            old.unlink()

    print(f"Listo: {len(docx_files)} episodios procesados desde .docx.")


if __name__ == "__main__":
    main()
