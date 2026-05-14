#!/usr/bin/env python3
"""
Genera Blog.md desde Script.md para Filosofía (episodios en episodes.json).

- Limpia aperturas/cierres de podcast y adapta lenguaje oral → lector (escuchar → leer).
- Sin **Excerpt:** en el cuerpo: el resumen va a descriptions.json.
- Convierte citas tipo bloque `> ...` a pull quotes *"...*".
- No inserta relleno genérico: el cuerpo sigue el guion.

Uso:
  python3 Filosofia/generate_blogs_from_scripts.py
  EPISODES=1,13-30 TARGET_WORDS=4000 python3 Filosofia/generate_blogs_from_scripts.py
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
    r"Bienvenidos a (Filosofía|Historia) en 20 minutos[^\n]*|"
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
    (r"\bescucharlas\b", "leerlas"),
    (r"\bescucharlos con atención\b", "leerlos con atención"),
]

# Frases típicas de cierre oral (patrón, reemplazo, flags)
CLOSING_SUBST: list[tuple[str, str, int]] = [
    (r"\bArrancamos\.\s*", "", 0),
    (r"\bArranquemos\.\s*", "", 0),
    (r"\bVamos\.\s*$", "", re.MULTILINE),
]


def load_episodes(numbers: set[int]) -> list[dict]:
    data = json.loads(EPISODES_JSON.read_text(encoding="utf-8"))
    out = []
    for ep in data.get("filosofia", []):
        n = ep.get("number")
        if isinstance(n, int) and n in numbers:
            out.append(ep)
    return sorted(out, key=lambda e: e["number"])


def parse_episode_arg(s: str) -> set[int]:
    if not s.strip():
        return set(range(1, 31))
    r: set[int] = set()
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            r.update(range(int(a), int(b) + 1))
        else:
            r.add(int(part))
    return r


def find_script(folder: Path) -> Path:
    if (folder / "Script.md").is_file():
        return folder / "Script.md"
    cands = sorted(folder.glob("*.md"))
    for p in cands:
        if p.name.lower() == "blog.md" or p.name.lower().endswith("_en.md"):
            continue
        return p
    raise FileNotFoundError(f"No Script.md in {folder}")


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
    for pat, _, *flags in [
        (r"\s*Bienvenidos a Filosofía en 20 minutos[^.]*\.", "", re.I | re.DOTALL),
    ]:
        fl = flags[0] if flags else 0
        body = re.sub(pat, "", body, flags=fl)
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
    """Un solo H1: el primero que aparezca; líneas previas (p.ej. hook en itálica) se conservan antes."""
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
    # quitar H1 duplicados suaves (fusionar ## # error)
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
        # hook antes del título (p.ej. Tales)
        return "\n".join(before + [""] + fixed).strip()
    return "\n".join(fixed).strip()


def extract_excerpt(body: str, max_chars: int = 248) -> str:
    """Primeras 1–2 oraciones del discurso principal (después del bloque inicial # título + opcional itálica)."""
    lines = body.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].startswith("#"):
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    # skip block of italic-only hook
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
        blob = "Reflexión en clave de texto a partir del guion del programa."
    # dos oraciones máximo
    parts = re.split(r"(?<=[.!?])\s+", blob)
    excerpt = " ".join(parts[:2]).strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 3].rsplit(" ", 1)[0] + "..."
    return excerpt


def word_count(s: str) -> int:
    return len(re.findall(r"\S+", s))


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


def resolve_episode_folder(rel: str) -> Path:
    """Coincide carpeta aunque episodes.json y el disco difieran en espacios finales."""
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


def process_episode(ep: dict, dry_run: bool) -> None:
    folder = resolve_episode_folder(ep["folder"])
    num = ep["number"]
    title = ep.get("title") or ""
    if not folder.is_dir():
        print(f"[{num}] skip: missing dir {folder}")
        return
    blog_path = folder / "Blog.md"
    force = os.environ.get("FORCE", "").lower() in ("1", "true", "yes")
    if blog_path.exists() and not force:
        print(f"[{num}] skip: Blog.md exists (FORCE=1 to overwrite)")
        return
    script_path = find_script(folder)
    raw = script_path.read_text(encoding="utf-8")
    body = strip_podcast_lines(raw)
    body = listen_to_read(body)
    body = blockquote_to_pull(body)
    body = normalize_headings(body)
    excerpt = extract_excerpt(body)
    body = pad_to_words(body, title, TARGET_WORDS)

    final = body
    if dry_run:
        print(f"[{num}] would write {word_count(final)} words -> {blog_path}")
        return
    desc_path = folder / "descriptions.json"
    if not desc_path.is_file():
        write_description(folder, excerpt)
    blog_path.write_text(final.strip() + "\n", encoding="utf-8")
    print(f"[{num}] OK {word_count(final)} w -> {blog_path.name}")


def main() -> None:
    nums = parse_episode_arg(os.environ.get("EPISODES", "1,13-30"))
    dry = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    for ep in load_episodes(nums):
        process_episode(ep, dry)


if __name__ == "__main__":
    main()
