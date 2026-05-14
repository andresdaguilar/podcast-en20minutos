#!/usr/bin/env python3
"""Genera Blog.md desde Script.md: limpia cierres de podcast, añade Excerpt y pull quotes."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def strip_podcast_noise(text: str) -> str:
    """Elimina párrafos típicos de cierre/apertura del podcast."""
    lines = text.splitlines()
    out: list[str] = []
    for line in lines:
        s = line.strip()
        if re.search(
            r"^Bienvenidos a Historia en 20 minutos|"
            r"^Gracias por escuchar Historia|"
            r"^Eso es todo por hoy|"
            r"^Nos vemos en el próximo|"
            r"^Si te gustó este episodio|"
            r"^Recap rápido|^Recap intermedio|^Recap final|"
            r"^hasta acá llegamos con este episodio|"
            r"^Si este episodio te resultó interesante, suscribite|"
            r"^Nos escuchamos la semana que viene",
            s,
            re.I,
        ):
            continue
        if s == "## **Cierre**" or s == "## Cierre":
            break
        out.append(line)
    body = "\n".join(out).strip()
    body = re.sub(r"^#\s+#\s+", "# ", body, flags=re.M)
    # Frases incrustadas en un párrafo
    body = re.sub(
        r"\s*Bienvenidos a Historia en 20 minutos[^.]*\.",
        "",
        body,
        flags=re.IGNORECASE,
    )
    body = re.sub(
        r"\s*Gracias por escuchar Historia[^.]*\.",
        "",
        body,
        flags=re.IGNORECASE,
    )
    body = re.sub(
        r"\s*Eso es todo por hoy[^.]*\.",
        "",
        body,
        flags=re.IGNORECASE,
    )
    body = re.sub(
        r"\s*Nos vemos en el próximo[^.]*\.",
        "",
        body,
        flags=re.IGNORECASE,
    )
    return body


def ensure_excerpt_and_title(body: str, excerpt: str, title_md: str) -> str:
    """Prepend **Excerpt:** y asegura un H1 al inicio del cuerpo narrativo."""
    body = body.lstrip()
    # Si ya empieza con **Excerpt**, no duplicar
    if body.startswith("**Excerpt:**"):
        parts = body.split("\n", 2)
        head = parts[0]
        rest = "\n".join(parts[1:]).lstrip()
    else:
        head = f"**Excerpt:** {excerpt}"
        rest = body
    # Si la primera línea del resto es H1, reemplazar por title_md
    lines = rest.splitlines()
    if lines and lines[0].startswith("#"):
        # usar nuestro título unificado
        lines[0] = title_md
        rest = "\n".join(lines)
    else:
        rest = title_md + "\n\n" + rest
    return f"{head}\n\n---\n\n{rest}"


def insert_after_first_separator(body: str, insertion: str) -> str:
    idx = body.find("\n---\n")
    if idx == -1:
        return body + "\n\n---\n\n" + insertion
    pos = idx + len("\n---\n")
    return body[:pos] + "\n" + insertion.strip() + "\n\n" + body[pos:]


def insert_pull_quotes(body: str, quotes: list[str]) -> str:
    if not quotes:
        return body
    blocks = []
    for q in quotes:
        blocks.append(f'*"{q}"*\n')
    return insert_after_first_separator(body, "\n".join(blocks).strip())


def write_description(folder: Path, text: str) -> None:
    desc_path = folder / "descriptions.json"
    if desc_path.exists():
        return
    t = text.strip()
    if len(t) > 250:
        t = t[:247].rsplit(" ", 1)[0] + "..."
    desc_path.write_text(
        json.dumps({"es": t + "\n"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    jobs = [
        (
            "021 - Las Cruzadas",
            "De 1099 a 1291, cruzados y musulmanes disputaron Jerusalén y el Mediterráneo oriental. Fue fe, política y negocio; dejó odios, comercio y un contacto cultural entre mundos.",
            "# **Las Cruzadas: Jerusalén, sangre y ambición en el medievo**",
            [
                "Deus vult — Dios lo quiere — fue el grito que lanzó a Europa hacia Tierra Santa.",
                "Fe, ambición y dinero. Ese fue el cóctel de fondo de toda la empresa cruzada.",
            ],
        ),
        (
            "022 - La guerra Fria",
            "Cuatro décadas de tensión entre EE. UU. y la URSS: alianzas, crisis nuclear y guerras por delegación. Historias como Stanislav Petrov muestran lo cerca que estuvo el planeta del abismo.",
            "# **La Guerra Fría: dos imperios, un planeta al borde**",
                [
                "Calculó que si Estados Unidos atacaba de verdad, mandaría cientos de misiles, no cinco. Apostó a que era una falla del sistema. Tenía razón.",
                "El Telón de Acero era la metáfora perfecta: una cortina que dividía Europa en dos bloques.",
            ],
        ),
        (
            "023 - El nacimiento de ciudades",
            "De Uruk a hoy: por qué nos concentramos en ciudades, qué inventó la escritura para la burocracia, y cómo el excedente agrícola hizo posible la complejidad urbana.",
            "# **El nacimiento de las ciudades: del campamento al millón de habitantes**",
            [
                "Los primeros textos escritos de la humanidad no son poemas ni himnos religiosos. Son listas de bienes. Recibos. Inventarios de grano.",
                "Una ciudad no es simplemente mucha gente junta. Una ciudad es un sistema de coordinación de recursos y trabajo a escala.",
            ],
        ),
        (
            "024 - La Torre Eiffel",
            "Ícono de París nacido de un boceto en servilleta, odiado por intelectuales, salvado por la radio y ligado al escándalo de Panamá. La historia humana detrás del hierro.",
            "# **La Torre Eiffel: escándalo, ingeniería y contradicción**",
            [
                "La Torre Eiffel no fue idea de Gustave Eiffel. Fue idea de dos ingenieros que trabajaban en su empresa.",
                "El dinero del escándalo que destruyó su nombre fue lo que salvó su mayor creación.",
            ],
        ),
        (
            "025 - El Imperio Bizantino",
            "Constantinopla mantuvo viva la herencia romana mil años más que Roma occidental: Justiniano, las murallas, el fuego griego, el cisma y la caída de 1453.",
            "# **El Imperio bizantino: mil años entre Roma y Estambul**",
            [
                "Prefiero morir como emperatriz que vivir como fugitiva —le dijo Teodora a Justiniano en la revuelta Niká.",
                "El último emperador romano muriendo como soldado anónimo entre las ruinas de la ciudad que Constantino había fundado once siglos antes.",
            ],
        ),
        (
            "026 - La Comuna de Paris",
            "En 1871, París experimentó 72 días de gobierno radical; Versalles lo aplastó en la Semana Sangrienta. Ideas y violencia que marcaron la izquierda moderna.",
            "# **La Comuna de París: setenta y dos días que asustaron al mundo**",
            [
                "Si no soy cobarde, ustedes tampoco deberían serlo. Mátenme —Louise Michel ante el tribunal.",
                "Fue más muertos en una semana que durante todo el Terror de la Revolución Francesa, que había durado más de un año.",
            ],
        ),
        (
            "027 - La carrera Espacial",
            "Del Sputnik al Apolo 11: cohetes, propaganda y ciencia; genios y sombras (Von Braun, Koroliov, tragedias de Apolo 1 y Soyuz 1) en la carrera entre superpotencias.",
            "# **La carrera espacial: de la paranoia nuclear a la Luna**",
            [
                "Elegimos ir a la Luna no porque sea fácil, sino porque es difícil.",
                "Un pequeño paso para un hombre, un gran salto para la humanidad.",
            ],
        ),
        (
            "028 - El Sacro Imperio Romano Germanico",
            "Ni sacro, ni romano, ni imperio —y aun así duró 844 años. Desde Carlomagno y los electores hasta Westfalia y Napoleón; legado en Alemania y en la idea europea.",
            "# **El Sacro Imperio Romano Germánico: el frankenstein político de Europa**",
            [
                "El Sacro Imperio Romano Germánico no es ni sacro, ni romano, ni un imperio. —Voltaire",
                "Bella gerant alii, tu felix Austria nube. Que los demás hagan guerras; vos, Austria feliz, casate.",
            ],
        ),
    ]

    for folder_name, excerpt, title, quotes in jobs:
        folder = ROOT / folder_name
        script = folder / "Script.md"
        if not script.exists():
            print(f"Skip (no Script): {folder_name}")
            continue
        blog_path = folder / "Blog.md"
        body = strip_podcast_noise(script.read_text(encoding="utf-8"))
        body = ensure_excerpt_and_title(body, excerpt, title)
        body = insert_pull_quotes(body, quotes)
        blog_path.write_text(body.strip() + "\n", encoding="utf-8")
        print(f"OK Blog: {folder_name}")
        write_description(folder, excerpt)

    # Descripciones para episodios con guion/blog pero sin descriptions.json
    extra_desc = [
        ("001 Revolucion Francesa", "La toma de la Bastilla, la Declaración de los Derechos y el Terror: cómo Francia del XVIII inventó la política moderna entre ideal y violencia."),
        ("003 Servicio Postal", "De mensajeros imperiales al sello y la tarifa plana: cómo el correo barato transformó estados, negocios y la vida cotidiana."),
        ("004 Invasiones Inglesas", "Las expediciones británicas al Río de la Plata: fracaso militar, mitos nacionales y el mapa que dejaron las invasiones."),
        ("005 Vikingos", "Más que barbudos de película: comercio, colonias y Estado vikingo entre Escandinavia, Rusia y el Atlántico."),
        ("006 Canal de Panama", "Sueño francés, escándalo y obra estadounidense: el corte geopolítico que unió dos océanos a costa humana colosal."),
        ("008 - Alejangro Magno", "De Macedonia al mundo helenístico: campañas, fusión cultural y un imperio que se fragmentó al morir su joven rey."),
        ("009 - La guerra de Vietnam", "Guerrilla, intervención estadounidense y costo humano: por qué la superpotencia no pudo ganar un conflicto asimétrico."),
        ("010 - La caida de Constantinopla", "1453: cañones, murallas y el fin de Bizancio; el legado otomano en el umbral entre medieval y moderno."),
        ("011 - Los Borgia", "Poder, rumor y Renacimiento en la Roma papal: la familia que condensa intrigas de la Italia del XV."),
        ("012 - El Cumpleaños", "Un episodio que usa el cumpleaños como lente para hablar de historia, memoria y cómo contamos el pasado."),
        ("013 - El Feudalismo", "Señores, vasallos y campesinos: el orden europeo entre catástrofe romana y ciudad mercantil."),
        ("014 - La revolucion industrial", "Vapor, fábricas y ferrocarril: el salto de Inglaterra que redefinió trabajo, ciudad y desigualdad global."),
        ("015 - El Imperio Otomano", "De beylik anatoliano a potencia multicontinental: religión, ejército y administración en seis siglos de imperio."),
        ("016 - La independencia de Estados Unidos", "Ilustración, guerra y constitución: cómo las trece colonias se convirtieron en república y ejemplo hemisférico."),
        ("017 - La unificacion de Italia", "Risorgimento, Garibaldi y el papel de las potencias: de fragmentación peninsular a nación unida con deudas internas."),
        ("018 - El Imperio Persa", "Aqueménidas y legado iraní: tolerancia fiscal, caminos reales y el espejo oriental del mundo clásico."),
        ("019 - El Antiguo Egipto", "Nilo, faraones y burocracia milenaria: continuidad política y religiosa en la civilización del río."),
        ("020 - El Imperio Inca", "Tawantinsuyu: quipus, mit'a y carreteras andinas; expansión, Templo del Sol y la conquista española."),
    ]
    for folder_name, blurb in extra_desc:
        folder = ROOT / folder_name
        if not folder.is_dir():
            continue
        if (folder / "descriptions.json").exists():
            continue
        write_description(folder, blurb)
        print(f"OK descriptions: {folder_name}")


if __name__ == "__main__":
    main()
