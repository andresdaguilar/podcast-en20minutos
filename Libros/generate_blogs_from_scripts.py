#!/usr/bin/env python3
"""
Genera Blog.md desde Script.md para Libros (episodios en episodes.json).

- Limpia cierres/oral, adapta escuchar → leer, episodio → artículo cuando aplique.
- Añade subtítulos ## si el guion trae pocos.
- Añade hasta dos pull quotes *"…"* si faltan (sin duplicar el arranque).
- No inserta relleno genérico: el cuerpo sigue el guion.
- Crea descriptions.json si no existe (excerpt desde blog o guion o título).
- Actualiza content.blog / hasDescriptions en podcast-web/data/episodes.json.

Uso:
  python3 Libros/generate_blogs_from_scripts.py
  EPISODES=1-15 FORCE=1 python3 Libros/generate_blogs_from_scripts.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EPISODES_JSON = REPO_ROOT / "podcast-web" / "data" / "episodes.json"
TARGET_WORDS = int(os.environ.get("TARGET_WORDS", "4000"))

PODCAST_STRIP_LINE = re.compile(
    r"^("
    r"Bienvenidos a (Filosofía|Historia|Libros) en 20 minutos[^\n]*|"
    r"Gracias por escuchar[^\n]*|"
    r"Eso es todo por hoy[^\n]*|"
    r"Nos vemos en el próximo[^\n]*|"
    r"Si te gustó este episodio[^\n]*|"
    r"Si este (episodio|texto) te resultó interesante[^\n]*|"
    r"hasta acá llegamos con este episodio[^\n]*|"
    r"Nos escuchamos[^\n]*|"
    r"Recap rápido[^\n]*|"
    r"Recap intermedio[^\n]*|"
    r"Recap final[^\n]*"
    r")\s*$",
    re.IGNORECASE,
)

RE_LISTEN_SUBST: list[tuple[str, str]] = [
    (r"\bHoy vamos a hablar de\b", "Aquí vamos a recorrer"),
    (r"\bHoy hablamos de\b", "Aquí recorremos"),
    (r"\bHoy vamos a\b", "Aquí vamos a"),
    (r"\bVale la pena escuchar\b", "Vale la pena atender"),
    (r"\bvale la pena escuchar\b", "vale la pena atender"),
    (r"\bte invito a escuchar\b", "te invito a leer con calma"),
    (r"\bal escuchar\b", "al leer"),
    (r"\bcuando escuchás\b", "cuando leés"),
    (r"\bcuando escuchas\b", "cuando lees"),
    (r"\bSi escuchás\b", "Si leés"),
    (r"\bSi escuchas\b", "Si lees"),
    (r"\bcuando lo escuchás\b", "cuando lo leés"),
    (r"\bcuando lo escuchas\b", "cuando lo lees"),
    (r"\bpara escuchar\b", "para leer"),
    (r"\bpor escuchar\b", "por leer"),
    (r"\bde escuchar\b", "de leer"),
    (r"\bestán escuchando\b", "están leyendo"),
    (r"\bestábamos escuchando\b", "estábamos leyendo"),
    (r"\bestamos escuchando\b", "estamos leyendo"),
    (r"\bescuchar con atención\b", "leer con atención"),
    (r"\bel episodio\b", "este artículo"),
    (r"\beste episodio\b", "este artículo"),
    (r"\ben el episodio\b", "en este artículo"),
    (r"\bdel episodio\b", "del texto"),
    (r"\bel podcast\b", "el texto"),
    (r"\beste podcast\b", "este texto"),
    (r"\bun podcast\b", "un texto"),
    (r"\bNos escuchamos\b", "Hasta una próxima"),
    (r"\bmedio (?:el )?mundo lo escuchaba\b", "muchos repasaban sus ideas"),
    (r"\blo escuchaba\b", "le prestaba atención"),
    (r"\blo escuchaban\b", "lo seguían"),
    (r"\bcómo se escucha\b", "cómo suena"),
    (r"\bse escucha mucho\b", "circula mucho"),
    (r"\bse escuchaba\b", "se decía"),
    (r"\bescucharlos\b", "leerlos"),
    (r"\bescuchás tu podcast\b", "dejás de fondo tu podcast"),
    (r"\bescuchar un podcast\b", "seguir un podcast en audio"),
]

CLOSING_SUBST: list[tuple[str, str, int]] = [
    (r"\bArrancamos\.\s*", "", 0),
    (r"\bArranquemos\.\s*", "", 0),
    (r"\bVamos\.\s*$", "", re.MULTILINE),
]


def load_data() -> dict:
    return json.loads(EPISODES_JSON.read_text(encoding="utf-8"))


def all_libros_numbers(data: dict) -> set[int]:
    return {e["number"] for e in data["libros"] if isinstance(e.get("number"), int)}


def parse_episode_arg(s: str, all_nums: set[int]) -> set[int]:
    if not s.strip():
        return all_nums
    r: set[int] = set()
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            r.update(range(int(a), int(b) + 1))
        else:
            r.add(int(part))
    return r & all_nums


def resolve_episode_folder(rel: str) -> Path:
    rel = rel.strip()
    p = REPO_ROOT / rel
    if p.is_dir():
        return p
    parent = p.parent
    base = p.name
    if parent.is_dir():
        for child in parent.iterdir():
            if not child.is_dir():
                continue
            if child.name.strip() == base.strip() or child.name == base + " ":
                return child
    return p


def find_script(folder: Path) -> Path | None:
    if (folder / "Script.md").is_file():
        return folder / "Script.md"
    for p in sorted(folder.glob("*.md")):
        if p.name.lower() == "blog.md" or p.name.lower().endswith("_en.md"):
            continue
        return p
    return None


def strip_podcast_lines(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    for line in lines:
        if PODCAST_STRIP_LINE.match(line.strip()):
            continue
        if re.match(r"^##\s*\*?\*?Cierre\*?\*?\s*$", line.strip(), re.I):
            break
        out.append(line)
    body = "\n".join(out).strip()
    for pat in (
        r"\s*Bienvenidos a Libros en 20 minutos[^.]*\.",
        r"\s*Bienvenidos a Filosofía en 20 minutos[^.]*\.",
    ):
        body = re.sub(pat, "", body, flags=re.I)
    return body


def listen_to_read(text: str) -> str:
    for pat, rep in RE_LISTEN_SUBST:
        text = re.sub(pat, rep, text, flags=re.IGNORECASE)
    for pat, rep, fl in CLOSING_SUBST:
        text = re.sub(pat, rep, text, flags=fl)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def blockquote_to_pull(body: str) -> str:
    lines = body.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("> "):
            chunk = []
            while i < len(lines) and lines[i].lstrip().startswith("> "):
                chunk.append(lines[i].lstrip()[2:].strip())
                i += 1
            q = " ".join(chunk).strip()
            if q:
                out.append(f'*"{q}"*')
                out.append("")
            continue
        out.append(line)
        i += 1
    return "\n".join(out).strip()


def normalize_headings(body: str) -> str:
    lines = body.splitlines()
    first_h1 = None
    for i, ln in enumerate(lines):
        if re.match(r"^#\s+[^#]", ln):
            first_h1 = i
            break
    if first_h1 is None:
        return body
    before = [ln for ln in lines[:first_h1] if ln.strip()]
    rest = lines[first_h1:]
    fixed: list[str] = []
    seen_h1 = False
    for ln in rest:
        if re.match(r"^#\s+[^#]", ln):
            if seen_h1:
                fixed.append(re.sub(r"^#\s+", "## ", ln))
            else:
                fixed.append(ln)
                seen_h1 = True
        else:
            fixed.append(ln)
    if before:
        return "\n".join(before + [""] + fixed).strip()
    return "\n".join(fixed).strip()


def extract_excerpt(body: str, max_chars: int = 248) -> str:
    lines = body.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].startswith("#"):
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines) and lines[i].strip().startswith("*") and lines[i].strip().endswith("*"):
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
    paras: list[str] = []
    while i < len(lines) and len(paras) < 2:
        ln = lines[i].strip()
        if not ln or ln.startswith("#") or ln.startswith("---") or ln.startswith('*"'):
            break
        if ln.startswith("*") and not ln.startswith('*"'):
            i += 1
            continue
        if ln.startswith(">") or ln.startswith('*"'):
            i += 1
            continue
        paras.append(ln)
        i += 1
    blob = " ".join(paras)
    blob = re.sub(r"\s+", " ", blob).strip()
    if not blob:
        blob = "Resumen en clave de lectura a partir del guion del episodio sobre el libro."
    parts = re.split(r"(?<=[.!?])\s+", blob)
    excerpt = " ".join(parts[:2]).strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 3].rsplit(" ", 1)[0] + "..."
    return excerpt


def word_count(s: str) -> int:
    return len(re.findall(r"\S+", s))


def count_h2(text: str) -> int:
    return len(re.findall(r"(?m)^##\s+", text))


def add_subtitles_if_sparse(text: str, min_h2: int = 4, every: int = 7) -> str:
    if count_h2(text) >= min_h2:
        return text
    parts = re.split(r"\n\n+", text.strip())
    out: list[str] = []
    since = 0
    for p in parts:
        ps = p.strip()
        if ps.startswith("#"):
            since = 0
            out.append(p)
            continue
        since += 1
        if since >= every and len(ps) > 160 and not ps.startswith("*") and not ps.startswith("---"):
            m = re.match(r"^([^.!?]{10,120}[.!?])", ps.replace("\n", " "))
            head = (m.group(1) if m else ps[:80]).strip()
            head = head.rstrip(".!?").strip()
            head = re.sub(r"\s+", " ", head)
            if len(head) > 72:
                head = head[:69].rsplit(" ", 1)[0] + "…"
            if len(head) > 12:
                out.append(f"## {head}")
                since = 0
        out.append(p)
    return "\n\n".join(out)


def pull_quote_count(text: str) -> int:
    return len(re.findall(r"(?m)^\*\".+\"\*\s*$", text))


def add_pull_quotes_if_sparse(text: str, want: int = 2) -> str:
    if pull_quote_count(text) >= want:
        return text
    paras = [
        p.strip()
        for p in re.split(r"\n\n+", text)
        if p.strip()
        and not p.strip().startswith("#")
        and not p.strip().startswith("---")
        and not p.strip().startswith("*")
    ]
    n = len(paras)
    if n < 4:
        return text
    mid = n // 2
    candidates: list[str] = []
    for p in paras[max(2, n // 5) : max(3, n // 5) + 6] + paras[mid : mid + 6]:
        if len(p) < 90:
            continue
        for sent in re.split(r"(?<=[.!?])\s+", p.replace("\n", " ")):
            s = sent.strip()
            if 55 < len(s) < 220:
                candidates.append(s)
    seen: set[str] = set()
    picks: list[str] = []
    prefix = "\n".join(paras[:2])[:400]
    for s in candidates:
        if s in seen or s in prefix:
            continue
        seen.add(s)
        picks.append(s)
        if len(picks) >= want:
            break
    if not picks:
        return text
    block = "\n\n".join(f'*"{s}"*' for s in picks) + "\n\n---\n\n"
    if "\n---\n" in text:
        a, b = text.split("\n---\n", 1)
        return a + "\n---\n\n" + block + b
    # después del tercer bloque de párrafos
    splits = text.split("\n\n")
    if len(splits) > 6:
        k = len(splits) // 3
        return "\n\n".join(splits[:k]) + "\n\n---\n\n" + block + "\n\n".join(splits[k:])
    return text + "\n\n---\n\n" + block


def pad_to_words(body: str, title: str, target: int) -> str:
    """Sin relleno: el blog debe seguir el guion, sin secciones genéricas repetidas."""
    return body


def write_description(folder: Path, excerpt: str) -> None:
    t = excerpt.strip()
    if len(t) > 250:
        t = t[:247].rsplit(" ", 1)[0] + "..."
    (folder / "descriptions.json").write_text(
        json.dumps({"es": t + "\n"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def title_fallback_description(title: str, max_chars: int = 248) -> str:
    t = title.strip().rstrip(".")
    base = f"{t}: de qué trata el libro y por qué sigue interpelando, en versión para leer con calma."
    if len(base) > max_chars:
        base = base[: max_chars - 3].rsplit(" ", 1)[0] + "..."
    return base


def script_to_blog_body(raw: str, title: str) -> tuple[str, str]:
    body = strip_podcast_lines(raw)
    body = listen_to_read(body)
    body = blockquote_to_pull(body)
    body = normalize_headings(body)
    excerpt = extract_excerpt(body)
    body = add_subtitles_if_sparse(body)
    body = add_pull_quotes_if_sparse(body)
    body = pad_to_words(body, title, TARGET_WORDS)
    return body, excerpt


def main() -> None:
    dry = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    data = load_data()
    all_n = all_libros_numbers(data)
    nums = parse_episode_arg(os.environ.get("EPISODES", ""), all_n)
    force = os.environ.get("FORCE", "").lower() in ("1", "true", "yes")
    json_dirty = False

    for ep in sorted((e for e in data["libros"] if e["number"] in nums), key=lambda e: e["number"]):
        num = ep["number"]
        title = (ep.get("title") or "").strip()
        folder = resolve_episode_folder(ep["folder"])
        if not folder.is_dir():
            print(f"[{num}] skip: sin carpeta")
            continue

        blog_path = folder / "Blog.md"
        script_path = find_script(folder)

        if blog_path.is_file() and not ep.get("content", {}).get("blog"):
            ep.setdefault("content", {})["blog"] = True
            json_dirty = True

        if script_path and (not blog_path.is_file() or force):
            raw = script_path.read_text(encoding="utf-8")
            body, _gen_excerpt = script_to_blog_body(raw, title)
            wc = word_count(body)
            if dry:
                print(f"[{num}] dry-run Blog {wc} w -> {blog_path.name}")
            else:
                blog_path.write_text(body.strip() + "\n", encoding="utf-8")
                ep.setdefault("content", {})["blog"] = True
                json_dirty = True
                print(f"[{num}] Blog OK {wc} w")
        elif not script_path and not blog_path.is_file():
            print(f"[{num}] skip blog: sin Script.md")

        desc_path = folder / "descriptions.json"
        if desc_path.is_file():
            if not ep.get("hasDescriptions"):
                ep["hasDescriptions"] = True
                json_dirty = True
        else:
            excerpt = ""
            if blog_path.is_file():
                excerpt = extract_excerpt(blog_path.read_text(encoding="utf-8"))
            elif script_path:
                raw = script_path.read_text(encoding="utf-8")
                b = strip_podcast_lines(raw)
                b = listen_to_read(b)
                b = blockquote_to_pull(b)
                b = normalize_headings(b)
                excerpt = extract_excerpt(b)

            if not excerpt or "Resumen en clave" in excerpt:
                excerpt = title_fallback_description(title)

            if dry:
                print(f"[{num}] dry-run descriptions.json ({len(excerpt)} chars)")
            else:
                write_description(folder, excerpt)
                ep["hasDescriptions"] = True
                json_dirty = True
                print(f"[{num}] descriptions.json OK")

    if json_dirty and not dry:
        EPISODES_JSON.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("episodes.json actualizado.")
    elif not dry:
        print("Sin cambios en JSON (tabla libros).")


if __name__ == "__main__":
    main()
