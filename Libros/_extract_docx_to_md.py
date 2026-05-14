#!/usr/bin/env python3
"""Extrae Script.md y Blog.md desde .docx en Libros (Tab 1 / Blog o Tab 2).

También importa .docx desde la carpeta Fuentes/ (o fuentes/), emparejando por prefijo NNN
con la carpeta del episodio correspondiente.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from docx import Document
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent

SKIP_TOP_LEVEL = frozenset(
    {"000 Recursos comunes", "Fuentes", "fuentes", "_Resources", ".claude"}
)


def should_skip_path(path: Path) -> bool:
    s = path.as_posix().lower()
    markers = (
        "/.claude/",
        "/_resources/",
        "/000 recursos comunes/",
        "/fuentes/",
    )
    return any(m in s for m in markers)


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
    blog_paras = paras[split_i + 1 :]
    return paragraphs_to_md(script_paras), paragraphs_to_md(blog_paras)


LEGACY_MD_NAMES = re.compile(
    r"^(\d{3})[-–].*\.md$"
    r"|^\d{3}-Script\.md$"
    r"|^00\d.*\.md$"
    r"|^[Ll]\d{3}[-–].*\.md$"
    r"|^[Ll]\d{3}[a-z0-9_-]*\.md$"
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


NUM_PREFIX = re.compile(r"^(\d{3})\s*")


def find_episode_dir(num: str) -> Path | None:
    num3 = f"{int(num):03d}"
    matches: list[Path] = []
    for d in ROOT.iterdir():
        if not d.is_dir() or d.name in SKIP_TOP_LEVEL:
            continue
        name = d.name
        if (
            name.startswith(num3 + " ")
            or name.startswith(num3 + "-")
            or name.startswith(num3 + "–")
        ):
            matches.append(d)
    if not matches:
        return None
    matches.sort(key=lambda p: p.name)
    if len(matches) > 1:
        print(f"  aviso: varias carpetas para {num3}, uso: {matches[0].name}")
    return matches[0]


def fuentes_folder() -> Path | None:
    for name in ("Fuentes", "fuentes"):
        p = ROOT / name
        if p.is_dir():
            return p
    return None


def process_docx(docx_path: Path, ep_dir: Path, *, move_into_episode: bool) -> None:
    script_md, blog_md = split_docx(docx_path)
    (ep_dir / "Script.md").write_text(script_md, encoding="utf-8")
    if blog_md and blog_md.strip():
        (ep_dir / "Blog.md").write_text(blog_md, encoding="utf-8")
    else:
        blog_file = ep_dir / "Blog.md"
        if blog_file.exists():
            blog_file.unlink()

    fuente = ep_dir / "Fuente.docx"
    if move_into_episode:
        if fuente.exists():
            fuente.unlink()
        shutil.move(str(docx_path), str(fuente))
        print("  → Fuente.docx en carpeta del episodio")
    else:
        if docx_path.name != "Fuente.docx":
            if fuente.exists() and fuente.resolve() != docx_path.resolve():
                print(
                    f"  advertencia: ya existe {fuente.name}, no renombro {docx_path.name!r}"
                )
            else:
                if fuente.exists() and not fuente.samefile(docx_path):
                    fuente.unlink()
                    shutil.move(str(docx_path), str(fuente))
                    print("  → renombrado a Fuente.docx")
                elif not fuente.exists():
                    shutil.move(str(docx_path), str(fuente))
                    print("  → renombrado a Fuente.docx")

    kept = {"Script.md"}
    if (ep_dir / "Blog.md").exists():
        kept.add("Blog.md")
    for old in legacy_md_to_remove(ep_dir, kept):
        print(f"  elimina obsoleto: {old.name}")
        old.unlink()


def import_from_fuentes() -> int:
    folder = fuentes_folder()
    if folder is None:
        return 0
    seen: set[str] = set()
    n_ok = 0
    for docx_path in sorted(folder.glob("*.docx")):
        m = NUM_PREFIX.match(docx_path.stem)
        if not m:
            print(f"· Fuentes/{docx_path.name} — omitido (sin prefijo NNN al inicio)")
            continue
        num = m.group(1)
        if num in seen:
            print(f"· Fuentes/{docx_path.name} — omitido (duplicado episodio {num})")
            continue
        seen.add(num)
        ep_dir = find_episode_dir(num)
        if ep_dir is None:
            print(
                f"· Fuentes/{docx_path.name} — sin carpeta de episodio para {num} en Libros/"
            )
            continue
        print(f"· Fuentes/{docx_path.name} → {ep_dir.name}/")
        process_docx(docx_path, ep_dir, move_into_episode=True)
        n_ok += 1
    if n_ok:
        print(f"Importados desde Fuentes: {n_ok} episodios.")
    return n_ok


def main() -> None:
    import_from_fuentes()

    docx_files = sorted(
        p
        for p in ROOT.rglob("*.docx")
        if p.is_file() and not should_skip_path(p)
    )
    if not docx_files:
        print(
            "No hay más .docx sueltos en carpetas de episodios (solo Fuentes o ya procesados)."
        )
        return

    for docx_path in docx_files:
        ep_dir = docx_path.parent
        rel = docx_path.relative_to(ROOT)
        print(f"· {rel}")
        process_docx(docx_path, ep_dir, move_into_episode=False)

    print(f"Listo: {len(docx_files)} .docx procesados en carpetas de episodio.")


if __name__ == "__main__":
    main()
