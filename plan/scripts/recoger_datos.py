"""Recoge vídeos de 10-30 min de los últimos 90 días por nicho e idioma (YouTube Data API v3).

Uso (desde canal-youtube/):
    python plan/scripts/recoger_datos.py --simular   # muestra el plan y la cuota, no llama a la API
    python plan/scripts/recoger_datos.py --prueba    # 1 sola búsqueda para comprobar la clave
    python plan/scripts/recoger_datos.py             # recogida completa (reanudable gracias a la caché)

Salidas en plan/data/: busquedas.csv, videos.csv, canales.csv, frecuencia_canales.csv
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from yt_cliente import DATOS, ClienteYT, CuotaAgotada

AQUI = Path(__file__).resolve().parent
CONFIG = json.loads((AQUI / "config_nichos.json").read_text(encoding="utf-8"))
RUN_CONFIG = DATOS / "run_config.json"
IDIOMAS = ["es", "en"]

PALABRAS = {
    "es": {"de", "la", "que", "el", "en", "los", "las", "del", "por", "una", "para", "con",
           "es", "su", "se", "lo", "como", "más", "historia", "qué", "fue", "sin", "pero", "este"},
    "en": {"the", "of", "and", "to", "in", "is", "that", "for", "with", "was", "this", "you",
           "what", "how", "why", "story", "who", "from", "his", "her", "they", "are", "about"},
}


def fecha_corte():
    """Fija la fecha de inicio la primera vez para que la caché sirva al reanudar otro día."""
    if RUN_CONFIG.exists():
        return json.loads(RUN_CONFIG.read_text(encoding="utf-8"))
    ahora = datetime.now(timezone.utc).replace(microsecond=0)
    rc = {
        "fecha_ejecucion": ahora.isoformat(),
        "published_after": (ahora - timedelta(days=CONFIG["dias_atras"])).isoformat().replace("+00:00", "Z"),
    }
    DATOS.mkdir(parents=True, exist_ok=True)
    RUN_CONFIG.write_text(json.dumps(rc, indent=2), encoding="utf-8")
    return rc


def plan_busquedas():
    plan = []
    for nicho in CONFIG["nichos"]:
        for idioma in IDIOMAS:
            for tipo, consulta in nicho["consultas"][idioma].items():
                for dur in CONFIG["duraciones_api"]:
                    plan.append({"nicho": nicho["id"], "idioma": idioma, "tipo": tipo,
                                 "consulta": consulta, "duracion_api": dur})
    return plan


def segundos_iso(d):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return 0
    dias, h, mi, s = (int(x or 0) for x in m.groups())
    return dias * 86400 + h * 3600 + mi * 60 + s


def detectar_idioma(snippet):
    declarado = (snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage") or "")[:2].lower()
    if declarado:
        return declarado, "declarado"
    texto = f"{snippet.get('title', '')} {snippet.get('description', '')[:500]}".lower()
    if re.search(r"[ऀ-ॿ؀-ۿЀ-ӿ぀-ヿ一-鿿가-힯]", texto):
        return "otro", "heuristica"
    palabras = re.findall(r"[a-záéíóúñü]+", texto)
    puntos = {idi: sum(p in lista for p in palabras) for idi, lista in PALABRAS.items()}
    if max(puntos.values()) == 0:
        return "desconocido", "heuristica"
    return max(puntos, key=puntos.get), "heuristica"


def trocear(lista, n=50):
    for i in range(0, len(lista), n):
        yield lista[i:i + n]


def escribir_csv(nombre, filas):
    if not filas:
        return
    ruta = DATOS / nombre
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"  -> {ruta.relative_to(DATOS.parents[1])} ({len(filas)} filas)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simular", action="store_true", help="solo muestra el plan y la cuota estimada")
    ap.add_argument("--prueba", action="store_true", help="hace 1 búsqueda para validar la clave")
    args = ap.parse_args()

    plan = plan_busquedas()
    combos = len(CONFIG["nichos"]) * len(IDIOMAS)
    est_unidades = len(plan) + 80 + combos * CONFIG["canales_frecuencia_por_combo"] * 2
    print(f"Plan: {len(plan)} búsquedas (límite diario 100) y ~{est_unidades} unidades (límite 10.000).")
    if args.simular:
        for p in plan:
            print(f"  {p['nicho']:15} {p['idioma']} {p['tipo']:8} {p['duracion_api']:6} '{p['consulta']}'")
        return

    yt = ClienteYT()
    if not yt.tiene_clave():
        sys.exit("No encuentro YOUTUBE_API_KEY en canal-youtube/.env (mira .env.example).")
    rc = fecha_corte()
    corte = datetime.fromisoformat(rc["published_after"].replace("Z", "+00:00"))
    ref = datetime.fromisoformat(rc["fecha_ejecucion"])

    if args.prueba:
        plan = plan[:1]

    # 1) Búsquedas
    filas_busq, apariciones = [], defaultdict(set)   # (nicho, idioma, video_id) -> {tipos}
    try:
        for i, p in enumerate(plan, 1):
            r = yt.get("search", part="snippet", type="video", q=p["consulta"], order=CONFIG["orden"],
                       publishedAfter=rc["published_after"], videoDuration=p["duracion_api"],
                       relevanceLanguage=p["idioma"], maxResults=50)
            items = r.get("items", [])
            filas_busq.append({**p, "resultados": len(items),
                               "total_aprox": r.get("pageInfo", {}).get("totalResults", "")})
            for it in items:
                apariciones[(p["nicho"], p["idioma"], it["id"]["videoId"])].add(p["tipo"])
            print(f"  [{i}/{len(plan)}] {p['nicho']} {p['idioma']} {p['tipo']} {p['duracion_api']}: {len(items)} vídeos")
    except CuotaAgotada as e:
        print(f"\nCuota agotada ({e}). Vuelve a ejecutar mañana (la cuota se reinicia a medianoche, hora del Pacífico): "
              f"lo ya descargado está en caché y no se repite.")
        escribir_csv("busquedas.csv", filas_busq)
        return

    if args.prueba:
        print("Clave OK: la API responde. Ya puedes lanzar la recogida completa.")
        return

    # 2) Detalles de vídeos y canales (IDs ordenados para que los lotes sean estables en caché)
    ids_video = sorted({vid for (_, _, vid) in apariciones})
    videos = {}
    for lote in trocear(ids_video):
        for it in yt.get("videos", part="snippet,contentDetails,statistics,liveStreamingDetails",
                         id=",".join(lote), maxResults=50).get("items", []):
            videos[it["id"]] = it
    ids_canal = sorted({v["snippet"]["channelId"] for v in videos.values()})
    canales = {}
    for lote in trocear(ids_canal):
        for it in yt.get("channels", part="snippet,statistics,contentDetails",
                         id=",".join(lote), maxResults=50).get("items", []):
            canales[it["id"]] = it

    # 3) Tabla de vídeos con filtros
    filas_vid = []
    for (nicho, idioma, vid), tipos in sorted(apariciones.items()):
        v = videos.get(vid)
        if not v:
            continue
        sn, st, cd = v["snippet"], v.get("statistics", {}), v["contentDetails"]
        ch = canales.get(sn["channelId"], {})
        ch_st = ch.get("statistics", {})
        dur = segundos_iso(cd.get("duration"))
        publicado = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))
        edad = max((ref - publicado).total_seconds() / 86400, 1)
        vistas = int(st.get("viewCount", 0))
        subs_ocultos = ch_st.get("hiddenSubscriberCount", False)
        subs = int(ch_st.get("subscriberCount", 0)) if not subs_ocultos else None
        lang, fuente_lang = detectar_idioma(sn)

        motivo = ""
        if not (CONFIG["duracion_min_s"] <= dur <= CONFIG["duracion_max_s"]):
            motivo = "duracion"
        elif "liveStreamingDetails" in v:
            motivo = "directo"
        elif publicado < corte:
            motivo = "antiguo"
        elif lang != idioma:
            motivo = f"idioma_{lang}"

        filas_vid.append({
            "nicho": nicho, "idioma": idioma, "tipos_consulta": "|".join(sorted(tipos)),
            "video_id": vid, "titulo": sn["title"], "canal_id": sn["channelId"],
            "canal": sn.get("channelTitle", ""), "publicado": sn["publishedAt"],
            "edad_dias": round(edad, 1), "duracion_s": dur, "vistas": vistas,
            "likes": st.get("likeCount", ""), "comentarios": st.get("commentCount", ""),
            "vistas_dia": round(vistas / edad, 1), "suscriptores": subs if subs is not None else "",
            "subs_ocultos": subs_ocultos,
            "ratio_vistas_subs": round(vistas / subs, 3) if subs else "",
            "idioma_detectado": lang, "fuente_idioma": fuente_lang,
            "valido": motivo == "", "motivo_exclusion": motivo,
        })

    # 4) Frecuencia de subida: top N canales (por vistas en la muestra) de cada combo
    vistas_canal = defaultdict(lambda: defaultdict(int))
    for f in filas_vid:
        if f["valido"]:
            vistas_canal[(f["nicho"], f["idioma"])][f["canal_id"]] += f["vistas"]
    elegidos = set()
    for combo, mapa in vistas_canal.items():
        top = sorted(mapa, key=mapa.get, reverse=True)[:CONFIG["canales_frecuencia_por_combo"]]
        elegidos.update(top)

    filas_frec = []
    try:
        for cid in sorted(elegidos):
            uploads = canales.get(cid, {}).get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
            if not uploads:
                continue
            pl = yt.get("playlistItems", part="contentDetails", playlistId=uploads, maxResults=50)
            ids = sorted(it["contentDetails"]["videoId"] for it in pl.get("items", []))
            durs = {}
            for lote in trocear(ids):
                for it in yt.get("videos", part="contentDetails,snippet", id=",".join(lote), maxResults=50).get("items", []):
                    durs[it["id"]] = (segundos_iso(it["contentDetails"].get("duration")),
                                      datetime.fromisoformat(it["snippet"]["publishedAt"].replace("Z", "+00:00")))
            en_ventana = [(d, p) for d, p in durs.values() if p >= corte]
            semanas = CONFIG["dias_atras"] / 7
            largos = sum(1 for d, _ in en_ventana if d > 180)
            de_10_30 = sum(1 for d, _ in en_ventana if 600 <= d <= 1800)
            ultimo_largo = max((p for d, p in durs.values() if d > 180), default=None)
            filas_frec.append({
                "canal_id": cid, "canal": canales[cid]["snippet"]["title"],
                "subidas_largas_90d": largos, "subidas_10_30min_90d": de_10_30,
                "largos_por_semana": round(largos / semanas, 2),
                "dias_desde_ultimo_largo": round((ref - ultimo_largo).total_seconds() / 86400, 1) if ultimo_largo else "",
                "muestra_incompleta": len(en_ventana) == 50,   # 50 subidas en 90 días: hay más que no vimos
            })
    except CuotaAgotada as e:
        print(f"Cuota agotada durante la frecuencia de subida ({e}). Reejecuta mañana para completarla.")

    filas_can = [{
        "canal_id": cid, "canal": c["snippet"]["title"], "pais": c["snippet"].get("country", ""),
        "creado": c["snippet"].get("publishedAt", ""),
        "suscriptores": c["statistics"].get("subscriberCount", ""),
        "subs_ocultos": c["statistics"].get("hiddenSubscriberCount", False),
        "videos_totales": c["statistics"].get("videoCount", ""),
        "vistas_totales": c["statistics"].get("viewCount", ""),
    } for cid, c in sorted(canales.items())]

    print("\nGuardando:")
    escribir_csv("busquedas.csv", filas_busq)
    escribir_csv("videos.csv", filas_vid)
    escribir_csv("canales.csv", filas_can)
    escribir_csv("frecuencia_canales.csv", filas_frec)
    validos = sum(f["valido"] for f in filas_vid)
    print(f"\nHecho: {validos} vídeos válidos de {len(filas_vid)}. Gasto en esta ejecución: {yt.gastado}")


if __name__ == "__main__":
    main()
