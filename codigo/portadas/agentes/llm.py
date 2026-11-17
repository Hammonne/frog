"""Modelo de lenguaje local (Hugging Face, en la misma sesión de Colab).

El texto del usuario nunca sale de la sesión: no se usan APIs externas. Temperatura 0
(decodificación determinista). Los dos modelos del informe son intercambiables:
`qwen2.5-7b` y `phi-3.5-mini`.
"""
from __future__ import annotations

from typing import Callable, Optional

MODELOS = {
    "qwen2.5-7b": "Qwen/Qwen2.5-7B-Instruct",
    "phi-3.5-mini": "microsoft/Phi-3.5-mini-instruct",
}

# Un generador es una función (prompt_de_sistema, mensaje_del_usuario) -> texto.
# Los agentes reciben cualquiera, así que se prueban en CPU con un generador falso.
Generador = Callable[[str, str], str]


class LLMLocal:
    def __init__(self, nombre: str = "qwen2.5-7b", cuantizar_4bit: Optional[bool] = None,
                 max_tokens: int = 900):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if nombre not in MODELOS:
            raise ValueError(f"Modelo desconocido {nombre!r}. Opciones: {list(MODELOS)}")
        self.nombre = nombre
        self.max_tokens = max_tokens
        repo = MODELOS[nombre]
        if cuantizar_4bit is None:
            # Con poca memoria (T4, 16 GB) el modelo de 7B necesita 4 bits.
            memoria = torch.cuda.get_device_properties(0).total_memory / 2**30 if torch.cuda.is_available() else 0
            cuantizar_4bit = memoria < 24
        kw = {}
        if cuantizar_4bit:
            from transformers import BitsAndBytesConfig
            kw["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4")
        else:
            kw["dtype"] = torch.float16
        self.tok = AutoTokenizer.from_pretrained(repo)
        self.modelo = AutoModelForCausalLM.from_pretrained(repo, device_map="auto", **kw)
        self.modelo.eval()
        self.torch = torch

    def __call__(self, sistema: str, mensaje: str) -> str:
        chat = [{"role": "system", "content": sistema}, {"role": "user", "content": mensaje}]
        entrada = self.tok.apply_chat_template(chat, add_generation_prompt=True, return_tensors="pt",
                                               return_dict=True).to(self.modelo.device)
        with self.torch.no_grad():
            salida = self.modelo.generate(**entrada, max_new_tokens=self.max_tokens, do_sample=False,
                                          pad_token_id=self.tok.eos_token_id)
        nuevos = salida[0, entrada["input_ids"].shape[1]:]
        return self.tok.decode(nuevos, skip_special_tokens=True).strip()

    def liberar(self) -> None:
        """Libera la GPU (útil para cambiar de modelo o cargar los motores de imagen)."""
        import gc
        del self.modelo
        gc.collect()
        self.torch.cuda.empty_cache()
