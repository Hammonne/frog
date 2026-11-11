"""Guardrails sobre cada portada generada (guardrails 3 y 4 de la sección 12).

El filtro de seguridad de Stable Diffusion solo apunta a contenido sexual
(Rando et al., 2022), así que se suma una verificación zero-shot con CLIP contra
descriptores de contenido no apto para niños.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from PIL import Image

from .. import config

DESCRIPTORES_NO_APTOS = [
    "a scary horror image",
    "blood and gore",
    "a person holding a weapon",
    "a violent fight",
    "a frightening monster attacking",
    "nudity",
]
DESCRIPTORES_APTOS = [
    "a friendly children's book illustration",
    "a cute and happy picture for kids",
    "a calm illustration of nature",
]


@dataclass
class ResultadoSalida:
    ok: bool
    motivos: List[str] = field(default_factory=list)
    prob_no_apto: float = 0.0
    descriptor: str = ""


class RevisorSalida:
    def __init__(self, evaluador_clip=None, umbral: float = config.UMBRAL_CLIP_NO_APTO):
        """evaluador_clip: instancia de metricas.clip_metricas.EvaluadorCLIP (o None
        para usar solo el filtro de SD, p. ej. en pruebas)."""
        self.clip = evaluador_clip
        self.umbral = umbral

    def revisar(self, img: Image.Image, nsfw_sd: Optional[bool] = None) -> ResultadoSalida:
        res = ResultadoSalida(ok=True)
        if nsfw_sd:
            res.ok = False
            res.motivos.append("filtro_sd")
        if self.clip is not None:
            etiquetas = DESCRIPTORES_NO_APTOS + DESCRIPTORES_APTOS
            probs = self.clip.zero_shot(img, etiquetas)
            no_aptos = {e: probs[e] for e in DESCRIPTORES_NO_APTOS}
            peor = max(no_aptos, key=no_aptos.get)
            res.prob_no_apto = float(sum(no_aptos.values()))
            res.descriptor = peor
            if res.prob_no_apto >= self.umbral:
                res.ok = False
                res.motivos.append("clip_no_apto")
        return res
