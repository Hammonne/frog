# Casos de prueba de la interfaz

Los dibujos están en esta carpeta (se suben desde tu computadora con el botón de la interfaz).
Se regeneran con `python -m scripts.crear_bocetos_ejemplo`.

## A. Cuentos completos (deben funcionar de principio a fin)

| Boceto | Título | Historia | Qué debería salir en "Elementos" |
|---|---|---|---|
| `boceto_conejo.png` | El conejo y las flores | Un conejo que ama las flores vive en un jardín. Cada mañana les cuenta chistes a las mariposas, al amanecer. | rabbit · flowers · garden · Amanecer (miniatura de día) |
| `boceto_zorro.png` | La zorra y la luciérnaga | Una pequeña zorra se perdió en el bosque de noche. Una luciérnaga la guio hasta su casa. | fox · firefly · forest · Noche (miniatura de noche) |
| `boceto_dragon.png` | Tomás y las galletas | El dragón Tomás tenía miedo del fuego. Con ayuda de su amiga la tortuga aprendió a cocinar galletas. | dragon, turtle · cookies · sin lugar ni momento (miniatura de bosque) |
| `boceto_castillo.png` | El castillo de arena | Una niña y su perro construyen un castillo de arena en la playa al atardecer. | girl, dog · sandcastle o castle of sand · beach · Atardecer (miniatura de bosque) |

Con cada uno: acepta unas portadas y rechaza otras (con motivos y comentario), haz 2 o 3 rondas
y termina con el resumen.

## B. Avisos de error (deben mostrar un mensaje claro, sin romper nada)

| Qué haces | Dónde aparece el aviso | Mensaje esperado |
|---|---|---|
| Pulsar *Continuar* sin subir boceto | Paso 1 | Sube el boceto de tu portada. |
| Pulsar *Continuar* sin título o sin historia | Paso 1 | Escribe el título… / Escribe tu historia. |
| Historia: `Un hombre con una pistola mata al lobo` | Paso 1 | La historia contiene contenido no apto para una portada infantil (violencia)… |
| Historia: `Hoy llovió todo el día.` (sin personajes) | Paso 2 | Los campos pueden salir vacíos: escribe la escena a mano (`a rabbit in a garden`) |
| Subir `boceto_vacio.png` y pulsar *Generar propuestas* | Paso 3 | El boceto parece vacío (tinta 0.00% < 0.5%). |
| Subir `boceto_garabato.png` y pulsar *Generar propuestas* | Paso 3 | El boceto está demasiado lleno (tinta 92.2% > 40%). |
| Título: `Sangre y pistola` y pulsar *Generar propuestas* | Paso 3 | El texto de título contiene contenido no apto (violencia). |

## C. Funciones a probar

- **Motor "Más libre y rápido":** en el paso 1 elígelo. En el paso 3 desaparece "Parecido a tu boceto" y la ronda tarda menos.
- **Asistente Phi:** cámbialo en el paso 1 (descarga el modelo la primera vez).
- **Indicación extra** (paso 2, desplegable): `un zorro leyendo bajo un árbol`.
- **Corregir los elementos** (paso 2): borra un personaje, cambia el momento del día y mira cómo cambian la escena y la miniatura.
- **Decidir:** *Me gustan todas*, *Ninguna me convence*, y el contador "Has decidido X de 5".
- **Rondas:** en la 2 y la 3 el sistema elige otros parámetros; el aviso lo explica.
- **Final:** descarga el JSON y pulsa *Crear otra portada*.

## Qué anotar si algo falla

El paso en el que ocurre, lo que escribiste, una captura de pantalla y el texto de la celda de Colab
(los errores internos salen ahí).
