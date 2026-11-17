<p align="center">
  <img src="assets/frog.svg" alt="Logo de FROG: una ranita leyendo un libro" width="180">
</p>

<h1 align="center">FROG</h1>
<p align="center"><b>F</b>riendly <b>R</b>ounds <b>O</b>f <b>G</b>eneration</p>
<p align="center"><i>From ROugh sketch to Great cover</i> · portadas de cuentos infantiles a partir de un boceto y una historia</p>

---

Dibujas un boceto, cuentas tu historia ("un conejo que ama las flores") y FROG te propone
**cinco portadas** que varían en un solo parámetro: estilo, paleta, edad del lector, ambiente,
fidelidad al boceto o zona del título. Aceptas o rechazas cada una y, como una rana que avanza
a saltos, el sistema da la siguiente ronda (máximo tres) aprendiendo de tus decisiones. Al final
explica en palabras qué elegiste y por qué cambió cada ronda. El título lo escribe un agente
tipográfico y lo puedes cambiar.

Proyecto 2 del curso *Planificación y Toma de Decisiones en IA* (UTEC). Todo es **gratuito**:
modelos abiertos de Hugging Face en Google Colab, sin APIs de pago.

## Cómo funciona

| Paso | Qué hace | Con qué |
|---|---|---|
| Boceto | Limpia el dibujo, extrae las líneas y deja espacio para el título | OpenCV |
| Historia | Extrae personajes, objetos y lugar, y verifica que estén en el texto | Qwen2.5-7B / Phi-3.5-mini |
| Generación | Cinco portadas por ronda con dos motores | SD 1.5 + ControlNet · SD-Turbo |
| Guardrails | Bloquea texto no apto, fotos de personas e imágenes inadecuadas | Lista de bloqueo, MediaPipe, CLIP |
| Planificador | Decide qué cambiar en la ronda siguiente | Muestreo de Thompson |
| Título | Elige la fuente y comprueba que se lea | Pillow, contraste WCAG, OCR |

## Estado

| Etapa | Estado |
|---|---|
| 1. Problema y diseño (design thinking) | Informe y materiales de entrevista listos; faltan las entrevistas |
| 2. Datos | Listo: datos, análisis exploratorio, preprocesamiento y guardrails de entrada |
| 3. Modelo generativo | Dos motores corridos en GPU (E1 automático con CLIP) |
| 4. Interfaz | Aplicación Gradio de cinco pantallas, probada en Colab |
| 5. Agentes y evaluación | Agentes de historia y resumen con validador, planificador con rondas 2–3 y simulación E2 listos; faltan E5 (seguridad), anotaciones manuales y el trabajo con usuarios |

## Empezar

```bash
python3 -m venv .venv && .venv/bin/pip install -r codigo/requirements-local.txt
cd codigo && ../.venv/bin/python -m pytest -q tests      # pruebas en CPU
```

Para generar portadas se usa, desde la [carpeta de Drive](https://drive.google.com/drive/folders/1SeLJ5SfBTYIJw6wqwDgotYYCGDPyCJl1?usp=sharing), la aplicación con el cuaderno de Colab
[`codigo/notebooks/app_frog.ipynb`](codigo/notebooks/app_frog.ipynb) (GPU L4 o T4); existe una variante sin Drive,
[`app_frog_sin_drive.ipynb`](codigo/notebooks/app_frog_sin_drive.ipynb), que usa un zip. Los experimentos están en
[`portadas_etapas_1_3.ipynb`](codigo/notebooks/portadas_etapas_1_3.ipynb).
Instrucciones completas en [`codigo/README.md`](codigo/README.md).

## Repositorio

| Ruta | Contenido |
|---|---|
| [`codigo/`](codigo/) | Implementación en Python: paquete `portadas` (motores, agentes, planificador), `app/` (interfaz Gradio), scripts, experimentos, pruebas y cuadernos |
| [`assets/`](assets/) | Logo y hoja de recursos visuales de la que se recortan los de la interfaz |
| [`docs/etapa1/`](docs/etapa1/) | Guía de entrevistas, consentimiento, ideación y el [mapa de empatía y lienzo de propuesta de valor](docs/etapa1/mapa_empatia_y_propuesta_de_valor.pdf) (PDF) |
| [`codigo/salidas/`](codigo/salidas/) | Resultados de los experimentos (CSV, JSON y láminas) |
| [`main.tex`](main.tex) / [`main.pdf`](main.pdf) | Informe en LaTeX y su PDF (máximo 10 páginas) |

## Datos y licencias

Los **resultados** de los experimentos (calibración, E1, E5, LoRA, EDA, demos) sí están en [`codigo/salidas/`](codigo/salidas/), salvo las 2 730 portadas de E1 (1,2 GB), que no caben en GitHub y están en Drive dentro de `frog_solo_drive_portadas_e1_y_datos.zip` (también se regeneran con `experimentos/e1_automatica.py`). Los **datos** no están en el repositorio. El equipo los tiene en esta **[carpeta de Google Drive](https://drive.google.com/drive/folders/1SeLJ5SfBTYIJw6wqwDgotYYCGDPyCJl1?usp=sharing)**
(acceso restringido al equipo), junto con el código y los resultados, lista para correr el cuaderno en Colab.
También se pueden volver a descargar con `python -m scripts.preparar_datos`.

- **Portadas de Amazon (Book32):** tienen derechos de autor. Solo se usan para estadísticas; no se publican.
- **Quick, Draw!:** CC BY 4.0. **TinyStories:** CDLA-Sharing-1.0. **Wikisource:** dominio público.
- **Modelos:** SD 1.5 y ControlNet con CreativeML OpenRAIL-M; SD-Turbo con la Stability AI Community License.
- El sistema no imita estilos de artistas con nombre ni reproduce personajes protegidos.

## Equipo

Andrea Coa · Jimena Gurbillon · Maria Surco · Bihonda Epiquien · Nayeli Guzman
