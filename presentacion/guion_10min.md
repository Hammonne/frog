# Guion de 10 minutos: FROG

Versión corta del guion para la presentación actual (`presentacion/index.html`, 19 diapositivas).
La demostración en vivo dura 2 min 45 s; el resto, 7 min 15 s.
El guion largo, con preguntas del jurado, está en `guion_presentador.md`.

| # | Diapositiva | Tiempo | Acumulado |
|---|---|---|---|
| 1 | Portada | 0:15 | 0:15 |
| 2 | Problemática | 0:25 | 0:40 |
| 3 | Protopersona | 0:30 | 1:10 |
| 4 | Visión general | 0:25 | 1:35 |
| 5 | Arquitectura | 0:30 | 2:05 |
| 6 | Datos y licencias | 0:25 | 2:30 |
| 7 | Parámetros y planificador | 0:25 | 2:55 |
| 8 | Motores A y B | 0:25 | 3:20 |
| 9 | Experimento con LoRA | 0:20 | 3:40 |
| 10 | Agentes | 0:25 | 4:05 |
| 11 | Interfaz | 0:15 | 4:20 |
| 12 | Demostración en vivo | 2:45 | 7:05 |
| 13 | Ética | 0:30 | 7:35 |
| 14 | Calidad visual | 0:25 | 8:00 |
| 15 | Feedback y agentes | 0:25 | 8:25 |
| 16 | Estudio con usuarios (E4) | 0:35 | 9:00 |
| 17 | Seguridad y sesgo | 0:20 | 9:20 |
| 18 | Limitaciones | 0:20 | 9:40 |
| 19 | Conclusiones | 0:20 | 10:00 |

> Atajos: **N** muestra las notas largas (`guion_presentador.md`) junto a la diapositiva, **F** pone pantalla completa.

---

## 1. Portada (0:15)

Buenas tardes, somos el equipo de FROG, *Friendly Rounds Of Generation*. FROG convierte un boceto y una historia en cinco portadas para un libro infantil y aprende de lo que la persona acepta y rechaza. Nos acompaña Runa, nuestra mascota.

## 2. Problemática (0:25)

Quien escribe un cuento no siempre puede ilustrarlo. No sabe dibujar bien, no puede pagar a un ilustrador para cada cuento, y la IA genérica no le sirve: las imágenes no se parecen a su idea y el título sale mal escrito.

## 3. Protopersona (0:30)

Diseñamos para Valeria, una estudiante de 23 años que adapta cuentos para niños de su entorno. Quiere portadas fieles a su historia, con colores para niños y un título legible. La contrastamos con dos entrevistas: una entrevistada tardó tres horas en hacer a lápiz la portada de un cuento para su hermana, y la dejó en blanco y negro porque no sabe pintar.

## 4. Visión general (0:25)

El flujo tiene cinco pasos: dibujas o subes un boceto y cuentas tu historia; FROG genera cinco portadas que cambian un solo parámetro; aceptas o rechazas cada una con un motivo; el planificador aprende y prepara otra ronda, hasta tres; y al final un agente te explica lo que pasó.

## 5. Arquitectura (0:30)

Primero revisamos la entrada: se rechaza un boceto vacío, una foto de una persona o un texto no apto. El planificador propone cinco configuraciones y un motor genera las portadas. Luego se revisa la salida y se escribe el título. La persona decide, todo queda en un registro JSON, y al final un validador compara el resumen del agente con ese registro.

## 6. Datos y licencias (0:25)

Usamos cuatro fuentes y revisamos la licencia de cada una. Las portadas de Amazon tienen derechos de autor: solo las usamos para estadísticas, nunca las mostramos ni entrenamos con ellas. Los bocetos de prueba son de Quick, Draw!, y las historias, de TinyStories y Wikisource. Todos los modelos son libres y corren gratis en Colab.

## 7. Parámetros y planificador (0:25)

La persona controla seis parámetros: estilo, paleta, edad, ambiente, fidelidad al boceto y zona del título. En cada ronda uno toma cinco valores y los demás quedan fijos, para que se vea qué cambió. El planificador usa muestreo de Thompson: fija lo que la persona aceptó y explora lo demás.

## 8. Motores A y B (0:25)

El motor A, Stable Diffusion con ControlNet, reinterpreta el boceto: acierta el estilo en el 93 % de los casos y tarda 7,8 segundos por ronda. El motor B, SD-Turbo, es cinco veces más rápido y casi copia el dibujo, pero sus estilos apenas se distinguen. Por eso A es el principal y B el respaldo.

## 9. Experimento con LoRA (0:20)

También probamos un LoRA de Hugging Face. Mejora un poco el parecido con el prompt, pero el acierto del estilo que elige la persona baja de 95 a 45 %: impone su propio estilo. Por eso lo descartamos.

## 10. Agentes (0:25)

Tenemos tres agentes, cada uno con un validador. El de historia saca personajes, objetos y lugar, y se comprueba que aparezcan en el texto. El tipográfico elige letra y color, pero las letras las dibuja un programa, así que el título nunca sale mal escrito. Y el de resumen se compara con el registro.

## 11. Interfaz (0:15)

Así se ve FROG: una pantalla de inicio que explica los tres pasos, y una pantalla de entrada para el boceto, el título y la historia. Vamos a verla funcionando.

## 12. Demostración en vivo (2:45)

1. **(0:20)** Dibujo un conejo en el lienzo y escribo una historia corta con su título.
2. **(0:15)** El agente saca los personajes, objetos y lugar. Si algo está mal, lo corrijo.
3. **(0:45)** Genero la primera ronda: cinco portadas, cada una con un estilo distinto. Mientras carga, explico que cada etiqueta dice qué valor cambió.
4. **(0:25)** Acepto dos y rechazo tres, marcando el motivo; por ejemplo, "colores".
5. **(0:40)** Genero la segunda ronda: el planificador mantiene lo que acepté y cambia lo demás.
6. **(0:20)** Termino y leo el resumen: dice qué acepté, qué rechacé y por qué.

> **Plan B:** si Colab tarda, volver a la diapositiva 11 y mostrar una ronda ya generada.

## 13. Ética (0:30)

La protección tiene cuatro capas: el texto, que bloquea violencia, contenido sexual, artistas y personajes con marca; la foto, porque solo aceptamos dibujos; la imagen, que CLIP revisa antes de mostrarla; y los derechos, con estilos genéricos. El filtro de texto bloqueó las 20 entradas peligrosas, pero los eufemismos pasan; por eso revisamos también la imagen.

## 14. Calidad visual (0:25)

Generamos 3 000 portadas. El motor A cumple en estilo, con 93 %; en elemento principal, con 91 %; y en tiempo, con 7,8 segundos. La paleta no llegó al 80 %: empezó en 69,7 % y, tras reforzar el prompt, subió a 79,2 %.

## 15. Feedback y agentes (0:25)

Con 500 usuarios simulados, Thompson llega al 43 % de aceptación en la ronda 3, frente al 34,8 % al azar. Los resúmenes coinciden con el registro el 85 % de las veces con Qwen, y el agente tipográfico baja el error al leer el título de 43,4 a 17,6 %.

## 16. Estudio con usuarios (0:35)

Probamos FROG con 10 personas que no estudian computación, cada una con su propio boceto y su historia. El SUS medio fue 86,8 sobre 100, y 9 de 10 superaron el promedio de referencia de 68. Pidieron que se expliquen los estilos y más precisión en las imágenes, y les preocupa que se reutilicen sus bocetos. Estas son algunas portadas que eligieron.

## 17. Seguridad y sesgo (0:20)

Una persona revisó 45 portadas: 42 eran aptas para niños. Con el umbral de CLIP en 0,25 detectamos 2 de las 3 no aptas. En sesgo, cuando el modelo dibuja rasgos, tiende a la piel clara; es una señal que vigilamos, no una conclusión.

## 18. Limitaciones (0:20)

No escondemos lo que falta: el agente de historia acierta entre 59 y 80 %, la paleta está en 79 %, el título no llega al 5 % de error, el filtro de imagen es débil, y la muestra de personas es pequeña.

## 19. Conclusiones (0:20)

FROG da cinco propuestas comparables, aprende de las decisiones de la persona, sus agentes se pueden verificar y sus límites de seguridad están medidos. Lo siguiente es explicar los estilos en la interfaz y un filtro de imagen más fuerte. Gracias, ¿preguntas?

---

## Preguntas probables del jurado

- **¿Por qué dos motores?** El A reinterpreta el estilo (93 %) y el B es muy rápido pero copia el boceto (20 % de estilo). B sirve de respaldo y de comparación.
- **¿Por qué no usaron el LoRA?** Impone su propio estilo y baja el acierto del estilo elegido de 95 a 45 %.
- **¿Qué evita que el agente invente?** Un validador compara cada ID y cada motivo del resumen con el registro. Si falla dos veces, se usa una plantilla.
- **¿Por qué Thompson?** Equilibra explorar y aprovechar con muy pocas rondas. En simulación supera al azar en la ronda 3.
- **¿El agente ve las imágenes?** No. Recibe texto, medidas o el registro JSON.
- **¿86,8 de SUS es bueno?** Supera el promedio de referencia de 68, pero con 10 personas es un resultado descriptivo.
- **¿Quién es dueño de la portada?** La ley protege lo generado por IA solo en la medida del aporte humano; por eso FROG registra el boceto, la historia y las decisiones.
