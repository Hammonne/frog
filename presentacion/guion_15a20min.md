# Guion de 15 a 20 minutos: FROG

Versión larga del guion para la presentación actual (`presentacion/index.html`, 19 diapositivas).
Dura **17 min 30 s**: la demostración en vivo ocupa 5 min y el resto 12 min 30 s.
Si hay que llegar a 20 min, alarga la demo hasta 6 min (el máximo que permite el enunciado) o deja tiempo para preguntas.
Si hay que bajar a 15 min, usa los recortes marcados con ✂️.

| # | Diapositiva | Tiempo | Acumulado |
|---|---|---|---|
| 1 | Portada | 0:30 | 0:30 |
| 2 | Problemática | 0:45 | 1:15 |
| 3 | Protopersona | 0:50 | 2:05 |
| 4 | Visión general | 0:40 | 2:45 |
| 5 | Arquitectura | 1:00 | 3:45 |
| 6 | Datos y licencias | 0:40 | 4:25 |
| 7 | Parámetros y planificador | 0:45 | 5:10 |
| 8 | Motores A y B | 0:45 | 5:55 |
| 9 | Experimento con LoRA | 0:30 | 6:25 |
| 10 | Agentes | 0:50 | 7:15 |
| 11 | Interfaz | 0:25 | 7:40 |
| 12 | Demostración en vivo | 5:00 | 12:40 |
| 13 | Ética | 0:45 | 13:25 |
| 14 | Calidad visual | 0:45 | 14:10 |
| 15 | Feedback y agentes | 0:50 | 15:00 |
| 16 | Estudio con usuarios (E4) | 0:50 | 15:50 |
| 17 | Seguridad y sesgo | 0:40 | 16:30 |
| 18 | Limitaciones | 0:35 | 17:05 |
| 19 | Conclusiones | 0:25 | 17:30 |

> Atajos: **N** muestra las notas del presentador junto a la diapositiva, **F** pone pantalla completa.

---

## 1. Portada (0:30)

Buenas tardes. Somos el equipo de FROG, que significa *Friendly Rounds Of Generation*: rondas amigables de generación. FROG convierte un boceto y una historia en cinco portadas para un libro infantil, deja que la persona elija y aprende de lo que acepta y rechaza. Ella es Runa, nuestra mascota, que nos acompaña en toda la presentación.

## 2. Problemática (0:45)

Mucha gente escribe cuentos para niños: estudiantes, docentes, familias. Pero quien escribe un cuento no siempre puede ilustrarlo. Tiene tres problemas. Primero, no sabe dibujar bien: hace dibujos simples, aunque sabe exactamente lo que quiere contar. Segundo, no puede pagar a un ilustrador para cada cuento. Y tercero, la IA genérica no le sirve: las imágenes no se parecen a su idea ni a su historia, y el título casi siempre sale con letras raras o mal escritas.

## 3. Protopersona (0:50)

Diseñamos pensando en Valeria, una estudiante universitaria de 23 años que crea y adapta cuentos para niños de su entorno. Sabe imaginar la escena, pero no domina la edición de imágenes. Busca tres cosas: portadas fieles a su historia, colores y estilo para niños, y un título legible. Valeria es un arquetipo, así que la contrastamos con dos entrevistas. Una entrevistada adaptó el Quijote para su hermana de 10 años: dibujó la portada a lápiz en tres horas y la dejó en blanco y negro porque, dijo, "no soy muy buena pintando". Cuando probó la IA, le cambiaba los personajes y el título salía mal escrito o tapando el dibujo.

## 4. Visión general (0:40)

El flujo tiene cinco pasos. Uno: dibujas o subes un boceto y cuentas tu historia. Dos: FROG genera cinco portadas, y cada una cambia un solo parámetro, para que puedas compararlas. Tres: aceptas o rechazas cada una, con un motivo. Cuatro: el planificador aprende qué prefieres y prepara la siguiente ronda, hasta tres. Y cinco: al final, un agente te explica lo que pasó en tu sesión.

## 5. Arquitectura (1:00)

Así se conecta todo. Primero, el preprocesamiento revisa la entrada: limpia el boceto y rechaza uno vacío, la foto de una persona real o un texto no apto para niños; además, un agente lee la historia. Luego el planificador propone las cinco configuraciones de la ronda, y uno de los dos motores genera las portadas. Después se revisa cada portada con un filtro de imagen, y el agente tipográfico decide cómo va el título. La persona decide en la interfaz y todo queda guardado en un registro JSON: qué aceptó, qué rechazó y por qué. Si pide otra ronda, se actualizan sus preferencias; si termina, el agente redacta el resumen y un validador lo compara con el registro. Si el resumen inventa algo, se reintenta hasta dos veces y, si sigue fallando, se usa una plantilla fija.

## 6. Datos y licencias (0:40)

Usamos cuatro fuentes de datos y revisamos la licencia de cada una. Las portadas infantiles de Amazon tienen derechos de autor: solo las usamos para medir cómo son las portadas reales, nunca las mostramos ni entrenamos con ellas. Los bocetos de prueba son de Quick, Draw!, de Google, con licencia abierta. Las historias son de TinyStories, en inglés, y de Wikisource, en español, y anotamos 30 de cada idioma a mano. Todos los modelos son libres y corren gratis en Colab. ✂️ Sobre las portadas generadas: la ley solo protege el aporte humano, por eso FROG registra el boceto, la historia y las decisiones de la persona.

## 7. Parámetros y planificador (0:45)

La persona controla seis parámetros: estilo, paleta, edad del lector, ambiente, fidelidad al boceto y zona del título. En cada ronda, uno de ellos toma sus cinco valores, uno por portada, y los demás quedan fijos. Así la persona ve exactamente qué cambió de una portada a otra. El planificador usa muestreo de Thompson: lleva la cuenta de qué valores acepta la persona, fija los que le gustan y prueba al azar los demás para seguir explorando, con un máximo de tres rondas.

## 8. Motores A y B (0:45)

Usamos dos motores, ambos gratuitos y corriendo en Colab. El motor A, Stable Diffusion con ControlNet, usa el boceto como guía y lo reinterpreta en el estilo pedido: acierta el estilo en el 93 % de los casos y tarda 7,8 segundos por ronda. El motor B, SD-Turbo, es cinco veces más rápido y casi copia el dibujo, con 98 % de fidelidad, pero por eso sus estilos apenas se distinguen: solo 20 % de acierto. Por eso A es el principal y B queda como respaldo y como línea base.

## 9. Experimento con LoRA (0:30)

El enunciado sugería explorar modelos de Hugging Face, así que probamos un LoRA, un adaptador que cambia el estilo del motor A. Con 20 bocetos, el parecido con el prompt sube un poco, de 0,72 a 0,76, pero el acierto del estilo que elige la persona cae de 95 a 45 %: el LoRA impone su propio estilo. Como FROG se basa en que la persona decide, lo descartamos.

## 10. Agentes (0:50)

Tenemos tres agentes de IA, cada uno con su validador, y ninguno ve las imágenes: solo trabajan con texto. El agente de historia lee el cuento y saca personajes, objetos y lugar; se comprueba que cada uno aparezca en el texto, y lo que no aparece se marca. El agente tipográfico recibe medidas de la zona del título y elige la letra y el color, pero las letras las dibuja un programa, así que el título nunca sale mal escrito. Y el agente de resumen cuenta lo que pasó en la sesión; un validador compara cada portada y cada motivo con el registro. Usamos Qwen 2.5 y Phi 3.5, que corren dentro de Colab.

## 11. Interfaz (0:25)

Así se ve FROG. A la izquierda, la pantalla de inicio explica los tres pasos. A la derecha, la entrada: subes o dibujas tu boceto, escribes el título y la historia, y eliges si quieres un resultado fiel a tu trazo o más libre. Ahora lo vemos funcionando.

## 12. Demostración en vivo (5:00)

1. **(0:40)** Dibujo un conejo en el lienzo, escribo una historia corta y le pongo título. Marco la casilla que declara que el boceto es mío.
2. **(0:30)** El agente saca los personajes, objetos y lugar. Muestro que, si algo está mal, se puede corregir antes de generar.
3. **(1:00)** Genero la primera ronda: cinco portadas, cada una con un estilo distinto. Mientras carga, explico que cada tarjeta tiene una etiqueta con el valor que cambia.
4. **(0:40)** Acepto dos y rechazo tres, marcando el motivo; por ejemplo, "colores". Muestro que se puede editar la letra del título sin volver a generar la imagen.
5. **(1:00)** Genero la segunda ronda: el planificador mantiene lo que acepté y cambia lo demás.
6. **(0:30)** Termino y leo el resumen del agente: qué acepté, qué rechacé y por qué.
7. **(0:40)** ✂️ Muestro un guardrail: escribo una historia con una palabra violenta y el sistema la bloquea.

> **Plan B:** si Colab tarda, volver a la diapositiva 11 y mostrar una ronda ya generada.

## 13. Ética (0:45)

La generación tiene cuatro capas de protección. El texto: bloqueamos palabras de violencia, contenido sexual, nombres de artistas y personajes con marca. La foto: solo aceptamos dibujos, y se rechaza cualquier foto con el rostro de una persona. La imagen: CLIP revisa cada portada antes de mostrarla. Y los derechos: usamos estilos genéricos, nunca "al estilo de" un artista. En la prueba, el filtro de texto bloqueó las 20 entradas peligrosas, pero los eufemismos pasan; por eso existe la revisión de la imagen. ✂️ Ojo: el motor B no trae filtro propio, así que ahí CLIP es la única protección.

## 14. Calidad visual (0:45)

Para medir la calidad generamos 3 000 portadas. El motor A cumple en estilo, con 93 % frente al 70 % que pedíamos; en el elemento principal, con 91 %; y en tiempo, con 7,8 segundos por ronda. La paleta no llegó a la meta del 80 %: empezó en 69,7 %. El gráfico muestra por qué: "cálida" y "primarios" fallaban. Reforzamos el texto de esas paletas en el prompt y subió a 79,2 %, todavía un poco por debajo.

## 15. Feedback y agentes (0:50)

Tres resultados. El planificador: con 500 usuarios simulados, Thompson y el azar empiezan igual, pero en la ronda 3 Thompson llega a 43 % de aceptación, frente a 34,8 % al azar. Los resúmenes: el 85 % de los de Qwen coinciden con el registro, frente al 50 % de Phi; por eso usamos Qwen. Y el título: el agente tipográfico baja el error de lectura de 43,4 % a 17,6 %. No llega a la meta del 5 %, porque el lector automático falla con títulos cortos o con dibujo detrás, aunque a simple vista se leen bien.

## 16. Estudio con usuarios (0:50)

Probamos FROG con 10 personas que no estudian computación ni ciencia de datos, cada una con su propio boceto y su propia historia, y respondieron el cuestionario SUS, que mide qué tan fácil es usar un sistema. La media fue 86,8 sobre 100, y 9 de 10 superaron el promedio de referencia de 68. Pidieron que se expliquen mejor los estilos y más precisión en las imágenes, y les preocupa que se reutilicen sus bocetos y el trabajo de quienes ilustran. Estas son algunas portadas que eligieron, con su permiso.

## 17. Seguridad y sesgo (0:40)

Una persona revisó a mano 45 portadas: 42 eran aptas para niños y 3 no. Con el umbral de CLIP en 0,25 detectamos 2 de esas 3, a cambio de bloquear por error el 1,3 % de las aptas. En sesgo, generamos 100 figuras humanas sin rasgos definidos: casi todas salieron ambiguas, pero cuando el modelo dibuja rasgos, tiende a la piel clara. Es una señal que vigilamos, no una conclusión: la anotó una sola persona.

## 18. Limitaciones (0:35)

No escondemos lo que falta. El agente de historia acierta entre 59 y 80 %, por debajo del 90 % que buscábamos. La paleta está en 79 %. El título no llega al 5 % de error. El filtro de imagen detecta solo la mitad de las portadas no aptas. Y la evidencia con personas es pequeña: dos entrevistas y diez participantes, ninguno autor ni docente.

## 19. Conclusiones (0:25)

En resumen: FROG da cinco propuestas comparables, aprende de las decisiones de la persona, sus agentes se pueden verificar y sus límites de seguridad están medidos. Lo siguiente es explicar los estilos en la interfaz, como pidieron en E4, y un filtro de imagen más fuerte, sobre todo para el motor B. Gracias, ¿preguntas?

---

## Recortes para bajar a 15 minutos (✂️)

| Recorte | Ahorra |
|---|---|
| Demo: saltar el paso 7 (guardrail) | 0:40 |
| Demo: segunda ronda más corta (solo mostrarla) | 0:30 |
| Diapositiva 6: saltar la frase de las portadas generadas | 0:10 |
| Diapositiva 13: saltar la frase del motor B | 0:10 |
| Diapositivas 9 y 11: decirlas en una frase cada una | 0:30 |
| Diapositiva 5: contar solo el camino principal, sin reintentos | 0:20 |
| **Total** | **2:20** (queda en unos 15 min) |

## Preguntas probables del jurado

- **¿Por qué dos motores?** El A reinterpreta el estilo (93 %) y el B es muy rápido pero copia el boceto (20 % de estilo). B sirve de respaldo y de comparación.
- **¿Por qué no usaron el LoRA?** Impone su propio estilo y baja el acierto del estilo elegido de 95 a 45 %.
- **¿Entrenaron un modelo propio?** No: el nivel avanzado se descartó por costo de cómputo y de datos.
- **¿Qué evita que el agente invente?** Un validador compara cada ID y cada motivo del resumen con el registro. Si falla dos veces, se usa una plantilla.
- **¿Por qué Thompson?** Equilibra explorar y aprovechar con muy pocas rondas. En simulación supera al azar en la ronda 3; con personas reales aún no está medido aparte.
- **¿El agente ve las imágenes?** No. Recibe texto, medidas o el registro JSON.
- **¿86,8 de SUS es bueno?** Supera el promedio de referencia de 68, pero con 10 personas es un resultado descriptivo.
- **¿Por qué no entrenaron con las portadas de Amazon?** Tienen derechos de autor y la ley peruana no tiene una excepción general como el *fair use*; solo las usamos para estadísticas.
- **¿Quién es dueño de la portada?** La ley protege lo generado por IA solo en la medida del aporte humano; por eso FROG registra el boceto, la historia y las decisiones.
- **¿Qué concluyen del sesgo?** Es una señal, con 100 figuras y una sola persona anotando. Se podría ofrecer un parámetro explícito de apariencia.
