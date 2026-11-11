"""Traducción de parámetros a prompts y armado de las cinco configuraciones de una ronda."""
from __future__ import annotations

from typing import Dict, List, Optional

from .. import config

EJES_VALIDOS = ("P1", "P2", "P3", "P4", "P5", "P6")


def validar_configuracion(cfg: Dict[str, str]) -> None:
    for p, valores in config.PARAMETROS.items():
        if p not in cfg:
            raise ValueError(f"Falta el parámetro {p}")
        if cfg[p] not in valores:
            raise ValueError(f"Valor inválido para {p}: {cfg[p]!r}. Opciones: {list(valores)}")


def escena_desde_elementos(elementos: Optional[Dict]) -> str:
    """Convierte la salida del agente de historia en la parte de escena del prompt.

    elementos = {"personajes": [...], "objetos": [...], "lugar": "...", "momento": "..."}
    Los elementos deben estar en inglés (el agente devuelve ambos idiomas).
    """
    if not elementos:
        return ""
    personajes = [p for p in elementos.get("personajes", []) if p]
    objetos = [o for o in elementos.get("objetos", []) if o]
    partes = []
    if personajes:
        partes.append(" and ".join(f"a {p}" for p in personajes))
    if objetos:
        partes.append("with " + ", ".join(objetos))
    if elementos.get("lugar"):
        partes.append(f"in a {elementos['lugar']}")
    if elementos.get("momento"):
        partes.append(f"at {elementos['momento']}")
    return " ".join(partes)


def construir_prompt(cfg: Dict[str, str], escena: str = "", instruccion: str = "") -> Dict[str, str]:
    """Arma prompt y prompt negativo.

    El orden importa: CLIP solo lee 77 tokens, así que primero va lo más
    importante (estilo, tipo de imagen, escena) y al final lo accesorio.
    """
    validar_configuracion(cfg)
    partes: List[str] = [
        config.ESTILOS[cfg["P1"]],
        config.BASE_PROMPT,
        escena,
        config.PALETAS[cfg["P2"]],
        config.AMBIENTES[cfg["P4"]],
        config.EDADES[cfg["P3"]],
        config.ZONAS_TITULO[cfg["P6"]]["prompt"],
        instruccion,
    ]
    prompt = ", ".join(p.strip() for p in partes if p and p.strip())
    return {"prompt": prompt, "negativo": config.NEGATIVO}


def configuraciones_por_eje(base: Dict[str, str], eje: str) -> List[Dict[str, str]]:
    """Ronda 1 (y modo individual): las cinco propuestas toman los cinco valores del eje
    y comparten el resto de parámetros. El planificador de la etapa 5 reemplaza esta
    función en las rondas siguientes."""
    if eje not in EJES_VALIDOS:
        raise ValueError(f"Eje inválido: {eje}")
    valores = list(config.PARAMETROS[eje])
    if len(valores) != 5:
        raise ValueError(f"El eje {eje} debe tener exactamente 5 valores")
    salida = []
    for v in valores:
        cfg = dict(base)
        cfg[eje] = v
        validar_configuracion(cfg)
        salida.append(cfg)
    return salida
