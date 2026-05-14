#!/usr/bin/env python3
"""
Publica en Contentful (tipo Podcast) Blog.md de Filosofía, Libros y Mitología.

Por defecto: Filosofía y Libros (episodes.json; exige publishDate; Blog.md;
descripcion desde descriptions.json o excerpt autogenerado guardado en disco).

Slugs: filosofia-NNN-..., libros-NNN-..., mitologia-NNN-...

Uso:
  python3 contentful-sync/sync_filosofia_libros_blog.py
  python3 contentful-sync/sync_filosofia_libros_blog.py --mitologia-range 6-24

Requiere contentful-sync/.env con CONTENTFUL_MANAGEMENT_TOKEN (ver .env.example).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EPISODES_JSON = REPO_ROOT / "podcast-web" / "data" / "episodes.json"

SPACE_ID = os.environ.get("CONTENTFUL_SPACE_ID", "ov6bno3s1chn")
ENV_ID = os.environ.get("CONTENTFUL_ENVIRONMENT", "master")
CT_PODCAST = "podcast"
LOCALE = "en-US"
AUTHOR_ID = os.environ.get("CONTENTFUL_AUTHOR_ENTRY_ID", "3oMOpFGzeVOd0d9fRN4UVk")

CMA = f"https://api.contentful.com/spaces/{SPACE_ID}/environments/{ENV_ID}"
UPLOAD_API = f"https://upload.contentful.com/spaces/{SPACE_ID}/uploads"


def load_dotenv() -> None:
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


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


def slugify_title(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:72] or "episodio"


def make_slug(series_key: str, num: int, title: str) -> str:
    """series_key: filosofia | libros | mitologia"""
    tail = slugify_title(title)
    raw = f"{series_key}-{num:03d}-{tail}"
    return raw[:96]


SERIES_PREFIX = {"filosofia": "F", "libros": "L", "mitologia": "M"}


def pick_cover(series_key: str, num: int, folder: Path) -> Path:
    prefix = SERIES_PREFIX[series_key]
    for pat in (f"{prefix}{num:03d}B.*", f"{prefix}{num:03d}Y.*", f"{prefix}{num:03d}S.*"):
        found = sorted(folder.glob(pat))
        if found:
            return found[0]
    raise FileNotFoundError(f"No cover {prefix}{num:03d}[BYS] in {folder}")


def guess_content_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")


def parse_inline(text: str) -> list[dict]:
    if not text:
        return [{"nodeType": "text", "value": "", "marks": [], "data": {}}]
    out: list[dict] = []
    i, n = 0, len(text)
    acc = ""

    def flush_acc() -> None:
        nonlocal acc
        if acc:
            out.append({"nodeType": "text", "value": acc, "marks": [], "data": {}})
            acc = ""

    while i < n:
        if text.startswith("**", i):
            flush_acc()
            j = text.find("**", i + 2)
            if j == -1:
                acc += text[i]
                i += 1
                continue
            out.append(
                {
                    "nodeType": "text",
                    "value": text[i + 2 : j],
                    "marks": [{"type": "bold"}],
                    "data": {},
                }
            )
            i = j + 2
            continue
        if text[i] == "*" and i + 1 < n and text[i + 1] != "*":
            flush_acc()
            j = text.find("*", i + 1)
            if j == -1:
                acc += text[i]
                i += 1
                continue
            out.append(
                {
                    "nodeType": "text",
                    "value": text[i + 1 : j],
                    "marks": [{"type": "italic"}],
                    "data": {},
                }
            )
            i = j + 1
            continue
        acc += text[i]
        i += 1
    flush_acc()
    return out or [{"nodeType": "text", "value": "", "marks": [], "data": {}}]


def paragraph_node(text: str) -> dict:
    return {"nodeType": "paragraph", "content": parse_inline(text), "data": {}}


def markdown_to_richtext(md: str) -> dict:
    lines = md.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and re.match(r"^\*\*Excerpt:\*\*\s*", lines[0].strip(), re.IGNORECASE):
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and re.match(r"^#\s+", lines[0].strip()):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
    blocks: list[dict] = []
    buf: list[str] = []

    def flush_para() -> None:
        nonlocal buf
        if not buf:
            return
        text = " ".join(buf).strip()
        buf = []
        if text:
            blocks.append(paragraph_node(text))

    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            flush_para()
            i += 1
            continue
        if stripped == "---":
            flush_para()
            blocks.append({"nodeType": "hr", "content": [], "data": {}})
            i += 1
            continue
        hm = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if hm:
            flush_para()
            level = len(hm.group(1))
            title = hm.group(2).strip()
            blocks.append(
                {
                    "nodeType": f"heading-{level}",
                    "content": parse_inline(title),
                    "data": {},
                }
            )
            i += 1
            continue
        if re.match(r'^\*".+"\*$', stripped):
            flush_para()
            inner = stripped[2:-2]
            blocks.append(
                {
                    "nodeType": "blockquote",
                    "content": [
                        {
                            "nodeType": "paragraph",
                            "content": [
                                {
                                    "nodeType": "text",
                                    "value": inner,
                                    "marks": [{"type": "italic"}],
                                    "data": {},
                                }
                            ],
                            "data": {},
                        }
                    ],
                    "data": {},
                }
            )
            i += 1
            continue
        buf.append(stripped)
        i += 1
    flush_para()
    return {"nodeType": "document", "data": {}, "content": blocks}


def api_request(
    method: str,
    url: str,
    token: str,
    body: dict | None = None,
    extra_headers: dict | None = None,
    raw: bytes | None = None,
) -> tuple[int, dict | None, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if extra_headers:
        headers.update(extra_headers)
    data = None
    if raw is not None:
        data = raw
    elif body is not None:
        headers["Content-Type"] = "application/vnd.contentful.management.v1+json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            b = resp.read().decode("utf-8")
            if not b:
                return resp.status, None, ""
            return resp.status, json.loads(b), b
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err_body) if err_body.strip().startswith("{") else None
        except json.JSONDecodeError:
            parsed = None
        return e.code, parsed, err_body


def upload_and_publish_asset(token: str, path: Path, title: str) -> str:
    raw = path.read_bytes()
    status, upload, raw_out = api_request(
        "POST",
        UPLOAD_API,
        token,
        raw=raw,
        extra_headers={"Content-Type": "application/octet-stream"},
    )
    if status not in (200, 201) or not upload:
        raise RuntimeError(f"Upload failed {status}: {raw_out}")
    up_id = upload["sys"]["id"]

    create_body = {
        "fields": {
            "title": {LOCALE: title},
            "description": {LOCALE: ""},
            "file": {
                LOCALE: {
                    "contentType": guess_content_type(path),
                    "fileName": path.name,
                    "uploadFrom": {
                        "sys": {
                            "type": "Link",
                            "linkType": "Upload",
                            "id": up_id,
                        }
                    },
                }
            },
        }
    }
    status, asset, bout = api_request("POST", f"{CMA}/assets", token, create_body)
    if status not in (200, 201) or not asset:
        raise RuntimeError(f"Asset create failed {status}: {bout}")
    aid = asset["sys"]["id"]
    ver = asset["sys"]["version"]

    ps, _, pbody = api_request(
        "PUT",
        f"{CMA}/assets/{aid}/files/{LOCALE}/process",
        token,
        body=None,
        extra_headers={"X-Contentful-Version": str(ver)},
    )
    if ps not in (204, 200):
        raise RuntimeError(f"Process failed {ps}: {pbody}")

    for _ in range(40):
        time.sleep(1)
        gs, cur, _ = api_request("GET", f"{CMA}/assets/{aid}", token)
        if gs != 200 or not cur:
            continue
        url_f = cur.get("fields", {}).get("file", {}).get(LOCALE, {}).get("url", "")
        if url_f:
            ver = cur["sys"]["version"]
            break
    else:
        raise RuntimeError("Asset processing timeout")

    pub_s, _, err = api_request(
        "PUT",
        f"{CMA}/assets/{aid}/published",
        token,
        body=None,
        extra_headers={"X-Contentful-Version": str(ver)},
    )
    if pub_s not in (200, 201):
        raise RuntimeError(f"Asset publish failed {pub_s}: {err}")
    return aid


def find_entry_by_slug(token: str, slug: str) -> dict | None:
    url = f"{CMA}/entries?content_type={CT_PODCAST}&fields.slug={urllib.parse.quote(slug)}&limit=1"
    _, res, _ = api_request("GET", url, token)
    if not res or not res.get("items"):
        return None
    return res["items"][0]


def upsert_podcast_entry(token: str, slug: str, fields_payload: dict) -> None:
    existing = find_entry_by_slug(token, slug)
    if existing:
        eid = existing["sys"]["id"]
        ver = existing["sys"]["version"]
        merged_fields = dict(existing.get("fields", {}))
        merged_fields.update(fields_payload)
        patch = {"fields": merged_fields}
        st, out, err = api_request(
            "PUT",
            f"{CMA}/entries/{eid}",
            token,
            patch,
            extra_headers={"X-Contentful-Version": str(ver)},
        )
        if st not in (200, 201):
            raise RuntimeError(f"Entry update failed {st}: {err}")
        new_ver = out["sys"]["version"] if out else ver + 1
    else:
        st, out, err = api_request(
            "POST",
            f"{CMA}/entries",
            token,
            {"fields": fields_payload},
            extra_headers={"X-Contentful-Content-Type": CT_PODCAST},
        )
        if st not in (200, 201) or not out:
            raise RuntimeError(f"Entry create failed {st}: {err}")
        eid = out["sys"]["id"]
        new_ver = out["sys"]["version"]

    pub_s, _, err = api_request(
        "PUT",
        f"{CMA}/entries/{eid}/published",
        token,
        body=None,
        extra_headers={"X-Contentful-Version": str(new_ver)},
    )
    if pub_s not in (200, 201):
        raise RuntimeError(f"Entry publish failed {pub_s}: {err}")


def find_blog_path(folder: Path) -> Path | None:
    for name in ("Blog.md", "blog.md", "Script.md", "script.md"):
        p = folder / name
        if p.is_file():
            return p
    return None


def excerpt_from_blog_md(md: str, fallback_title: str = "", max_content: int = 252) -> str:
    """Primer párrafo tras el título # …; apto para campo descripción breve."""
    lines = md.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].strip().startswith("#"):
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    parts: list[str] = []
    while i < len(lines) and len(" ".join(parts)) < 800:
        line = lines[i].strip()
        if line.startswith("#"):
            break
        if line:
            line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            line = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", line)
            parts.append(line)
        elif parts:
            break
        i += 1
    text = " ".join(parts).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_content:
        text = text[: max_content - 3].rstrip() + "..."
    if text:
        return text
    if fallback_title:
        return f"En este episodio hablamos de {fallback_title}."
    return "Episodio de podcast."


def resolve_description(folder: Path, md: str, titulo: str) -> str:
    """Lee descriptions.json; si falta o \"es\" vacío, excerpt + escribe JSON."""
    p = folder / "descriptions.json"
    if p.is_file():
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            es = raw.get("es", "")
            if isinstance(es, str) and es.strip():
                text = es.strip().replace("\n", " ")
                if len(text) > 255:
                    text = text[:252] + "..."
                return text
        except (json.JSONDecodeError, TypeError, OSError):
            pass

    excerpt = excerpt_from_blog_md(md, titulo)
    out_obj = {"es": excerpt if excerpt.endswith("\n") else excerpt + "\n"}
    p.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    send = excerpt.replace("\n", " ")
    if len(send) > 255:
        send = send[:252] + "..."
    return send


def read_data_json_title(folder: Path) -> str | None:
    """Título canónico en carpeta del episodio: data.json con claves titulo o title."""
    p = folder / "data.json"
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    for key in ("titulo", "title"):
        v = raw.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def blog_titulo(md: str) -> str:
    for line in md.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            t = m.group(1).strip()
            return re.sub(r"^\*\*(.+)\*\*$", r"\1", t).replace("**", "")
    return "Sin título"


def resolve_episode_title(folder: Path, md: str, ep: dict) -> str:
    data_t = read_data_json_title(folder)
    if data_t:
        return data_t
    blog_t = blog_titulo(md).strip()
    if blog_t and blog_t != "Sin título":
        return blog_t
    ep_t = (ep.get("title") or "").strip()
    return ep_t or "Sin título"


def load_series_episodes(data: dict, key: str) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for ep in data.get(key, []):
        n = ep.get("number")
        if isinstance(n, int):
            out[n] = ep
    return out


def process_one(
    token: str,
    series_key: str,
    categoria: str,
    num: int,
    ep: dict,
) -> None:
    folder = resolve_episode_folder(ep["folder"])
    if not folder.is_dir():
        print(f"[{series_key} {num}] skip: sin carpeta {folder}")
        return
    blog_path = find_blog_path(folder)
    if not blog_path:
        print(f"[{series_key} {num}] skip: sin Blog.md / blog.md / Script.md")
        return
    fecha = ep.get("publishDate")
    if not isinstance(fecha, str):
        print(f"[{series_key} {num}] skip: sin publishDate")
        return

    md = blog_path.read_text(encoding="utf-8")
    titulo = resolve_episode_title(folder, md, ep)
    desc = resolve_description(folder, md, titulo)
    slug = make_slug(series_key, num, (ep.get("title") or "").strip() or titulo)

    print(f"[{series_key} {num}] cover…", flush=True)
    cover_path = pick_cover(series_key, num, folder)
    label = categoria
    asset_id = upload_and_publish_asset(
        token,
        cover_path,
        title=f"{label} {num} — {cover_path.name}",
    )

    doc = markdown_to_richtext(md)

    def link(tid: str, lt: str) -> dict:
        return {"sys": {"type": "Link", "linkType": lt, "id": tid}}

    fields_payload = {
        "numeroEpisodio": {LOCALE: num},
        "titulo": {LOCALE: titulo},
        "slug": {LOCALE: slug},
        "descripcion": {LOCALE: desc},
        "contenido": {LOCALE: doc},
        "fecha": {LOCALE: fecha},
        "autor": {LOCALE: link(AUTHOR_ID, "Entry")},
        "cover": {LOCALE: link(asset_id, "Asset")},
        "hero": {LOCALE: link(asset_id, "Asset")},
        "categoria": {LOCALE: categoria},
    }

    print(f"[{series_key} {num}] upsert slug={slug}…", flush=True)
    upsert_podcast_entry(token, slug, fields_payload)
    print(f"[{series_key} {num}] OK", flush=True)
    time.sleep(0.35)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Sync podcast blogs a Contentful")
    parser.add_argument(
        "--mitologia-range",
        metavar="N-M",
        help="Solo Mitología: episodios N a M inclusive (ej. 6-24). Categoría Contentful: Mitologia",
    )
    args = parser.parse_args()

    token = os.environ.get("CONTENTFUL_MANAGEMENT_TOKEN", "").strip()
    if not token:
        print("Definí CONTENTFUL_MANAGEMENT_TOKEN o contentful-sync/.env", file=sys.stderr)
        sys.exit(1)

    data = json.loads(EPISODES_JSON.read_text(encoding="utf-8"))

    if args.mitologia_range:
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", args.mitologia_range.strip())
        if not m:
            print("Usá --mitologia-range M-N (ej. 6-24)", file=sys.stderr)
            sys.exit(2)
        lo, hi = int(m.group(1)), int(m.group(2))
        mit = load_series_episodes(data, "mitologia")
        for num in sorted(n for n in mit if lo <= n <= hi):
            process_one(token, "mitologia", "Mitologia", num, mit[num])
        print(f"Listo Mitología {lo}–{hi}.")
        return

    fil = load_series_episodes(data, "filosofia")
    lib = load_series_episodes(data, "libros")

    for num in sorted(fil):
        process_one(token, "filosofia", "Filosofía", num, fil[num])
    for num in sorted(lib):
        process_one(token, "libros", "Libros", num, lib[num])

    print("Listo (Filosofía + Libros, todos los episodios con datos completos).")


if __name__ == "__main__":
    main()
