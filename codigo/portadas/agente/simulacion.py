"""Usuarios simulados para E2 (y sesiones sintéticas para E3).

Cada usuario tiene una preferencia oculta sobre dos parámetros (p. ej. estilo = acuarela y
paleta = pastel). Acepta una propuesta con probabilidad 0.8 si coincide en todos sus
parámetros preferidos y 0.15 si no. Al rechazar marca como motivo los parámetros preferidos
que no coinciden, como haría una persona ("colores" si la paleta no le gusta).

Límite conocido: la preferencia simulada es fija durante la sesión; la de una persona no.
No se generan imágenes: el registro tiene la misma forma que el de la interfaz, sin "image".
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np

from .. import config
from .planificador import Planificador

PARAMS_PREFERENCIA = ("P1", "P2", "P3", "P4")  # los que una persona reconoce a simple vista
MOTIVO_DE = {p: m for m, p in config.MOTIVOS_RECHAZO.items()}


class UsuarioSimulado:
    def __init__(self, rng: np.random.Generator, n_preferencias: int = 2,
                 p_coincide: float = config.E2_P_ACEPTA_COINCIDE,
                 p_no_coincide: float = config.E2_P_ACEPTA_NO_COINCIDE):
        params = rng.choice(PARAMS_PREFERENCIA, size=n_preferencias, replace=False)
        self.preferencia = {str(p): str(rng.choice(list(config.PARAMETROS[str(p)]))) for p in params}
        self.p_coincide, self.p_no_coincide = p_coincide, p_no_coincide
        self.rng = rng

    def decidir(self, params: Dict[str, str]) -> Dict:
        distintos = [p for p, v in self.preferencia.items() if params[p] != v]
        p_acepta = self.p_coincide if not distintos else self.p_no_coincide
        if self.rng.random() < p_acepta:
            return {"decision": "accepted", "reasons": [], "comment": ""}
        return {"decision": "rejected", "reasons": [MOTIVO_DE[p] for p in distintos], "comment": ""}


def simular_sesion(usuario: UsuarioSimulado, politica: str, semilla: int,
                   ejes: Sequence[str] = config.E2_EJES, base: Optional[Dict[str, str]] = None) -> Dict:
    """Sesión completa en formato del registro JSON (sección 8)."""
    base = dict(base or config.POR_DEFECTO)
    plan = Planificador(politica, semilla=semilla)
    rondas = []
    for r, eje in enumerate(ejes[:config.MAX_RONDAS], start=1):
        propuesta = plan.proponer(r, base, eje)
        variaciones = []
        for i, cfg in enumerate(propuesta["configs"], start=1):
            v = {"id": f"R{r}-V{i}", "params": cfg,
                 "exploited": propuesta["planner"]["exploited"][i - 1]}
            v.update(usuario.decidir(cfg))
            variaciones.append(v)
        ronda = {"round": r, "axis": eje, "engine": "simulado", "fixed": {k: v for k, v in base.items() if k != eje},
                 "planner": propuesta["planner"], "variations": variaciones}
        plan.actualizar(ronda)
        rondas.append(ronda)
    return {"session_id": f"sim-{politica}-{semilla}", "title": "Sesión simulada",
            "simulated_preference": usuario.preferencia, "rounds": rondas}


def tasa_por_ronda(sesiones: List[Dict]) -> List[float]:
    n = max(len(s["rounds"]) for s in sesiones)
    tasas = []
    for r in range(n):
        dec = [v["decision"] == "accepted" for s in sesiones if len(s["rounds"]) > r
               for v in s["rounds"][r]["variations"]]
        tasas.append(float(np.mean(dec)) if dec else float("nan"))
    return tasas


def tasa_explotadas_vs_exploradas(sesiones: List[Dict]) -> Dict[str, float]:
    """Rondas 2+: una propuesta es "explotada" si todos sus parámetros muestreados tomaron el
    valor con mayor media posterior; si alguno no, es "explorada"."""
    grupos = {"explotadas": [], "exploradas": []}
    for s in sesiones:
        for r in s["rounds"][1:]:
            for v in r["variations"]:
                marca = v.get("exploited") or {}
                if not marca:
                    continue
                g = "explotadas" if all(marca.values()) else "exploradas"
                grupos[g].append(v["decision"] == "accepted")
    return {k: (float(np.mean(x)) if x else float("nan")) for k, x in grupos.items()} | \
           {f"n_{k}": len(x) for k, x in grupos.items()}


def experimento_e2(n_usuarios: int = config.E2_USUARIOS, repeticiones: int = 20,
                   semilla: int = config.SEMILLA_GLOBAL, ejes: Sequence[str] = config.E2_EJES) -> Dict:
    """Compara Thompson y aleatorio con los MISMOS usuarios (misma preferencia y misma semilla
    de decisiones) en cada repetición. Devuelve medias y desviaciones por ronda."""
    tasas = {pol: [] for pol in ("thompson", "aleatoria")}
    explot = []
    ejemplo = {}
    for rep in range(repeticiones):
        for pol in tasas:
            sesiones = []
            for u in range(n_usuarios):
                s_user = semilla + 10_000 * rep + u
                usuario = UsuarioSimulado(np.random.default_rng(s_user))
                sesiones.append(simular_sesion(usuario, pol, semilla=s_user + 7, ejes=ejes))
            tasas[pol].append(tasa_por_ronda(sesiones))
            if pol == "thompson":
                explot.append(tasa_explotadas_vs_exploradas(sesiones))
                if rep == 0:
                    ejemplo = {"sesiones": sesiones}
    resumen = {}
    for pol, filas in tasas.items():
        m = np.array(filas)
        resumen[pol] = {"media_por_ronda": m.mean(axis=0).round(4).tolist(),
                        "de_por_ronda": m.std(axis=0, ddof=1).round(4).tolist() if len(filas) > 1 else None}
    t, a = np.array(tasas["thompson"]), np.array(tasas["aleatoria"])
    resumen["diferencia_thompson_menos_aleatoria"] = (t - a).mean(axis=0).round(4).tolist()
    resumen["explotadas_vs_exploradas"] = {
        k: float(np.nanmean([e[k] for e in explot])) for k in ("explotadas", "exploradas")}
    tm = resumen["thompson"]["media_por_ronda"]
    resumen["criterio"] = {"aceptacion ronda 2 > ronda 1 (thompson)": bool(len(tm) > 1 and tm[1] > tm[0])}
    resumen["config"] = {"usuarios": n_usuarios, "repeticiones": repeticiones, "ejes": list(ejes),
                         "p_coincide": config.E2_P_ACEPTA_COINCIDE, "p_no_coincide": config.E2_P_ACEPTA_NO_COINCIDE,
                         "semilla": semilla}
    return {"resumen": resumen, "filas": tasas, **ejemplo}
