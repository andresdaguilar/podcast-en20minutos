# Podcast en 20 Minutos

Repositorio de trabajo para la producción de la serie de podcasts **En 20 Minutos**: episodios pensados en formato breve (alrededor de veinte minutos), con guiones, material para plataformas y flujo de audio/video.

## Propósito

Este proyecto concentra **cuatro líneas editoriales** en carpetas separadas:

| Carpeta     | Contenido (orientación) |
|------------|-------------------------|
| `Filosofia/` | Ideas, autores y debates de la filosofía |
| `Historia/`  | Relatos y procesos históricos |
| `Libros/`    | Obras y conceptos de literatura / no ficción |
| `Mitologia/` | Mitos, dioses y narrativas clásicas |

Cada episodio vive en su propia carpeta numerada (por ejemplo `Filosofia/022 - …`). Ahí suele haber script, blog, descripciones para redes, imágenes de portada y archivos de audio en distintas etapas (raw, enhanced, completo, etc.).

## La app web (`podcast-web/`)

Es una aplicación **Next.js** que corre en local y actúa como **panel de producción** sobre el mismo árbol de carpetas del repo:

- **Escaneo**: lee el disco, detecta episodios y actualiza un JSON con el estado de cada uno (script, blog, audio, imágenes, video, publicación).
- **Edición**: abre y guarda `Script.md`, `Blog.md`, textos en inglés y `descriptions.json` por episodio.
- **Modo grabación** (solo guion): vista de lectura amplia para narrar frente al micrófono; en Chrome de escritorio permite grabar, subir y convertir a MP3 en la carpeta del episodio (vía API y `ffmpeg` en el servidor local).
- **Generación**: orquesta `ffmpeg` para audio completo (intro + narración + outro) y video a partir del cover y el audio final.

La app **no** sustituye el DAW ni el hosting del podcast: organiza el material y automatiza pasos repetitivos mientras los archivos “fuente” siguen viviendo en Git.

### Cómo ejecutarla

Requisitos: **Node.js**, **ffmpeg** instalado y accesible en el `PATH` (para generación de audio/video y conversión de grabaciones).

```bash
cd podcast-web
npm install
npm run dev
```

Abre la URL que indica la consola (por defecto [http://localhost:3000](http://localhost:3000)). El servidor Next.js debe tener permiso de lectura/escritura sobre las carpetas del repo (está pensado para uso en tu máquina, no como SaaS público).

## Estructura útil del repo

- **`Filosofia/`, `Historia/`, `Libros/`, `Mitologia/`** — Episodios y, en muchos casos, carpeta `000 …` con recursos comunes (intros, plantillas, etc.).
- **`podcast-web/`** — Código del dashboard y rutas API.
- **`.gitignore`** — Excluye secretos (`.env`), medios muy pesados según reglas (por ejemplo WAV grandes de plantillas GarageBand, raw de ciertos MP3, MP4) para no romper límites de Git/GitHub.

## Scripts de ayuda

En varias carpetas de podcast hay scripts Python (por ejemplo generación de blogs o descripciones) documentados en los propios archivos o en recursos `000 …`. El repo también incluye utilidades en `scripts/` para flujos de Git (por ejemplo commits por carpeta de episodio).

---

Si colaborás en el proyecto, conviene acordar convenciones de nombres de archivo (portadas `F###B`, `F###Y`, etc.) y correr **Escanear carpetas** en la app después de mover o renombrar episodios.
