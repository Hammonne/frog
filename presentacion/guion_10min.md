# Guion de 10 minutos: FROG

Versión corta del guion para la presentación actual (`presentacion/index.html`, 15 diapositivas).
La demostración en vivo dura 2 min 25 s; el resto, 7 min 35 s.

| # | Diapositiva | Tiempo | Acumulado |
|---|---|---|---|
| 1 | Portada | 0:20 | 0:20 |
| 2 | Problemática | 0:35 | 0:55 |
| 3 | Protopersona | 0:40 | 1:35 |
| 4 | Visión general | 0:30 | 2:05 |
| 5 | Arquitectura | 0:40 | 2:45 |
| 6 | Parámetros y planificador | 0:35 | 3:20 |
| 7 | Motores A y B | 0:35 | 3:55 |
| 8 | Agentes | 0:35 | 4:30 |
| 9 | Demostración en vivo | 2:25 | 6:55 |
| 10 | Ética | 0:35 | 7:30 |
| 11 | Calidad visual | 0:35 | 8:05 |
| 12 | Feedback y agentes | 0:35 | 8:40 |
| 13 | Seguridad y sesgo | 0:35 | 9:15 |
| 14 | Limitaciones | 0:25 | 9:40 |
| 15 | Conclusiones | 0:20 | 10:00 |

> Atajos: **N** muestra este guion junto a la diapositiva, **F** pone pantalla completa.

---

## 1. Portada (0:20)

Buenas tardes, somos el equipo de FROG, *Friendly Rounds Of Generation*. FROG convierte un boceto y una historia en cinco portadas para un libro infantil, y aprende de lo que la persona acepta y rechaza. Ella es Runa, nuestra mascota, que nos acompaña en la presentación.

## 2. Problemática (0:35)

Quien escribe un cuento no siempre puede ilustrarlo. Tiene tres problemas. Primero, no sabe dibujar bien: hace dibujos simples, aunque sabe lo que quiere contar. Segundo, no puede pagar a un ilustrador para cada cuento. Y tercero, la IA genérica no le sirve: las imágenes no se parecen a su idea ni a su historia, y el título sale mal escrito.

## 3. Protopersona (0:40)

Diseñamos pensando en Valeria, una estudiante de 23 años que crea y adapta cuentos para niños de su entorno. Sabe imaginar la escena, pero no domina la edición de imágenes. Busca tres cosas: portadas fieles a su historia, colores y estilo para niños, y un título legible. Y le frustra justo lo contrario: que la IA cambie sus personajes, que los colores no se sientan infantiles y que el título salga mal. Valeria es una hipótesis de diseño: la estamos validando con las pruebas con usuarios.

## 4. Visión general (0:30)

El flujo tiene cinco pasos. Dibujas o subes un boceto y cuentas tu historia. FROG genera cinco portadas, y cada una cambia un solo parámetro. Aceptas o rechazas cada una, con un motivo. El planificador aprende qué prefieres y prepara la siguiente ronda, hasta tres. Al final, un agente te explica lo que pasó.

## 5. Arquitectura (0:40)

Así se conecta todo. Primero, el preprocesamiento revisa la entrada: rechaza un boceto vacío, la foto de una persona o un texto no apto. Luego el planificador propone las cinco configuraciones y uno de los dos motores genera las portadas. Después se revisa la salida y se escribe el título. La persona decide en la interfaz y todo queda en un registro JSON. Si hay otra ronda, se actualizan las preferencias; si no, el agente redacta el resumen y un validador lo compara con el registro.

## 6. Parámetros y planificador (0:35)

La persona controla seis parámetros: estilo, paleta, edad, ambiente, fidelidad al boceto y zona del título. En cada ronda uno de ellos toma cinco valores, uno por portada, y los demás quedan fijos. Así se ve qué cambió. El planificador usa muestreo de Thompson: fija los valores que la persona ya aceptó y explora al azar los demás.

## 7. Motores A y B (0:35)

Usamos dos motores gratuitos en Colab. El motor A, Stable Diffusion con ControlNet, reinterpreta el boceto en cada estilo: acierta el estilo en el 93 % de los casos y tarda 7,8 segundos por ronda. El motor B, SD-Turbo, es cinco veces más rápido y casi copia el dibujo, pero sus estilos apenas se distinguen: 20 %. Por eso A es el principal y B queda de respaldo.

## 8. Agentes (0:35)

Tenemos tres agentes, y cada uno tiene un validador. El de historia saca personajes, objetos y lugar del cuento, y se comprueba que cada uno aparezca en el texto. El tipográfico elige letra y color, pero las letras las dibuja un programa, así que el título nunca sale mal escrito. Y el de resumen cuenta lo que pasó en la sesión, y se compara con el registro.

## 9. Demostración en vivo (2:25)

Ahora lo vemos funcionando.

1. **(0:20)** Dibujo un conejo en el lienzo y escribo una historia corta con su título.
2. **(0:15)** El agente saca los personajes, objetos y lugar. Si algo está mal, lo corrijo.
3. **(0:40)** Genero la primera ronda: cinco portadas, cada una con un estilo distinto.
4. **(0:25)** Acepto dos y rechazo tres, marcando el motivo. Por ejemplo: "colores".
5. **(0:25)** Genero la segunda ronda: el planificador mantiene lo que acepté y cambia lo demás.
6. **(0:20)** Termino y leo el resumen: dice qué acepté, qué rechacé y por qué.

> **Plan B:** si Colab tarda, tener ya generada una ronda y mostrarla. Si sobra tiempo, mostrar un texto bloqueado por el filtro.

## 10. Ética (0:35)

La protección tiene cuatro capas. El texto: bloqueamos palabras de violencia, contenido sexual, artistas y personajes con marca. La foto: solo se aceptan dibujos, y se rechaza cualquier foto con una cara. La imagen: CLIP revisa cada portada antes de mostrarla. Y los derechos: usamos estilos genéricos y avisamos que la portada no tiene la protección de autor garantizada. El filtro de texto bloqueó las 20 entradas peligrosas de la prueba, pero los eufemismos pasan; por eso existe la revisión de imagen.

## 11. Calidad visual (0:35)

Generamos 3 000 portadas para medir la calidad. El motor A cumple en estilo, con 93 %, en el elemento principal, con 91 %, y en tiempo, con 7,8 segundos. La paleta no llegó a la meta del 80 %: empezó en 69,7 %. El gráfico muestra por qué: "cálida" y "primarios" fallaban. Reforzamos el prompt y subió a 79,2 %, todavía un poco por debajo.

## 12. Feedback y agentes (0:35)

Tres resultados. El planificador: con 500 usuarios simulados, Thompson llega al 43 % de aceptación en la ronda 3, frente a 34,8 % al azar. Los resúmenes: 85 % fieles al registro con Qwen y 50 % con Phi, por eso usamos Qwen. Y el título: el agente tipográfico baja el error de lectura de 43,4 % a 17,6 %.

## 13. Seguridad y sesgo (0:35)

Una persona revisó a mano 45 portadas: 42 eran aptas para niños y 3 no. Con el umbral de CLIP en 0,25 detectamos 2 de esas 3. En sesgo, generamos 100 figuras humanas sin rasgos definidos: casi todas salieron ambiguas, pero cuando el modelo dibuja rasgos, tiende a la piel clara. Es una observación de un solo anotador, no una conclusión.

## 14. Limitaciones (0:25)

No escondemos lo que falta. El agente de historia acierta entre 59 y 80 %, debajo del 90 % que buscábamos. La paleta está en 79 %, el título no llega al 5 % de error y el filtro de imagen detecta solo la mitad de los casos. Y la evidencia con personas está en curso.

## 15. Conclusiones (0:20)

En resumen: FROG da cinco propuestas comparables, aprende de las decisiones de la persona, sus agentes se pueden verificar y sus límites de seguridad están medidos. Lo siguiente es el estudio con usuarios y un filtro de imagen más fuerte. Gracias, ¿preguntas?

---

## Preguntas probables del jurado

- **¿Por qué dos motores?** El A reinterpreta el estilo (93 %) y el B es muy rápido pero copia el boceto (20 % de estilo). B sirve de respaldo y de comparación.
- **¿Qué evita que el agente invente?** Un validador compara cada ID y cada motivo del resumen con el registro. Si falla dos veces, se usa una plantilla.
- **¿Por qué Thompson?** Equilibra explorar y aprovechar con muy pocas rondas. En simulación supera al azar en la ronda 3; con personas reales aún no está probado.
- **¿El agente ve las imágenes?** No. Recibe texto, medidas o el registro JSON.
- **¿Qué concluyen del sesgo?** Es una señal, con 100 figuras y una sola persona anotando. Se podría ofrecer un parámetro explícito de apariencia.
- **¿Quién es dueño de la portada?** El sistema registra la contribución de la persona (boceto, historia y decisiones). La ley protege lo generado por IA solo en la medida del aporte humano.
