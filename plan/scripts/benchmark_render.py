"""Mini benchmark de render: compone fondo + 3 personajes por capas y codifica con NVENC.

No instala nada: usa numpy, Pillow y el FFmpeg que ya tienes.
Uso (desde canal-youtube/):  python plan/scripts/benchmark_render.py [libx264|h264_nvenc]
Escribe: plan/data/benchmark_render.json
Nota: h264_nvenc con FFmpeg 9.0.1 exige driver NVIDIA >= 610 (medido el 01-10-2026 con el 591.86: falla).
"""

import json
import math
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
DATOS = Path(__file__).resolve().parents[1] / "data"
W, H, FPS, SEGUNDOS = 1920, 1080, 30, 10


def capa(tam, color, forma="elipse"):
    im = Image.new("RGBA", tam, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    caja = (4, 4, tam[0] - 5, tam[1] - 5)
    (d.ellipse if forma == "elipse" else d.rounded_rectangle)(caja, fill=color, outline=(20, 20, 20, 255), width=6)
    return im


def personaje():
    """~12 capas, como un rig de recortes: cuerpo, 2 brazos, cabeza, 2 ojos, 2 pupilas, 2 cejas, boca, pelo."""
    return {
        "cuerpo": capa((260, 380), (70, 120, 200, 255), "rect"),
        "brazo_i": capa((70, 260), (240, 200, 170, 255), "rect"),
        "brazo_d": capa((70, 260), (240, 200, 170, 255), "rect"),
        "cabeza": capa((300, 320), (240, 200, 170, 255)),
        "pelo": capa((320, 140), (60, 40, 30, 255)),
        "ojo_i": capa((70, 80), (255, 255, 255, 255)), "ojo_d": capa((70, 80), (255, 255, 255, 255)),
        "pupila_i": capa((26, 30), (20, 20, 20, 255)), "pupila_d": capa((26, 30), (20, 20, 20, 255)),
        "ceja_i": capa((70, 18), (40, 30, 20, 255), "rect"), "ceja_d": capa((70, 18), (40, 30, 20, 255), "rect"),
        "boca": capa((90, 50), (150, 40, 50, 255)),
    }


def pegar(lienzo, im, x, y, angulo=0.0):
    if angulo:
        im = im.rotate(angulo, resample=Image.BICUBIC, expand=True)
    lienzo.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))


def dibujar_personaje(lienzo, p, cx, cy, t, fase):
    s = math.sin(t * 2 + fase)
    pegar(lienzo, p["brazo_i"], cx - 150, cy + 60, 15 * s)
    pegar(lienzo, p["brazo_d"], cx + 150, cy + 60, -15 * s)
    pegar(lienzo, p["cuerpo"], cx, cy + 80)
    pegar(lienzo, p["cabeza"], cx, cy - 200, 3 * s)
    pegar(lienzo, p["pelo"], cx, cy - 330)
    for lado, dx in (("i", -60), ("d", 60)):
        pegar(lienzo, p[f"ojo_{lado}"], cx + dx, cy - 220)
        pegar(lienzo, p[f"pupila_{lado}"], cx + dx + 10 * s, cy - 215)
        pegar(lienzo, p[f"ceja_{lado}"], cx + dx, cy - 275 - 6 * abs(s), 8 * s)
    boca = p["boca"].resize((90, max(10, int(50 * abs(math.sin(t * 9 + fase))))))
    pegar(lienzo, boca, cx, cy - 120)


def main():
    fondo = Image.new("RGBA", (int(W * 1.2), int(H * 1.2)), (180, 210, 230, 255))
    d = ImageDraw.Draw(fondo)
    for i in range(0, fondo.width, 120):
        d.rectangle((i, 700, i + 80, 1100), fill=(90, 140, 90, 255), outline=(20, 20, 20, 255), width=5)
    pjs = [personaje() for _ in range(3)]

    codec = sys.argv[1] if len(sys.argv) > 1 else "libx264"
    opciones = {"h264_nvenc": ["-preset", "p5", "-cq", "21"], "libx264": ["-preset", "medium", "-crf", "20"]}[codec]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", codec, *opciones,
           "-pix_fmt", "yuv420p", str(DATOS / "benchmark_render.mp4")]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    n = FPS * SEGUNDOS
    t0 = time.perf_counter()
    for f in range(n):
        t = f / FPS
        zoom = 1 + 0.05 * t / SEGUNDOS                       # movimiento de cámara lento (Ken Burns)
        cw, ch = int(W * 1.2 / zoom), int(H * 1.2 / zoom)
        x0, y0 = (fondo.width - cw) // 2, (fondo.height - ch) // 2
        lienzo = fondo.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR)
        for i, p in enumerate(pjs):
            dibujar_personaje(lienzo, p, 420 + i * 540, 640, t, i)
        ff.stdin.write(lienzo.convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    dur = time.perf_counter() - t0

    fps_render = n / dur
    res = {
        "frames": n, "segundos_video": SEGUNDOS, "segundos_reloj": round(dur, 2),
        "fps_render": round(fps_render, 1),
        "minutos_para_video_15min": round(15 * 60 * FPS / fps_render / 60, 1),
        "config": f"1920x1080@30, 3 personajes x 12 capas, zoom de cámara, Pillow + {codec}, 1 proceso",
    }
    (DATOS / "benchmark_render.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
