"""Lógica de la aplicación FROG, sin Gradio (se prueba en CPU con piezas falsas).

Flujo de una sesión:
  1. analizar_historia  -> agente de historia (LLM local) -> elementos editables
  2. iniciar            -> boceto preparado, parámetros base, planificador (Sesion)
  3. proponer_ronda     -> 5 configuraciones (ronda 1: eje completo; 2 y 3: Thompson),
                           generación, guardrails y título renderizado sobre cada portada
  4. cerrar_ronda       -> decisiones del usuario (aceptar/rechazar + motivos) al planificador
  5. resumir            -> agente de explicación con validador (o plantilla)
Todo queda en `<carpeta>/sesion.json` (registro de la sesión, sin el boceto ni el texto
de la historia: solo los elementos extraídos).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from PIL import Image

from portadas import config
from portadas.agentes.historia import HistoriaInvalida, extraer_elementos
from portadas.agentes.resumen import resumir
from portadas.guardrails.texto import filtrar_texto
from portadas.motores.prompts import escena_desde_elementos
from portadas.planificador import MAX_RONDAS, Sesion, ejes_de_motivos
from portadas.agentes.tipografia import titular_basico
from portadas.titulo import CATALOGO, limitar, render_titulo

NOMBRES_EJE = {"P1": "Estilo", "P2": "Paleta", "P3": "Edad", "P4": "Ambiente",
               "P5": "Fidelidad", "P6": "Zona del título"}
OPCIONES = ["Sin decidir", "Aceptar", "Rechazar"]
DECISION = {"Aceptar": "accepted", "Rechazar": "rejected"}
MOTIVOS = ["estilo", "colores", "no apto para la edad", "ambiente", "se aleja del boceto"]
CARPETA = config.SALIDAS / "interfaz"


@dataclass
class Estado:
    """Todo lo que la interfaz recuerda de una sesión."""
    carpeta: Path
    motor: str = "A"
    titulo: str = ""
    boceto: object = None                 # portadas.preprocesamiento.Boceto
    escena: str = ""
    instruccion: str = ""
    elementos: Dict = field(default_factory=dict)      # personajes, objetos, lugar, momento (en inglés)
    base: Dict[str, str] = field(default_factory=lambda: dict(config.POR_DEFECTO))
    sesion: Optional[Sesion] = None
    resumen: Optional[Dict] = None
    cambios_tipografia: List[Dict] = field(default_factory=list)    # para el agente de resumen
    declaracion_autoria: bool = False     # la persona declaró que el boceto es suyo o que tiene permiso
    creada: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))


# ------------------------------------------------------------------------- historia
def analizar_historia(texto: str, llm) -> Dict:
    """Devuelve los elementos extraídos. Lanza ValueError con un mensaje para el usuario."""
    try:
        return extraer_elementos(texto, llm)
    except HistoriaInvalida as e:
        raise ValueError(str(e))


def aplanar_dibujo(valor) -> Optional[Image.Image]:
    """Convierte lo que devuelve el lienzo de dibujo en una imagen RGB sobre fondo blanco.
    Acepta el valor del editor ({"composite": ..., "background": ..., "layers": [...]}) o una imagen."""
    if valor is None:
        return None
    if isinstance(valor, dict):
        capas = [c for c in [valor.get("composite"), *(valor.get("layers") or [])] if c is not None]
        if not capas:
            return None
        imagen = capas[0]
    else:
        imagen = valor
    imagen = imagen.convert("RGBA")
    fondo = Image.new("RGBA", imagen.size, (255, 255, 255, 255))
    plano = Image.alpha_composite(fondo, imagen).convert("RGB")
    if plano.convert("L").getextrema()[0] >= 250:        # lienzo en blanco: no hay dibujo
        return None
    return plano


def partir(texto: str) -> List[str]:
    """'rabbit, flowers' -> ['rabbit', 'flowers'] (campos de texto editables)."""
    return [t.strip().lower() for t in (texto or "").replace(";", ",").split(",") if t.strip()]


def construir_escena(personajes: str, objetos: str, lugar: str, momento: str) -> str:
    return escena_desde_elementos({"personajes": partir(personajes), "objetos": partir(objetos),
                                   "lugar": (lugar or "").strip().lower(), "momento": momento or ""})


# --------------------------------------------------------------------------- sesión
def iniciar(boceto_img: Image.Image, titulo: str, motor: str, base: Dict[str, str], escena: str,
            instruccion: str = "", fijados: Optional[List[str]] = None, elementos: Optional[Dict] = None,
            preparar: Optional[Callable] = None, revisar_entrada: Optional[Callable] = None,
            declaracion_autoria: bool = False) -> Estado:
    """Valida el boceto y los textos y crea la sesión. Lanza ValueError con un mensaje claro."""
    if boceto_img is None:
        raise ValueError("Sube un boceto primero.")
    for nombre, texto in (("escena", escena), ("instrucción", instruccion), ("título", titulo)):
        f = filtrar_texto(texto or "")
        if not f.ok:
            raise ValueError(f"El texto de {nombre} contiene contenido no apto ({', '.join(f.motivos)}).")
    if preparar is None:
        from portadas.guardrails.entrada import revisar_imagen_entrada
        from portadas.preprocesamiento import BocetoInvalido, preparar_boceto
        revisar_entrada = revisar_entrada or revisar_imagen_entrada
        revision = revisar_entrada(boceto_img)
        if not revision.ok:
            raise ValueError(revision.motivo)
        try:
            boceto = preparar_boceto(boceto_img, zona_titulo=base["P6"])
        except BocetoInvalido as e:
            raise ValueError(str(e))
    else:
        boceto = preparar(boceto_img, base["P6"])
    carpeta = CARPETA / time.strftime("%Y%m%d-%H%M%S")
    carpeta.mkdir(parents=True, exist_ok=True)
    e = Estado(carpeta=carpeta, motor=motor, titulo=(titulo or "").strip(), boceto=boceto, escena=escena.strip(),
               instruccion=(instruccion or "").strip(), elementos=elementos or {}, base=dict(base),
               declaracion_autoria=bool(declaracion_autoria))
    e.sesion = Sesion(dict(base), motor=motor, fijados=fijados or [])
    return e


def ejes_disponibles(e: Estado) -> List[str]:
    return e.sesion.ejes_disponibles() if e.sesion and not e.sesion.terminada() else []


def proponer_ronda(e: Estado, eje: str, generar_fn: Callable, titulador=titular_basico) -> Dict:
    """Genera la ronda siguiente con el eje elegido y le pone el título a cada portada.

    `generar_fn(estado, configs, numero) -> ronda` devuelve la ronda con imágenes ya guardadas
    (image_path); en producción es `generar_real`. `titulador(img, titulo, zona, edad, params)` dibuja
    el título (con el agente tipográfico en producción) y devuelve (imagen, info)."""
    plan = e.sesion.configs_ronda(eje)
    ronda = generar_fn(e, plan["configs"], plan["round"])
    ronda["axis"] = eje
    # "fixed" = lo que realmente no cambió entre las 5 propuestas (en las rondas 2 y 3 el
    # planificador varía otros parámetros además del eje).
    comunes = {p: v for p, v in plan["configs"][0].items()
               if p != eje and all(c[p] == v for c in plan["configs"])}
    ronda["fixed"] = comunes
    ronda["planner_plan"] = {"free": plan["free"], "sampled": plan["sampled"]}
    for v in ronda["variations"]:
        v.setdefault("title_layout", None)
        v["titled_path"] = None
        if v.get("image_path"):
            img, info = titulador(Image.open(v["image_path"]), e.titulo, v["params"]["P6"], v["params"]["P3"],
                                  v["params"])
            ruta = Path(v["image_path"]).with_name(f"{v['id']}_titulo.png")
            img.save(ruta)
            v["titled_path"], v["title_layout"] = str(ruta), info
            v["typography"] = {"agent": {"origin": (info.get("agente") or {}).get("origen", "respaldo"),
                                         "style": info.get("estilo")}, "user_edit": None}
    return ronda


# ---------------------------------------------------------------------- editar el título
NOMBRE_FUENTE = {"Andika": "Andika", "Fredoka": "Fredoka", "Baloo2": "Baloo 2", "LilitaOne": "Lilita One"}


def editar_titulo(e: Estado, v: Dict, fuente: Optional[str] = None, tamano: Optional[float] = None,
                  curva: Optional[float] = None, color: Optional[str] = None) -> str:
    """La persona cambia fuente, tamaño, curva o color del título de UNA portada. Solo se vuelve a
    dibujar el título (la imagen no se regenera). Queda en `v["typography"]["user_edit"]` y, si
    cambió la fuente, en `e.cambios_tipografia` para que el resumen lo mencione. Devuelve la ruta
    de la portada con el nuevo título."""
    if not v.get("image_path"):
        raise ValueError("Esa portada no se mostró.")
    estilo = dict((v.get("typography") or {}).get("agent", {}).get("style") or {})
    antes = dict(estilo)
    for clave, valor in (("fuente", fuente), ("tamano", tamano), ("curva", curva), ("color", color)):
        if valor not in (None, ""):
            estilo[clave] = valor
    estilo = limitar(estilo, v["params"]["P3"], restringir_edad=False)      # lo elige la persona
    img, info = render_titulo(Image.open(v["image_path"]), e.titulo, v["params"]["P6"], v["params"]["P3"],
                              restringir_edad=False, **estilo)
    ruta = Path(v["image_path"]).with_name(f"{v['id']}_titulo.png")
    img.save(ruta)
    v["titled_path"], v["title_layout"] = str(ruta), info
    cambios = {k: info["estilo"][k] for k in ("fuente", "tamano", "curva", "color") if info["estilo"][k] != antes.get(k)}
    v["typography"]["user_edit"] = {**(v["typography"].get("user_edit") or {}), **cambios}
    if "fuente" in cambios:
        e.cambios_tipografia = [c for c in e.cambios_tipografia if c["id"] != v["id"]]
        e.cambios_tipografia.append({"id": v["id"], "cambio": f"fuente: {NOMBRE_FUENTE[cambios['fuente']]}"})
    return str(ruta)


def generar_real(e: Estado, configs: List[Dict], numero: int, motores, revisor) -> Dict:
    """Generación con los motores reales, guardrails de salida y guardado de imágenes."""
    from portadas.motores.generar import generar_ronda, guardar_imagenes
    ronda = generar_ronda(e.boceto, e.base, e.sesion.planes[-1]["axis"], {e.motor: motores(e.motor)},
                          motor_preferido=e.motor, escena=e.escena, instruccion=e.instruccion,
                          ronda=numero, configs=configs, revisor=revisor())
    return guardar_imagenes(ronda, e.carpeta, prefijo=f"r{numero}_")


# --------------------------------------------------------------------------- decisiones
def aplicar_decisiones(ronda: Dict, opciones: List[str], comentarios: List[str],
                       motivos: Optional[List[List[str]]] = None) -> Dict:
    """Llena `decision`, `reasons` (casillas) y `reason` (comentario). Las portadas bloqueadas
    quedan como "blocked". Lanza ValueError si falta decidir alguna portada visible."""
    motivos = motivos or [[] for _ in ronda["variations"]]
    faltan = []
    for v, op, com, mot in zip(ronda["variations"], opciones, comentarios, motivos):
        if v.get("image_path") is None:
            v["decision"], v["reason"], v["reasons"] = "blocked", "", []
        elif op in DECISION:
            v["decision"] = DECISION[op]
            rechazada = v["decision"] == "rejected"
            v["reasons"] = [m for m in mot if m in MOTIVOS] if rechazada else []
            v["reason"] = (com or "").strip() if rechazada else ""
        else:
            faltan.append(v["id"])
    if faltan:
        raise ValueError("Falta decidir: " + ", ".join(faltan))
    return ronda


def cerrar_ronda(e: Estado, ronda: Dict, opciones, comentarios, motivos) -> Dict:
    aplicar_decisiones(ronda, opciones, comentarios, motivos)
    for v in ronda["variations"]:
        v["reason_axes"] = ejes_de_motivos(v.get("reasons"))
    e.sesion.cerrar_ronda(ronda)
    guardar(e)
    return ronda


# ----------------------------------------------------------------------------- resumen
def sesion_para_resumen(e: Estado) -> Dict:
    return {"rounds": e.sesion.rondas, "story": e.elementos, "typography_changes": list(e.cambios_tipografia)}


def resumir_sesion(e: Estado, llm, modelo: str = "") -> Dict:
    if not e.sesion.rondas:
        raise ValueError("Cierra al menos una ronda antes de pedir el resumen.")
    e.resumen = resumir(sesion_para_resumen(e), llm)
    e.resumen["model"] = modelo
    e.resumen.pop("borradores", None)          # los borradores del LLM no se guardan
    guardar(e)
    return e.resumen


def guardar(e: Estado) -> Path:
    """Escribe el registro de la sesión (sin boceto ni texto de la historia)."""
    ruta = e.carpeta / "sesion.json"
    datos = {"created": e.creada, "engine": e.motor, "title": e.titulo, "authorship_declared": e.declaracion_autoria, "scene": e.escena,
             "story_elements": e.elementos, "base_params": e.base, "fixed": e.sesion.fijados,
             "rounds": e.sesion.rondas, "summary": e.resumen,
             "posterior_mean": e.sesion.planificador.estado()}
    e.carpeta.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return ruta
