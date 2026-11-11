"""D4-es: historias infantiles en español de Wikisource (dominio público).

Sirven para evaluar al agente de historia con el idioma real de la app. Fuentes:
- Horacio Quiroga, *Cuentos de la selva* (1918): cuentos con animales, Uruguay/Argentina.
- *Fábulas* (categoría de Wikisource): Daireaux (*Fábulas argentinas*), Samaniego, Iriarte, Esopo...
- Cuentos de Andersen en traducciones antiguas.

Solo se usa Wikisource porque todo su contenido es de dominio público o tiene licencia libre
y su API está pensada para reutilizarse. StoryWeaver se descartó: su API no entrega el texto
sin iniciar sesión. Se respeta la política de Wikimedia: User-Agent propio, una petición a la
vez y una pausa entre peticiones.
"""
from __future__ import annotations

import csv
import json
import random
import re
import time
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .. import config

API = "https://es.wikisource.org/w/api.php"
AGENTE = "ProyectoPortadasInfantiles/0.1 (proyecto universitario UTEC; uso academico)"
PAUSA_S = 1.0
LICENCIA = "Dominio público (Wikisource en español)"

# Páginas índice cuyos enlaces son los cuentos, y categorías cuyos miembros son cuentos.
INDICES = ["Cuentos de la selva"]
CATEGORIAS = ["Categoría:Fábulas argentinas", "Categoría:Fábulas"]

# Categoría de D2 -> palabras en español (sin tildes) que la identifican en el texto.
PALABRAS_CATEGORIA: Dict[str, List[str]] = {
    "cat": ["gato", "gata", "gatito", "gatita", "gatos", "minino"],
    "dog": ["perro", "perra", "perrito", "perros", "cachorro", "can"],
    "rabbit": ["conejo", "coneja", "conejito", "conejos", "liebre"],
    "bear": ["oso", "osa", "osito", "osos"],
    "fish": ["pez", "peces", "pescado", "pececito", "dorado", "raya"],
    "bird": ["pajaro", "pajarito", "pajaros", "ave", "aves", "loro", "paloma", "gorrion", "chingolo",
             "flamenco", "flamencos", "golondrina", "cuervo", "aguila", "condor", "buho", "lechuza"],
    "tree": ["arbol", "arboles", "bosque", "selva", "roble", "sauce", "pino"],
    "house": ["casa", "casita", "rancho", "choza", "hogar"],
    "sun": ["sol"],
    "dragon": ["dragon", "dragones"],
}


class _Texto(HTMLParser):
    """Extrae el texto del cuento del HTML de Wikisource, sin cabeceras, notas ni estilos."""

    SALTAR = ("noprint", "ws-noexport", "reference", "mw-editsection", "ws-header", "wsbox",
              "pagenum", "ws-pagenum", "mw-references", "navbox", "licencia")
    BLOQUES = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"}

    def __init__(self):
        super().__init__()
        self.partes: List[str] = []
        self.pila: List[bool] = []  # True si la etiqueta abre una zona que se salta

    def _saltando(self) -> bool:
        return any(self.pila)

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "img", "hr", "meta", "link", "input"):
            if tag == "br" and not self._saltando():
                self.partes.append("\n")
            # Letra capital como imagen (Cuentos de la selva): la letra viene en `alt`.
            alt = dict(attrs).get("alt") or ""
            if tag == "img" and len(alt) == 1 and alt.isalpha() and not self._saltando():
                self.partes.append(alt)
            return
        clase = dict(attrs).get("class") or ""
        ident = dict(attrs).get("id") or ""
        saltar = tag in ("style", "script", "sup", "table") or any(s in clase for s in self.SALTAR) \
            or ident.startswith(("headertemplate", "footer"))
        self.pila.append(saltar)
        if tag in self.BLOQUES and not self._saltando():
            self.partes.append("\n")

    def handle_endtag(self, tag):
        if tag in ("br", "img", "hr", "meta", "link", "input"):
            return
        if self.pila:
            self.pila.pop()
        if tag in self.BLOQUES:
            self.partes.append("\n")

    def handle_data(self, data):
        if not self._saltando():
            self.partes.append(data)

    def texto(self) -> str:
        t = "".join(self.partes).replace("\xa0", " ")
        lineas = [re.sub(r"[ \t]+", " ", l).strip() for l in t.split("\n")]
        t = "\n".join(lineas)
        return re.sub(r"\n{3,}", "\n\n", t).strip()


def html_a_texto(html: str, titulo: str = "") -> str:
    p = _Texto()
    p.feed(html)
    texto = p.texto()
    # Quita el título repetido al inicio ("LAS MEDIAS DE LOS FLAMENCOS").
    primera, _, resto = texto.partition("\n")
    if titulo and sin_tildes(primera).strip(" .") == sin_tildes(titulo).strip(" ."):
        texto = resto.strip()
    return texto


def sin_tildes(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def categoria_es(texto: str) -> str:
    """Categoría de D2 más mencionada en el texto, o 'otro'."""
    palabras = re.findall(r"[a-zñ]+", sin_tildes(texto))
    conteo = {c: sum(palabras.count(p) for p in ps) for c, ps in PALABRAS_CATEGORIA.items()}
    mejor = max(conteo, key=conteo.get)
    return mejor if conteo[mejor] >= 2 else "otro"


def es_verso(texto: str) -> bool:
    lineas = [l for l in texto.split("\n") if l.strip()]
    if len(lineas) < 6:
        return False
    cortas = sum(len(l) < 60 for l in lineas)
    return cortas / len(lineas) > 0.7


# --------------------------------------------------------------------- red

class ClienteWikisource:
    def __init__(self, pausa_s: float = PAUSA_S):
        import requests

        self.s = requests.Session()
        self.s.headers["User-Agent"] = AGENTE
        self.pausa_s = pausa_s

    def _get(self, **params) -> Dict:
        params.update(format="json", formatversion=2)
        for intento in range(6):
            r = self.s.get(API, params=params, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                # Se respeta el tiempo que pide el servidor; si no lo dice, espera creciente.
                espera = float(r.headers.get("Retry-After") or 30 * (intento + 1))
                print(f"[D4-es] servidor ocupado ({r.status_code}); espero {espera:.0f} s")
                time.sleep(espera)
                continue
            r.raise_for_status()
            time.sleep(self.pausa_s)
            return r.json()
        r.raise_for_status()
        return {}

    def miembros(self, categoria: str, limite: int = 2000) -> List[str]:
        titulos, cont = [], {}
        while len(titulos) < limite:
            d = self._get(action="query", list="categorymembers", cmtitle=categoria,
                          cmnamespace=0, cmlimit=500, **cont)
            titulos += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
            if "continue" not in d:
                break
            cont = {"cmcontinue": d["continue"]["cmcontinue"]}
        return titulos[:limite]

    def pagina(self, titulo: str) -> Optional[Dict]:
        d = self._get(action="parse", page=titulo, prop="text|links|categories",
                      disablelimitreport=1, redirects=1)
        if "parse" not in d:
            return None
        p = d["parse"]
        return {"titulo": p["title"], "html": p["text"],
                "enlaces": [l["title"] for l in p.get("links", []) if l.get("exists") and l.get("ns") == 0],
                "categorias": [c["category"] for c in p.get("categories", [])]}


# --------------------------------------------------------------------- flujo

def candidatos(cliente: ClienteWikisource) -> List[Dict]:
    """Títulos a descargar con su colección de origen."""
    vistos, salida = set(), []
    for indice in INDICES:
        p = cliente.pagina(indice)
        for t in (p or {}).get("enlaces", []):
            if t not in vistos and not t.startswith(("Ayuda:", "Wikisource:", "Autor:")):
                vistos.add(t)
                salida.append({"titulo": t, "coleccion": indice})
    for cat in CATEGORIAS:
        nuevos = [t for t in cliente.miembros(cat) if t not in vistos and not t.startswith("Portal:")]
        # Las categorías vienen en orden alfabético: se mezclan para no quedarse solo con la "A".
        random.Random(config.SEMILLA_GLOBAL).shuffle(nuevos)
        for t in nuevos:
            vistos.add(t)
            salida.append({"titulo": t, "coleccion": cat.replace("Categoría:", "")})
    return salida


def descargar(cliente: ClienteWikisource, cands: Iterable[Dict], min_palabras: int = 60,
              max_palabras: int = 3500, max_paginas: int = 250) -> List[Dict]:
    from ..guardrails.texto import filtrar_texto

    historias = []
    for i, c in enumerate(list(cands)[:max_paginas], start=1):
        try:
            p = cliente.pagina(c["titulo"])
        except Exception as e:  # una página que falla no detiene la descarga
            print(f"[D4-es] se salta {c['titulo']!r}: {e}")
            continue
        if not p:
            continue
        texto = html_a_texto(p["html"], p["titulo"])
        n = len(texto.split())
        filtro = filtrar_texto(texto)
        historias.append({
            "titulo": p["titulo"], "coleccion": c["coleccion"],
            "autor": _autor(p["categorias"], c["coleccion"]),
            "fuente_url": "https://es.wikisource.org/wiki/" + p["titulo"].replace(" ", "_"),
            "licencia": LICENCIA, "palabras": n, "formato": "verso" if es_verso(texto) else "prosa",
            "categoria": categoria_es(texto), "apta": filtro.ok, "motivos_filtro": filtro.motivos,
            "en_rango": min_palabras <= n <= max_palabras, "texto_es": texto,
        })
        if i % 25 == 0:
            print(f"[D4-es] {i} páginas descargadas")
    return historias


AUTOR_COLECCION = {"Fábulas argentinas": "Godofredo Daireaux", "Cuentos de la selva": "Horacio Quiroga"}


def _autor(categorias: List[str], coleccion: str = "") -> str:
    if coleccion in AUTOR_COLECCION:
        return AUTOR_COLECCION[coleccion]
    for c in categorias:
        m = re.match(r"(?:Fábulas|Cuentos) de (.+)", c.replace("_", " "))
        if m:
            return m.group(1)
    return ""


def seleccionar_es(historias: List[Dict], n: int = 60, semilla: int = config.SEMILLA_GLOBAL) -> List[Dict]:
    """Elige hasta n historias aptas, en rango de longitud, priorizando prosa y repartiendo
    entre categorías (las de D2 primero)."""
    # Las fábulas son breves: una "fábula" de más de 1 000 palabras es un poema culto, no infantil.
    validas = [h for h in historias if h["apta"] and h["en_rango"]
               and not (h["coleccion"].startswith("Fábulas") and h["palabras"] > 1000)]
    rng = random.Random(semilla)
    rng.shuffle(validas)
    validas.sort(key=lambda h: (h["formato"] != "prosa", h["categoria"] == "otro"))
    por_cat: Dict[str, List[Dict]] = {}
    for h in validas:
        por_cat.setdefault(h["categoria"], []).append(h)
    elegidas: List[Dict] = []
    while len(elegidas) < n and any(por_cat.values()):
        for cat in list(por_cat):
            if por_cat[cat] and len(elegidas) < n:
                elegidas.append(por_cat[cat].pop(0))
    for i, h in enumerate(elegidas):
        h["id"] = f"es_{h['categoria']}_{i:02d}"
    return elegidas


def plantilla_anotacion_es(historias: List[Dict], ruta: Path, n: int = 30,
                           semilla: int = config.SEMILLA_GLOBAL) -> Path:
    """Igual que la plantilla en inglés, pero se anota en español (el idioma de la historia);
    el verificador del agente busca la versión en el idioma del texto."""
    muestra = random.Random(semilla).sample(historias, min(n, len(historias)))
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "categoria", "titulo", "autor", "fuente_url", "texto_es", "personajes",
                    "objetos", "lugar", "momento", "tono", "anotado_por", "notas"])
        for h in muestra:
            w.writerow([h["id"], h["categoria"], h["titulo"], h["autor"], h["fuente_url"], h["texto_es"],
                        "", "", "", "", "", "", ""])
    return ruta


def preparar_d4_es(destino: Path = config.DATOS / "d4es_historias", n: int = 60,
                   max_paginas: int = 250) -> Path:
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    cliente = ClienteWikisource()
    cands = candidatos(cliente)
    print(f"[D4-es] {len(cands)} páginas candidatas")
    todas = descargar(cliente, cands, max_paginas=max_paginas)
    with open(destino / "todas.jsonl", "w", encoding="utf-8") as fh:
        for h in todas:
            fh.write(json.dumps(h, ensure_ascii=False) + "\n")
    elegidas = seleccionar_es(todas, n=n)
    with open(destino / "historias_es.jsonl", "w", encoding="utf-8") as fh:
        for h in elegidas:
            fh.write(json.dumps(h, ensure_ascii=False) + "\n")
    plantilla = destino / "anotacion_30_es.csv"
    if not plantilla.exists():
        plantilla_anotacion_es(elegidas, plantilla)
    (destino / "LICENCIA.txt").write_text(
        "Textos de Wikisource en español, de dominio público (autores fallecidos hace más de 80 años\n"
        "o traducciones antiguas). Cada historia guarda su URL de origen en `fuente_url`.\n",
        encoding="utf-8")
    resumen = {
        "candidatas": len(cands), "descargadas": len(todas),
        "bloqueadas_por_filtro": sum(not h["apta"] for h in todas),
        "fuera_de_rango": sum(not h["en_rango"] for h in todas),
        "elegidas": len(elegidas),
        "por_categoria": {c: sum(h["categoria"] == c for h in elegidas) for c in
                          list(PALABRAS_CATEGORIA) + ["otro"]},
        "prosa": sum(h["formato"] == "prosa" for h in elegidas),
    }
    (destino / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[D4-es] {json.dumps(resumen, ensure_ascii=False)}")
    return destino


def reseleccionar(destino: Path = config.DATOS / "d4es_historias", n: int = 60) -> None:
    """Rehace la selección y la plantilla desde `todas.jsonl`, sin volver a descargar."""
    destino = Path(destino)
    todas = [json.loads(l) for l in open(destino / "todas.jsonl", encoding="utf-8") if l.strip()]
    for h in todas:
        h["autor"] = AUTOR_COLECCION.get(h["coleccion"], h["autor"])
    elegidas = seleccionar_es(todas, n=n)
    with open(destino / "historias_es.jsonl", "w", encoding="utf-8") as fh:
        for h in elegidas:
            fh.write(json.dumps(h, ensure_ascii=False) + "\n")
    plantilla_anotacion_es(elegidas, destino / "anotacion_30_es.csv")
