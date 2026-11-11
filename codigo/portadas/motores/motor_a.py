"""Motor A (nivel intermedio): Stable Diffusion 1.5 + ControlNet 1.1 en local (Colab T4).

- `scribble` para bocetos y `lineart` para dibujos de líneas limpias.
- Las peticiones con la misma escala de ControlNet se generan en un solo lote.
- Modo img2img opcional para fotos de dibujos coloreados (conserva sus colores).
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Optional

from PIL import Image

from .. import config
from .base import MotorNoDisponible, Peticion, Resultado


class MotorA:
    nombre = "A"

    def __init__(self, device: str = "cuda", tipo_inicial: str = "scribble",
                 cpu_offload: bool = False):
        try:
            import torch
            from diffusers import (ControlNetModel, DPMSolverMultistepScheduler,
                                   StableDiffusionControlNetPipeline)
        except ImportError as e:  # pragma: no cover
            raise MotorNoDisponible(f"Faltan dependencias del motor A: {e}")
        if device == "cuda" and not torch.cuda.is_available():
            raise MotorNoDisponible("No hay GPU disponible para el motor A.")
        self.torch = torch
        self.device = device
        dtype = torch.float16 if device == "cuda" else torch.float32
        self._dtype = dtype
        self._ControlNetModel = ControlNetModel
        self._controlnets: Dict[str, object] = {}
        cn = self._controlnet(tipo_inicial)
        pipe = StableDiffusionControlNetPipeline.from_pretrained(
            config.MODELO_BASE, controlnet=cn, torch_dtype=dtype)
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            pipe.scheduler.config, algorithm_type="dpmsolver++", use_karras_sigmas=True)
        pipe.set_progress_bar_config(disable=True)
        pipe.enable_attention_slicing()
        pipe.enable_vae_slicing()
        if cpu_offload:
            pipe.enable_model_cpu_offload()
        else:
            pipe = pipe.to(device)
        self.pipe = pipe
        self.tipo = tipo_inicial
        self._img2img = None
        self.lora: Optional[Dict] = None

    # ------------------------------------------------------------------ modelos
    def _controlnet(self, tipo: str):
        if tipo not in self._controlnets:
            self._controlnets[tipo] = self._ControlNetModel.from_pretrained(
                config.CONTROLNETS[tipo], torch_dtype=self._dtype)
        return self._controlnets[tipo]

    def usar_controlnet(self, tipo: str) -> None:
        if tipo == self.tipo:
            return
        cn = self._controlnet(tipo).to(self.device)
        self.pipe.controlnet = cn
        if self._img2img is not None:
            self._img2img.controlnet = cn
        self.tipo = tipo

    def cargar_lora(self, repo_o_ruta: str, escala: float = 0.8, weight_name: Optional[str] = None) -> None:
        """Experimento opcional: solo con LoRAs de licencia compatible y sin nombre de artista."""
        self.pipe.load_lora_weights(repo_o_ruta, weight_name=weight_name, adapter_name="infantil")
        self.pipe.set_adapters(["infantil"], adapter_weights=[escala])
        self.lora = {"repo": repo_o_ruta, "escala": escala}

    def quitar_lora(self) -> None:
        if self.lora:
            self.pipe.unload_lora_weights()
            self.lora = None

    def _pipe_img2img(self):
        if self._img2img is None:
            from diffusers import StableDiffusionControlNetImg2ImgPipeline
            self._img2img = StableDiffusionControlNetImg2ImgPipeline(**self.pipe.components)
            self._img2img.set_progress_bar_config(disable=True)
        return self._img2img

    # --------------------------------------------------------------- generación
    def generar(self, control: Image.Image, peticiones: List[Peticion],
                imagen_inicial: Optional[Image.Image] = None, strength: float = 0.75,
                tipo_control: Optional[str] = None) -> List[Resultado]:
        if tipo_control:
            self.usar_controlnet(tipo_control)
        grupos: Dict[tuple, List[Peticion]] = defaultdict(list)
        for p in peticiones:
            grupos[(p.escala_control, p.pasos, p.guia)].append(p)
        resultados: Dict[str, Resultado] = {}
        for (escala, pasos, guia), grupo in grupos.items():
            resultados.update(self._lote(control, grupo, escala, pasos, guia, imagen_inicial, strength))
        return [resultados[p.id] for p in peticiones]

    def _lote(self, control, grupo, escala, pasos, guia, imagen_inicial, strength):
        torch = self.torch
        gens = [torch.Generator(device="cpu").manual_seed(p.semilla) for p in grupo]
        kwargs = dict(
            prompt=[p.prompt for p in grupo],
            negative_prompt=[p.negativo for p in grupo],
            num_inference_steps=pasos,
            guidance_scale=guia,
            controlnet_conditioning_scale=float(escala),
            generator=gens,
            width=config.ANCHO,
            height=config.ALTO,
        )
        if self.lora:
            kwargs["cross_attention_kwargs"] = {"scale": self.lora["escala"]}
        inicio = time.perf_counter()
        try:
            if imagen_inicial is not None:
                kwargs.pop("width"), kwargs.pop("height")
                salida = self._pipe_img2img()(image=[imagen_inicial] * len(grupo),
                                              control_image=[control] * len(grupo),
                                              strength=strength, **kwargs)
            else:
                salida = self.pipe(image=[control] * len(grupo), **kwargs)
            if self.device == "cuda":
                torch.cuda.synchronize()
        except torch.cuda.OutOfMemoryError as e:  # pragma: no cover
            torch.cuda.empty_cache()
            raise MotorNoDisponible(f"Memoria de GPU insuficiente: {e}")
        latencia = (time.perf_counter() - inicio) / len(grupo)
        nsfw = salida.nsfw_content_detected or [None] * len(grupo)
        return {
            p.id: Resultado(peticion=p, imagen=img, motor=self.nombre, latencia_s=latencia,
                            nsfw_sd=bool(f) if f is not None else None,
                            extra={"controlnet": self.tipo, "lora": self.lora})
            for p, img, f in zip(grupo, salida.images, nsfw)
        }
