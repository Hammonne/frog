/**
 * Crea el formulario de Google del estudio E4 (consentimiento + datos + SUS + preguntas finales)
 * y una hoja de cálculo donde caen las respuestas.
 *
 * Uso: entra a https://script.google.com con tu cuenta, "Nuevo proyecto", pega este archivo,
 * guarda y ejecuta la función `crearFormularioE4` (acepta los permisos). Al terminar, mira
 * "Registro de ejecución": ahí salen el enlace para compartir y el enlace para editar.
 */
function crearFormularioE4() {
  const form = FormApp.create('FROG · Prueba con usuarios');
  form.setCollectEmail(false)
      .setAllowResponseEdits(false)
      .setProgressBar(true)
      .setConfirmationMessage('¡Gracias por participar! Tus respuestas ya quedaron registradas.');

  form.setDescription(
    'Proyecto FROG: sistema generativo interactivo de portadas para libros infantiles.\n' +
    'Curso Planificación y Toma de Decisiones en IA, UTEC. Profesora: Dra. Aurea Soriano-Vargas.\n' +
    'Equipo: Andrea Coa, Nayeli Guzman, Maria Surco, Bihonda Epiquien, Jimena Gurbillon.\n\n' +
    'Completa este formulario después de usar la herramienta con el equipo. Toma unos 5 minutos. ' +
    'Evaluamos la herramienta, no a ti.');

  // ---------------------------------------------------------------- 1. consentimiento
  form.addSectionHeaderItem().setTitle('Consentimiento informado').setHelpText(
    'Qué harás: usaste la herramienta con una historia breve y un boceto tuyos, y ahora respondes un ' +
    'cuestionario de 10 preguntas y unas preguntas finales.\n\n' +
    '• Participación voluntaria: puedes dejar de participar cuando quieras, sin dar explicaciones.\n' +
    '• Qué guardamos: tus respuestas con un código (U1, U2...) y el registro de tus decisiones en la ' +
    'herramienta. No guardamos tu nombre en los resultados. El registro no incluye tu boceto ni el texto de tu historia.\n' +
    '• Tu boceto y tu historia solo se usan para esta prueba y no se publican. Declaras que el boceto es tuyo ' +
    'o que tienes permiso para usarlo.\n' +
    '• Para retirar tus datos, escribe a cualquier integrante del equipo.');

  const acepta = form.addMultipleChoiceItem().setTitle('¿Aceptas participar en esta prueba?').setRequired(true);
  const datos = form.addPageBreakItem().setTitle('Sobre ti');
  acepta.setChoices([
    acepta.createChoice('Sí, acepto participar', datos),
    acepta.createChoice('No acepto', FormApp.PageNavigationType.SUBMIT)
  ]);

  form.addCheckboxItem()
      .setTitle('Autorizaciones opcionales')
      .setHelpText('Puedes marcar ninguna, una o las dos.')
      .setChoiceValues([
        'Autorizo que se grabe la pantalla y la voz durante mi sesión (se borra al terminar el curso)',
        'Autorizo mostrar en el informe las portadas generadas en mi sesión'
      ]);

  // ---------------------------------------------------------------- 2. datos
  form.addTextItem()
      .setTitle('Código de participante')
      .setHelpText('Te lo da el equipo (por ejemplo U3). No escribas tu nombre.')
      .setRequired(true);
  form.addMultipleChoiceItem()
      .setTitle('Rango de edad')
      .setChoiceValues(['Menos de 18', '18 a 24', '25 a 34', '35 a 49', '50 o más'])
      .setRequired(true);
  form.addMultipleChoiceItem()
      .setTitle('¿Estudias o trabajas en Ciencia de la Computación o Ciencia de Datos?')
      .setChoiceValues(['No', 'Sí'])
      .setRequired(true);
  form.addMultipleChoiceItem()
      .setTitle('¿Tu relación con los cuentos infantiles?')
      .setChoiceValues(['Escribo cuentos', 'Enseño o trabajo con niñas y niños', 'Dibujo o ilustro',
                        'Leo cuentos a niñas o niños de mi familia', 'Otra'])
      .setRequired(true);

  // ---------------------------------------------------------------- 3. SUS
  form.addPageBreakItem().setTitle('Cuestionario de usabilidad')
      .setHelpText('Marca de 1 (totalmente en desacuerdo) a 5 (totalmente de acuerdo). Se refiere a la herramienta que acabas de usar.');
  const sus = [
    'Creo que me gustaría usar esta herramienta con frecuencia.',
    'Encontré la herramienta innecesariamente compleja.',
    'Pensé que la herramienta era fácil de usar.',
    'Creo que necesitaría ayuda de una persona con conocimientos técnicos para usarla.',
    'Encontré que las funciones de la herramienta estaban bien integradas.',
    'Pensé que había demasiada inconsistencia en la herramienta.',
    'Imagino que la mayoría de las personas aprendería a usarla muy rápido.',
    'Encontré la herramienta muy incómoda de usar.',
    'Me sentí muy seguro/a usando la herramienta.',
    'Necesité aprender muchas cosas antes de poder usarla.'
  ];
  sus.forEach(function (texto, i) {
    form.addScaleItem()
        .setTitle((i + 1) + '. ' + texto)          // el número al inicio lo lee experimentos/e4_sus.py
        .setBounds(1, 5)
        .setLabels('Totalmente en desacuerdo', 'Totalmente de acuerdo')
        .setRequired(true);
  });

  // ---------------------------------------------------------------- 4. preguntas finales
  form.addPageBreakItem().setTitle('Preguntas finales').setHelpText('Todas son opcionales; responde con tus palabras.');
  [
    '¿Las cinco propuestas se parecían a lo que imaginabas?',
    '¿Entendiste para qué sirve cada parámetro (estilo, paleta, edad...)?',
    '¿El resumen explicó bien lo que pasó en tu sesión? ¿Algo te pareció incorrecto?',
    '¿Qué cambiarías primero?',
    '¿Qué te preocupa de que una IA genere la portada de un cuento?'
  ].forEach(function (p) { form.addParagraphTextItem().setTitle(p); });

  // ---------------------------------------------------------------- respuestas en una hoja
  const hoja = SpreadsheetApp.create('FROG · Respuestas de la prueba con usuarios');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, hoja.getId());

  Logger.log('Enlace para compartir con participantes: ' + form.getPublishedUrl());
  Logger.log('Enlace para editar: ' + form.getEditUrl());
  Logger.log('Hoja de respuestas: ' + hoja.getUrl());
}
