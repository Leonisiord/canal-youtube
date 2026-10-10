# 00 · Resumen (una página)

**Objetivo:** un canal faceless de vídeos animados por recortes, de 10-20 min, 1 a la semana, con 0 € y todo lo pesado en tu RTX 4060 Ti. Un comando lanza 2-4 h de trabajo desatendido; tú revisas el guion antes y el vídeo después.

**Estado (01-10-2026):** FASE 1 casi completa. Falta **ejecutar la investigación de nicho con datos**, que necesita tu clave de la YouTube Data API (5 min, pasos en el chat). Plan técnico y de ejecución: **terminados**.

## Lo más importante que he encontrado (verificado)

1. **El YPP se duplica el 01-02-2027:** los canales nuevos necesitarán **1.000 subs + 8.000 h** de visualización en 12 meses (hoy son 4.000 h). Fuente: [blog oficial de YouTube](https://blog.youtube/news-and-events/youtube-partner-program-updates-2027-new-opportunities-earn/), 10-08-2026. Es un proyecto de 12 meses o más.
2. **La política de «contenido no auténtico»** prohíbe monetizar personajes *"in the same situation over and over again with the same outcome"* y la IA con *"generic or unoriginal templates"*. Un reparto fijo sí está permitido, pero **cada historia debe ser distinta y llevar tu aportación**. Es el riesgo n.º 1.
3. **Subir por API no sirve en la v1:** los proyectos sin auditar dejan los vídeos **bloqueados en privado**. Se sube a mano en Studio (5-10 min) con un paquete preparado.
4. **Hay que verificar la cuenta por teléfono:** sin ella, máximo 15 min por vídeo y sin miniaturas personalizadas.
5. **La etiqueta de IA no es obligatoria** para vídeos totalmente animados de ficción.
6. **RPM:** inglés ≈ **5 veces** el español (factor 0,20, rango de 0,06 a 0,44 según el país del público).
7. **Tu PC:** el render de prueba da **10,6 fps en un proceso** (≈42 min por vídeo de 15 min, cabe en la ventana). **NVENC no funciona** hasta que actualices el driver a ≥610. **Solo quedan 108 GB libres** en C:, y el proyecto necesita unos 45-50.

## Arquitectura elegida (todo gratis y local salvo el guion)

| Pieza | Herramienta | Licencia |
|---|---|---|
| Guion y storyboard JSON | Gemini API gratuita → Groq → Ollama (un solo cliente) | — |
| Fondos | ComfyUI 0.38 + Z-Image Turbo + paleta forzada + biblioteca | GPL-3 / Apache-2 |
| Personajes | Rig vectorial en Inkscape 1.4.4, dibujado **una vez** (no IA por vídeo) | GPL (tus dibujos son tuyos) |
| Voces | Chatterbox (pack *Spain Spanish*) + voces de referencia de Qwen3-TTS VoiceDesign | MIT / Apache-2 |
| Lip sync y tiempos | Rhubarb 1.14 + faster-whisper 1.2.1 (con control de calidad automático) | MIT / MIT |
| Render | Compositor propio Pillow/numpy multiproceso → FFmpeg | — |
| Música | Biblioteca de audio de YouTube (sin reclamaciones de Content ID) | YouTube |
| Subida | Manual en Studio | — |

## Hoja de ruta (FASE 2)

H0 entorno → H1 benchmarks reales → H2 storyboard → H3 guionista → H4 fondos → H5 personajes → H6 voces → H7 lip sync → H8 render → H9 audio → H10 orquestador → H11 publicación → H12 episodio 1 → **H13 primer vídeo subido**.

Unas 35-50 h de trabajo conjunto + 10-16 h tuyas de dibujo → **3-5 semanas** a ritmo de estudiante (estimación). Render por vídeo: **≈35 min a 1 h 50 min** (los pasos de GPU están por medir en H1).

## Decisiones que te tocan

1. Aprobar **nicho e idioma** (cuando estén los datos).
2. **Motor y acento de voz** tras la escucha a ciegas (H1). ¿Tu voz para el narrador?
3. Nombre del canal y estilo de los personajes (lo diseñas tú).
4. Subida manual (recomendada) o auditoría de la API más adelante.
5. ¿Subtítulos quemados en el vídeo además del SRT?

## Dudas no resueltas (marcadas como NO VERIFICADO en los documentos)

- Límites reales de la capa gratuita de Gemini (Google no los publica; se ven en AI Studio).
- Velocidad y VRAM de Z-Image Turbo, Chatterbox y Rhubarb en tu GPU → se miden en H1.
- RPM de misterios, mitología, libros, psicología y storytime (sin fuente directa; uso categorías cercanas).
- Si un vídeo bloqueado en privado por la API se puede pasar a público a mano (los desarrolladores dicen que no).
- La fiscalidad de los ingresos de YouTube en Canarias (fuera de alcance: gestoría antes de activar AdSense).

**Documentos:** [01-nicho.md](01-nicho.md) · [02-tecnico.md](02-tecnico.md) · [03-ejecucion.md](03-ejecucion.md) · datos en `data/` · scripts en `scripts/`.
