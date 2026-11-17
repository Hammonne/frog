"""E2: ¿el planificador de Thompson mejora la aceptación entre rondas? (sin GPU)

Usuarios simulados: cada uno tiene un valor preferido por parámetro. Acepta una propuesta
con probabilidad 0.05 + 0.90 * (fracción de parámetros que coinciden con sus preferidos).
Al rechazar, marca como motivo cada parámetro que no coincide con probabilidad 0.7
(si no marca ninguno, el planificador penaliza solo el eje de la ronda).
Se compara Thompson con una política aleatoria (los parámetros libres se eligen al azar).

Uso: python -m experimentos.e2_simulacion --usuarios 500 --salida salidas/e2
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, List

from portadas import config
from portadas.planificador import EJES_VARIABLES, MAX_RONDAS, MOTIVOS, Sesion

ETIQUETA_DE_EJE = {v: k for k, v in MOTIVOS.items()}


def _decidir(rng: random.Random, params: Dict[str, str], pref: Dict[str, str]) -> Dict:
    malos = [p for p in params if params[p] != pref[p]]
    acepta = rng.random() < 0.05 + 0.90 * (1 - len(malos) / len(params))
    if acepta:
        return {"decision": "accepted", "reasons": []}
    marcados = [ETIQUETA_DE_EJE[p] for p in malos if rng.random() < 0.7]
    return {"decision": "rejected", "reasons": marcados}


def _ronda_aleatoria(rng: random.Random, sesion: Sesion, eje: str) -> Dict:
    libres = [p for p in sesion.planificador.ejes if p != eje and p not in sesion.fijados]
    configs = []
    for valor in config.PARAMETROS[eje]:
        cfg = dict(sesion.base)
        cfg[eje] = valor
        for p in libres:
            cfg[p] = rng.choice(list(config.PARAMETROS[p]))
        configs.append(cfg)
    return {"axis": eje, "configs": configs, "sampled": [{} for _ in configs], "free": libres,
            "round": sesion.numero}


def simular_usuario(politica: str, semilla: int) -> List[float]:
    """Tasa de aceptación en cada ronda para un usuario simulado."""
    rng = random.Random(semilla)
    pref = {p: rng.choice(list(config.PARAMETROS[p])) for p in EJES_VARIABLES}
    pref["P6"] = config.POR_DEFECTO["P6"]           # ajuste fijo, no se aprende
    sesion = Sesion(dict(config.POR_DEFECTO), semilla=semilla)
    tasas = []
    while not sesion.terminada():
        eje = rng.choice(sesion.ejes_disponibles())
        if politica == "thompson" or not sesion.rondas:
            plan = sesion.configs_ronda(eje)
        else:
            plan = _ronda_aleatoria(rng, sesion, eje)
            sesion.planes.append(plan)
        variaciones = []
        for i, cfg in enumerate(plan["configs"], start=1):
            variaciones.append({"id": f"R{sesion.numero}-V{i}", "params": cfg, **_decidir(rng, cfg, pref)})
        sesion.cerrar_ronda({"round": sesion.numero, "axis": eje, "variations": variaciones})
        tasas.append(sum(v["decision"] == "accepted" for v in variaciones) / len(variaciones))
    return tasas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--usuarios", type=int, default=500)
    ap.add_argument("--salida", default=str(config.SALIDAS / "e2"))
    args = ap.parse_args()

    resumen = {}
    for politica in ("thompson", "aleatorio"):
        tabla = [simular_usuario(politica, config.SEMILLA_GLOBAL + u) for u in range(args.usuarios)]
        resumen[politica] = {f"ronda_{r + 1}": round(sum(t[r] for t in tabla) / len(tabla), 3)
                             for r in range(MAX_RONDAS)}
    resumen["usuarios"] = args.usuarios
    carpeta = Path(args.salida)
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "resumen.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    print(json.dumps(resumen, indent=2))


if __name__ == "__main__":
    main()
