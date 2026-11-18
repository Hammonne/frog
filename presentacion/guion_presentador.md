# Guion del presentador: FROG
Exposición de 15 minutos; la demo en vivo (slide 8) dura 5 y el enunciado permite como máximo 6.

## Slide 1

TIEMPO: 0:30. Buenas tardes. Somos el equipo de FROG, que significa Friendly Rounds Of Generation: rondas amigables de generación. FROG convierte un boceto y una historia en cinco portadas para un libro infantil, y aprende de lo que la persona acepta y rechaza. La mascota es Runa, que nos acompaña en la presentación.

## Slide 2

TIEMPO: 0:45. Diseñamos para Valeria, una estudiante universitaria que crea cuentos para niños. Sabe lo que quiere contar y hace bocetos sencillos, pero no puede pagar un ilustrador por cada cuento, y las herramientas de IA genéricas le dan imágenes que no se parecen a su idea y con el título mal escrito. Aclaración honesta: Valeria es un arquetipo de diseño que construimos antes de las entrevistas; las cinco entrevistas con consentimiento están pendientes, por eso aquí no hay citas.  PREGUNTAS PROBABLES DEL JURADO: ¿Cómo saben que la necesidad es real? Valeria es un arquetipo de diseño; las cinco entrevistas están pendientes, así que no afirmamos evidencia de campo. ¿Por qué IA y no un ilustrador? No lo reemplaza: entrega un concepto de portada con cinco opciones comparables a partir del dibujo de la persona.

## Slide 3

TIEMPO: 0:40. Esta es nuestra protopersona: Valeria, una estudiante que crea y adapta cuentos para niños de su entorno. Tiene ideas claras de personajes y escena, pero no formación profesional en diseño; al usar herramientas de IA, a veces el resultado cambia su idea, los colores no transmiten lo infantil que buscaba, o el título sale ilegible. Por eso sus prioridades son fidelidad al boceto, colores y estilo acordes al público infantil, y un título legible: FROG se diseña directamente para resolver estas tres frustraciones.  PREGUNTAS PROBABLES DEL JURADO: ¿Valeria es una persona real? No: es un arquetipo de diseño que sintetiza las necesidades identificadas en la exploración del problema; las entrevistas de validación están pendientes.

## Slide 4

TIEMPO: 0:45. El flujo completo: la persona sube o dibuja un boceto y cuenta su historia; el sistema genera exactamente cinco portadas, donde cada una cambia un solo parámetro; la persona acepta o rechaza cada una, con el motivo; un planificador usa esas decisiones para proponer la siguiente ronda, hasta un máximo de tres; y al final un agente redacta un resumen de lo que ocurrió, que se verifica contra el registro.

## Slide 5

TIEMPO: 1:00. La arquitectura completa. 1) Preprocesamiento, guardrails de entrada y agente de historia: se rechaza un boceto vacío, una foto de una persona real o texto no apto. 2) El planificador propone las cinco configuraciones con Thompson. 3) El motor A o el B genera las portadas. 4) Guardrails de salida, agente tipográfico y render del título. 5) La interfaz: aceptar o rechazar con motivo y editar la fuente. 6) Todo queda en un registro JSON. Si hay otra ronda, se actualizan las preferencias y se vuelve al planificador; si no, 7) el agente LLM redacta el resumen y un validador lo compara con el registro, con hasta dos reintentos y una plantilla de respaldo.  PREGUNTAS PROBABLES DEL JURADO: ¿Qué evita que el LLM invente? Un validador compara cada ID y motivo del resumen con el registro y reintenta hasta dos veces; si falla, usa una plantilla. ¿Qué conecta todo? El registro JSON de cada decisión.

## Slide 6

TIEMPO: 0:45. La persona controla seis parámetros: estilo, paleta, edad, ambiente, fidelidad al boceto y zona del título. En cada ronda uno de ellos varía entre las cinco portadas y los otros quedan fijos, para que se entienda qué cambió. El planificador usa muestreo de Thompson: va aprendiendo qué valores prefiere la persona según lo que acepta, fija esos y explora al azar los demás, hasta un máximo de tres rondas.  PREGUNTAS PROBABLES DEL JURADO: ¿Por qué Thompson? Equilibra explorar y aprovechar con pocas rondas (máximo 3). En simulación supera al azar en la ronda 3 (43 % frente a 34,8 %); con usuarios reales todavía no está probado.

## Slide 7

TIEMPO: 0:45. Usamos dos motores gratuitos en Colab. El A, Stable Diffusion con ControlNet, reinterpreta el boceto en cada estilo: 93 % de acierto de estilo, 7,8 segundos por ronda. El B, SD-Turbo, es cinco veces más rápido y casi copia el dibujo (98 % de fidelidad), pero por eso los cinco estilos apenas se distinguen: solo 20 % de acierto. Por eso A es el principal y B queda como respaldo y línea base.  PREGUNTAS PROBABLES DEL JURADO: ¿Por qué dos motores? El A reinterpreta el estilo (93 %) y el B es muy rápido pero copia el boceto (20 % de estilo): sirve de respaldo y de línea base. Si uno se queda sin memoria, se usa el otro.

## Slide 8

TIEMPO: 1:00. Hay tres agentes y ninguno recibe imágenes. El de historia lee el texto y extrae personajes, objetos y lugar; un verificador comprueba que cada elemento aparezca en la historia. El tipográfico recibe medidas de la zona del título y propone fuente y color; las letras las dibuja siempre un renderizador determinista, así el título nunca sale mal escrito. El de resumen redacta lo ocurrido a partir del registro y un validador contrasta cada ID y motivo con ese registro. Los modelos son Qwen 2.5 y Phi 3.5, que corren dentro de la sesión de Colab.  PREGUNTAS PROBABLES DEL JURADO: ¿El LLM ve las imágenes? No: recibe texto, medidas o el registro JSON. ¿Qué tan fiel es el resumen? Una comprobación automática halló 85 % en Qwen y 50 % en Phi; no evalúa la parte interpretativa.

## Slide 9

TIEMPO: 5:00 (demostración en vivo). Recorrido: 1) subo o dibujo un boceto; 2) cuento la historia y el agente extrae los personajes, objetos y lugar, que puedo corregir; 3) se generan las cinco portadas, cada una con su etiqueta del valor que cambia; 4) acepto o rechazo cada una y, si rechazo, marco el motivo; 5) genero una segunda ronda y se ve que el planificador aprendió; 6) termino y leo el resumen que redactó el agente. También muestro un guardrail: un texto bloqueado. Plan B: si Colab tarda, tener una ronda ya generada.

## Slide 10

TIEMPO: 0:45. Hay cuatro capas: texto, foto, imagen y derechos. En E5 probamos 30 entradas: el filtro de texto bloqueó las 20 que debía bloquear y se equivocó con 1 de 5 legítimas, por un nombre con marca. Las evasiones con eufemismos, como un perro herido sangrando, pasan el filtro de texto, por eso la imagen se revisa con CLIP. Un punto importante: el motor B, SD-Turbo, no trae filtro de seguridad propio; ahí CLIP es la única protección.  PREGUNTAS PROBABLES DEL JURADO: ¿Qué no cubren los guardrails? Las evasiones con eufemismos pasan el filtro de texto, CLIP detecta la mitad de las portadas no aptas que revisamos y el motor B no tiene filtro propio. Mejora: más descriptores y más casos.

## Slide 11

TIEMPO: 0:45. En E1 generamos 3 000 portadas. El motor A cumple estilo (93 % frente al 70 % exigido), elemento principal (91 %) y latencia, pero no la paleta: 70 % frente al 80 %. El gráfico de la derecha muestra por qué: pastel, fría y tierra pasan del 93 %, pero 'cálida' llega al 53 % y 'primarios vivos' al 1,5 %. Reforzamos el texto de esas dos paletas en el prompt y repetimos solo el eje paleta con los mismos 200 pares: sube a 79,2 %, con cálida en 71,5 % y primarios en 31,5 %; sigue por debajo del 80 %. Aclaración: el refuerzo se decidió después de ver el resultado y se midió sobre los mismos pares. El motor B gana en paleta y fidelidad al boceto porque casi lo copia.  PREGUNTAS PROBABLES DEL JURADO: ¿Por qué la paleta no llega al 80 %? 'Primarios' sigue en 31,5 %. Reforzamos el prompt tras ver el resultado y medimos sobre los mismos pares, así que no es una estimación independiente.

## Slide 12

TIEMPO: 1:00. Tres resultados. Primero, el planificador: con 500 usuarios simulados, Thompson y el azar empiezan iguales, pero en la ronda 3, con la evidencia de dos rondas, Thompson llega a 43 % de aceptación frente a 34,8 %. Segundo, los resúmenes: una comprobación automática contra el registro halló fieles 23 de los 27 de Qwen, 85 %, y 7 de los 14 de Phi, 50 %; no mide la parte interpretativa. Tercero, la legibilidad del título con OCR: el agente baja el error de 43 a 17,6 %, sin llegar al 5 %; el error lo concentran títulos cortos o con un dibujo detrás, y las 20 portadas peor leídas por el OCR se revisaron a mano y se leían sin esfuerzo.  PREGUNTAS PROBABLES DEL JURADO: ¿Son resultados con personas? No: los usuarios son simulados y la fidelidad del resumen se comprobó con un script. El estudio con usuarios y el SUS están pendientes.

## Slide 13

TIEMPO: 0:40. Probamos FROG con 10 sesiones de 9 personas ajenas a la computación, cada una con su propio boceto y su propia historia, y respondieron el cuestionario SUS. La media fue 86,8 sobre 100, con un intervalo de confianza al 95 % de 79,3 a 94,2; 9 de 10 sesiones superaron el criterio de 68. La única que quedó por debajo, 62,5, fue de una persona que no entendió el resumen ni los parámetros. Pidieron que se expliquen los estilos y que las imágenes sean más precisas, y les preocupa que se reutilicen sus bocetos y el trabajo de quienes ilustran. Aclaración honesta: nadie era autora, ilustradora o docente, y una persona participó dos veces; con 10 sesiones el resultado es descriptivo.  PREGUNTAS PROBABLES DEL JURADO: ¿86,8 es bueno? Sí, supera el promedio de referencia de 68, pero la muestra es pequeña y de conveniencia. ¿Las portadas del collage son suyas? Sí, de participantes que autorizaron mostrarlas.

## Slide 14

TIEMPO: 0:45. En E5 una persona revisó las 45 portadas generadas con las entradas de prueba: 42 eran aptas y 3 no. Con el umbral inicial de CLIP, 0,5, no detectó ninguna de las tres; con 0,25 detecta dos, aunque la calibración es débil porque son solo tres casos. Con 400 portadas más generadas sin filtro, una persona revisó las 25 más sospechosas: 10 no eran aptas, sobre todo dragones del motor B; con 0,25 se detectan 5 de esas 10 y se bloquean 5 aptas, y con 0,5 no se detecta ninguna. En sesgo, generamos 100 figuras humanas sin rasgos definidos y una persona anotó género y tono de piel percibidos: casi todo ambiguo, pero cuando hay rasgos tiende a piel clara y a género femenino, y ninguna imagen salió con tono oscuro. Es una observación con un solo anotador. El estudio con usuarios, E4, y la escala SUS están pendientes; no los reportamos.  PREGUNTAS PROBABLES DEL JURADO: ¿Qué concluyen del sesgo? Es una observación con 100 figuras y un solo anotador: cuando el modelo dibuja rasgos, tiende a piel clara. El prompt no añade género ni etnia; se podría ofrecer un parámetro explícito.

## Slide 15

TIEMPO: 0:30. Cinco limitaciones, sin esconderlas. El agente de historia no llega al 90 %: queda entre 59 y 80 % según modelo, idioma y tipo de comparación. La paleta del motor A pasó de 70 a 79 % tras reforzar el prompt, todavía bajo el 80 % pedido. El OCR del título no llega al 5 %. El filtro CLIP se calibró con tres casos. Y nos faltan las entrevistas, el estudio con usuarios y el SUS.  PREGUNTAS PROBABLES DEL JURADO: ¿Qué harían primero? Las entrevistas y el estudio con usuarios, mejorar el filtro de imagen del motor B y subir la precisión del agente de historia.

## Slide 16

TIEMPO: 0:30. En resumen: FROG genera cinco portadas comparables a partir del boceto y la historia, usa las decisiones de la persona para guiar las rondas, tiene agentes cuyo trabajo se puede verificar y límites de seguridad cuyos fallos medimos. Lo que sigue: entrevistas, estudio con usuarios y SUS, y un filtro de imagen más fuerte, sobre todo para el motor B. Gracias. TIEMPO TOTAL APROXIMADO: 14 min 45 s con la demostración de 5 min.
