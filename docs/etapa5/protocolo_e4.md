# Protocolo del estudio con usuarios (E4)

**Participantes:** 10 (mínimo 8) que no estudien Ciencia de la Computación ni Ciencia de Datos. Antes, 2 de prueba piloto.
**Duración:** 20–25 min · **Quiénes:** una persona guía y otra anota. La guía no ayuda con la interfaz salvo que la persona lleve más de 2 minutos atascada (se anota).

## Antes
1. Leer y firmar `consentimiento_e4.md`. Asignar un código (U1, U2...).
2. Pedir que traiga una historia breve propia (3–5 líneas) y un boceto propio, o que lo dibuje en la pantalla.
3. Grabar solo si la persona lo autoriza (marcar en el consentimiento). El video del proyecto es con **una** persona.

## Durante (la persona usa la interfaz sola)
1. Sube o dibuja el boceto, pega su historia, escribe el título y marca la declaración de autoría.
2. Hace las 3 rondas: acepta o rechaza propuestas y elige un eje de variación.
3. Elige su portada final y lee el resumen.
Anotar en `hoja_registro_e4.csv`: si completó la tarea (sí/no), errores o confusiones, y cuándo pidió ayuda.

## Después
1. **SUS** (`sus_cuestionario.md`): 10 preguntas, escala 1–5.
2. **Entrevista breve** (5 min):
   - ¿Las cinco propuestas se parecían a lo que imaginabas?
   - ¿Entendiste para qué sirve cada parámetro?
   - ¿El resumen explicó bien lo que pasó? ¿Algo te pareció incorrecto?
   - ¿Qué cambiarías primero?
   - ¿Qué te preocupa de que una IA genere la portada?
3. Copiar el `sesion.json` de la sesión a `salidas/e4/UX/` (sin boceto ni historia, así lo guarda la app).

## Formulario de Google
`crear_formulario_e4.gs` crea el formulario (consentimiento, datos, SUS y preguntas finales) y una hoja con las respuestas. Los participantes lo llenan **después** de usar la herramienta. Para analizar: descargar la hoja como CSV, guardarla como `salidas/e4/respuestas_sus.csv` y correr el comando de abajo. Si alguien marca "No acepto", su fila se ignora. La columna `completo` (sí/no) la agregas tú a mano.

## Qué se calcula (`python -m experimentos.e4_sus`)
- **SUS por persona y promedio.** Criterio del informe: ≥ 68. Con 10 personas el resultado es descriptivo.
- **Tarea completada:** fracción de personas que llegó a la portada final.
- **Decisiones por sesión:** rondas, aceptadas y rechazadas, leídas de `sesion.json`.

No se mide el tiempo por decisión: la app no lo registra.
