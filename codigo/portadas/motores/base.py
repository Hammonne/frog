"""Interfaz común de los motores generativos."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol

from PIL import Image


@dataclass
class Peticion:
    """Una de las cinco propuestas de la ronda."""
    id: str
    params: Dict[str, str]
    prompt: str
    negativo: str
    semilla: int
    escala_control: float        # P5 traducido al motor
    pasos: int = 25
    guia: float = 7.0


@dataclass
class Resultado:
    peticion: Peticion
    imagen: Optional[Image.Image]
    motor: str
    latencia_s: float
    nsfw_sd: Optional[bool] = None       # filtro de seguridad de SD (motor A)
    error: str = ""
    extra: Dict = field(default_factory=dict)


class Motor(Protocol):
    nombre: str

    def generar(self, control, peticiones: List[Peticion], **kw) -> List[Resultado]:
        ...


class MotorNoDisponible(RuntimeError):
    """El motor no puede usarse (sin GPU, sin clave de API, cuota agotada...)."""
