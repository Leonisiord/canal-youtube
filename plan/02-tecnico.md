# 02 · Plan técnico pieza por pieza

> Fecha de verificación: **01-10-2026**. Todo dato lleva su fuente. Lo que no he podido comprobar está marcado como **NO VERIFICADO** y tiene una prueba asignada en la FASE 2 (Hito 1, «benchmarks reales»).

## 0. Tu máquina (medido hoy, no supuesto)

| Componente | Valor | Cómo lo medí |
|---|---|---|
| GPU | RTX 4060 Ti, 16.380 MiB, driver 591.86, CUDA 13.1 | `nvidia-smi` |
| CPU / RAM | Ryzen 5 7600X (6 núcleos / 12 hilos) / 31 GiB | `Get-CimInstance` |
| Python | 3.11.9 (global, con torch 2.6.0+cu124, numpy, Pillow, requests, python-dotenv, google-api-python-client) | `pip list` |
| FFmpeg | 9.0.1 *full build* (gyan.dev), incluye `h264_nvenc`, `hevc_nvenc`, `av1_nvenc` | `ffmpeg -encoders` |
| Disco C: | **108 GB libres de 1,9 TB (95 % lleno)** | `df -h` |

**Dos problemas detectados al medir:**

1. **NVENC no funciona todavía.** Error real: *"Driver does not support the required nvenc API version. Required: 13.1 Found: 13.0 … minimum required Nvidia driver for nvenc is 610.00"*. Solución: actualizar el driver desde la app de NVIDIA. Ya existen el 610.62 (16-06-2026) y el 616.56 ([VideoCardz](https://videocardz.com/driver/nvidia-geforce-game-ready-616-56), [NVIDIA](https://www.nvidia.com/en-us/geforce/news/june-16-2026-geforce-game-ready-driver/)). Mientras tanto se codifica con CPU (`libx264`), que funciona.
2. **Espacio en disco.** El presupuesto de disco del proyecto es de unos 45 GB (ver tabla al final). Cabe, pero hay que usar variantes fp8 cuando existan y borrar los intermedios después de cada render.

**Benchmark de render medido hoy** (`plan/scripts/benchmark_render.py`, resultado en `plan/data/benchmark_render.json`): fondo + 3 personajes de 12 capas + zoom de cámara a 1920×1080 y 30 fps, con Pillow y libx264 en **un solo proceso**, da **10,6 fps**, es decir, **≈42 min para un vídeo de 15 min**. Con varios procesos en paralelo y NVENC debería bajar a ~10-15 min (**NO VERIFICADO**: se mide en el Hito 1).

---

## Resumen de herramientas

| # | Pieza | Elegida | Alternativa | Licencia de la elegida | ¿Uso comercial? |
|---|---|---|---|---|---|
| 1 | Guion y storyboard | Gemini API (capa gratuita) → Groq de respaldo, mediante un solo cliente `openai` | Ollama 0.35.0 + `gemma4:12b` en local | Términos de la API de Gemini | Sí (uso profesional) |
| 2 | Fondos | ComfyUI v0.38.0 + Z-Image Turbo (6B) + ControlNet Union | SDXL 1.0 + LoRA de estilo plano | ComfyUI GPL-3.0 · Z-Image Apache-2.0 · ControlNet Apache-2.0 | Sí |
| 3 | Personajes por capas | Inkscape 1.4.4 (SVG con grupos con nombre) + exportador Python | Rig 100 % programático en SVG | GPL-2.0+ (la herramienta; tus dibujos son tuyos) | Sí |
| 4 | Voces | Chatterbox Multilingual V3 / pack *Spain Spanish* (0.5B) | Qwen3-TTS 1.7B (Apache-2.0); Kokoro-82M si el idioma es inglés | MIT | Sí |
| 5 | Lip sync y tiempos | Rhubarb Lip Sync 1.14.0 + faster-whisper 1.2.1 | Reglas grafema→visema para español con tiempos de Whisper | MIT / MIT | Sí |
| 6 | Montaje y render | Compositor propio (Pillow + numpy, multiproceso) → FFmpeg | MoviePy 2.2.1 | Pillow 12.3.0: MIT-CMU · FFmpeg: LGPL/GPL según build | Sí |
| 7 | Música y efectos | Biblioteca de audio de YouTube | ACE-Step 1.5 (generación local, MIT) | Licencia de la biblioteca de audio de YouTube | Sí, en YouTube |
| 8 | Miniatura y título | Pillow (composición con assets propios) + LLM para títulos + *Probar y comparar* de Studio | — | — | Sí |
| 9 | Subida | **Manual en YouTube Studio** (paquete preparado por el pipeline) | API `videos.insert` (bloquea en privado sin auditoría) | — | — |

---

## 1. Guion largo y storyboard en JSON con LLM

**Elegida:** API de Gemini (capa gratuita) a través de su endpoint compatible con OpenAI. **Respaldo automático:** Groq. **Alternativa offline:** Ollama.

| Proveedor | Datos verificados | Fuente |
|---|---|---|
| Gemini API (gratuita) | Endpoint compatible con OpenAI `https://generativelanguage.googleapis.com/v1beta/openai/`, admite salida JSON estructurada (`response_format`); modelo del ejemplo oficial: `gemini-3.8-flash`. **Los límites gratuitos por modelo NO se publican**: *"can be viewed in Google AI Studio"*. Requisito: mayor de 18 años. **Para usuarios del EEE (España), los datos de la capa gratuita se tratan como en la de pago** (no se usan para mejorar productos). | [OpenAI compat.](https://ai.google.dev/gemini-api/docs/openai) (02-09-2026), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) (02-09-2026), [términos](https://ai.google.dev/gemini-api/terms) (28-04-2026) |
| Gemini: límites concretos | Webs de terceros dan cifras contradictorias (de ~20 a 1.500 peticiones/día según el modelo) → **NO VERIFICADO**. Lo comprobarás tú en `aistudio.google.com/rate-limit`. | [tinkerllm](https://tinkerllm.com/blog/gemini-api-free-tier-limits-rate-quotas/), [aifreeapi](https://www.aifreeapi.com/en/posts/gemini-api-free-tier-rate-limits) |
| Groq (plan gratuito) | `openai/gpt-oss-120b`: **30 RPM, 1.000 RPD, 8.000 TPM, 200.000 TPD**; Qwen 3.8 27B: los mismos límites | [console.groq.com/docs/rate-limits](https://console.groq.com/docs/rate-limits) (consultado el 01-10-2026) |
| Ollama (local) | v0.35.0 (28-09-2026); `gemma4:12b` ocupa 7,7-8,0 GB y tiene 256K de contexto | [GitHub](https://github.com/ollama/ollama/releases), [ollama.com/library/gemma4](https://ollama.com/library/gemma4) |

**Por qué un solo cliente:** Gemini, Groq y Ollama exponen la misma API de OpenAI, así que `pipeline/guion/llm.py` usa la librería `openai` (v3.22.1, Apache-2.0, [PyPI](https://pypi.org/project/openai/)) y solo cambia `base_url` y `model`. Si un proveedor falla o se queda sin cuota, pasa al siguiente.

**Cómo conseguir 10-20 min coherentes (guion en varios pasos):**

1. **Ficha del episodio** (la escribes tú en 5 líneas: tema, ángulo, qué opinas tú). Esto es lo que evita el «contenido no auténtico» (ver 01-nicho.md §4).
2. **Documentación** (en nichos con hechos reales): extractos de la API de Wikipedia o fuentes que tú añadas, guardados en `episodios/epXXX/fuentes/`. El LLM solo puede usar hechos de ahí.
3. **Escaleta:** gancho de 0 a 30 s, entre 5 y 8 actos con su objetivo de retención, giros y cierre. Se pide como JSON.
4. **Redacción acto por acto:** cada acto de 300-450 palabras recibe como contexto la escaleta y un resumen de lo ya escrito (la «memoria»). Así cada llamada queda por debajo de 8.000 tokens, el límite TPM de Groq.
5. **Pase crítico:** un segundo prompt revisa repeticiones, ritmo, coherencia de personajes y hechos sin fuente, y se reescribe lo marcado.
6. **Storyboard:** se convierte el guion en el JSON de `plan/data/storyboard.schema.json` y se valida con `jsonschema` 4.26.0 (MIT, [PyPI](https://pypi.org/project/jsonschema/)). Si no valida, se reintenta con el error como contexto.
7. **Duración:** palabras objetivo = minutos × ritmo de la voz elegida. El ritmo real se mide en el Hito 1; hasta entonces se usan ~150 palabras/min, valor **NO VERIFICADO**.

Coste estimado: 15-25 llamadas por guion, unos 60-90K tokens en total → cabe en los 200K tokens/día de Groq aunque Gemini no responda.

- **Instalación:** `pip install openai==3.22.1 jsonschema==4.26.0` (venv principal).
- **VRAM:** 0 con API; 8-10 GB con Ollama. Ollama no puede compartir la GPU con ComfyUI, pero no hace falta: el guion se genera *antes* de la ejecución desatendida.
- **Prueba:** `python -m pipeline.guion ep000 --tema "prueba"` genera `guion.md` con ±10 % de las palabras objetivo y un `storyboard.json` que pasa la validación.
- **Riesgos:** hechos inventados (por eso hay fuentes y revisión humana); límites de Gemini desconocidos (por eso Groq de respaldo); Groq puede cambiar su capa gratuita sin avisar.

---

## 2. Fondos con generación de imágenes local

**Elegida:** ComfyUI **v0.38.0** (29-09-2026, [release](https://github.com/comfyanonymous/ComfyUI/releases)), licencia **GPL-3.0**, como servidor local en `127.0.0.1:8188`, controlado por su API desde Python. Modelo: **Z-Image Turbo** (Alibaba Tongyi-MAI, 6B, 27-11-2025), licencia **Apache-2.0** ([HF](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)).

| Dato | Valor | Fuente |
|---|---|---|
| Archivos | `z_image_turbo_bf16.safetensors` → `models/diffusion_models/`, `qwen_3_4b.safetensors` → `models/text_encoders/`, `ae.safetensors` → `models/vae/` | [docs.comfy.org](https://docs.comfy.org/tutorials/image/z-image/z-image-turbo) |
| Tamaño en disco | ~21 GB en bf16 (DiT 12,3 + texto 8,0 + VAE 0,3) | [smeltcore](https://smeltcore.com/recipes/z-image-turbo-on-rtx-4060-ti-16gb-8-step-text-to-image-at-bf16-with-diffusers-or-comfyui/) (20-05-2026) |
| VRAM | *"fits comfortably within 16G VRAM consumer devices"* | Ficha oficial en HF |
| Ajustes | 9 pasos (8 pasadas DiT), **guidance 0**, así que los prompts negativos **no funcionan** y el estilo va en el prompt positivo | Ficha oficial en HF |
| Velocidad en 4060 Ti | "5-10 s por imagen 1024²", según una estimación sin medir | **NO VERIFICADO** ([smeltcore](https://smeltcore.com/recipes/z-image-turbo-on-rtx-4060-ti-16gb-8-step-text-to-image-at-bf16-with-diffusers-or-comfyui/) admite que no hay benchmark) |
| ControlNet | `Z-Image-Turbo-Fun-Controlnet-Union` (Canny, HED, Depth, Pose, MLSD), **Apache-2.0**, `control_context_scale` de 0,65-0,80 → `models/model_patches/` | [HF alibaba-pai](https://huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union) |

**Estilo fijo (sin LoRA en la v1).** Son cuatro capas de control:

1. **Prefijo de estilo fijo** en `config/estilo.json`, por ejemplo: «flat 2D cartoon background, bold clean dark outlines, flat colors, no gradients, simple geometric shapes, no people, no text, wide shot». El LLM solo escribe el contenido de la escena.
2. **Paleta forzada:** un posproceso con Pillow cuantiza cada fondo a una paleta fija del canal (~24 colores) y refuerza los contornos. Así, aunque el modelo se desvíe, el resultado sale plano y coherente. Es la pieza clave de la coherencia.
3. **ControlNet HED/Canny** para los lugares recurrentes, a partir de un boceto de composición.
4. **Biblioteca de fondos:** cada fondo aprobado se guarda con un ID (`casa_salon_noche`) y se reutiliza. Cuantos más episodios, menos imágenes nuevas.

Si la coherencia no basta, se entrena una **LoRA de estilo** (AI Toolkit) en un hito posterior. No es necesaria para el primer vídeo.

- **Resolución:** se genera a ~1344×768 (16:9) y se reescala ×2 con un modelo de reescalado dentro de ComfyUI para tener margen para el zoom de cámara (**se ajusta en el Hito 4**).
- **Instalación:** descargar `ComfyUI_windows_portable_nvidia.7z` (1,9 GB) de la release v0.38.0, descomprimir en `C:\IA\ComfyUI` (fuera del repo), poner los 3 modelos en sus carpetas y lanzar con `run_nvidia_gpu.bat`.
- **Prueba:** `python -m pipeline.assets.generar_fondos --prueba` genera 10 fondos, mide segundos por imagen y VRAM máxima, y crea una hoja de contacto para que tú la apruebes.
- **Alternativa:** SDXL base 1.0 (licencia CreativeML Open RAIL++-M, [HF](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0)) con una LoRA de estilo plano. Usa menos VRAM pero entiende peor los prompts. Hay que revisar el texto completo de la licencia antes de usarla.
- **Descartados por licencia:** FLUX.2 [klein] 4B. Según una fuente secundaria es "FLUX Non-Commercial" ([thundercompute](https://www.thundercompute.com/blog/best-open-source-image-generation-models)), **NO VERIFICADO en la licencia original**, así que no se usa.
- **Riesgos:** deriva de estilo entre fondos (mitigada con paleta y biblioteca), manos o texto raros en los fondos (se piden fondos sin personas ni texto) y disco (21 GB; buscar variante fp8 en el Hito 4).

---

## 3. Personajes por capas (sin que la IA los separe)

**Decisión:** los personajes **no se generan con IA en cada vídeo**. Se dibujan **una vez** como un *rig* vectorial, y por eso salen idénticos en todos los episodios. La IA solo se usa, si quieres, para bocetos de concepto que luego calcas.

**Herramienta:** Inkscape **1.4.4** (06-05-2026), licencia **GPL-2.0-or-later** ([Wikipedia](https://en.wikipedia.org/wiki/Inkscape)). Tus dibujos son tuyos, porque la GPL no afecta a lo que creas con ella.

**Cómo se construye un rig (plantilla común):**

```
personaje.svg
├── brazo_atras_I / brazo_atras_D (con antebrazo y 3 manos: abierta, puño, señalar)
├── cuerpo (ropa intercambiable)
├── cabeza
│   ├── pelo_atras
│   ├── cara
│   ├── ojo_I / ojo_D       → blanco, pupila, parpado (para parpadear)
│   ├── ceja_I / ceja_D
│   ├── boca_A … boca_H, boca_X   (9 visemas de Rhubarb)
│   └── pelo_delante
└── pivote_<parte>  (circulitos invisibles que marcan el eje de giro)
```

- **Partes compartidas:** las bocas, ojos y cejas se dibujan **una sola vez** y todos los personajes las reutilizan, cambiando solo colores (piel, labios) mediante variables de color en el SVG. Cada personaje nuevo solo necesita cabeza, pelo, cuerpo y ropa propios.
- **Exportación automática:** `pipeline/personajes/exportar_rig.py` lee el SVG, exporta cada grupo a PNG con la línea de comandos de Inkscape (`inkscape personaje.svg --export-id=boca_A --export-id-only --export-type=png ...`) y genera un `rig.json` con los pivotes leídos del XML.
- **Expresiones:** no son dibujos nuevos, sino combinaciones de ángulo de cejas, tamaño de pupilas, párpado y boca. Hay 9: neutral, feliz, triste, enfadado, sorprendido, asustado, pensativo, preocupado y sospecha. Se definen en `config/expresiones.yaml`.

**Cuántos hacen falta para el primer vídeo:**

| Elemento | Cantidad | Esfuerzo estimado (tuyo) |
|---|---|---|
| Plantilla base (cuerpo, set de bocas, ojos y cejas, manos) | 1 | 6-10 h la primera vez |
| Personajes fijos del reparto (presentador o narrador + 2-3 recurrentes) | 3-4 | 2-3 h cada uno |
| Extras (cambio de pelo, ropa y colores sobre la plantilla) | los que pida el guion | ~10 min cada uno |
| Visemas | 9 (A-H + X) | incluidos en la plantilla |
| Poses de brazos | 4-8 (reposo, señalar, brazos arriba, mano a la barbilla…) por rotación | incluidas |

Son estimaciones de esfuerzo, no datos medidos.

- **Prueba:** `python -m pipeline.personajes.exportar_rig assets/personajes/lucia/lucia.svg` genera los PNG, `rig.json` y una **hoja de contacto** con las 9 expresiones y los 9 visemas, que revisas tú.
- **Alternativa:** un rig 100 % programático (formas generadas por código). Es más rápido de crear y totalmente consistente, pero menos expresivo. Sirve también para los extras.
- **Descartado:** generar cada parte con IA y recortarla. Las piezas salen con estilos distintos y no encajan entre sí.
- **Riesgo:** es la pieza que más tiempo humano consume. Es inversión única, y además es tu diseño original, lo cual ayuda frente a la política de contenido no auténtico.

---

## 4. Voces locales (varias voces)

**Elegida:** **Chatterbox** (Resemble AI), licencia **MIT** ([GitHub](https://github.com/resemble-ai/chatterbox)), paquete `chatterbox-tts` **0.1.7** (26-03-2026, [PyPI](https://pypi.org/project/chatterbox-tts/)).

| Dato | Valor |
|---|---|
| Modelos | Multilingual V3 (0,5B, 23 idiomas, incluido español) + *Single Language Pack* con ajustes dedicados para **Spain Spanish** y **Latam Spanish**; Turbo (350M, solo inglés) |
| Clonación | Clip de referencia de unos 10 s por voz; tiene control de intensidad emocional (`exaggeration`), útil para expresiones |
| Marca de agua | Todo el audio lleva la marca de agua inaudible «Perth» de Resemble AI |
| Requisitos | Python ≥3.10 y **`torch==2.6.0` fijado** (choca con ComfyUI, por eso va en un venv propio) |
| Velocidad en 4060 Ti | RTF 0,12 según [gigagpu](https://gigagpu.com/tts-latency-benchmarks/) (citado por un buscador, la página da 403) → **NO VERIFICADO** |

**¿De dónde salen las voces de referencia sin clonar a nadie?** De **Qwen3-TTS VoiceDesign** (1,7B, **Apache-2.0**, 22-01-2026, `pip install -U qwen-tts`, 10 idiomas incluido español, [GitHub](https://github.com/QwenLM/Qwen3-TTS)). Genera una voz a partir de una descripción («hombre de 50 años, voz grave, ritmo pausado»). Se graba un clip de 10-15 s por personaje, una sola vez, y Chatterbox lo usa como referencia. Así no se imita a ninguna persona real. La otra opción es tu propia voz para el narrador (con tu consentimiento, claro).

**Si el idioma elegido es inglés:** Kokoro-82M (Apache-2.0) tiene voces de calidad A (`af_heart`) y es rapidísimo. En español solo tiene 3 voces (`ef_dora`, `em_alex`, `em_santa`) sin nota de calidad publicada ([VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)), así que no lo uso para español.

**Control de calidad automático:** cada línea generada se transcribe con faster-whisper y se compara con el texto (tasa de error de palabras). Si supera un umbral, se regenera con otra semilla hasta 3 veces. Las que fallan quedan anotadas en el informe final para que las revises.

- **Instalación** (venv `.venv-tts`): `py -3.11 -m venv .venv-tts` y después `.venv-tts\Scripts\pip install chatterbox-tts==0.1.7`. Qwen3-TTS va en otro venv (`.venv-voces`, se usa una sola vez) porque fija `transformers==4.57.3`.
- **VRAM:** **NO VERIFICADO**, se mide en el Hito 1. Por tamaño (0,5B) se esperan pocos GB.
- **Prueba (Hito 1):** las mismas 5 frases con 3 motores (Chatterbox Spain Spanish, Chatterbox Multilingual y Qwen3-TTS), escucha a ciegas por tu parte, más RTF y VRAM medidos.
- **Riesgos:** acento latino o castellano no deseado (Qwen3-TTS tiende al latinoamericano según [spokio](https://spokio.pro/chatterbox-vs-qwen3-tts-technical-comparison), **NO VERIFICADO**), alucinaciones en frases largas (control con Whisper y frases de menos de 400 caracteres) y pronunciación de nombres propios (diccionario de reemplazos fonéticos).
- **Otras opciones verificadas:** MOSS-TTS (Apache-2.0, 31 idiomas, diálogo multihablante con MOSS-TTSD de 8B, más pesado, [GitHub](https://github.com/OpenMOSS/MOSS-TTS)).
- **Descartadas por licencia no comercial** (de memoria, **NO VERIFICADO hoy**): XTTS-v2 (Coqui Public Model License), F5-TTS (pesos CC-BY-NC) y Fish Speech/OpenAudio (CC-BY-NC-SA). No hace falta verificarlas porque no se van a usar.

---

## 5. Sincronización labial y tiempos

**Lip sync:** **Rhubarb Lip Sync v1.14.0** (03-04-2025), licencia **MIT** ([GitHub](https://github.com/DanielSWolf/rhubarb-lip-sync)). Hay binario para Windows (`Rhubarb-Lip-Sync-1.14.0-Windows.zip`, 87 MB).

- Formas de boca: 6 básicas (A-F) y 3 extendidas (G, H, X). Salida en JSON.
- **Reconocedores:** `pocketSphinx` para inglés y **`phonetic` para otros idiomas** (*"usually less precise"*). Con `--dialogFile` se le pasa el texto de la línea, lo que mejora el resultado.
- Comando: `rhubarb -f json --extendedShapes GHX -r phonetic --dialogFile linea.txt -o linea.json linea.wav`.
- Se procesa **línea a línea** (archivos cortos) y en paralelo.

**Tiempos de palabra:** **faster-whisper 1.2.1** (31-10-2025), licencia **MIT** ([GitHub](https://github.com/SYSTRAN/faster-whisper)), `word_timestamps=True`. Benchmark oficial: 13 min de audio en **1 min 03 s** (large-v2, fp16, 4,5 GB de VRAM) en una RTX 3070 Ti, o en 17 s con `batch_size=8`. Sirve para:

1. Subtítulos `.srt` para subir a YouTube.
2. El control de calidad del TTS (sección 4).
3. Animación secundaria: subir las cejas en palabras enfáticas o en «?» y «!».

- **Alternativa al lip sync:** el español se escribe casi como se pronuncia, así que un mapeo de letras a visemas, repartido con los tiempos de palabra de Whisper, es un respaldo fiable si Rhubarb con `phonetic` queda mal.
- **Instalación:** descomprimir Rhubarb en `tools/rhubarb/` y `pip install faster-whisper==1.2.1` (venv principal).
- **Prueba:** un clip de 30 s renderizado con la boca superpuesta que tú revisas, más el tiempo de Rhubarb por minuto de audio (**NO VERIFICADO**, se mide en el Hito 1).
- **Riesgos:** la precisión del modo `phonetic` en español (mitigada con el respaldo por reglas) y conflictos de cuDNN de faster-whisper en Windows (si pasa, se ejecuta en CPU con int8, que es más lento pero funciona).

---

## 6. Montaje y render

**Elegida:** un **compositor propio** en Python (Pillow + numpy) que genera fotogramas en bruto y los envía por tubería a FFmpeg. Los motivos:

- Control total de las capas, pivotes y animación procedural, que es justo lo que necesita el rig.
- Ya está medido en tu PC: **10,6 fps en un proceso** (benchmark de hoy).
- Se paraleliza fácil: el vídeo se divide en tramos, cada proceso renderiza uno y FFmpeg los concatena sin recodificar (`-f concat -c copy`).

**Animación automática (sin keyframes a mano):**

| Elemento | Cómo |
|---|---|
| Boca | Visemas de Rhubarb durante sus líneas; X (reposo) el resto del tiempo |
| Parpadeo | Aleatorio cada 2-6 s, cerrar y abrir en 3 fotogramas |
| Pupilas | Miran al que habla, o la `mirada` del storyboard, más microsacadas aleatorias |
| Cejas | Según la expresión; se suben en palabras enfáticas (Whisper) |
| Cabeza | Pequeño balanceo según la energía (RMS) del audio |
| Brazos | El `gesto` del storyboard, con interpolación suave (*easing*) |
| Respiración | Escalado sinusoidal leve del cuerpo |
| Cámara | `estatica`, `zoom_lento` (Ken Burns), paneos, primer plano automático del que habla y `sacudida` para sustos |
| Transiciones | Corte, fundido y fundido a negro |

- **Codificación:** `h264_nvenc` (tras actualizar el driver a ≥610) o `libx264 -preset medium -crf 20` (CPU, ya verificado). Salida 1080p a 30 fps.
- **Mezcla de audio** con FFmpeg: voces con sus pausas, música con *ducking* bajo la voz (`sidechaincompress`), efectos y normalización final de sonoridad (`loudnorm`).
- **Prueba:** `python -m pipeline.render.render ep000 --desde 0 --hasta 60` renderiza 60 s y anota los fps reales con N procesos.
- **Alternativa:** MoviePy 2.2.1 (MIT, [PyPI](https://pypi.org/project/moviepy/)) es más simple de escribir, pero componer decenas de capas transformadas por fotograma es más lento (**NO VERIFICADO**, no se ha medido). Blender sería más potente, pero la curva de aprendizaje es mucho mayor.
- **Riesgos:** tiempo de render (mitigado con multiproceso, NVENC y caché de fondos) y RAM (cada proceso necesita sus capas, ~1-2 GB estimados → 5 procesos caben en 31 GB).

---

## 7. Música y efectos libres de derechos

**Elegida:** **Biblioteca de audio de YouTube** (Studio → Biblioteca de audio). Cita de la ayuda oficial: *"Copyright-safe music and sound effects downloaded from the Audio Library won't be claimed by a rights holder through the Content ID system"*, y se pueden monetizar en el YPP. Las pistas con licencia Creative Commons **exigen el crédito en la descripción** ([ayuda de YouTube](https://support.google.com/youtube/answer/3376882?hl=en)).

- **Proceso:** descargas a mano, una sola vez, ~30 pistas clasificadas por ambiente (tensión, misterio, calma…) y ~50 efectos, y las guardas en `assets/musica/<ambiente>/` con un `creditos.csv`. El pipeline elige la pista según el `ambiente` del storyboard y **añade los créditos a la descripción automáticamente**.
- **Alternativa:** **ACE-Step 1.5** (licencia **MIT**, desde 4 GB de VRAM, portable para Windows, 02-04-2026, [GitHub](https://github.com/ace-step/ACE-Step-1.5)) para generar pistas instrumentales propias.
- **Evitar como fuente principal:** Pixabay. Su resumen de licencia no aclara qué pasa con Content ID en YouTube ([pixabay](https://pixabay.com/service/license-summary/)), y YouTube avisa de que solo garantiza lo que sale de su propia biblioteca.
- **Prueba:** una mezcla de 60 s con música, efectos y voz, revisada a oído.

---

## 8. Miniatura y título

- **Miniatura** (1280×720): Pillow compone el fondo del episodio, un personaje en expresión extrema (sorpresa o miedo) y 2-4 palabras con contorno grueso. Se generan **3 variantes** automáticamente.
- **Título y descripción:** el LLM propone 10 títulos (≤60 caracteres, con curiosidad pero sin mentir) y tú eliges 3. La descripción incluye un resumen, capítulos (con tiempos reales del audio), créditos de música y fuentes.
- ***Probar y comparar*** de Studio: prueba hasta **3 variantes de título y/o miniatura**, solo en ordenador y solo para vídeos largos públicos, sin necesidad de estar en el YPP ([vidIQ](https://vidiq.com/blog/post/youtube-launches-new-thumbnail-testing-tool/), [Search Engine Journal](https://www.searchenginejournal.com/youtube-title-a-b-testing-rolls-out-globally-to-creators/562571/); son fuentes secundarias).
- **Requisitos de cuenta** (fuente oficial, [ayuda de YouTube](https://support.google.com/youtube/answer/9890437?hl=en)):
  - La verificación por **teléfono** (funciones intermedias) desbloquea las **miniaturas personalizadas** y los vídeos de **más de 15 min**.
  - Las **pruebas A/B** son una función **avanzada**: se consiguen con verificación por vídeo, con un documento de identidad o con historial del canal.
  - Si al principio no tienes funciones avanzadas, se sube 1 miniatura y las otras 2 se guardan para más adelante.
- **Prueba:** `python -m pipeline.publicar.miniatura ep000` genera 3 PNG de 1280×720 de menos de 2 MB.

---

## 9. Subida a YouTube

**Hechos verificados (documentación oficial de la YouTube Data API):**

| Tema | Dato | Fuente |
|---|---|---|
| Cuota diaria | **100 llamadas `search.list` + 100 llamadas `videos.insert` + 10.000 unidades** para el resto (cubos separados desde el 01-06-2026) | [Quota calculator](https://developers.google.com/youtube/v3/determine_quota_cost) (15-09-2026), [historial](https://developers.google.com/youtube/v3/revision_history) |
| Coste de una subida | **1 llamada del cubo de subidas**; `thumbnails.set` = **50 unidades** | ídem |
| Proyectos sin verificar | *"All videos uploaded via the videos.insert endpoint from unverified API projects created after 28 July 2020 will be restricted to private viewing mode."* Para quitarlo hay que pasar una **auditoría** | [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert) (14-09-2026) |
| ¿Se puede pasar a público a mano? | Según desarrolladores, **no**: el vídeo queda bloqueado en privado | **NO VERIFICADO oficialmente** ([upload-post](https://www.upload-post.com/youtube-api/)) |
| Auditoría | Formulario *YouTube API Services – Audit and Quota Extension*; sin plazo garantizado y puede denegarse | [Guía de auditorías](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits) |
| OAuth en modo «Testing» | *"…a publishing status of 'Testing' is issued a refresh token expiring in 7 days"* | [Google Identity](https://developers.google.com/identity/protocols/oauth2) |
| App sin verificar en producción | Muestra la pantalla de «app no verificada» y tiene un límite de 100 usuarios | [Google Cloud](https://support.google.com/cloud/answer/7454865?hl=en) |
| Vídeos de más de 15 min | *"By default, you can upload videos that are up to 15 minutes long"*. Para subir más largos hay que **verificar la cuenta por teléfono** | [Ayuda de YouTube](https://support.google.com/youtube/answer/71673?hl=en) |

**Decisión: subida manual (plan A).** El pipeline deja en `episodios/epXXX/subida/` el `video.mp4`, las 3 miniaturas, `titulos.txt`, `descripcion.txt` (con capítulos y créditos), `etiquetas.txt`, `subtitulos.srt` y `checklist.md`. Subirlo te lleva 5-10 min en Studio, y de todas formas ya revisas el vídeo antes.

**Plan B, si algún día quieres automatizarla:** cliente OAuth «de escritorio» con el alcance `youtube.upload`, consentimiento en modo «En producción» (para que el token no caduque a los 7 días) y solicitud de auditoría. Hasta que la aprueben, todo lo subido por API queda privado. Por eso no compensa para el primer vídeo.

**Etiqueta de contenido alterado o sintético:**

- En Studio: *"In the Attributes section, under 'AI use'"* → Sí o No ([ayuda](https://support.google.com/youtube/answer/14328491?hl=en)). Por API: `status.containsSyntheticMedia` en `videos.insert/update` ([docs](https://developers.google.com/youtube/v3/docs/videos)).
- **Cuándo es obligatoria:** cuando hay contenido **realista** que puede confundirse con algo real (alguien diciendo o haciendo lo que no hizo, eventos o lugares reales alterados, escenas realistas inventadas).
- **No es obligatoria** (ejemplos oficiales): una animación generada con IA dentro de un *"fully animated video"*, la ayuda de IA para guion, esquema, miniatura y título, y clonar **tu propia** voz.
- **En nuestro formato** (todo animado y personajes de ficción) **no hace falta marcarla**. Se marca «Sí» si algún vídeo incluye algo realista sobre personas o hechos reales. Esta regla va en la checklist.

---

## Entornos y disco

| Entorno | Qué contiene | Disco estimado |
|---|---|---|
| `.venv` (principal) | pipeline, openai, jsonschema, faster-whisper, Pillow, numpy | ~3 GB + 3 GB de modelos Whisper |
| `.venv-tts` | chatterbox-tts (torch 2.6.0) | ~6 GB + ~3 GB de modelos |
| `.venv-voces` (uso único) | qwen-tts VoiceDesign | ~6 GB + ~4 GB (se puede borrar después) |
| `C:\IA\ComfyUI` (portable) | ComfyUI + Z-Image Turbo + ControlNet | ~2 GB + ~23 GB |
| Assets y episodios | fondos, música, renders | ~1-2 GB por episodio (se borran los intermedios) |
| **Total** | | **≈45-50 GB de los 108 GB libres** |

Todas las cifras de tamaño son estimaciones salvo las citadas arriba (ComfyUI 1,9 GB y Z-Image 21 GB).
