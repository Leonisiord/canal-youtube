# Canal de YouTube automatizado · Investigación y plan técnico

Planificación y herramientas en Python para un canal *faceless* de vídeos animados por recortes, producido con herramientas gratuitas y ejecutado en local.

## Contenido
| Ruta | Qué es |
|---|---|
| `plan/00-resumen.md` | Resumen de una página: objetivo, hallazgos clave y hoja de ruta |
| `plan/01-nicho.md` | Método de investigación de nicho |
| `plan/02-tecnico.md` | Arquitectura técnica (guion, fondos, voces, lip sync, render) |
| `plan/03-ejecucion.md` | Plan de ejecución por fases |
| `plan/scripts/` | Scripts de Python: cliente de la YouTube Data API, recogida y análisis de datos, benchmark de render |
| `plan/data/` | Datos de referencia (RPM por fuente, criterios, esquema del storyboard) |

## Puesta en marcha
```
cp .env.example .env    # y rellena tus claves
```
Las claves de API van en `.env`, que está excluido en `.gitignore` y nunca se sube.

## Tecnología
Python, YouTube Data API v3, Gemini API, FFmpeg.
