# Portadas infantiles generativas — código (etapas 1 a 3)

Proyecto 2 de *Planificación y Toma de Decisiones en IA* (UTEC). Aquí está la
implementación de la etapa 2 (datos, Jimena) y de la etapa 3 (modelo generativo, Maria).
Los materiales de la etapa 1 (design thinking, Andrea) están en `../docs/etapa1/`.

## Cómo correrlo

**En Colab (recomendado, GPU T4):** abrir `notebooks/portadas_etapas_1_3.ipynb` y ejecutar las celdas en orden.

**Pruebas en tu computadora (sin GPU):**
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-local.txt
cd codigo && ../.venv/bin/python -m pytest -q tests
```

## Estructura

| Ruta | Qué hace | Etapa |
|---|---|---|
| `portadas/config.py` | Parámetros (estilo, paleta, edad, ambiente, fidelidad, zona del título), modelos, umbrales | 1–3 |
| `portadas/datos/portadas.py` | D1: listado Book32, muestra de 2 000 portadas infantiles | 2 |
| `portadas/datos/quickdraw.py` | D2: bocetos de Quick, Draw! en streaming y render | 2 |
| `portadas/datos/historias.py` | D4: TinyStories (en inglés), selección por personaje, plantilla de anotación | 2 |
| `portadas/datos/historias_es.py` | D4-es: scraper de cuentos y fábulas en español de Wikisource (dominio público) | 2 |
| `portadas/datos/eda.py` | Análisis exploratorio y rangos de referencia (percentiles) | 2 |
| `portadas/preprocesamiento.py` | Boceto → líneas, validación de tinta, ubicación 2:3 respetando la zona del título | 2 |
| `portadas/guardrails/texto.py` | Lista de bloqueo (violencia, sexual, odio, terror, personajes y artistas) | 2–3 |
| `portadas/guardrails/entrada.py` | Rechazo de fotos de personas reales | 2 |
| `portadas/guardrails/salida.py` | Filtro de SD + verificación zero-shot con CLIP | 3 |
| `portadas/motores/prompts.py` | Parámetros → prompt; 5 configuraciones por eje | 3 |
| `portadas/motores/motor_a.py` | Motor A: SD 1.5 + ControlNet 1.1 (scribble/lineart), lotes, img2img, LoRA | 3 |
| `portadas/motores/motor_b.py` | Motor B: SD-Turbo img2img sin control (nivel básico, gratuito) | 3 |
| `portadas/motores/generar.py` | Ronda completa: motor con respaldo, guardrails, regeneración, registro | 3 |
| `portadas/metricas/` | Color, bordes, CLIP, LPIPS, KID/FID | 3 |
| `scripts/preparar_datos.py` | Corre toda la etapa 2 | 2 |
| `scripts/demo_ronda.py` | Primer hito de la etapa 3: ronda de 5 portadas + lámina | 3 |
| `experimentos/calibracion.py` | Barrido de fidelidad y pasos → valores para `config.FIDELIDAD` | 3 |
| `experimentos/aplicar_calibracion.py` | Copia la propuesta de la calibración a `config.py` | 3 |
| `experimentos/lora.py` | Experimento opcional con LoRA: revisa la ficha (licencia, SD 1.5, sin artista) y compara con la base | 3 |
| `experimentos/e1_automatica.py` | Evaluación E1 (2 000 + 1 000 portadas), con reanudación | 3 |
| `experimentos/e5_seguridad.py` | Evaluación E5 (adversariales y sesgo) | 3 |

## Lo que usan las etapas 4 y 5

- `generar_ronda(boceto, base, eje, motores, configs=..., escena=...)` devuelve un diccionario
  con el formato del registro JSON del informe (sección 8). El campo `decision` lo llena la interfaz.
- El planificador (etapa 5) decide las 5 configuraciones y las pasa en `configs=`.
- El agente de historia (etapa 5) entrega `{"personajes": [...], "objetos": [...], "lugar": ...}`
  en inglés; `escena_desde_elementos` lo convierte en la parte de escena del prompt.
- Todo texto del usuario pasa por `guardrails.texto.filtrar_texto` antes de generar.

## Datos y licencias

- **D1** (portadas de Amazon): derechos reservados. Solo estadísticas; `datos/` está en `.gitignore`. No compartir.
- **D2** Quick, Draw!: CC BY 4.0 (se guarda `ATRIBUCION.txt`).
- **D4** TinyStories: CDLA-Sharing-1.0; se usan en inglés, sin modificar.
- **D4-es** Wikisource: dominio público (Quiroga, Daireaux, Samaniego…); cada historia guarda su URL.
- **SD 1.5 / ControlNet:** CreativeML OpenRAIL-M (respetar los usos prohibidos).
- **SD-Turbo:** Stability AI Community License (uso académico gratuito).

## Trabajo pendiente (manual o en Colab)

El código ya está escrito y probado en CPU; falta ejecutarlo con GPU y hacer las tareas
que requieren personas. Responsables según el reparto del informe (Tabla 6).

### Correr el cuaderno en Colab

| # | Tarea | Celda del cuaderno | Responsable | Semana | Resultado |
|---|---|---|---|---|---|
| 1 | Subir `codigo/` a Google Drive, abrir el cuaderno con GPU (T4 gratis; L4/A100 con Colab Pro) y correr las pruebas | 0 y 1 | Jimena | 1 | Todas las pruebas en verde |
| 2 | Descargar los datos en la computadora (`python -m scripts.preparar_datos --solo d1 d2 d4`), subir `datos/` dentro de `codigo/` en Drive y correr en Colab el análisis exploratorio con OCR (opción A del cuaderno) | 2 | Jimena | 1 | `salidas/eda/` (gráficos y `resumen_d1.json`) |
| 3 | Primera ronda de 5 portadas con el motor A y con el motor B | 3.1 | Maria | 1 | `salidas/demo/lamina.png` (primer hito de la etapa 3) |
| 4 | Calibración de la fidelidad y los pasos (y aplicar la propuesta a `config.py`) | 3.2 | Maria | 2 | `salidas/calibracion/` |
| 4b | Experimento opcional con LoRA | 3.3 | Maria | 2 | `salidas/lora/` |
| 5 | Evaluación E1: primero la prueba de 5 pares, luego la completa (si Colab se desconecta, se vuelve a correr y continúa) | E1 | Maria | 3 | `salidas/e1/e1_resumen.json` |
| 6 | Evaluación E5 (partes a y b) | E5 | Maria | 3 | `salidas/e5/` |

Problemas conocidos en Colab:
- **`KeyError: 'The task translation has been removed'`**: viene de una versión vieja del cuaderno
  o de `portadas/datos/historias.py`. Ya no se traduce: la opción A solo corre `--solo eda --ocr`.
- **Cambié un archivo y Colab sigue usando el viejo:** en Drive borra el archivo antes de subir el
  nuevo (si no, queda `archivo (1).py`), luego *Entorno de ejecución → Reiniciar sesión*.
- **`No such file or directory` en `%cd`:** la carpeta no está en `Mi unidad/planif_proyecto/codigo`.

Cuidado: los resultados se guardan en `codigo/salidas/` y `codigo/datos/` dentro de Drive.
`datos/d1_portadas/` tiene portadas con derechos de autor: no compartir esa carpeta.

### Tareas manuales

| # | Tarea | Archivo | Responsable | Semana |
|---|---|---|---|---|
| 7 | Hacer las 5 entrevistas (2 docentes, 2 personas que escriben cuentos, 1 ilustrador) con consentimiento firmado | `docs/etapa1/guia_entrevistas.md`, `consentimiento_entrevista.md` | Bihonda (pasa las notas a Andrea) | 1 |
| 8 | Llenar un mapa de empatía por entrevista y la síntesis (patrones, proto-persona, punto de vista, pregunta guía) | `docs/etapa1/mapa_empatia_plantilla.md` | Andrea | 1 |
| 9 | Pasar los hallazgos al informe (texto en rojo de la sección 1.1) y ajustar la proto-persona | `main.tex` | Andrea | 1 |
| 10 | Probar el prototipo en papel con 2 personas y pasar los cambios a la etapa 4 | `docs/etapa1/ideacion_y_prototipo.md` | Andrea (con Bihonda) | 1 |
| 11 | Reunir unos 20 bocetos propios fotografiados con celular (D3) en `datos/d3_bocetos/` | — | Nayeli (apoyo a la etapa 2) | 1 |
| 12 | ~~Revisar traducciones~~: ya no aplica, las historias se usan en inglés | — | — | — |
| 13b | Anotar a mano, en español, las 30 historias de `datos/d4es_historias/anotacion_30_es.csv` | `datos/d4es_historias/` | Bihonda (apoyo a la etapa 2) | 2 |
| 13 | Anotar a mano, en inglés, los elementos visuales de las 30 historias (personajes, objetos, lugar, momento, tono) | `datos/d4_historias/anotacion_30.csv` | Bihonda (apoyo a la etapa 2) | 2 |
| 14 | Revisar los valores que propone la calibración; la celda `experimentos.aplicar_calibracion` los copia a `config.py` y corre las pruebas | `salidas/calibracion/resumen.json` | Maria | 2 |
| 15 | ~~Ajustar `CRITERIOS_PALETA`~~: hecho con los percentiles de D1 | `portadas/metricas/color.py` | — | — |
| 16 | Revisar a mano cada portada que mostró E5a (¿es apta para niños?) y recalibrar `UMBRAL_CLIP_NO_APTO` si hace falta | `salidas/e5/e5a_revision_manual.csv` | Maria | 3 |
| 17 | Anotar el género y el tono de piel percibidos en las 100 imágenes de E5b, idealmente con dos anotadoras | `salidas/e5/e5b_anotacion_sesgo.csv` | Maria (con otra integrante) | 3 |
| 18 | Escribir los resultados de la sección 6 (Jimena) y de la sección 7 (Maria) | `main.tex` | Jimena y Maria | 3 |

## Costo

Cero. Todo corre en Colab con modelos abiertos de Hugging Face; no hay APIs de pago.
Con Colab gratis la GPU tiene un límite de horas por día: la E1 completa puede requerir
dos sesiones (se reanuda sola). Con Colab Pro conviene elegir L4 o A100.
