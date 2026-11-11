"""Diversidad intra-ronda (LPIPS medio entre los 10 pares) y KID/FID frente a D1."""
from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Sequence

import numpy as np
from PIL import Image


class EvaluadorLPIPS:
    def __init__(self, red: str = "alex", device: str = None):
        import lpips
        import torch

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.modelo = lpips.LPIPS(net=red, verbose=False).to(self.device).eval()

    def _tensor(self, img: Image.Image):
        a = np.asarray(img.convert("RGB").resize((256, 384)), dtype=np.float32) / 127.5 - 1.0
        return self.torch.from_numpy(a).permute(2, 0, 1).unsqueeze(0).to(self.device)

    def distancia(self, a: Image.Image, b: Image.Image) -> float:
        with self.torch.no_grad():
            return float(self.modelo(self._tensor(a), self._tensor(b)).item())

    def diversidad_ronda(self, imgs: Sequence[Image.Image]) -> float:
        pares = list(combinations(range(len(imgs)), 2))
        return float(np.mean([self.distancia(imgs[i], imgs[j]) for i, j in pares]))


def kid_fid(reales: List[Image.Image], generadas: List[Image.Image],
            subset_size: int = 50) -> Dict[str, float]:
    """KID (menos sesgado con muestras pequeñas) y FID con torchmetrics."""
    import torch
    from torchmetrics.image.fid import FrechetInceptionDistance
    from torchmetrics.image.kid import KernelInceptionDistance

    def lote(imgs):
        arr = np.stack([np.asarray(i.convert("RGB").resize((299, 299))) for i in imgs])
        return torch.from_numpy(arr).permute(0, 3, 1, 2)

    subset = min(subset_size, len(reales), len(generadas))
    kid = KernelInceptionDistance(subset_size=subset)
    fid = FrechetInceptionDistance(feature=2048)
    for metrica in (kid, fid):
        for i in range(0, len(reales), 64):
            metrica.update(lote(reales[i:i + 64]), real=True)
        for i in range(0, len(generadas), 64):
            metrica.update(lote(generadas[i:i + 64]), real=False)
    kid_media, kid_std = kid.compute()
    return {"kid": float(kid_media), "kid_std": float(kid_std), "fid": float(fid.compute())}
