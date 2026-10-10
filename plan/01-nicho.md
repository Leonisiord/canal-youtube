# 01 · Investigación de nicho

> **Estado (01-10-2026):** el método, los scripts, el RPM, la monetización y el sistema de puntuación están **terminados y verificados**. Las secciones 2, 3.1 y 6 (datos de YouTube, TOP 3 y 10 ideas) están **pendientes de ejecutar la recogida**, que necesita tu clave de la YouTube Data API.

## 1. Método

**Scripts** (en `plan/scripts/`, ejecutar desde `canal-youtube/`):

| Script | Qué hace |
|---|---|
| `config_nichos.json` | 11 nichos × 2 idiomas, con una consulta «general» y otra «animado» por idioma |
| `yt_cliente.py` | Cliente de la API con **caché en disco** (`plan/data/raw/`) y control de cuota; registra cada llamada en `plan/data/cuota_log.csv` |
| `recoger_datos.py` | `--simular` (plan sin gastar cuota), `--prueba` (1 búsqueda para validar la clave) y recogida completa |
| `analizar_nichos.py` | Métricas por nicho e idioma + puntuación ponderada + ranking con pesos alternativos |

**Cuota (verificada hoy, [documentación oficial](https://developers.google.com/youtube/v3/determine_quota_cost), actualizada el 15-09-2026):** desde el 01-06-2026, `search.list` tiene su **propio cubo de 100 llamadas al día** y el resto de métodos comparte **10.000 unidades al día**. La recogida necesita **88 búsquedas** (11 nichos × 2 idiomas × 2 consultas × 2 duraciones) y **~830 unidades**. Cabe en un día. Si se corta, se reanuda al día siguiente sin repetir llamadas (la cuota se reinicia a medianoche, hora del Pacífico, ≈08:00 en Canarias).

**Muestra:**

- Por cada consulta: `search.list` con `order=viewCount`, `publishedAfter` = hace 90 días, `videoDuration` = `medium` (4-20 min) y `long` (>20 min), `relevanceLanguage` = es/en, 50 resultados.
- Después, `videos.list` (duración, vistas, idioma) y `channels.list` (suscriptores).
- **Filtros:** duración real de 10-30 min, sin directos, publicado en la ventana e idioma correcto. El idioma se toma de `defaultAudioLanguage`; si falta, se estima con una heurística de palabras frecuentes.
- **Frecuencia de subida:** para los 15 canales con más vistas de cada combinación nicho e idioma se leen sus últimas 50 subidas (`playlistItems` + `videos.list`) y se cuentan los vídeos de más de 3 min en 90 días.

**Métricas por nicho e idioma** (`plan/data/metricas_nicho.csv`):

| Métrica | Para qué |
|---|---|
| Mediana de vistas y percentil 75 | Demanda |
| Mediana de vistas por día | Demanda corregida por la edad del vídeo |
| Mediana del ratio vistas/suscriptores | Si el algoritmo empuja a canales que no son enormes |
| Nº de canales con <10.000 subs y algún vídeo >100.000 vistas | **Canales pequeños que despegan** |
| % de vídeos de canales <10.000 subs | Hueco para los nuevos |
| Concentración: % de vistas de los 5 canales top | Si el nicho está dominado |
| Nº de canales distintos + `totalResults` medio | Saturación (`totalResults` es *"an approximation"*, máximo 1.000.000) |
| Mediana de vídeos largos por semana (canales top) y nº activos en los últimos 30 días | Frecuencia de subida de la competencia |
| Mediana de vistas de la consulta «animado» | Demanda específica del formato animado |

**Limitaciones (para leer los datos con honestidad):**

- `order=viewCount` devuelve **los más vistos**. Las medianas son de los mejores vídeos de cada nicho, no del vídeo típico. **Sirven para comparar nichos entre sí, no como expectativa de un canal nuevo.**
- La búsqueda de YouTube no es un censo: dos consultas por nicho son una muestra, no todo el nicho.
- Los suscriptores ocultos se excluyen del ratio.
- `relevanceLanguage` prioriza pero no filtra, por eso se filtra el idioma después.

## 2. Resultados por nicho e idioma

> **PENDIENTE:** se rellena al ejecutar `python plan/scripts/recoger_datos.py` y `python plan/scripts/analizar_nichos.py`.

## 3. Idioma: español vs inglés

### 3.1 Datos de YouTube (comparación de demanda y competencia)

> **PENDIENTE** (mismo script). Se compararán la mediana de vistas, el ratio vistas/suscriptores, los canales pequeños que despegan y la concentración por idioma.

### 3.2 RPM por idioma y nicho (fuentes citadas)

**RPM** = lo que cobra el creador por cada 1.000 vistas (después del reparto con YouTube). **CPM** = lo que paga el anunciante por cada 1.000 impresiones.

**Por idioma y país:**

| Dato | Valor | Fuente (fecha) |
|---|---|---|
| CPM por idioma | Inglés 13-20 USD · **español 1,10-5,61 USD** · alemán ~9,79 · francés ~6,76 | [AIR Media-Tech](https://air.io/en/audience-growth/what-are-the-most-popular-languages-on-youtube) (01-04-2026; datos de 3.000 canales) |
| CPM España | 2,807 USD | ídem |
| RPM por país | EE. UU. 10,81 · **España 3,91** · México 0,62 · Argentina 0,56 · Colombia 0,57 USD | [Lenostube](https://www.lenostube.com/en/youtube-cpm-rpm-rates/) (02-04-2026) |
| RPM por país | EE. UU. 7,50-12,00 · **España 3,00-5,50** · Reino Unido 5,50-8,50 USD | [FluxNote](https://fluxnote.io/guides/youtube-rpm-by-country) (2026, a partir de informes de MilX y Lenos) |

Ojo: el CPM de España que da Lenostube (14,22 USD) contradice el de AIR (2,807 USD). **Las fuentes no coinciden en el CPM. El RPM de España, en cambio, sí es coherente entre fuentes: entre 3 y 5,5 USD.**

**Conclusión sobre el RPM por idioma.** El RPM depende del **país del espectador**, no del idioma. Un canal en español tiene sobre todo audiencia latinoamericana (México, Colombia, Argentina…), con RPM de ~0,6 USD. Para puntuar uso un **factor de 0,20** respecto al inglés: es el ratio de CPM entre idiomas de AIR (3,36 / 16,5). El rango plausible va de 0,06 (audiencia casi toda latinoamericana) a 0,44 (audiencia casi toda de España). En inglés, a igual número de vistas, **se cobra unas 5 veces más**. Esto no decide el idioma por sí solo: falta compararlo con la competencia de cada idioma (§3.1).

**Por nicho (inglés, mayoritariamente benchmarks de EE. UU.):**

| Nicho | RPM (USD) | Tipo | Fuentes |
|---|---|---|---|
| Finanzas personales | 10-25 / 15-50 | directo | [OutlierKit](https://outlierkit.com/resources/youtube-niches-guide/) (13-09-2026) / [FluxNote](https://fluxnote.io/blog/youtube-rpm-by-niche-2026) (02-05-2026) |
| Negocios / emprendimiento | 8-19 | directo | OutlierKit |
| Historia / documental | 3-7 / 6-14 | directo | OutlierKit / FluxNote |
| True crime | 3-7 / 5-12 | directo | OutlierKit / FluxNote |
| Ciencia | 5-11 / 4-11 | directo / aproximación | FluxNote / OutlierKit |
| Terror (narración) | 4-8 | directo, **sin metodología** | [FluxNote, guía de terror](https://fluxnote.io/guides/scary-story-videos-guide) (12-06-2026) |
| Misterios | — | **NO VERIFICADO** (aproximación con historia y true crime) | — |
| Mitología | — | **NO VERIFICADO** (aproximación con historia) | — |
| Resúmenes de libros | — | **NO VERIFICADO** (aproximación con educación y automejora: 3-8 / 8-18) | — |
| Psicología | — | **NO VERIFICADO** (aproximación con automejora y salud: 3-8 / 4-11) | — |
| Historias de vida animadas | — | **NO VERIFICADO** (aproximación con animación infantil: 1-4) | FluxNote |

Todo está en bruto en `plan/data/rpm_fuentes.csv`. Avisos de las propias fuentes: son *"US planning benchmarks"* (OutlierKit), recopilados de *"public creator disclosures"* (FluxNote), y el **CPM del cuarto trimestre suele ser un 30-50 % más alto que el del primero** (OutlierKit).

## 4. Viabilidad de monetización

### 4.1 Requisitos del Programa de Socios (YPP), verificados

**Hoy** ([ayuda de YouTube](https://support.google.com/youtube/answer/72851?hl=en)): *"1,000 subscribers with 4,000 qualified watch hours in the last 12 months"* o *"1,000 subscribers with 10 million qualified Shorts views in the last 90 days"*. Además hay que:

- vivir en un país del YPP (**España sí**, según la [lista oficial](https://support.google.com/youtube/answer/7101720?hl=en));
- no tener avisos activos de las normas de la comunidad;
- tener la verificación en 2 pasos;
- tener acceso a funciones avanzadas;
- tener AdSense vinculado.

**⚠️ Cambio importante, ya anunciado.** El blog oficial de YouTube (10-08-2026, [blog.youtube](https://blog.youtube/news-and-events/youtube-partner-program-updates-2027-new-opportunities-earn/)) y la [ayuda](https://support.google.com/youtube/answer/12843009?hl=en) dicen que **desde el 01-02-2027** los canales nuevos necesitan *"8,000 qualified watch hours in the last 365 days, or 20M qualified Shorts views in the last 90 days, in addition to still needing 1k subscribers"*.

- Los canales que ya están en el YPP no se ven afectados.
- Los umbrales de *Fan Funding* y compras no cambian.
- Se añade un requisito de actividad: 1.000 h en 365 días, o 1M de vistas de Shorts en 90 días, o **2 vídeos largos o 5 Shorts cada 90 días**.

**Qué significa para ti.** Un canal que empieza en octubre de 2026 casi seguro no llegará a 4.000 h y 1.000 suscriptores antes del 01-02-2027, así que hay que **planificar para 8.000 horas**. Una cuenta orientativa, con suposiciones propias y no datos:

- 8.000 h = 480.000 min.
- Si un espectador ve de media unos 5 min de un vídeo de 15 min (**suposición**), hacen falta ~96.000 vistas en 12 meses.
- Con 52 vídeos, salen a una media de **~1.850 vistas por vídeo**.

Es alcanzable si el nicho tiene demanda, pero es un objetivo de **12 meses o más**, no de semanas. Por eso la puntuación da mucho peso a la demanda y a los «canales pequeños que despegan».

### 4.2 Política de contenido no auténtico (antes, «repetitivo»)

Políticas de monetización ([ayuda de YouTube](https://support.google.com/youtube/answer/1311392?hl=en), actualizada el 15-07-2025, cuando *repetitious content* pasó a llamarse *inauthentic content*). **No se puede monetizar:**

- *"Videos where characters are put in the same situation over and over again with the same outcome (i.e., using a highly similar storyline template across multiple videos)"*
- *"AI-generated content made with generic or unoriginal templates giving the impression of mass production without adding the creator's original, authentic insights or perspective"*
- *"Image slideshows, templated storylines, or scrolling text with minimal or no narrative"*

**Sí se permite:** usar la misma intro y el mismo cierre si *"the bulk of your content is different"*, y series con historias o enfoques distintos en cada episodio.

**Implicaciones para el diseño (ya incluidas en el plan):**

1. Un **reparto fijo de personajes está permitido**, pero **cada episodio necesita una historia y un desenlace distintos**. El pipeline guarda un registro de tramas y el pase crítico del guion compara con episodios anteriores.
2. Tu **aportación propia** es obligatoria: una ficha con tu ángulo y tu opinión en cada episodio, la revisión del guion, y personajes y estilo diseñados por ti.
3. Animación real (rig con lip sync y gestos), no presentaciones de imágenes.

Según medios del sector, la aplicación desde julio de 2025 ha incluido desmonetizaciones y cierres de canales de IA genérica ([milx](https://milx.app/en/news/why-youtube-just-suspended-thousands-of-ai-channels-and-how-to-protect-yours), fuente secundaria, sin cifras oficiales). **Es el riesgo n.º 1 del proyecto.**

### 4.3 Etiqueta de IA

Desarrollado en 02-tecnico.md §9: **no es obligatoria para vídeos totalmente animados de ficción**, ni para usar IA en el guion, la miniatura o el título ([ayuda de YouTube](https://support.google.com/youtube/answer/14328491?hl=en)).

## 5. Puntuación ponderada

Cada nicho e idioma recibe una nota de 0 a 10 en 6 criterios. Pesos en `plan/data/criterios_cualitativos.json`:

| Criterio | Peso | De dónde sale | Por qué este peso |
|---|---|---|---|
| **Demanda** | 25 % | API: log de la mediana de vistas + log de vistas/día (normalizado entre todos) | Con el umbral de 8.000 h, sin demanda no hay canal |
| **Oportunidad** (competencia inversa) | 20 % | API: canales pequeños que despegan + ratio vistas/subs + (100 − concentración top 5) | Mide si un canal **nuevo** puede entrar, no solo si hay vistas |
| **RPM** | 20 % | Fuentes citadas × factor de idioma (escala log) | Multiplica los ingresos; log porque ingresos = vistas × RPM |
| **Encaje con recortes** | 15 % | Juicio razonado (1-5) | Si el nicho pide 20 personajes nuevos por vídeo, el pipeline no escala |
| **Facilidad de guiones largos y buenos** | 10 % | Juicio razonado (1-5) | Riesgo de hechos falsos o de difamación con LLM |
| **Riesgo de monetización** (5 = bajo) | 10 % | Juicio razonado (1-5) con la política citada | Anuncios limitados y contenido no auténtico |

Los datos medibles (demanda, oportunidad y RPM) pesan el **65 %**, y el juicio, el **35 %**. Para comprobar que el resultado no depende de los pesos, el script calcula también el ranking con dos juegos alternativos: **«solo datos»** (35/35/30/0/0/0) y **«pipeline»** (15/15/10/30/15/15). Un nicho que queda arriba en los tres es una apuesta robusta.

**Notas cualitativas** (son juicio, no datos; el motivo de cada una está en el JSON):

| Nicho | Encaje | Guiones | Riesgo (5 = bajo) | Motivo resumido |
|---|---|---|---|---|
| Terror | 5 | 4 | 3 | Fondos atmosféricos y pocos personajes, ficción; anunciantes evitan el gore |
| Historia | 4 | 3 | 4 | Cada época pide vestuario; hay que verificar hechos |
| Misterios | 4 | 3 | 4 | Lugares + narrador; separar hechos de teorías |
| True crime | 3 | 2 | 2 | Personas reales (difamación) y anuncios limitados |
| Mitología | 3 | 4 | 4 | Dominio público, pero criaturas nuevas en cada mito |
| Resúmenes de libros | 5 | 3 | 3 | Reparto de arquetipos ideal; saturado de vídeos IA genéricos |
| Ciencia («qué pasaría si») | 4 | 3 | 4 | Reparto que reacciona; hay que verificar cifras |
| Finanzas | 4 | 2 | 4 | RPM alto; consejos que dependen del país y causan daño si fallan |
| Psicología | 5 | 3 | 4 | Situaciones cotidianas con reparto fijo; evitar pseudociencia |
| Negocios y biografías | 3 | 3 | 4 | Fundadores reales distintos en cada vídeo |
| Historias de vida animadas | 5 | 4 | 2 | El formato exacto, pero roza la cláusula de «misma situación» y el «hecho para niños» |

## 6. TOP 3, recomendación y 10 ideas de primer vídeo

> **PENDIENTE de los datos.** Se decidirá con `plan/data/puntuacion.csv`: TOP 3 por puntuación total, comprobando su estabilidad con los pesos alternativos, con argumentos, riesgos y 10 ideas concretas para el elegido.
