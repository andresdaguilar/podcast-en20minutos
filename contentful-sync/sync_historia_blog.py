#!/usr/bin/env python3
"""
Publica en Contentful entradas Podcast de Historia a partir de Blog.md local.

Uso:
  export CONTENTFUL_MANAGEMENT_TOKEN="CFPAT-..."
  python3 contentful-sync/sync_historia_blog.py

O: crear contentful-sync/.env con CONTENTFUL_MANAGEMENT_TOKEN=...
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORIA = REPO_ROOT / "Historia"
EPISODES_JSON = REPO_ROOT / "podcast-web" / "data" / "episodes.json"

SPACE_ID = os.environ.get("CONTENTFUL_SPACE_ID", "ov6bno3s1chn")
ENV_ID = os.environ.get("CONTENTFUL_ENVIRONMENT", "master")
CT_PODCAST = "podcast"
LOCALE = "en-US"
AUTHOR_ID = os.environ.get("CONTENTFUL_AUTHOR_ENTRY_ID", "3oMOpFGzeVOd0d9fRN4UVk")

CMA = f"https://api.contentful.com/spaces/{SPACE_ID}/environments/{ENV_ID}"
UPLOAD_API = f"https://upload.contentful.com/spaces/{SPACE_ID}/uploads"

EPISODES: list[tuple[int, str, str]] = [
    (13, "013 - El Feudalismo", "el-feudalismo"),
    (14, "014 - La revolucion industrial", "la-revolucion-industrial"),
    (15, "015 - El Imperio Otomano", "el-imperio-otomano"),
    (16, "016 - La independencia de Estados Unidos", "la-independencia-de-estados-unidos"),
    (17, "017 - La unificacion de Italia", "la-unificacion-de-italia"),
    (18, "018 - El Imperio Persa", "el-imperio-persa"),
    (19, "019 - El Antiguo Egipto", "el-antiguo-egipto"),
    (20, "020 - El Imperio Inca", "el-imperio-inca"),
    (21, "021 - Las Cruzadas", "las-cruzadas"),
    (22, "022 - La guerra Fria", "la-guerra-fria"),
    (23, "023 - El nacimiento de ciudades", "el-nacimiento-de-ciudades"),
]


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


def load_publish_dates() -> dict[int, str]:
    data = json.loads(EPISODES_JSON.read_text(encoding="utf-8"))
    out: dict[int, str] = {}
    for ep in data.get("historia", []):
        n = ep.get("number")
        pd = ep.get("publishDate")
        if isinstance(n, int) and isinstance(pd, str) and 13 <= n <= 23:
            out[n] = pd
    return out


def pick_cover_image(ep: int, folder: str) -> Path:
    d = HISTORIA / folder
    for pat in (f"H{ep:03d}B.*", f"H{ep:03d}Y.*", f"H{ep:03d}S.*"):
        found = sorted(d.glob(pat))
        if found:
            return found[0]
    raise FileNotFoundError(f"No cover image in {d}")


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
    # Quitar **Excerpt:** — mismo texto que `descripcion` en Contentful.
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and re.match(r"^\*\*Excerpt:\*\*\s*", lines[0].strip(), re.IGNORECASE):
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
    # Omit H1: el campo `titulo` ya lo lleva Contentful.
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


def read_description(folder: str) -> str:
    p = HISTORIA / folder / "descriptions.json"
    text = json.loads(p.read_text(encoding="utf-8"))["es"].strip().replace("\n", " ")
    if len(text) > 255:
        text = text[:252] + "..."
    return text


def blog_titulo(md: str) -> str:
    for line in md.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            t = m.group(1).strip()
            return re.sub(r"^\*\*(.+)\*\*$", r"\1", t).replace("**", "")
    return "Sin título"


def main() -> None:
    load_dotenv()
    token = os.environ.get("CONTENTFUL_MANAGEMENT_TOKEN", "").strip()
    if not token:
        print("Definí CONTENTFUL_MANAGEMENT_TOKEN o contentful-sync/.env", file=sys.stderr)
        sys.exit(1)

    dates = load_publish_dates()

    for num, folder, slug in EPISODES:
        blog_path = HISTORIA / folder / "Blog.md"
        if not blog_path.is_file():
            print(f"[skip {num}] No Blog.md: {folder}")
            continue
        md = blog_path.read_text(encoding="utf-8")
        titulo = blog_titulo(md)
        desc = read_description(folder)
        fecha = dates.get(num)
        if not fecha:
            raise RuntimeError(f"Falta publishDate para episodio {num} en episodes.json")

        print(f"Ep {num}: uploading cover…", flush=True)
        cover_path = pick_cover_image(num, folder)
        asset_id = upload_and_publish_asset(
            token,
            cover_path,
            title=f"Historia {num} — {cover_path.name}",
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
            "categoria": {LOCALE: "Historia"},
        }

        print(f"Ep {num}: upsert entry slug={slug}…", flush=True)
        upsert_podcast_entry(token, slug, fields_payload)
        print(f"Ep {num}: OK publicado.", flush=True)
        time.sleep(0.35)

    print("Listo.")


if __name__ == "__main__":
    main()
