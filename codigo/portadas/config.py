"""Parámetros del sistema (Tabla 1 del informe) y valores por defecto.

Todos los valores son iniciales: la calibración (experimentos/calibracion.py)
y el análisis exploratorio de D1 (datos/eda.py) los ajustan.
"""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "datos"
SALIDAS = RAIZ / "salidas"

# Formato de portada: vertical 2:3, múltiplo de 8 para el VAE de SD 1.5.
ANCHO, ALTO = 512, 768

# ---------------------------------------------------------------------------
# P1 Estilo de ilustración: técnicas genéricas, nunca nombres de artistas.
ESTILOS = {
    "acuarela": "soft watercolor illustration, gentle washes of color, paper texture",
    "lapices": "colored pencil and crayon illustration, visible strokes",
    "collage": "cut paper collage illustration, layered paper shapes",
    "vectorial": "flat vector illustration, clean simple shapes, smooth colors",
    "plastilina": "clay 3D render, plasticine characters, soft studio light",
}

# P2 Paleta. Además del texto, cada paleta tiene un criterio medible
# (metricas/color.py::adherencia_paleta).
PALETAS = {
    "pastel": "pastel colors, soft light palette",
    "calida": "warm color palette, oranges, yellows and reds",
    "fria": "cool color palette, blues, teals and purples",
    "primarios": "vivid primary colors, bright saturated palette",
    "tierra": "earthy palette, ochre, brown and olive tones",
}

# P3 Edad del lector.
EDADES = {
    "0-3": "very simple shapes, one main character, bold outlines, high contrast",
    "4-6": "simple friendly scene, few elements",
    "7-9": "detailed scene with background",
    "10-12": "rich detailed illustration, dynamic composition",
    "sin": "",
}

# P4 Ambiente.
AMBIENTES = {
    "alegre": "cheerful happy mood, bright light",
    "aventura": "adventurous mood, sense of journey",
    "calma": "calm cozy bedtime mood, gentle warm light",
    "misterio": "gentle mystery, soft shadows, curious mood",
    "humor": "funny playful whimsical mood",
}

# P5 Fidelidad al boceto -> escala de ControlNet (motor A). En el motor B el strength es
# constante (0.90): no hay punto intermedio fiable (ver PASOS_TURBO).
FIDELIDAD = {
    "muy_baja": {"controlnet": 0.60, "turbo": 0.90},
    "baja": {"controlnet": 0.65, "turbo": 0.90},
    "media": {"controlnet": 0.70, "turbo": 0.90},
    "alta": {"controlnet": 0.75, "turbo": 0.90},
    "muy_alta": {"controlnet": 0.80, "turbo": 0.90},
}

# P6 Zona del título: texto para el prompt y fracción de la altura reservada
# (arriba, abajo) al ubicar el boceto en el lienzo.
ZONAS_TITULO = {
    "superior": {"prompt": "empty sky at the top, copy space at the top", "reserva": (0.28, 0.0)},
    "inferior": {"prompt": "empty space at the bottom, copy space at the bottom", "reserva": (0.0, 0.25)},
    "ambas": {"prompt": "empty space at the top and at the bottom", "reserva": (0.22, 0.16)},
    "centrada": {"prompt": "", "reserva": (0.0, 0.0)},
    "sin": {"prompt": "", "reserva": (0.0, 0.0)},
}

PARAMETROS = {
    "P1": ESTILOS,
    "P2": PALETAS,
    "P3": EDADES,
    "P4": AMBIENTES,
    "P5": FIDELIDAD,
    "P6": ZONAS_TITULO,
}

POR_DEFECTO = {
    "P1": "acuarela",
    "P2": "pastel",
    "P3": "4-6",
    "P4": "alegre",
    "P5": "media",
    "P6": "superior",
}

BASE_PROMPT = "children's picture book cover illustration"

NEGATIVO = (
    "text, letters, words, typography, watermark, signature, logo, "
    "scary, horror, violent, blood, gore, weapon, nsfw, nude, "
    "deformed, extra limbs, bad anatomy, lowres, blurry, jpeg artifacts"
)

# ---------------------------------------------------------------------------
# Modelos (repositorios de Hugging Face).
# El repo original runwayml/stable-diffusion-v1-5 fue retirado; este es el espejo oficial.
MODELO_BASE = "stable-diffusion-v1-5/stable-diffusion-v1-5"
CONTROLNETS = {
    "scribble": "lllyasviel/control_v11p_sd15_scribble",
    "lineart": "lllyasviel/control_v11p_sd15_lineart",
}
MODELO_CLIP = "openai/clip-vit-base-patch32"
# Motor B: SD-Turbo (Stability AI Community License; gratuito para uso académico).
MODELO_TURBO = "stabilityai/sd-turbo"
# Calibrado con experimentos/calibracion_b.py: SD-Turbo img2img no admite un punto
# intermedio entre copiar el boceto y reemplazarlo, así que el motor B reinterpreta
# libremente (strength 0.90, 10 pasos) y P5 (fidelidad) no aplica a este motor.
PASOS_TURBO = 10
# Radio del desenfoque del boceto de partida del motor B (0 = sin desenfoque).
SUAVIZADO_TURBO = 0.0

PASOS = 20
GUIA = 7.0
SEMILLAS_RONDA_1 = [101, 202, 303, 404, 505]

# Guardrails
TINTA_MIN = 0.005  # < 0.5 % de píxeles con trazo: boceto vacío
TINTA_MAX = 0.40   # > 40 %: boceto saturado
MAX_REGENERACIONES = 2
UMBRAL_CLIP_NO_APTO = 0.5  # se recalibra en E5
TIMEOUT_MOTOR_A_S = 90

# Datos
QUICKDRAW_CATEGORIAS = ["cat", "dog", "rabbit", "bear", "fish", "bird", "tree", "house", "sun", "dragon"]
QUICKDRAW_URL = "https://storage.googleapis.com/quickdraw_dataset/full/simplified/{categoria}.ndjson"
BOOK32_URL = "https://raw.githubusercontent.com/uchidalab/book-dataset/master/Task2/book32-listing.csv"
BOOK32_CATEGORIA_INFANTIL = "4"  # "Children's Books" (13 605 libros)
TINYSTORIES_URL = "https://huggingface.co/datasets/roneneldan/TinyStories/resolve/main/TinyStories-valid.txt"

# Palabras que identifican al personaje principal de cada categoría en TinyStories.
SINONIMOS_CATEGORIA = {
    "cat": ["cat", "kitten", "kitty"],
    "dog": ["dog", "puppy", "doggy"],
    "rabbit": ["rabbit", "bunny"],
    "bear": ["bear", "teddy"],
    "fish": ["fish"],
    "bird": ["bird", "birdie", "robin", "sparrow"],
    "tree": ["tree"],
    "house": ["house"],
    "sun": ["sun"],
    "dragon": ["dragon"],
}

SEMILLA_GLOBAL = 2026

# ---------------------------------------------------------------------------
# Etapa 5: planificador, agentes y explicación.
MAX_RONDAS = 3  # fatiga del usuario (Takagi, 2001)

# Motivos de rechazo que ofrece la interfaz -> parámetro que penalizan (ecuación 1 del informe).
MOTIVOS_RECHAZO = {
    "estilo": "P1",
    "colores": "P2",
    "no_apto_edad": "P3",
    "ambiente": "P4",
    "se_aleja_del_boceto": "P5",
    "espacio_titulo": "P6",
}

# Nombres legibles (para la interfaz, el agente explicador y el validador).
NOMBRES_PARAMETROS = {"P1": "estilo", "P2": "paleta", "P3": "edad", "P4": "ambiente",
                      "P5": "fidelidad al boceto", "P6": "zona del título"}
ETIQUETAS_VALORES = {
    "P1": {"acuarela": "acuarela", "lapices": "lápices de colores", "collage": "collage de papel",
           "vectorial": "vectorial plano", "plastilina": "plastilina 3D"},
    "P2": {"pastel": "paleta pastel", "calida": "paleta cálida", "fria": "paleta fría",
           "primarios": "colores primarios", "tierra": "tonos tierra"},
    "P3": {"0-3": "0 a 3 años", "4-6": "4 a 6 años", "7-9": "7 a 9 años", "10-12": "10 a 12 años",
           "sin": "edad sin indicar"},
    "P4": {"alegre": "ambiente alegre", "aventura": "ambiente de aventura", "calma": "ambiente de calma",
           "misterio": "misterio suave", "humor": "ambiente de humor"},
    "P5": {"muy_baja": "fidelidad muy baja", "baja": "fidelidad baja", "media": "fidelidad media",
           "alta": "fidelidad alta", "muy_alta": "fidelidad muy alta"},
    "P6": {"superior": "título arriba", "inferior": "título abajo", "ambas": "título arriba y abajo",
           "centrada": "título centrado", "sin": "sin título"},
}

# LLM abiertos, en la sesión de Colab, cuantizados a 4 bits y con temperatura 0.
LLMS = {
    "qwen": "Qwen/Qwen2.5-7B-Instruct",
    "phi": "microsoft/Phi-3.5-mini-instruct",
}
MAX_TOKENS_RESUMEN = 700
MAX_TOKENS_HISTORIA = 400
MAX_REINTENTOS_RESUMEN = 2
MAX_PALABRAS_HISTORIA = 500
PRECISION_MIN_HISTORIA = 0.90  # criterio de la Tabla de métricas

# E2: usuarios simulados.
E2_USUARIOS = 50
E2_P_ACEPTA_COINCIDE = 0.80
E2_P_ACEPTA_NO_COINCIDE = 0.15
E2_EJES = ("P1", "P2", "P4")  # eje de cada ronda (ronda 1 = paquete de exploración por estilo)

