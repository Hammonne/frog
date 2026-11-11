"""Métricas basadas en CLIP: CLIPScore, clasificación zero-shot del estilo y
detección de los elementos de la historia. Requiere torch y transformers (Colab)."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from PIL import Image

from .. import config

PLANTILLAS_ESTILO = {
    "acuarela": "a watercolor painting",
    "lapices": "a colored pencil drawing",
    "collage": "a cut paper collage",
    "vectorial": "a flat vector illustration",
    "plastilina": "a 3D clay render",
}

DISTRACTORES = [
    "cat", "dog", "rabbit", "bear", "fish", "bird", "tree", "house", "sun", "dragon",
    "car", "boat", "flower", "moon", "star", "mountain", "girl", "boy", "ball", "cake",
]


class EvaluadorCLIP:
    def __init__(self, modelo: str = config.MODELO_CLIP, device: Optional[str] = None):
        import torch
        from transformers import CLIPModel, CLIPProcessor

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.modelo = CLIPModel.from_pretrained(modelo).to(self.device).eval()
        self.proc = CLIPProcessor.from_pretrained(modelo)

    def _emb_img(self, imgs: Sequence[Image.Image]):
        with self.torch.no_grad():
            x = self.proc(images=list(imgs), return_tensors="pt").to(self.device)
            e = self.modelo.get_image_features(**x)
        return e / e.norm(dim=-1, keepdim=True)

    def _emb_txt(self, textos: Sequence[str]):
        with self.torch.no_grad():
            x = self.proc(text=list(textos), return_tensors="pt", padding=True,
                          truncation=True).to(self.device)
            e = self.modelo.get_text_features(**x)
        return e / e.norm(dim=-1, keepdim=True)

    def clipscore(self, img: Image.Image, texto: str) -> float:
        """CLIPScore = 2.5 * max(cos, 0) (Hessel et al., 2021)."""
        cos = (self._emb_img([img]) @ self._emb_txt([texto]).T).item()
        return 2.5 * max(cos, 0.0)

    def zero_shot(self, img: Image.Image, etiquetas: List[str]) -> Dict[str, float]:
        logits = 100.0 * self._emb_img([img]) @ self._emb_txt(etiquetas).T
        probs = logits.softmax(dim=-1)[0].tolist()
        return dict(zip(etiquetas, probs))

    def estilo_predicho(self, img: Image.Image) -> str:
        probs = self.zero_shot(img, list(PLANTILLAS_ESTILO.values()))
        inverso = {v: k for k, v in PLANTILLAS_ESTILO.items()}
        return inverso[max(probs, key=probs.get)]

    def elementos_detectados(self, img: Image.Image, elementos: List[str],
                             top_k: int = 3) -> Dict[str, bool]:
        """Un elemento se considera presente si queda entre los top_k de una lista
        con distractores. Es una aproximación: CLIP no localiza objetos."""
        candidatos = list(dict.fromkeys(list(elementos) + DISTRACTORES))
        textos = [f"an illustration of a {c}" for c in candidatos]
        probs = self.zero_shot(img, textos)
        orden = sorted(candidatos, key=lambda c: -probs[f"an illustration of a {c}"])
        return {e: e in orden[:top_k] for e in elementos}
