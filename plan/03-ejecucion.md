# 03 · Plan de ejecución

## 1. Estructura del repositorio

```
canal-youtube/
├── .env.example · .gitignore · README.md
├── requirements.txt              # venv principal
├── requirements-tts.txt          # venv .venv-tts (Chatterbox, torch 2.6.0)
├── config/
│   ├── canal.yaml                # idioma, resolución, fps, rutas (ComfyUI, rhubarb, venvs), proveedores LLM
│   ├── estilo.json               # prefijo de estilo, paleta del canal, semillas, tamaños
│   ├── reparto.yaml              # personajes: rig, voz de referencia, colores, en_pantalla
│   └── expresiones.yaml          # expresión → (cejas, pupilas, párpado, boca por defecto)
├── pipeline/
│   ├── run.py                    # COMANDO ÚNICO desatendido: fondos → voces → lipsync → render → mezcla → paquete
│   ├── estado.py                 # checkpoints por paso (estado.json): reanuda donde se quedó
│   ├── guion/
│   │   ├── llm.py                # cliente único (openai) con cadena Gemini → Groq → Ollama
│   │   ├── generar_guion.py      # ficha → fuentes → escaleta → actos → pase crítico → storyboard
│   │   ├── fuentes.py            # extractos de Wikipedia y URLs que añadas tú
│   │   ├── validar.py            # valida storyboard.json contra el esquema
│   │   └── prompts/*.md          # plantillas de prompt versionadas
│   ├── assets/
│   │   ├── comfy.py              # cliente HTTP/WebSocket de ComfyUI
│   │   ├── generar_fondos.py     # genera solo los fondos que no existan en la biblioteca
│   │   ├── estilo_plano.py       # cuantización a la paleta + refuerzo de contorno
│   │   └── workflows/fondo_zimage_api.json
│   ├── personajes/
│   │   ├── exportar_rig.py       # SVG de Inkscape → PNG por capa + rig.json (pivotes)
│   │   ├── rig.py                # carga del rig, poses, expresiones, visemas
│   │   └── hoja_contacto.py      # PNG con todas las expresiones y visemas para revisar
│   ├── voz/
│   │   ├── tts_worker.py         # se ejecuta DENTRO de .venv-tts; genera un WAV por línea
│   │   ├── tts.py                # lanza el worker y aplica el control de calidad con Whisper
│   │   └── diseñar_voces.py      # (uso único, en .venv-voces) voces de referencia con Qwen3-TTS
│   ├── sincronia/
│   │   ├── lipsync.py            # Rhubarb por línea → visemas.json (respaldo: reglas ES)
│   │   └── tiempos.py            # faster-whisper → palabras con tiempo, SRT y tasa de error
│   ├── render/
│   │   ├── linea_tiempo.py       # storyboard + audio → eventos por fotograma
│   │   ├── animacion.py          # parpadeo, pupilas, cejas, gestos, respiración, cámara
│   │   ├── compositor.py         # dibuja un fotograma (Pillow + numpy)
│   │   ├── render.py             # multiproceso por tramos → FFmpeg → concat
│   │   └── audio_mix.py          # voces + música (ducking) + efectos + loudnorm
│   ├── publicar/
│   │   ├── miniatura.py          # 3 variantes de 1280×720
│   │   ├── metadatos.py          # títulos, descripción con capítulos y créditos, etiquetas
│   │   ├── paquete.py            # carpeta subida/ + checklist.md
│   │   └── subir_api.py          # PLAN B (no se usa en v1): videos.insert por OAuth
│   └── utils/ (log.py, notificar.py, rutas.py)
├── assets/
│   ├── personajes/<id>/<id>.svg · export/*.png · rig.json
│   ├── fondos/<id>.png + fondos.csv          # biblioteca reutilizable
│   ├── musica/<ambiente>/*.mp3 + creditos.csv
│   ├── sfx/*.wav + creditos.csv
│   └── voces/<id>_ref.wav
├── episodios/registro_tramas.csv           # tema, conflicto y desenlace de cada episodio (para no repetir plantilla)
├── episodios/epXXX/
│   ├── ficha.md · fuentes/ · guion.md · storyboard.json · estado.json · informe.md
│   ├── audio/ · lipsync/ · render/        # intermedios (se borran tras aprobar)
│   └── subida/                            # lo que subes a YouTube
├── tests/                                 # pytest: esquema, rig, lipsync, compositor, mezcla
├── tools/                                 # check_entorno.py, benchmarks.py (binarios como rhubarb, ignorados por git)
└── plan/                                  # esta carpeta (FASE 1)
```

**Flujo semanal (2 comandos):**

1. `python -m pipeline.guion ep001` (5-15 min con API) → **revisas y editas `guion.md`** (añades tu opinión y corriges hechos) → `python -m pipeline.guion ep001 --solo-storyboard`.
2. `python -m pipeline.run ep001` → **desatendido** (te vas a clase) → al volver, revisas `informe.md` y `render/final.mp4` → subes `subida/` a mano.

`run.py` es **reanudable**: cada paso escribe su checkpoint en `estado.json`, de modo que un corte de luz o un error a mitad no obliga a empezar de cero. Si falla, guarda el error en `informe.md` y sigue con lo que pueda. La notificación al móvil (ntfy.sh, sin cuenta) es opcional.

## 2. Esquema JSON del storyboard

El archivo completo, validable, está en [`plan/data/storyboard.schema.json`](data/storyboard.schema.json). Estructura:

| Nivel | Campos |
|---|---|
| Episodio | `episodio`, `idioma`, `titulo_trabajo`, `duracion_objetivo_min`, `reparto[]`, `escenas[]` |
| Escena | `id`, `acto`, `fondo{id, prompt, hora}`, `camara{tipo, zoom_inicio, zoom_fin, foco}`, `musica{ambiente, volumen_db}`, `personajes[]`, `lineas[]`, `transicion_salida`, `duracion_estimada_s` |
| Personaje en escena | `id`, `posicion`, `escala`, `mirando`, `movimiento`, `expresion_inicial` |
| Línea | `id`, `personaje` (su voz sale de `reparto.yaml`), `texto`, `expresion`, `intensidad_voz`, `gesto`, `mirada`, `reacciones[]`, `sfx[]`, `pausa_despues_s`, y `audio`, `duracion_s`, `visemas` (**los rellena el pipeline**) |

Ejemplo mínimo:

```json
{
  "episodio": "ep001", "idioma": "es", "titulo_trabajo": "La casa del final de la calle",
  "duracion_objetivo_min": 14, "reparto": ["narrador", "lucia", "marcos"],
  "escenas": [{
    "id": "s01", "acto": 1,
    "fondo": {"id": "calle_suburbio_noche", "prompt": "quiet suburban street, one old house at the end, street lamps", "hora": "noche"},
    "camara": {"tipo": "zoom_lento", "zoom_inicio": 1.0, "zoom_fin": 1.08, "foco": "centro"},
    "musica": {"ambiente": "misterio", "volumen_db": -22},
    "personajes": [{"id": "lucia", "posicion": "centro_izquierda", "mirando": "derecha", "movimiento": "entra_izq"}],
    "lineas": [
      {"id": "s01_l01", "personaje": "narrador", "texto": "Nadie en el barrio se acercaba a esa casa. Nadie, excepto Lucía.", "expresion": "neutral"},
      {"id": "s01_l02", "personaje": "lucia", "texto": "¿Otra vez esa luz en la ventana?", "expresion": "sospecha",
       "gesto": "senalar", "mirada": "derecha", "intensidad_voz": 0.6, "sfx": [{"id": "viento_suave"}]}
    ],
    "transicion_salida": "fundido"
  }]
}
```

## 3. APIs, cuentas y pasos manuales

| # | Cuenta / API | Para qué | Límite gratuito verificado | ¿Tarjeta? | Paso manual tuyo |
|---|---|---|---|---|---|
| 1 | Google Cloud + **YouTube Data API v3** (clave de API) | Investigación de nicho (FASE 1) | 100 búsquedas/día + 10.000 unidades/día; se reinicia a medianoche, hora del Pacífico (~08:00 en Canarias) | No | **Ahora:** crear la clave (pasos en el chat) y guardarla en `.env` |
| 2 | **Canal de YouTube** (cuenta de marca recomendada) | Publicar | Hasta 15 min por vídeo **sin verificar el teléfono** | No | Crear el canal + **verificar por SMS** (obligatorio para vídeos de 10-20 min y para miniaturas personalizadas) |
| 3 | **Google AI Studio** (clave de Gemini) | Guiones | No publicado: se ve en AI Studio (**NO VERIFICADO**) | No | Crear la clave en aistudio.google.com y guardarla en `.env` (`GEMINI_API_KEY`) |
| 4 | **Groq** | Respaldo de guiones | gpt-oss-120b: 30 RPM / 1.000 RPD / 8K TPM / 200K TPD | No | Crear una cuenta en console.groq.com → API key → `.env` (`GROQ_API_KEY`) |
| 5 | Hugging Face (opcional) | Descargar modelos | Público sin cuenta para los modelos elegidos (**se confirma en el Hito 0**) | No | Solo si algún modelo resulta estar restringido |
| 6 | NVIDIA (app) | Driver ≥610 para NVENC | — | No | **Actualizar el driver** (paso de sistema: lo haces tú) |
| 7 | OAuth de escritorio + auditoría de la API | Subida automática (**plan B**, no en la v1) | 100 subidas/día; vídeos privados hasta la auditoría | No | Nada por ahora |
| 8 | AdSense (en el futuro) | Cobrar al entrar en el YPP | — | No | Cuando llegues a los umbrales (ver 01-nicho.md) |

Ninguna pide tarjeta. Las claves siempre van en `canal-youtube/.env` y **nunca en el chat**.

**Tu trabajo creativo (no automatizable, y conviene que no lo sea):** diseñar los personajes en Inkscape, elegir las voces (escucha a ciegas), aprobar el estilo de fondos, descargar ~30 pistas y ~50 efectos de la Biblioteca de audio de YouTube, y escribir la ficha y revisar el guion de cada episodio.

## 4. Hoja de ruta (FASE 2)

Las horas son de trabajo conjunto (tú + yo) y son **estimaciones**. Las tuyas se marcan aparte.

| Hito | Tarea | Archivos | Comando de prueba | «Hecho» cuando… | Tiempo |
|---|---|---|---|---|---|
| **H0** Entorno | Driver ≥610, `git init`, 3 venvs, ComfyUI portable + modelos, Rhubarb, Inkscape | `requirements*.txt`, `tools/check_entorno.py`, `config/canal.yaml` | `python tools/check_entorno.py` | Todo en verde: GPU, NVENC, ComfyUI responde, Rhubarb y Whisper funcionan, cada venv importa lo suyo | 2-3 h (+ descargas, ~30 GB) |
| **H1** Benchmarks reales | Medir Z-Image (s/imagen, VRAM), Chatterbox vs Qwen3-TTS (RTF, VRAM, escucha a ciegas), Whisper, Rhubarb y render multiproceso + NVENC | `tools/benchmarks.py`, `plan/data/benchmarks.json` | `python tools/benchmarks.py --todo` | Los JSON tienen cifras reales y **tú eliges el motor y el acento de voz** | 2-3 h |
| **H2** Storyboard | Esquema, validador y un episodio de ejemplo de 1 min hecho a mano | `pipeline/guion/validar.py`, `episodios/ep000/storyboard.json`, `tests/test_storyboard.py` | `pytest tests/test_storyboard.py` | El ejemplo válido pasa y 5 casos inválidos fallan con un mensaje claro | 1-2 h |
| **H3** Guionista | LLM en varios pasos con fuentes, memoria y pase crítico | `pipeline/guion/*.py`, `prompts/*.md` | `python -m pipeline.guion ep000 --tema "…" --min 12` | `guion.md` con ±10 % de las palabras objetivo, `storyboard.json` válido y **tu nota ≥7/10 al leerlo** | 4-6 h |
| **H4** Estilo y fondos | Workflow de ComfyUI por API, prefijo de estilo, paleta y biblioteca | `pipeline/assets/*`, `config/estilo.json` | `python -m pipeline.assets.generar_fondos --prueba 10` | **Apruebas** 8 de 10 fondos en la hoja de contacto; s/imagen anotado | 3-5 h |
| **H5** Personajes | Plantilla del rig + 1 personaje completo + exportador + hoja de contacto | `assets/personajes/*`, `pipeline/personajes/*` | `python -m pipeline.personajes.exportar_rig assets/personajes/lucia/lucia.svg` | Hoja con 9 expresiones y 9 visemas sin piezas descolocadas, **aprobada por ti** | 2-3 h (yo) + **6-10 h tuyas de dibujo** |
| **H6** Voces | Voces de referencia, TTS por línea, control de calidad con Whisper | `pipeline/voz/*`, `assets/voces/*` | `python -m pipeline.voz.tts ep000` | 20 líneas con tasa de error ≤5 % (umbral **a calibrar**) y voces distinguibles | 3-4 h |
| **H7** Lip sync | Rhubarb por línea + respaldo por reglas | `pipeline/sincronia/*` | `python -m pipeline.sincronia.lipsync ep000 --previa` | Clip de 30 s donde la boca va a tiempo, **aprobado por ti** | 2-3 h |
| **H8** Compositor y animación | Rig en pantalla, parpadeo, pupilas, cejas, gestos, cámara, transiciones, multiproceso | `pipeline/render/*` | `python -m pipeline.render.render ep000 --hasta 60` | 60 s fluidos; fps medido; un vídeo de 15 min estimado en ≤45 min | 6-10 h |
| **H9** Audio final | Mezcla con *ducking*, efectos, loudnorm y SRT | `pipeline/render/audio_mix.py`, `pipeline/sincronia/tiempos.py` | `python -m pipeline.render.audio_mix ep000` | Sin saturación, música audible pero debajo de la voz y SRT sincronizado | 2-3 h |
| **H10** Orquestador | `run.py` con checkpoints, reanudación, logs e informe | `pipeline/run.py`, `pipeline/estado.py` | `python -m pipeline.run ep000` (y matarlo a mitad + relanzar) | El piloto de 3 min sale de principio a fin **sin intervención** y se reanuda tras matarlo | 3-4 h |
| **H11** Publicación | Miniaturas, títulos, descripción con capítulos y créditos, paquete y checklist | `pipeline/publicar/*` | `python -m pipeline.publicar.paquete ep000` | La carpeta `subida/` está completa y la miniatura pesa menos de 2 MB | 2-3 h |
| **H12** Canal + episodio 1 | Creas y verificas el canal; ficha, guion revisado y ejecución desatendida de 10-20 min | `episodios/ep001/*` | `python -m pipeline.run ep001` | El render completo termina en ≤4 h y **tú apruebas** el vídeo final | 1 día (gran parte desatendida) |
| **H13** Subida | Subida manual en Studio con la checklist | `episodios/ep001/subida/checklist.md` | — | **Primer vídeo subido** (público o programado) | 30 min |

**Total estimado:** 35-50 h de trabajo conjunto + 10-16 h de dibujo tuyo. A un ritmo de estudiante (~10-12 h/semana), son **3-5 semanas hasta el primer vídeo**. Es una estimación.

## 5. Tiempo de render por vídeo (15 min) con tu GPU

| Paso | Estimación | Base | Estado |
|---|---|---|---|
| Fondos (15-25 nuevos; menos según crece la biblioteca) | 5-15 min | 5-10 s/imagen a 1024², más el reescalado | **NO VERIFICADO** → H1 |
| TTS (15 min de audio + regeneraciones) | 5-25 min | RTF 0,12 de un tercero; el peor caso supone RTF 1 + 30 % de reintentos | **NO VERIFICADO** → H1 |
| Control de calidad con Whisper | 2-3 min | 13 min de audio en 1 min 03 s en una RTX 3070 Ti (README oficial de faster-whisper) | Fuente oficial, GPU distinta |
| Rhubarb (phonetic) | 5-15 min | Sin datos | **NO VERIFICADO** → H1 |
| Render de vídeo | 42 min (1 proceso, CPU) → ~10-15 min (5 procesos + NVENC) | **10,6 fps medidos hoy** en tu PC | 1 proceso medido; multiproceso → H1 |
| Mezcla, miniaturas y paquete | ~5 min | — | Estimación |
| **Total** | **≈35 min a 1 h 50 min** | | Cabe en la ventana de 2-4 h con margen |

Los pasos de GPU van en serie (ComfyUI → TTS → Whisper) para no competir por los 16 GB. ComfyUI se cierra antes del TTS.

## 6. Riesgos principales y plan B

| Riesgo | Probabilidad | Impacto | Mitigación | Plan B |
|---|---|---|---|---|
| **Voz** poco natural en español o con acento no deseado | Media | Alto (la retención depende de la voz) | Escucha a ciegas en H1, pack *Spain Spanish*, intensidad por línea, diccionario de pronunciación | Qwen3-TTS o MOSS-TTS; o **tu voz para el narrador** y TTS solo para los personajes |
| **Coherencia visual** de los fondos | Media | Medio | Prefijo fijo, paleta forzada, biblioteca reutilizable, ControlNet | LoRA de estilo; o fondos vectoriales hechos en Inkscape para los lugares recurrentes |
| **Cuota de la API** en la investigación | Baja | Bajo | 88 de 100 búsquedas, caché y reanudación al día siguiente | Reducir a 1 duración por consulta (44 búsquedas) |
| **Cuota y límites del LLM** (Gemini no publica los suyos) | Media | Medio | Cadena Gemini → Groq → Ollama | Ollama local con `gemma4:12b` (más lento y algo peor, pero gratis y sin límites) |
| **Monetización: contenido no auténtico** | Media | **Muy alto** | Personajes y diseño propios, tu ficha y opinión en cada guion, historias distintas (nunca la misma plantilla), revisión humana | Si YouTube rechaza el YPP: corregir y volver a solicitar pasados 30 días (**NO VERIFICADO**, comprobar al llegar) |
| **Umbral del YPP doblado** (8.000 h desde el 01-02-2027) | Segura | Alto | Vídeos de 15-20 min con buena retención, listas de reproducción y series | Ver la cuenta en 01-nicho.md: es un plan de 12+ meses, no de semanas |
| **Tiempo de render > ventana** | Baja | Medio | Multiproceso, NVENC y caché | Renderizar de noche; bajar a 24 fps |
| **Disco lleno** (108 GB libres) | Media | Alto | Presupuesto de 45-50 GB y borrado automático de intermedios | Mover ComfyUI y modelos a un disco externo |
| **Errores factuales** en el guion | Media | Medio | Fuentes obligatorias en nichos con hechos y pase crítico | Elegir un nicho de ficción (menos riesgo) |
| **Cambios de terceros** (Groq, Gemini, YouTube) | Media | Medio | Un solo cliente LLM intercambiable; nada depende de una sola API | Ollama; subida manual |
| **Fiscalidad** al cobrar | — | — | Fuera del alcance de este plan | Consultar en una gestoría antes de activar AdSense (**NO VERIFICADO**) |

## 7. Checklist antes de subir cada vídeo

La copia por episodio se genera en `subida/checklist.md`.

**Guion y contenido**
- [ ] He revisado el guion entero y he añadido mi ficha u opinión (no es una plantilla genérica).
- [ ] La historia o estructura no repite la de vídeos anteriores (*"same situation over and over… same outcome"* está prohibido para monetizar).
- [ ] Los hechos tienen fuente en `fuentes/`, y lo especulativo se presenta como tal.
- [ ] No hay difamación de personas reales, gore explícito ni contenido sensible innecesario (afecta a los anuncios).

**Vídeo**
- [ ] He visto el vídeo completo: sin cortes de audio, bocas sincronizadas y sin piezas del rig descolocadas.
- [ ] `informe.md` no tiene líneas marcadas con tasa de error alta, o las he escuchado y están bien.
- [ ] La sonoridad es correcta: la música no tapa la voz.

**Derechos**
- [ ] Toda la música y los efectos salen de `assets/` con licencia anotada en `creditos.csv`.
- [ ] Los créditos Creative Commons están en la descripción (el pipeline los añade, pero compruébalo).
- [ ] No hay marcas, logos ni personajes de terceros en fondos ni miniaturas.

**Etiquetas y ajustes de Studio**
- [ ] **Uso de IA (Atributos):** «No» si todo es animado y de ficción; «Sí» si hay algo realista sobre personas o hechos reales.
- [ ] **Audiencia:** «No es contenido creado para niños» (salvo que realmente lo sea).
- [ ] Idioma del vídeo y de los subtítulos correcto; SRT subido.
- [ ] Categoría, etiquetas, capítulos (el primero en 0:00) y lista de reproducción.

**Miniatura y título**
- [ ] 3 miniaturas listas para *Probar y comparar* (requiere funciones avanzadas; si aún no las tienes, sube la mejor): legibles en pequeño y sin texto engañoso.
- [ ] El título (≤60 caracteres) cumple lo que promete el vídeo.
- [ ] La cuenta está verificada por teléfono (los vídeos de más de 15 min y las miniaturas personalizadas lo exigen).
