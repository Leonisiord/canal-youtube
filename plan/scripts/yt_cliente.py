"""Cliente mínimo de la YouTube Data API v3 con caché en disco y control de cuota.

- Cada respuesta se guarda en plan/data/raw/ (JSON). Si la misma llamada ya está
  en caché, no se vuelve a pedir y no gasta cuota.
- Cuota verificada (developers.google.com/youtube/v3/determine_quota_cost, 15-09-2026):
  search.list tiene su propio cubo de 100 llamadas/día; el resto comparte 10.000 unidades/día.
"""

import csv
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import sys

import requests
from dotenv import load_dotenv

# La consola de Windows no siempre usa UTF-8: evita las tildes rotas al imprimir
sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[2]          # canal-youtube/
DATOS = RAIZ / "plan" / "data"
CACHE = DATOS / "raw"
LOG_CUOTA = DATOS / "cuota_log.csv"
URL_BASE = "https://www.googleapis.com/youtube/v3/"

# endpoint -> (cubo de cuota, coste por llamada)
COSTES = {
    "search": ("busquedas", 1),
    "videos": ("unidades", 1),
    "channels": ("unidades", 1),
    "playlistItems": ("unidades", 1),
}


class CuotaAgotada(Exception):
    pass


class ClienteYT:
    def __init__(self, max_busquedas=95, max_unidades=9500):
        load_dotenv(RAIZ / ".env")
        self.clave = os.getenv("YOUTUBE_API_KEY", "").strip()
        self.max = {"busquedas": max_busquedas, "unidades": max_unidades}
        self.gastado = {"busquedas": 0, "unidades": 0}
        CACHE.mkdir(parents=True, exist_ok=True)

    def tiene_clave(self):
        return bool(self.clave)

    def _ruta_cache(self, endpoint, params):
        firma = json.dumps(params, sort_keys=True, ensure_ascii=False)
        h = hashlib.sha1(f"{endpoint}|{firma}".encode("utf-8")).hexdigest()[:16]
        return CACHE / f"{endpoint}_{h}.json"

    def _anotar(self, endpoint, cubo, coste, en_cache):
        nuevo = not LOG_CUOTA.exists()
        with open(LOG_CUOTA, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if nuevo:
                w.writerow(["fecha_utc", "endpoint", "cubo", "coste", "desde_cache"])
            w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        endpoint, cubo, 0 if en_cache else coste, en_cache])

    def get(self, endpoint, **params):
        ruta = self._ruta_cache(endpoint, params)
        cubo, coste = COSTES[endpoint]
        if ruta.exists():
            self._anotar(endpoint, cubo, coste, True)
            return json.loads(ruta.read_text(encoding="utf-8"))

        if not self.clave:
            raise RuntimeError("Falta YOUTUBE_API_KEY en canal-youtube/.env")
        if self.gastado[cubo] + coste > self.max[cubo]:
            raise CuotaAgotada(f"Límite de seguridad alcanzado en el cubo '{cubo}'")

        for intento in range(3):
            r = requests.get(URL_BASE + endpoint, params={**params, "key": self.clave}, timeout=30)
            if r.status_code == 200:
                break
            motivo = ""
            try:
                motivo = r.json()["error"]["errors"][0]["reason"]
            except Exception:
                pass
            if motivo in ("quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded") and r.status_code == 403:
                raise CuotaAgotada(f"Google dice: {motivo}")
            if r.status_code >= 500:
                time.sleep(2 ** intento)
                continue
            raise RuntimeError(f"Error {r.status_code} en {endpoint}: {r.text[:300]}")
        else:
            raise RuntimeError(f"{endpoint} falló 3 veces seguidas")

        datos = r.json()
        ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        self.gastado[cubo] += coste
        self._anotar(endpoint, cubo, coste, False)
        return datos
