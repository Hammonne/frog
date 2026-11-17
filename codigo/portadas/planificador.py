"""Planificador (muestreo de Thompson) y control de rondas.

Cada valor v de cada parámetro p tiene una Beta(alfa, beta), con alfa = beta = 1.
Al cerrar una ronda, sea V el conjunto de parámetros que VARIARON entre las 5 propuestas
(el eje y los elegidos por Thompson). Un parámetro que fue igual en las cinco no aporta
información sobre lo que prefiere la persona, así que no se actualiza:
    aceptada  -> alfa[p][v_i(p)] += 1 para todo p en V
    rechazada -> beta[p][v_i(p)] += 1 para los p marcados como motivo que están en V; si no
                 queda ninguno (no se marcó motivo, o el motivo se refiere a algo que no
                 varió), solo para el eje de la ronda
    bloqueada por guardrails -> no cuenta (no fue una decisión del usuario)
En la ronda siguiente el usuario elige un eje nuevo: sus 5 valores se reparten entre las
5 propuestas y, en cada propuesta, los demás parámetros no fijados se muestrean con
Thompson (valor con mayor theta ~ Beta). Las semillas de imagen cambian en cada ronda
(generar.peticiones_ronda suma 1000 por ronda). Máximo 3 rondas.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from . import config

MAX_RONDAS = 3

# Parámetros que el planificador puede variar. P6 (zona del título) es un ajuste fijo
# que elige el usuario: no se varía entre propuestas ni se aprende.
EJES_VARIABLES = ["P1", "P2", "P3", "P4", "P5"]

# Motivos de rechazo que ofrece la interfaz -> parámetro al que se atribuyen.
MOTIVOS = {
    "estilo": "P1",
    "colores": "P2",
    "no apto para la edad": "P3",
    "ambiente": "P4",
    "se aleja del boceto": "P5",
}


def ejes_de_motivos(motivos: Optional[List[str]]) -> List[str]:
    """Convierte las casillas marcadas en parámetros (ignora textos desconocidos)."""
    return [MOTIVOS[m] for m in dict.fromkeys(motivos or []) if m in MOTIVOS]


class Planificador:
    def __init__(self, semilla: int = config.SEMILLA_GLOBAL, ejes_activos: Optional[List[str]] = None):
        """`ejes_activos`: parámetros que el planificador puede variar. En el motor B, P5
        (fidelidad) no tiene efecto, así que se excluye."""
        self.rng = random.Random(semilla)
        self.ejes = list(ejes_activos or EJES_VARIABLES)
        self.post: Dict[str, Dict[str, List[float]]] = {
            p: {v: [1.0, 1.0] for v in config.PARAMETROS[p]} for p in config.PARAMETROS}
        # Valores de cada parámetro que se llegaron a mostrar con una decisión del usuario.
        self.vistos: Dict[str, set] = {p: set() for p in config.PARAMETROS}

    # ---------------------------------------------------------------- actualización
    @staticmethod
    def variaron(ronda: Dict) -> set:
        """Parámetros cuyo valor cambió entre las propuestas de la ronda (se miran todas, también
        las bloqueadas: la variación es parte del diseño de la ronda, no de lo que se mostró)."""
        vs = ronda["variations"]
        return {p for p in vs[0]["params"] if len({v["params"][p] for v in vs}) > 1}

    def actualizar(self, ronda: Dict) -> None:
        """Usa `decision` ('accepted'/'rejected') y `reason_axes` de cada variación.
        Solo se actualizan los parámetros que variaron en la ronda."""
        eje = ronda["axis"]
        variaron = self.variaron(ronda) or {eje}
        for v in ronda["variations"]:
            dec = v.get("decision")
            if dec in ("accepted", "rejected"):
                for p in variaron:
                    self.vistos[p].add(v["params"][p])
            if dec == "accepted":
                for p in variaron:
                    self.post[p][v["params"][p]][0] += 1
            elif dec == "rejected":
                ejes = [p for p in v.get("reason_axes") or [] if p in variaron] or [eje]
                for p in ejes:
                    self.post[p][v["params"][p]][1] += 1

    # ------------------------------------------------------------------ propuesta
    def _muestrear(self, p: str):
        """Valor de p con mayor theta ~ Beta(alfa, beta), y esa theta."""
        mejor = max(((self.rng.betavariate(a, b), v) for v, (a, b) in self.post[p].items()))
        return mejor[1], mejor[0]

    def proponer(self, eje: str, base: Dict[str, str], fijados: Optional[List[str]] = None) -> Dict:
        """5 configuraciones para la ronda: los 5 valores de `eje` y, en cada propuesta,
        los parámetros no fijados por Thompson. `base` trae los 6 parámetros; `fijados`
        son los que el usuario fijó y no se muestrean (p. ej. edad y ambiente que
        confirmó a partir de la historia)."""
        if eje not in config.PARAMETROS or len(config.PARAMETROS[eje]) != 5:
            raise ValueError(f"Eje inválido: {eje}")
        fijos = dict(base)
        libres = [p for p in self.ejes if p != eje and p not in (fijados or [])]
        configs, muestreo = [], []
        for valor in config.PARAMETROS[eje]:
            cfg = dict(fijos)
            cfg[eje] = valor
            info = {}
            for p in libres:
                cfg[p], theta = self._muestrear(p)
                info[p] = {"valor": cfg[p], "theta": round(theta, 3)}
            configs.append(cfg)
            muestreo.append(info)
        return {"axis": eje, "configs": configs, "sampled": muestreo, "free": libres}

    # ------------------------------------------------------------------ resumen
    def estado(self) -> Dict:
        """Media posterior alfa/(alfa+beta) por valor; sirve para el registro y el resumen."""
        return {p: {v: round(a / (a + b), 3) for v, (a, b) in vals.items()}
                for p, vals in self.post.items()}

    def favoritos(self, minimo: float = 0.6) -> Dict[str, str]:
        """Valores que el usuario prefiere de verdad: solo parámetros que el planificador puede
        variar y que se probaron con al menos dos valores distintos, y solo si un valor gana de
        forma única (un empate no es una preferencia). Un parámetro que nunca cambió acumula
        aceptaciones solo por estar siempre presente, así que no cuenta."""
        salida = {}
        medias = self.estado()
        for p in self.ejes:
            if len(self.vistos[p]) < 2:
                continue
            ordenados = sorted(medias[p].items(), key=lambda kv: kv[1], reverse=True)
            (v, m), (_, segundo) = ordenados[0], ordenados[1]
            if m >= minimo and m > segundo:
                salida[p] = v
        return salida


class Sesion:
    """Control de rondas: eje nuevo por ronda, máximo 3, y registro para el resumen."""

    def __init__(self, base: Dict[str, str], motor: str = "A", semilla: int = config.SEMILLA_GLOBAL,
                 fijados: Optional[List[str]] = None):
        activos = [p for p in EJES_VARIABLES if not (motor == "B" and p == "P5")]
        self.base = dict(base)
        self.fijados = list(fijados or [])
        self.planificador = Planificador(semilla, activos)
        self.rondas: List[Dict] = []
        self.planes: List[Dict] = []

    @property
    def numero(self) -> int:
        """Número de la ronda que toca (1, 2, 3...)."""
        return len(self.rondas) + 1

    def ejes_disponibles(self) -> List[str]:
        usados = {r["axis"] for r in self.rondas}
        return [p for p in self.planificador.ejes if p not in usados]

    def terminada(self) -> bool:
        return len(self.rondas) >= MAX_RONDAS

    def configs_ronda(self, eje: str) -> Dict:
        """Ronda 1: los 5 valores del eje con el resto en `base`. Rondas 2 y 3: Thompson."""
        if self.terminada():
            raise ValueError(f"Máximo {MAX_RONDAS} rondas.")
        if eje not in self.ejes_disponibles():
            raise ValueError(f"El eje {eje} ya se usó o no está disponible.")
        if not self.rondas:
            from .motores.prompts import configuraciones_por_eje
            plan = {"axis": eje, "configs": configuraciones_por_eje(self.base, eje),
                    "sampled": [{} for _ in range(5)], "free": []}
        else:
            plan = self.planificador.proponer(eje, self.base, self.fijados)
        plan["round"] = self.numero
        self.planes.append(plan)
        return plan

    def cerrar_ronda(self, ronda: Dict) -> None:
        """Registra la ronda ya decidida y actualiza las distribuciones."""
        for v in ronda["variations"]:
            if "reason_axes" not in v:
                v["reason_axes"] = ejes_de_motivos(v.get("reasons"))
        self.planificador.actualizar(ronda)
        ronda["planner"] = self.bloque_planificador()
        self.rondas.append(ronda)

    def bloque_planificador(self) -> Dict:
        """Lo que el agente de resumen puede afirmar sobre las decisiones del planificador."""
        plan = self.planes[-1] if self.planes else {}
        return {
            "method": "thompson" if len(self.rondas) >= 1 else "eje completo (ronda 1)",
            "free_params": plan.get("free", []),
            "sampled": plan.get("sampled", []),
            "posterior_mean": self.planificador.estado(),
            "favorites": self.planificador.favoritos(),
        }
