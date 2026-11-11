"""Motor B (nivel básico): SD-Turbo preentrenado en modo img2img, sin control adicional.

Es gratuito y corre en la misma GPU de Colab que el motor A. Parte del boceto (negro
sobre blanco) y lo reinterpreta con el prompt en 1-4 pasos (Sauer et al., 2023).
Sirve como respaldo rápido y como línea base: al no tener ControlNet, permite medir
cuánto aporta el control estructural del motor A.

La fidelidad (P5) se traduce en `strength`: más fidelidad = menos ruido sobre el boceto.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List

from PIL import Image

from .. import config
from .base import MotorNoDisponible, Peticion, Resultado


def pasos_efectivos(pasos: int, strength: float) -> int:
    """img2img aplica int(pasos * strength) pasos; debe ser al menos 1."""
    return max(1, int(pasos * strength))


class MotorB:
    nombre = "B"

    def __init__(self, device: str = "cuda", pasos: int = config.PASOS_TURBO):
        try:
            import torch
            from diffusers import AutoPipelineForImage2Image
        except ImportError as e:  # pragma: no cover
            raise MotorNoDisponible(f"Faltan dependencias del motor B: {e}")
        if device == "cuda" and not torch.cuda.is_available():
            raise MotorNoDisponible("No hay GPU disponible para el motor B.")
        self.torch = torch
        self.device = device
        dtype = torch.float16 if device == "cuda" else torch.float32
        kw = {"variant": "fp16"} if device == "cuda" else {}
        pipe = AutoPipelineForImage2Image.from_pretrained(config.MODELO_TURBO, torch_dtype=dtype, **kw)
        pipe.set_progress_bar_config(disable=True)
        self.pipe = pipe.to(device)
        self.pasos = pasos

    def generar(self, lineas: Image.Image, peticiones: List[Peticion], **_) -> List[Resultado]:
        inicial = lineas.convert("RGB").resize((config.ANCHO, config.ALTO))
        grupos: Dict[float, List[Peticion]] = defaultdict(list)
        for p in peticiones:
            grupos[p.escala_control].append(p)
        resultados: Dict[str, Resultado] = {}
        torch = self.torch
        for strength, grupo in grupos.items():
            if pasos_efectivos(self.pasos, strength) < 1:
                raise ValueError("strength demasiado bajo para el número de pasos")
            gens = [torch.Generator(device="cpu").manual_seed(p.semilla) for p in grupo]
            inicio = time.perf_counter()
            salida = self.pipe(
                prompt=[p.prompt for p in grupo],
                image=[inicial] * len(grupo),
                strength=float(strength),
                num_inference_steps=self.pasos,
                guidance_scale=0.0,  # SD-Turbo se usa sin guía; por eso ignora el prompt negativo
                generator=gens,
            )
            if self.device == "cuda":
                torch.cuda.synchronize()
            latencia = (time.perf_counter() - inicio) / len(grupo)
            nsfw = getattr(salida, "nsfw_content_detected", None) or [None] * len(grupo)
            for p, img, f in zip(grupo, salida.images, nsfw):
                resultados[p.id] = Resultado(p, img.resize((config.ANCHO, config.ALTO)), self.nombre, latencia,
                                             nsfw_sd=bool(f) if f is not None else None,
                                             extra={"modelo": config.MODELO_TURBO, "strength": strength,
                                                    "pasos_efectivos": pasos_efectivos(self.pasos, strength)})
        return [resultados[p.id] for p in peticiones]
