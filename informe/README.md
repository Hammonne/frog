# Informe de FROG

| Archivo | Qué es |
|---|---|
| `main.tex` | El informe en LaTeX. **Este es el que se edita.** |
| `main.pdf` | El informe compilado (máximo 10 páginas). |
| `figuras/` | Las imágenes que usa el informe. |

## Figuras

| Archivo | Dónde aparece |
|---|---|
| `figuras/lamina_motor_a.png` | Resultados: una ronda del motor A |
| `figuras/lamina_motor_b.png` | Resultados: una ronda del motor B |
| `figuras/muestras_titulos.png` | Resultados: legibilidad del título |
| `figuras/collage_e4.png` | Resultados: portadas elegidas en el estudio con usuarios (E4) |
| `figuras/ui_interfaz.jpg` | Interfaz: pantalla de inicio y pantalla de entrada de Gradio |

Para agregar una figura, guárdala en `figuras/` y en `main.tex` escribe
`\includegraphics[width=\columnwidth]{figuras/nombre.png}`.

## Compilar

Desde esta carpeta, dos veces (la segunda arregla las referencias a tablas y figuras):

```bash
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

También se puede subir la carpeta `informe/` completa a Overleaf y compilar ahí.
