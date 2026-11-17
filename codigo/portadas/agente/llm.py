"""LLM abiertos ejecutados en la sesión de Colab (Qwen2.5-7B y Phi-3.5-mini, 4 bits, temperatura 0).

Ningún texto sale de la sesión: la historia del usuario y el registro se procesan en local.
Los agentes reciben cualquier objeto invocable `llm(mensajes) -> str`, así que las pruebas
usan un LLM falso y no necesitan GPU.

Colab trae transformers 5: se usa apply_chat_template + generate (no `pipeline`).
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from .. import config

Mensajes = List[Dict[str, str]]  # [{"role": "system"|"user"|"assistant", "content": "..."}]


class LLMLocal:
    def __init__(self, nombre: str = "qwen", cuatro_bits: bool = True, device: str = "cuda"):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.nombre = nombre
        self.modelo_id = config.LLMS.get(nombre, nombre)
        self.torch = torch
        kw = {"torch_dtype": torch.float16 if device == "cuda" else torch.float32}
        if cuatro_bits and device == "cuda":
            from transformers import BitsAndBytesConfig

            kw["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4")
            kw["device_map"] = "auto"
        self.tok = AutoTokenizer.from_pretrained(self.modelo_id)
        self.modelo = AutoModelForCausalLM.from_pretrained(self.modelo_id, **kw)
        if "device_map" not in kw:
            self.modelo.to(device)
        self.modelo.eval()
        self.ultima_latencia_s: Optional[float] = None

    def __call__(self, mensajes: Mensajes, max_tokens: int = config.MAX_TOKENS_RESUMEN) -> str:
        # Plantilla a texto y luego tokenizar: funciona igual en transformers 4 y 5.
        texto = self.tok.apply_chat_template(mensajes, tokenize=False, add_generation_prompt=True)
        x = self.tok(texto, return_tensors="pt").to(self.modelo.device)
        inicio = time.perf_counter()
        with self.torch.no_grad():
            salida = self.modelo.generate(
                **x, max_new_tokens=max_tokens, do_sample=False,  # temperatura 0 (greedy)
                pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id)
        self.ultima_latencia_s = time.perf_counter() - inicio
        nuevos = salida[0][x["input_ids"].shape[1]:]
        return self.tok.decode(nuevos, skip_special_tokens=True).strip()

    def liberar(self) -> None:
        """Libera la GPU antes de cargar el otro LLM (en una T4 no caben los dos a la vez
        junto con Stable Diffusion)."""
        del self.modelo
        import gc

        gc.collect()
        if self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()


def extraer_json(texto: str):
    """Devuelve el último objeto JSON válido que aparezca en el texto (o None).
    Tolera bloques ```json ... ``` y texto antes o después."""
    import json

    texto = texto.replace("```json", "```")
    candidatos = []
    pila, inicio = 0, None
    for i, c in enumerate(texto):
        if c == "{":
            if pila == 0:
                inicio = i
            pila += 1
        elif c == "}" and pila:
            pila -= 1
            if pila == 0 and inicio is not None:
                candidatos.append(texto[inicio:i + 1])
    for c in reversed(candidatos):
        try:
            return json.loads(c)
        except json.JSONDecodeError:
            continue
    return None
