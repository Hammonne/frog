# FROG explicado de forma sencilla

**FROG** significa *Friendly Rounds Of Generation* (rondas amigables de generación). Es el Proyecto 2 del curso Planificación y Toma de Decisiones en IA (UTEC, 2026-2).

En una frase: **tú haces un dibujo simple y cuentas tu cuento; FROG te propone cinco portadas para tu libro infantil, tú eliges cuáles te gustan y FROG aprende de tus decisiones.**

---

## 1. El problema

Mucha gente escribe cuentos para niños, como estudiantes, docentes o autores que publican por su cuenta, pero:

- **no sabe dibujar bien**: tiene la idea en la cabeza, pero su dibujo es un boceto simple;
- **no puede pagar a un ilustrador** para cada cuento;
- **la IA común no le sirve**: le pide una imagen y sale algo que no se parece a su idea, y el título casi siempre sale con letras raras o mal escritas.

FROG resuelve esto partiendo **de su propio dibujo** y dejando que **la persona decida** en cada paso.

## 2. Para quién lo diseñamos

Usamos una **protopersona**, un personaje inventado que representa a nuestro usuario típico. En la presentación es **Valeria**: tiene 23 años, estudia en la universidad y adapta cuentos para niños de su entorno. Quiere tres cosas:

1. portadas que respeten su idea;
2. colores y un estilo que les gusten a los niños;
3. un título que se lea bien.

> Ojo: en el informe la protopersona todavía es **Carmen**, una docente de inicial. El equipo tiene que elegir una de las dos.

## 3. Cómo se usa (lo que ve la persona)

1. **Dibuja o sube su boceto** y escribe la historia y el título.
2. **Revisa los elementos** que encontró la IA en su historia (personajes, objetos y lugar) y los corrige si hace falta.
3. **Elige qué quiere explorar**, por ejemplo el estilo.
4. **Recibe 5 portadas.** Todas son iguales salvo en una sola cosa: si explora el estilo, salen en acuarela, lápices, collage, vectorial y plastilina.
5. **Marca "Me gusta" o "No me gusta"** en cada una y, si no le gusta, dice por qué (por ejemplo, "los colores").
6. **Puede pedir otra ronda**, hasta 3 en total. FROG recuerda lo que aceptó y prueba cosas nuevas en lo demás.
7. **Al final lee un resumen** con lo que eligió y por qué, y puede descargar el registro de su sesión.

## 4. Los 6 parámetros que se pueden cambiar

| Parámetro | Valores |
|---|---|
| Estilo | acuarela, lápices, collage, vectorial, plastilina |
| Paleta de colores | pastel, cálida, fría, primarios, tierra |
| Edad del lector | 0-3, 4-6, 7-9, 10-12 años, sin edad |
| Ambiente | alegre, aventura, calma, misterio, humor |
| Fidelidad al boceto | muy baja, baja, media, alta, muy alta |
| Zona del título | superior, inferior, ambas, centrada, sin título |

En cada ronda **solo cambia uno** de estos parámetros. Así la persona entiende la diferencia entre una portada y otra.

## 5. Cómo funciona por dentro

Piensa en FROG como una fábrica con estaciones:

1. **Revisión de la entrada.** Se limpia el dibujo y se rechaza lo que no sirve: un boceto vacío, una foto de una persona real o un texto no apto para niños.
2. **El planificador.** Decide las 5 configuraciones de cada ronda. Usa un método llamado **muestreo de Thompson**: lleva la cuenta de qué valores acepta la persona, fija los que le gustan y prueba al azar los demás.
3. **Los motores que dibujan.** Hay dos, ambos gratuitos y corriendo en Google Colab:
   - **Motor A** (Stable Diffusion 1.5 + ControlNet), el principal: usa el boceto como guía y lo vuelve a dibujar en el estilo pedido.
   - **Motor B** (SD-Turbo), el de respaldo: es mucho más rápido, pero casi copia el boceto y los estilos se parecen entre sí.
4. **Revisión de la salida.** Un modelo llamado CLIP revisa cada portada y bloquea las que no son aptas para niños.
5. **El título.** Un agente elige la letra y el color, y un programa dibuja las letras. Por eso el título **nunca sale mal escrito**: no lo dibuja la IA.
6. **La interfaz.** Es una página hecha con Gradio, donde la persona ve las 5 portadas y decide.
7. **El registro.** Cada decisión se guarda en un archivo JSON: qué se aceptó, qué se rechazó, por qué y con qué parámetros.
8. **El resumen.** Un agente redacta lo que pasó en la sesión, y un validador lo compara con el registro. Si el resumen inventa algo, se vuelve a intentar hasta 2 veces; si sigue fallando, se usa una plantilla fija.

## 6. Los tres agentes de IA

Los agentes usan modelos de lenguaje gratuitos (**Qwen 2.5** y **Phi 3.5**) y **ninguno ve las imágenes**: solo trabajan con texto.

| Agente | Qué recibe | Qué produce | Cómo se comprueba |
|---|---|---|---|
| De historia | El cuento | Personajes, objetos y lugar | Cada elemento debe aparecer en el cuento |
| Tipográfico | Medidas de la zona del título | Letra y color | Un programa dibuja las letras |
| De resumen | El registro JSON | El resumen final | Se compara con el registro |

## 7. Los datos que usamos

| Nombre | Qué es | Para qué sirve |
|---|---|---|
| D1 | Portadas de libros infantiles de Amazon | Solo para medir cómo son las portadas reales (colores, dónde va el título). **Tienen derechos de autor: nunca se muestran ni se comparten.** |
| D2 | Dibujos de *Quick, Draw!* de Google (200) | Bocetos de prueba |
| D3 | Bocetos hechos a mano por el equipo | Pruebas más realistas (**pendiente**) |
| D4 | Cuentos cortos en inglés (TinyStories) y en español (Wikisource) | Historias de prueba y para evaluar al agente de historia |

Los modelos ya vienen entrenados. Los datos no se usan para entrenar: sirven para entender el problema y para hacer las pruebas.

## 8. Qué tan bien funciona (resultados)

| Prueba | Resultado | ¿Cumple la meta? |
|---|---|---|
| Acierto del estilo (motor A) | 93 % | ✅ (meta: 70 %) |
| Detecta el elemento principal | 91 % | ✅ (meta: 80 %) |
| Tiempo por ronda (motor A) | 7,8 segundos | ✅ (meta: menos de 60) |
| Paleta de colores | 79,2 % (antes 69,7 %) | ❌ casi (meta: 80 %) |
| Planificador frente al azar (ronda 3) | 43 % frente a 34,8 % de aceptación | ✅ |
| Resúmenes fieles al registro | 85 % con Qwen, 50 % con Phi | Se usa Qwen |
| Agente de historia | entre 59 y 80 % | ❌ (meta: 90 %) |
| Error al leer el título | 17,6 % (antes 43,4 %) | ❌ (meta: 5 %) |
| Filtro de texto | bloqueó 20 de 20 entradas peligrosas | ✅ |
| Portadas aptas para niños | 42 de 45 | El filtro de imagen detecta solo una parte de las no aptas |

**Las pruebas, con nombre:**
- **E1:** calidad, con 3 000 portadas generadas.
- **E2:** el planificador, con 500 usuarios simulados.
- **E3:** los resúmenes.
- **E4:** pruebas con personas reales. **Pendiente**.
- **E5:** seguridad y sesgo.

## 9. Ética y seguridad

FROG tiene **cuatro capas de protección**:

1. **Texto:** bloquea palabras de violencia, contenido sexual, nombres de artistas y personajes con marca registrada.
2. **Foto:** solo acepta dibujos; rechaza cualquier foto con una cara.
3. **Imagen:** CLIP revisa cada portada antes de mostrarla.
4. **Derechos:** usa estilos genéricos (nunca "al estilo de" un artista) y avisa que la portada puede no tener protección de autor.

**Sesgo:** generamos 100 figuras humanas sin rasgos definidos. Casi todas salieron ambiguas, pero cuando el modelo dibuja rasgos, tiende a la piel clara. Es una señal que hay que vigilar, no una conclusión firme.

## 10. Lo que falta

**Lo obligatorio:**
- **E4:** pruebas con al menos 10 personas usando la interfaz, con el cuestionario SUS.
- **Video de 3 minutos o menos:** con un docente de la UTEC o un estudiante de otra carrera (no Ciencia de Datos ni Computación) usando FROG.
- **El informe:**
  - recuperar las citas y la bibliografía;
  - agregar fragmentos del taller de Design Thinking;
  - completar los 2 textos pendientes en rojo;
  - elegir entre Valeria y Carmen.

**Lo opcional:**
- las 5 entrevistas para la protopersona;
- los bocetos propios (D3);
- entrenar un LoRA propio, que sería el nivel avanzado.

## 11. Dónde está cada cosa

| Carpeta o archivo | Qué hay |
|---|---|
| `codigo/portadas/` | El corazón del sistema: motores, agentes, planificador, filtros y métricas |
| `codigo/app/` | La interfaz en Gradio |
| `codigo/notebooks/app_frog.ipynb` | El cuaderno de Colab para abrir la aplicación (GPU T4 o L4) |
| `codigo/tests/` | Las pruebas automáticas |
| `docs/etapa1/` | Design Thinking: guía de entrevistas, consentimiento, mapa de empatía, protopersona |
| `informe/` | El informe: `main.tex`, `main.pdf` y la carpeta `figuras/` (máximo 10 páginas) |
| `presentacion/index.html` | La presentación (15 diapositivas) |
| `presentacion/guion_15a20min.md` | El guion de la presentación (15 a 20 minutos) |

## 12. Palabras que conviene saber

- **Boceto:** el dibujo simple que hace la persona.
- **Ronda:** un grupo de 5 portadas que la persona evalúa.
- **Prompt:** el texto que se le da al modelo para que dibuje.
- **ControlNet:** una pieza que obliga al modelo a respetar las líneas del boceto.
- **Muestreo de Thompson:** una forma de decidir que mezcla "repetir lo que funcionó" con "probar algo nuevo".
- **CLIP:** un modelo que compara imágenes con frases; aquí revisa si una portada es apta para niños y si tiene el estilo pedido.
- **Guardrail:** un filtro de seguridad.
- **SUS:** un cuestionario de 10 preguntas que mide qué tan fácil es usar un sistema (de 0 a 100; 68 es el promedio).
- **OCR:** un programa que lee texto en una imagen; lo usamos para medir si el título se lee bien.
