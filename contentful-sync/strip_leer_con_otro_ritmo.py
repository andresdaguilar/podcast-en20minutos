#!/usr/bin/env python3
"""
Elimina el bloque inyectado «Leer con otro ritmo» y los párrafos puente asociados
de Blog.md en Filosofía y Libros (idempotente).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

FIL_BRIDGE = [
    "Leer filosofía en lugar de consumirla solo en audio cambia el contrato con las ideas: podés volver atrás, discutir con el párrafo que te incomoda y marcar la frase que antes pasaba volando cuando el reloj del episodio apuraba.",
    "En formato escrito, el ritmo lo definís vos. Eso tiene costo: no hay voz que te lleve de la mano. La ganancia es poder sostener una objeción un poco más larga, revisar un ejemplo y ver si el autor realmente respondió la duda.",
    "Una ventaja del texto es que las distinciones —las que en viva voz suelen comprimirse— pueden detenerse hasta que realmente las entendiste, aunque sea solo para rechazarlas después con argumentos propios.",
    "Si algo de lo anterior resonó, probá cerrar los ojos un momento y formular en una sola oración qué tesis estarías dispuesto a defender; el archivo completo es la defensa, pero esa oración es la brújula.",
    "Las filosofías que importan no solo informan: reordenan prioridades. Por eso a veces molestan más que entretener; en texto, esa molestia es más fácil de reconocer sin confundirla con el tono de quien habla.",
    "No hace falta estar de acuerdo con cada eslabón del argumento. El ejercicio honesto es aislar el eslabón que falla, explicar por qué, y ver si el resto del edificio sigue en pie.",
    "Muchas objeciones filosóficas nacen de tomar un ejemplo como si fuera la prueba entera. En lectura lenta se nota cuándo un caso solo ilustra y cuándo pretende demostrar.",
    "Cuando un autor apela a la historia, preguntate si el relato es representativo o si es una ancla narrativa: en ambos casos sirve, pero no siempre para lo mismo.",
    "Si al terminar una sección sentís que falta un paso, puede ser culpa del texto o del pensamiento original: anotar el hueco ya es avanzar.",
    "La repetición, en podcast, acompaña al oído; en blog, conviene condensar. Por eso este texto prioriza variaciones y retomadas cuando aportan matices, no cuando solo marcan tiempo.",
    "Traducir ideas densas a decisiones concretas del día a día es donde mucha filosofía se gana o se pierde; el puente es personal y por eso incompleto, pero debe ser consciente.",
    "Si comparás este recorrido con el guion original, vas a encontrar formulaciones afinadas al ojo: mismas tesis, distinta superficie de contacto con el lector.",
    "Un hipotético interlocutor que lleva la contra es útil incluso cuando no está citado: sirve para separar lo que demuestra el texto de lo que solo sugiere.",
    "Cuando el autor cita fuentes o épocas lejanas, el gesto filosófico a veces es mostrar continuidades inesperadas; la prueba suele estar en cómo se actualiza el problema, no en la erudición como trofeo.",
    "Antes de cerrar, conviene mirar hacia atrás y nombrar una idea que antes te parecía obvia y ahora ya no: ese retroceso es señal de que leíste de verdad.",
]

LIB_BRIDGE = [
    "Un libro contiene ritmo propio; este artículo retoma el hilo del guion para que puedas frenarte en un ejemplo, releer una tesis o saltar a la biografía del autor sin depender del minuto del audio.",
    "Leer sobre un libro no reemplaza al libro, pero sí ordena qué buscar cuando lo abras: personajes, tesis, objeciones y el momento histórico en que se escribió.",
    "En texto podés contrastar una cita con tu experiencia sin pausar a nadie: subrayar, anotar al margen, o simplemente dudar más tiempo del que permite un pase en limpio oral.",
    "Las novelas y ensayos suelen tener un ‘capítulo invisible’ que solo aparece cuando ves la obra entera; acá resaltamos uno o dos hitos para que no se pierdan.",
    "Si algo te suena a autoayuda barata o a dogma, frená: muchos clásicos populares mezclan oro y arena; separar ambos es parte del oficio del lector.",
    "El contexto editorial importa: año de publicación, crisis, moda intelectual. En podcast eso a veces se comprime; acá podés volver cuando quieras.",
    "Los libros de no ficción viven de un argumento; los de ficción, de escenas. Este recorrido intenta honrar cuál de los dos venís siguiendo.",
    "Antes de cerrar el navegador, probá formular en voz baja qué te llevás: un hábito, una imagen, una pregunta incómoda. Ese es el verdadero ‘takeaway’.",
    "Releer una anécdota del autor puede cambiar el tono emocional del conjunto; no es sentimentalismo, es atención sostenida.",
    "Cuando el original está en otro idioma, las traducciones son mediadoras: si una frase suena rara, a veces es la costura, no la idea.",
    "Si comparás con el audio, notarás cortes y afianzamientos distintos; misma historia, distinta superficie.",
    "Una buena objeción vale más que un resumen complaciente: guardá la tuya para el café o para la reseña que escribas después.",
    "El cierre del libro no siempre cierra la discusión; a veces solo deja la puerta entreabierta para tu propia continuación intelectual.",
]

SUF_FIL = re.compile(
    r"\s+Eso rima con preguntas que «[^»]+» deja abiertas a propósito\.\s*$"
)
SUF_LIB = re.compile(r"\s+Esto enlaza con el libro tratado en «[^»]+»\.\s*$")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def _bridge_set() -> set[str]:
    return {_norm(b) for b in FIL_BRIDGE + LIB_BRIDGE}


BRIDGE_SET = _bridge_set()


def _base_paragraph(chunk: str) -> str:
    t = _norm(chunk)
    t = SUF_FIL.sub("", t)
    t = SUF_LIB.sub("", t)
    return _norm(t)


def _is_bridge_paragraph(chunk: str) -> bool:
    s = chunk.strip()
    if not s:
        return True
    if s.lstrip().startswith("#"):
        return False
    return _base_paragraph(chunk) in BRIDGE_SET


HEADING = "## Leer con otro ritmo"


def strip_once(text: str) -> tuple[str, bool]:
    idx = text.find(HEADING)
    if idx == -1:
        return text, False

    head = text[:idx].rstrip()
    head = re.sub(r"\n*---\s*$", "", head).rstrip()

    tail = text[idx + len(HEADING) :].lstrip("\n")
    parts = tail.split("\n\n")
    i = 0
    while i < len(parts) and _is_bridge_paragraph(parts[i]):
        i += 1
    remainder = "\n\n".join(parts[i:]).lstrip("\n")

    out = head
    if remainder:
        out = out + "\n\n" + remainder
    return out, True


def strip_markdown(text: str) -> str:
    while True:
        text, ch = strip_once(text)
        if not ch:
            return text


def main() -> None:
    touched = 0
    for base in ("Filosofia", "Libros"):
        root = REPO_ROOT / base
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("Blog.md")):
            raw = path.read_text(encoding="utf-8")
            if HEADING not in raw:
                continue
            new = strip_markdown(raw)
            if new != raw:
                path.write_text(new.rstrip() + "\n", encoding="utf-8")
                touched += 1
                print(f"OK {path.relative_to(REPO_ROOT)}")
    print(f"Actualizados: {touched} archivos")


if __name__ == "__main__":
    main()
