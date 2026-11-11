"""D4: historias de prueba de TinyStories (Eldan y Li, 2023; CDLA-Sharing-1.0).

Se usa el archivo de validación (~22 000 historias). Se eligen historias cuyo
personaje principal sea de una de las 10 categorías de D2, para emparejar cada
historia con un boceto de su categoría. Se usan en inglés, su idioma original: una prueba
con MarianMT dio errores (nombres traducidos, género cambiado) que habrían contaminado la
referencia. `traducir` queda como opción, sin usarse en el flujo principal.
"""
from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Optional

from .. import config

SEPARADOR = "<|endoftext|>"


def separar_historias(texto: str) -> List[str]:
    return [h.strip() for h in texto.split(SEPARADOR) if len(h.strip()) > 80]


def categoria_principal(historia: str) -> Optional[str]:
    """La categoría cuyo sinónimo aparece en las dos primeras oraciones y más veces en total."""
    inicio = " ".join(re.split(r"(?<=[.!?])\s+", historia)[:2]).lower()
    texto = historia.lower()
    mejor, mejor_n = None, 0
    for cat, palabras in config.SINONIMOS_CATEGORIA.items():
        patron = r"\b(" + "|".join(map(re.escape, palabras)) + r")s?\b"
        if not re.search(patron, inicio):
            continue
        n = len(re.findall(patron, texto))
        if n > mejor_n:
            mejor, mejor_n = cat, n
    return mejor if mejor_n >= 2 else None


def seleccionar(historias: List[str], n_por_categoria: int = 20,
                semilla: int = config.SEMILLA_GLOBAL) -> List[Dict]:
    por_cat: Dict[str, List[str]] = {c: [] for c in config.QUICKDRAW_CATEGORIAS}
    for h in historias:
        c = categoria_principal(h)
        if c in por_cat:
            por_cat[c].append(h)
    rng = random.Random(semilla)
    salida = []
    for c, lista in por_cat.items():
        rng.shuffle(lista)
        for i, h in enumerate(lista[:n_por_categoria]):
            salida.append({"id": f"{c}_{i:02d}", "categoria": c, "texto_en": h, "texto_es": None})
    return salida


def traducir(historias: List[Dict], modelo: str = "Helsinki-NLP/opus-mt-en-es",
             lote: int = 8) -> List[Dict]:
    """Traducción automática al español (MarianMT, en Colab). Se revisa a mano una muestra."""
    # Sin pipeline("translation"): transformers 5 eliminó esa tarea. Se usa el modelo directo.
    import torch
    from transformers import MarianMTModel, MarianTokenizer

    # Se traduce oración por oración: con la historia entera, MarianMT omite el final,
    # inventa frases y a veces repite una sílaba sin fin (visto en la primera corrida).
    disp = ("cuda" if torch.cuda.is_available()
            else "mps" if torch.backends.mps.is_available() else "cpu")
    tok = MarianTokenizer.from_pretrained(modelo)
    mt = MarianMTModel.from_pretrained(modelo).to(disp).eval()
    for n, h in enumerate(historias, start=1):
        parrafos = [dividir_oraciones(p) for p in h["texto_en"].split("\n") if p.strip()]
        oraciones = [o for p in parrafos for o in p]
        traducidas: List[str] = []
        for i in range(0, len(oraciones), lote * 4):
            entrada = tok(oraciones[i:i + lote * 4], return_tensors="pt", padding=True,
                          truncation=True, max_length=256).to(disp)
            with torch.no_grad():
                ids = mt.generate(**entrada, max_new_tokens=256, num_beams=4,
                                  no_repeat_ngram_size=4, repetition_penalty=1.2)
            traducidas += tok.batch_decode(ids, skip_special_tokens=True)
        it = iter(traducidas)
        h["texto_es"] = "\n".join(" ".join(next(it) for _ in p) for p in parrafos)
        if n % 20 == 0 or n == len(historias):
            print(f"[D4] traducidas {n}/{len(historias)}")
    return historias


def dividir_oraciones(parrafo: str) -> List[str]:
    """Corta en '.', '!' o '?' seguidos de espacio, sin separar el cierre de comillas."""
    partes = re.split(r'(?:(?<=[.!?])|(?<=[.!?]["”’]))\s+(?=[A-Z"“‘])', parrafo.strip())
    return [p for p in partes if p]


def plantilla_anotacion(historias: List[Dict], ruta: Path, n: int = 30,
                        semilla: int = config.SEMILLA_GLOBAL) -> Path:
    """CSV para anotar a mano los elementos visuales de 30 historias (referencia para
    evaluar al agente de historia). Se anota en inglés, como el texto y como lo que el
    agente entrega al prompt. Varios valores se separan con ';'."""
    muestra = random.Random(semilla).sample(historias, min(n, len(historias)))
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "categoria", "texto_en", "personajes", "objetos", "lugar",
                    "momento", "tono", "anotado_por", "notas"])
        for h in muestra:
            w.writerow([h["id"], h["categoria"], h["texto_en"], "", "", "", "", "", "", ""])
    return ruta


def preparar_d4(destino: Path = config.DATOS / "d4_historias", n_por_categoria: int = 20,
                con_traduccion: bool = False) -> Path:
    import requests

    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    r = requests.get(config.TINYSTORIES_URL, timeout=300)
    r.raise_for_status()
    historias = seleccionar(separar_historias(r.content.decode("utf-8", "ignore")), n_por_categoria)
    if con_traduccion:
        historias = traducir(historias)
    with open(destino / "historias.jsonl", "w", encoding="utf-8") as fh:
        for h in historias:
            fh.write(json.dumps(h, ensure_ascii=False) + "\n")
    plantilla_anotacion(historias, destino / "anotacion_30.csv")
    (destino / "LICENCIA.txt").write_text(
        "Historias de TinyStories (Eldan y Li, 2023), licencia CDLA-Sharing-1.0.\n"
        "Se usan en inglés, sin modificar. Si se publicaran datos derivados, llevarían la misma licencia.\n",
        encoding="utf-8")
    conteo = {c: sum(h["categoria"] == c for h in historias) for c in config.QUICKDRAW_CATEGORIAS}
    print(f"[D4] {len(historias)} historias: {conteo}")
    return destino


def emparejar(historias: List[Dict], indice_d2: List[Dict]) -> List[Dict]:
    """Une cada historia con un boceto de D2 de la misma categoría (en orden)."""
    bocetos: Dict[str, List[Dict]] = {}
    for b in indice_d2:
        bocetos.setdefault(b["categoria"], []).append(b)
    pares, usados = [], {c: 0 for c in bocetos}
    for h in historias:
        lista = bocetos.get(h["categoria"], [])
        if not lista:
            continue
        b = lista[usados[h["categoria"]] % len(lista)]
        usados[h["categoria"]] += 1
        pares.append({"historia": h, "boceto": b})
    return pares
