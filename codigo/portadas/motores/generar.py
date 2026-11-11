"""Una ronda completa: 5 configuraciones -> motor -> guardrails de salida -> registro.

- Si el motor A no está disponible o se queda sin memoria, se usa el motor B (respaldo).
- Si una portada no pasa los guardrails, se regenera con otra semilla
  (máximo config.MAX_REGENERACIONES); si persiste, la tarjeta queda vacía con el motivo.
- Devuelve diccionarios compatibles con el registro JSON de la sección 8.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from PIL import Image

from .. import config
from ..guardrails.salida import ResultadoSalida, RevisorSalida
from ..guardrails.texto import filtrar_texto
from ..preprocesamiento import Boceto
from .base import MotorNoDisponible, Peticion, Resultado
from .prompts import configuraciones_por_eje, construir_prompt


def peticiones_ronda(configs: List[Dict[str, str]], motor: str, escena: str = "",
                     instruccion: str = "", semillas: Optional[List[int]] = None,
                     ronda: int = 1, pasos: int = config.PASOS,
                     guia: float = config.GUIA) -> List[Peticion]:
    semillas = semillas or [s + 1000 * (ronda - 1) for s in config.SEMILLAS_RONDA_1]
    if len(configs) != 5 or len(semillas) != 5:
        raise ValueError("Una ronda tiene exactamente 5 propuestas.")
    clave = "controlnet" if motor == "A" else "turbo"
    salida = []
    for i, (cfg, semilla) in enumerate(zip(configs, semillas), start=1):
        pr = construir_prompt(cfg, escena=escena, instruccion=instruccion)
        salida.append(Peticion(
            id=f"R{ronda}-V{i}", params=dict(cfg), prompt=pr["prompt"], negativo=pr["negativo"],
            semilla=semilla, escala_control=config.FIDELIDAD[cfg["P5"]][clave], pasos=pasos, guia=guia,
        ))
    return salida


def _entrada_motor(motor_obj, boceto: Boceto):
    return boceto.control if motor_obj.nombre == "A" else boceto.lineas


def generar_ronda(boceto: Boceto, base: Dict[str, str], eje: str,
                  motores: Dict[str, object], motor_preferido: str = "A",
                  escena: str = "", instruccion: str = "", ronda: int = 1,
                  configs: Optional[List[Dict[str, str]]] = None,
                  revisor: Optional[RevisorSalida] = None,
                  semillas: Optional[List[int]] = None,
                  usar_img2img: bool = False, strength: float = 0.75) -> Dict:
    """`motores` = {"A": MotorA(...), "B": MotorB(...)}; puede faltar cualquiera.
    `configs` permite que el planificador (etapa 5) decida las 5 configuraciones;
    si no se pasa, se usan los 5 valores del eje (ronda 1 / modo individual)."""
    for texto in (instruccion, escena):
        filtro = filtrar_texto(texto)
        if not filtro.ok:
            raise ValueError(f"Texto bloqueado por guardrail: {filtro.motivos}")
    configs = configs or configuraciones_por_eje(base, eje)
    revisor = revisor or RevisorSalida(None)

    orden = [motor_preferido] + [m for m in ("A", "B") if m != motor_preferido]
    disponibles = [m for m in orden if motores.get(m) is not None]
    if not disponibles:
        raise MotorNoDisponible("No hay ningún motor disponible.")

    inicio = time.perf_counter()
    resultados: Optional[List[Resultado]] = None
    motor_usado, errores = None, []
    for nombre in disponibles:
        m = motores[nombre]
        peticiones = peticiones_ronda(configs, nombre, escena, instruccion, semillas, ronda)
        try:
            kw = {}
            if nombre == "A" and usar_img2img and boceto.color_original is not None:
                kw = {"imagen_inicial": boceto.color_original, "strength": strength}
            resultados = m.generar(_entrada_motor(m, boceto), peticiones, **kw)
            motor_usado = nombre
            break
        except MotorNoDisponible as e:
            errores.append(f"{nombre}: {e}")
    if resultados is None:
        raise MotorNoDisponible("; ".join(errores))

    variaciones = []
    m = motores[motor_usado]
    for res in resultados:
        res, revision, regeneraciones = _con_guardrails(m, boceto, res, revisor)
        variaciones.append(_a_registro(res, revision, regeneraciones))
    return {
        "round": ronda,
        "axis": eje,
        "engine": motor_usado,
        "fallback_errors": errores,
        "fixed": {k: v for k, v in base.items() if k != eje},
        "scene": escena,
        "instruction": instruccion,
        "latency_round_s": time.perf_counter() - inicio,
        "variations": variaciones,
    }


def _con_guardrails(motor, boceto: Boceto, res: Resultado, revisor: RevisorSalida):
    regeneraciones = 0
    revision = _revisar(res, revisor)
    while not revision.ok and regeneraciones < config.MAX_REGENERACIONES:
        regeneraciones += 1
        p = res.peticion
        nueva = Peticion(**{**p.__dict__, "semilla": p.semilla + 7919 * regeneraciones})
        try:
            res = motor.generar(_entrada_motor(motor, boceto), [nueva])[0]
        except MotorNoDisponible:
            break
        res.peticion = Peticion(**{**nueva.__dict__, "id": p.id})
        revision = _revisar(res, revisor)
    if not revision.ok:
        res.imagen = None  # tarjeta vacía con el motivo
    return res, revision, regeneraciones


def _revisar(res: Resultado, revisor: RevisorSalida) -> ResultadoSalida:
    if res.imagen is None:
        return ResultadoSalida(ok=False, motivos=[res.error or "sin_imagen"])
    return revisor.revisar(res.imagen, nsfw_sd=res.nsfw_sd)


def _a_registro(res: Resultado, revision: ResultadoSalida, regeneraciones: int) -> Dict:
    p = res.peticion
    return {
        "id": p.id,
        "params": p.params,
        "prompt": p.prompt,
        "negative_prompt": p.negativo,
        "seed": p.semilla,
        "control_scale": p.escala_control,
        "engine": res.motor,
        "latency_s": round(res.latencia_s, 3),
        "guardrails": {
            "output": "ok" if revision.ok else "bloqueada",
            "reasons": revision.motivos,
            "p_not_child_safe": round(revision.prob_no_apto, 4),
            "regenerations": regeneraciones,
        },
        "error": res.error,
        "image": res.imagen,  # PIL.Image o None; el registro JSON guarda la ruta, no la imagen
        "decision": None,     # lo completa la interfaz (etapa 4)
    }


def guardar_imagenes(ronda: Dict, carpeta, prefijo: str = "") -> Dict:
    """Guarda las imágenes en disco y reemplaza el objeto PIL por la ruta, para poder
    serializar el registro a JSON."""
    from pathlib import Path

    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    for v in ronda["variations"]:
        img = v.pop("image", None)
        if isinstance(img, Image.Image):
            ruta = carpeta / f"{prefijo}{v['id']}.png"
            img.save(ruta)
            v["image_path"] = str(ruta)
        else:
            v["image_path"] = None
    return ronda
