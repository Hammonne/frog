"""E4: puntaje SUS y resumen de las sesiones con usuarios.

Entrada: salidas/e4/respuestas_sus.csv con columnas `participante,p1,...,p10` (respuestas 1–5)
y, opcionalmente, `completo` (si/no). Si existe salidas/e4/<participante>/sesion.json se cuentan las
rondas y las decisiones.

Uso:
    python -m experimentos.e4_sus
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from portadas import config

CRITERIO = 68.0
T_975 = {4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179}   # t de Student, gl = n - 1


def sus(respuestas: list[int]) -> float:
    """Puntaje SUS (0–100) a partir de 10 respuestas de 1 a 5."""
    if len(respuestas) != 10 or any(not 1 <= r <= 5 for r in respuestas):
        raise ValueError("el SUS necesita 10 respuestas entre 1 y 5")
    impares = sum(r - 1 for r in respuestas[0::2])      # preguntas 1, 3, 5, 7, 9
    pares = sum(5 - r for r in respuestas[1::2])        # preguntas 2, 4, 6, 8, 10
    return (impares + pares) * 2.5


def normalizar_fila(fila: dict) -> dict | None:
    """Acepta el CSV con columnas `participante,p1..p10` o la exportación del formulario de Google
    (columna 'Código de participante' y preguntas que empiezan con '1.', '2.', ...)."""
    if "participante" in fila:
        return fila
    codigo = next((v for k, v in fila.items() if k.lower().startswith("código de participante")), "").strip()
    out = {"participante": codigo, "completo": fila.get("completo", "")}
    for k, v in fila.items():
        num = k.split(".")[0].strip()
        if num.isdigit() and 1 <= int(num) <= 10 and k.strip()[len(num)] == ".":
            if not str(v).strip():
                return None
            out[f"p{num}"] = v
    return out if codigo and all(f"p{i}" in out for i in range(1, 11)) else None


def decisiones(ruta: Path) -> dict:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    rondas = datos.get("rounds", [])
    vs = [v for r in rondas for v in r.get("variations", [])]
    return {"rondas": len(rondas), "aceptadas": sum(v.get("decision") == "accepted" for v in vs),
            "rechazadas": sum(v.get("decision") == "rejected" for v in vs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--carpeta", default=str(config.SALIDAS / "e4"))
    args = ap.parse_args()
    carpeta = Path(args.carpeta)
    filas, puntajes, crudas = [], [], []
    with open(carpeta / "respuestas_sus.csv", encoding="utf-8-sig") as fh:
        for f in csv.DictReader(fh):
            f = normalizar_fila(f)
            if f is None:                                      # respuesta sin SUS (por ejemplo, "No acepto")
                continue
            p = sus([int(f[f"p{i}"]) for i in range(1, 11)])
            puntajes.append(p)
            crudas.append([int(f[f"p{i}"]) for i in range(1, 11)])
            fila = {"participante": f["participante"], "sus": p, "completo": f.get("completo", "")}
            sesion = carpeta / f["participante"] / "sesion.json"
            if sesion.exists():
                fila.update(decisiones(sesion))
            filas.append(fila)
    n = len(puntajes)
    media = sum(puntajes) / n
    desv = (sum((p - media) ** 2 for p in puntajes) / (n - 1)) ** 0.5 if n > 1 else 0.0
    aporte = [[(r[i] - 1) if i % 2 == 0 else (5 - r[i]) for i in range(10)] for r in crudas]   # 0 (peor) a 4 (mejor)
    por_item = [round(sum(a[i] for a in aporte) / n, 2) for i in range(10)]
    ic = round(T_975[n - 1] * desv / n ** 0.5, 1) if (n - 1) in T_975 else None
    ordenados = sorted(puntajes)
    mediana = (ordenados[(n - 1) // 2] + ordenados[n // 2]) / 2
    completos = [f for f in filas if f["completo"]]
    resumen = {"n": n, "sus_media": round(media, 1), "sus_desv": round(desv, 1),
               "sus_mediana": mediana, "sus_ic95": [round(media - ic, 1), round(media + ic, 1)] if ic else None,
               "n_sobre_criterio": sum(p >= CRITERIO for p in puntajes), "aporte_medio_por_item_0a4": por_item,
               "sus_min": min(puntajes), "sus_max": max(puntajes), "criterio": CRITERIO,
               "cumple": media >= CRITERIO,
               "tarea_completada": (sum(f["completo"].lower() == "si" for f in completos) / len(completos))
               if completos else None, "participantes": filas}
    (carpeta / "resumen_e4.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
