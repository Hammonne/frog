"""Planificador de rondas con muestreo de Thompson (sección 5 del informe).

Cada valor v de cada parámetro p tiene una Beta(alfa, beta), con alfa = beta = 1 al inicio.
Al cerrar una ronda:
- propuesta aceptada: alfa[p][v] += 1 para todos sus parámetros;
- propuesta rechazada: beta[p][v] += 1 solo para los parámetros marcados como motivo;
  si no se marcó ninguno, se penaliza solo el eje de la ronda.

Ronda 1: las cinco propuestas son los cinco valores del eje con el resto fijado por el usuario
(`configuraciones_por_eje`). Rondas 2 y 3: el eje vuelve a tomar sus cinco valores y, en cada
propuesta, los parámetros que el usuario no fijó se eligen por muestreo de Thompson.

La política "aleatoria" elige esos parámetros al azar; sirve de línea base en E2.
"""
from __future__ import annotations

import copy
from typing import Dict, Iterable, List, Optional

import numpy as np

from .. import config
from ..motores.prompts import EJES_VALIDOS, configuraciones_por_eje, validar_configuracion

POLITICAS = ("thompson", "aleatoria")


class Planificador:
    def __init__(self, politica: str = "thompson", semilla: int = config.SEMILLA_GLOBAL):
        if politica not in POLITICAS:
            raise ValueError(f"Política inválida: {politica}. Opciones: {POLITICAS}")
        self.politica = politica
        self.rng = np.random.default_rng(semilla)
        self.alfa = {p: {v: 1.0 for v in valores} for p, valores in config.PARAMETROS.items()}
        self.beta = {p: {v: 1.0 for v in valores} for p, valores in config.PARAMETROS.items()}

    # ------------------------------------------------------------ actualización
    def actualizar(self, ronda: Dict) -> None:
        """Actualiza las Beta con las decisiones de una ronda en formato del registro JSON
        (`ronda["variations"][i]` con "params", "decision" y "reasons")."""
        eje = ronda["axis"]
        for v in ronda["variations"]:
            decision = v.get("decision")
            if decision == "accepted":
                for p, valor in v["params"].items():
                    self.alfa[p][valor] += 1
            elif decision == "rejected":
                for p in parametros_penalizados(v.get("reasons") or [], eje):
                    self.beta[p][v["params"][p]] += 1
            # Sin decisión o tarjeta bloqueada por guardrail: no aporta información.

    # ------------------------------------------------------------ propuesta
    def proponer(self, ronda: int, base: Dict[str, str], eje: str,
                 fijos: Optional[Iterable[str]] = None) -> Dict:
        """Devuelve {"configs": [5 configuraciones], "planner": bloque para el registro}.

        `fijos`: parámetros que el usuario bloqueó (se toman de `base`). En la ronda 1 se
        consideran fijos todos menos el eje."""
        if eje not in EJES_VALIDOS:
            raise ValueError(f"Eje inválido: {eje}")
        if not 1 <= ronda <= config.MAX_RONDAS:
            raise ValueError(f"La sesión admite como máximo {config.MAX_RONDAS} rondas.")
        validar_configuracion(base)
        bloque = {"policy": self.politica, "posterior_before": self.posterior()}

        if ronda == 1:
            configs = configuraciones_por_eje(base, eje)
            bloque["sampled"] = []
            bloque["exploited"] = [{} for _ in configs]
            return {"configs": configs, "planner": bloque}

        fijos = set(fijos or []) - {eje}
        libres = [p for p in config.PARAMETROS if p != eje and p not in fijos]
        configs, explotados = [], []
        for valor_eje in config.PARAMETROS[eje]:
            cfg = dict(base)
            cfg[eje] = valor_eje
            marca = {}
            for p in libres:
                cfg[p] = self._elegir(p)
                marca[p] = cfg[p] in self.mejores(p)
            validar_configuracion(cfg)
            configs.append(cfg)
            explotados.append(marca)
        bloque["sampled"] = libres
        bloque["exploited"] = explotados
        return {"configs": configs, "planner": bloque}

    def _elegir(self, p: str) -> str:
        valores = list(config.PARAMETROS[p])
        if self.politica == "aleatoria":
            return valores[int(self.rng.integers(len(valores)))]
        muestras = [self.rng.beta(self.alfa[p][v], self.beta[p][v]) for v in valores]
        return valores[int(np.argmax(muestras))]

    # ------------------------------------------------------------ consultas
    def media(self, p: str, v: str) -> float:
        a, b = self.alfa[p][v], self.beta[p][v]
        return a / (a + b)

    def mejores(self, p: str) -> List[str]:
        """Valores con la mayor media posterior (puede haber empates)."""
        medias = {v: self.media(p, v) for v in config.PARAMETROS[p]}
        m = max(medias.values())
        return [v for v, x in medias.items() if np.isclose(x, m)]

    def posterior(self) -> Dict[str, Dict[str, List[float]]]:
        """Copia serializable: {p: {v: [alfa, beta]}}."""
        return {p: {v: [self.alfa[p][v], self.beta[p][v]] for v in config.PARAMETROS[p]}
                for p in config.PARAMETROS}

    def cargar_posterior(self, posterior: Dict[str, Dict[str, List[float]]]) -> None:
        for p, valores in posterior.items():
            for v, (a, b) in valores.items():
                self.alfa[p][v], self.beta[p][v] = float(a), float(b)

    def copia(self) -> "Planificador":
        return copy.deepcopy(self)


def parametros_penalizados(motivos: List[str], eje: str) -> List[str]:
    """Motivos de la interfaz -> parámetros a penalizar. Sin motivos válidos: solo el eje."""
    params = []
    for m in motivos:
        p = config.MOTIVOS_RECHAZO.get(m)
        if p and p not in params:
            params.append(p)
    return params or [eje]


def cambios_entre_rondas(anterior: Dict, siguiente: Dict) -> List[Dict]:
    """Qué parámetros cambió el planificador para la ronda siguiente, a partir solo del registro.
    Lo usa el explicador para describir la planificación sin inventar."""
    post = (siguiente.get("planner") or {}).get("posterior_before") or {}
    cambios = []
    for p in (siguiente.get("planner") or {}).get("sampled", []):
        usados = sorted({v["params"][p] for v in siguiente["variations"]})
        favoritos = []
        for valor, (a, b) in post.get(p, {}).items():
            aceptadas, rechazadas = int(a - 1), int(b - 1)
            if aceptadas or rechazadas:
                favoritos.append({"valor": valor, "aceptadas": aceptadas, "rechazadas": rechazadas})
        cambios.append({"parametro": p, "valores_usados": usados, "historial": favoritos})
    return cambios
