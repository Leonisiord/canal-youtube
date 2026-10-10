"""Calcula métricas por nicho e idioma y la puntuación ponderada.

Uso (desde canal-youtube/):  python plan/scripts/analizar_nichos.py
Lee:    plan/data/videos.csv, busquedas.csv, frecuencia_canales.csv,
        rpm_fuentes.csv, criterios_cualitativos.json
Escribe: plan/data/metricas_nicho.csv, plan/data/puntuacion.csv, plan/data/resumen_analisis.json
"""

import csv
import json
import math
import statistics as st
from collections import defaultdict

from yt_cliente import DATOS

CONFIG = json.loads((DATOS.parent / "scripts" / "config_nichos.json").read_text(encoding="utf-8"))
CRIT = json.loads((DATOS / "criterios_cualitativos.json").read_text(encoding="utf-8"))
UMBRAL_SUBS, UMBRAL_VISTAS = 10_000, 100_000


def leer(nombre):
    with open(DATOS / nombre, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def mediana(xs):
    return st.median(xs) if xs else 0


def p75(xs):
    return st.quantiles(xs, n=4)[2] if len(xs) >= 2 else (xs[0] if xs else 0)


def normalizar(valores):
    """Min-max a 0-10 entre todos los combos."""
    lo, hi = min(valores.values()), max(valores.values())
    return {k: (10 * (v - lo) / (hi - lo) if hi > lo else 5) for k, v in valores.items()}


def metricas():
    videos = [v for v in leer("videos.csv") if v["valido"] == "True"]
    busq = leer("busquedas.csv")
    frec = {f["canal_id"]: f for f in leer("frecuencia_canales.csv")} if (DATOS / "frecuencia_canales.csv").exists() else {}

    por_combo = defaultdict(list)
    for v in videos:
        por_combo[(v["nicho"], v["idioma"])].append(v)

    totales = defaultdict(list)
    for b in busq:
        if b["total_aprox"]:
            totales[(b["nicho"], b["idioma"])].append(int(b["total_aprox"]))

    filas = []
    for nicho in CONFIG["nichos"]:
        for idioma in ("es", "en"):
            vs = por_combo.get((nicho["id"], idioma), [])
            vistas = [int(v["vistas"]) for v in vs]
            ratios = [float(v["ratio_vistas_subs"]) for v in vs if v["ratio_vistas_subs"]]
            animados = [int(v["vistas"]) for v in vs if "animado" in v["tipos_consulta"]]

            # canales pequeños (<10k subs) con algún vídeo de >100k vistas
            pequenos_virales = {v["canal_id"] for v in vs if v["suscriptores"]
                                and int(v["suscriptores"]) < UMBRAL_SUBS and int(v["vistas"]) > UMBRAL_VISTAS}
            n_pequenos = sum(1 for v in vs if v["suscriptores"] and int(v["suscriptores"]) < UMBRAL_SUBS)

            # concentración: % de vistas que se llevan los 5 canales más vistos
            vistas_canal = defaultdict(int)
            for v in vs:
                vistas_canal[v["canal_id"]] += int(v["vistas"])
            total = sum(vistas_canal.values()) or 1
            top5 = sum(sorted(vistas_canal.values(), reverse=True)[:5]) / total

            # frecuencia de subida de los canales top de este combo
            top_canales = sorted(vistas_canal, key=vistas_canal.get, reverse=True)[:CONFIG["canales_frecuencia_por_combo"]]
            fr = [frec[c] for c in top_canales if c in frec]
            por_semana = [float(f["largos_por_semana"]) for f in fr]
            activos_30d = sum(1 for f in fr if f["dias_desde_ultimo_largo"] and float(f["dias_desde_ultimo_largo"]) <= 30)

            filas.append({
                "nicho": nicho["id"], "idioma": idioma, "n_videos": len(vs), "n_canales": len(vistas_canal),
                "mediana_vistas": round(mediana(vistas)), "p75_vistas": round(p75(vistas)),
                "mediana_vistas_dia": round(mediana([float(v["vistas_dia"]) for v in vs]), 1),
                "mediana_ratio_vistas_subs": round(mediana(ratios), 3),
                "canales_pequenos_virales": len(pequenos_virales),
                "pct_videos_canales_pequenos": round(100 * n_pequenos / len(vs), 1) if vs else 0,
                "concentracion_top5_pct": round(100 * top5, 1),
                "total_resultados_aprox": round(st.mean(totales[(nicho["id"], idioma)])) if totales[(nicho["id"], idioma)] else "",
                "mediana_largos_semana_top": round(mediana(por_semana), 2),
                "top_activos_ult_30d": f"{activos_30d}/{len(fr)}",
                "mediana_vistas_consulta_animado": round(mediana(animados)),
            })
    return filas


def rpm_estimado():
    mids = defaultdict(list)
    for r in leer("rpm_fuentes.csv"):
        mids[r["nicho"]].append((float(r["rpm_min_usd"]) + float(r["rpm_max_usd"])) / 2)
    return {n: st.mean(m) for n, m in mids.items()}


def puntuar(filas):
    rpm_base = rpm_estimado()
    factor = CRIT["factor_rpm_idioma"]
    clave = lambda f: (f["nicho"], f["idioma"])
    validas = [f for f in filas if f["n_videos"] >= 5]   # sin muestra suficiente no se puntúa

    log = lambda x: math.log10(max(x, 1))
    dem_a = normalizar({clave(f): log(f["mediana_vistas"]) for f in validas})
    dem_b = normalizar({clave(f): log(f["mediana_vistas_dia"]) for f in validas})
    op_a = normalizar({clave(f): f["canales_pequenos_virales"] for f in validas})
    op_b = normalizar({clave(f): log(1 + 100 * f["mediana_ratio_vistas_subs"]) for f in validas})
    op_c = normalizar({clave(f): 100 - f["concentracion_top5_pct"] for f in validas})
    rpm_usd = {clave(f): rpm_base[f["nicho"]] * factor[f["idioma"]] for f in validas}
    # escala log, igual que la demanda: ingresos = vistas x RPM, ambos multiplican
    rpm_n = normalizar({k: math.log10(v) for k, v in rpm_usd.items()})

    salida = []
    for f in validas:
        k = clave(f)
        c = CRIT["nichos"][f["nicho"]]
        notas = {
            "demanda": (dem_a[k] + dem_b[k]) / 2,
            "oportunidad": (op_a[k] + op_b[k] + op_c[k]) / 3,
            "rpm": rpm_n[k],
            "encaje": (c["encaje"] - 1) * 2.5,
            "guiones": (c["guiones"] - 1) * 2.5,
            "riesgo": (c["riesgo"] - 1) * 2.5,
        }
        fila = {"nicho": f["nicho"], "idioma": f["idioma"], "rpm_estimado_usd": round(rpm_usd[k], 2)}
        fila.update({f"nota_{n}": round(v, 2) for n, v in notas.items()})
        fila["total"] = round(sum(CRIT["pesos"][n] * v for n, v in notas.items()), 2)
        for nombre, pesos in CRIT["pesos_alternativos"].items():
            fila[f"total_{nombre}"] = round(sum(pesos[n] * v for n, v in notas.items()), 2)
        salida.append(fila)

    salida.sort(key=lambda r: r["total"], reverse=True)
    for i, r in enumerate(salida, 1):
        r["puesto"] = i
    for nombre in CRIT["pesos_alternativos"]:
        for i, r in enumerate(sorted(salida, key=lambda r: r[f"total_{nombre}"], reverse=True), 1):
            r[f"puesto_{nombre}"] = i
    return salida


def guardar(nombre, filas):
    with open(DATOS / nombre, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)


def main():
    filas = metricas()
    guardar("metricas_nicho.csv", filas)
    punt = puntuar(filas)
    guardar("puntuacion.csv", punt)

    # comparación por idioma (medianas de las medianas)
    idiomas = {}
    for idi in ("es", "en"):
        fs = [f for f in filas if f["idioma"] == idi and f["n_videos"]]
        idiomas[idi] = {
            "mediana_de_medianas_vistas": mediana([f["mediana_vistas"] for f in fs]),
            "mediana_ratio_vistas_subs": mediana([f["mediana_ratio_vistas_subs"] for f in fs]),
            "canales_pequenos_virales_total": sum(f["canales_pequenos_virales"] for f in fs),
            "mediana_concentracion_top5": mediana([f["concentracion_top5_pct"] for f in fs]),
        }
    (DATOS / "resumen_analisis.json").write_text(
        json.dumps({"por_idioma": idiomas, "top": punt[:5]}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{'#':>2} {'nicho':15} {'id':3} {'total':>6} {'dem':>5} {'opo':>5} {'rpm':>5} {'enc':>5} {'gui':>5} {'rie':>5}  datos/pipeline")
    for r in punt:
        print(f"{r['puesto']:>2} {r['nicho']:15} {r['idioma']:3} {r['total']:>6} {r['nota_demanda']:>5} "
              f"{r['nota_oportunidad']:>5} {r['nota_rpm']:>5} {r['nota_encaje']:>5} {r['nota_guiones']:>5} "
              f"{r['nota_riesgo']:>5}  {r['puesto_solo_datos']}/{r['puesto_pipeline']}")
    print("\nPor idioma:", json.dumps(idiomas, ensure_ascii=False))


if __name__ == "__main__":
    main()
