'use strict';
const one = (selector, root = document) => root.querySelector(selector);
const all = (selector, root = document) => [...root.querySelectorAll(selector)];
const menu = one('.menu-toggle');
if (menu) menu.addEventListener('click', () => {
  const panel = document.getElementById(menu.getAttribute('aria-controls'));
  panel.hidden = !panel.hidden;
  menu.setAttribute('aria-expanded', String(!panel.hidden));
});
all('.password-toggle').forEach(button => button.addEventListener('click', () => {
  const input = document.getElementById(button.getAttribute('aria-controls'));
  const visible = input.type === 'password';
  input.type = visible ? 'text' : 'password';
  button.textContent = visible ? 'Ocultar' : 'Mostrar';
  button.setAttribute('aria-pressed', String(visible));
}));
all('[data-role-form]').forEach(form => {
  const role = form.elements.rol;
  const help = one('[data-role-help]', form);
  const update = () => {
    for (const [name, value] of [['profesional_id', 'profesional'], ['paciente_id', 'paciente']]) {
      const field = form.elements[name];
      if (!field) continue;
      const active = role.value === value;
      field.closest('label').hidden = !active;
      field.disabled = !active;
      field.required = active;
    }
    if (help) help.textContent = ({profesional:'Vincula la cuenta al funcionario que realizará las atenciones.', paciente:'Vincula la cuenta al paciente que consultará sus propias citas.', admin:'Puede administrar usuarios, pacientes y agendas.', recepcion:'Puede registrar pacientes, gestionar admisiones y reservar citas.', auditor:'Puede consultar los eventos de auditoría.'})[role.value] || 'Elige un rol para continuar.';
  };
  role.addEventListener('change', update); update();
});
all('[data-admision-form]').forEach(form => {
  const patient = form.elements.paciente_id;
  if (patient) {
    const fieldset = one('[data-new-patient]', form);
    const update = () => {
      fieldset.hidden = Boolean(patient.value);
      fieldset.disabled = Boolean(patient.value);
      one('[data-patient-mode-help]', form).textContent = patient.value ? 'Usaremos los datos del paciente seleccionado. No necesitas registrarlo de nuevo.' : 'Completa los datos para registrar un paciente nuevo.';
    };
    patient.addEventListener('change', update); update();
  }
  const professional = form.elements.profesional_id;
  professional.addEventListener('change', () => {
    const option = professional.selectedOptions[0];
    if (option.dataset.especialidad) form.elements.especialidad.value = option.dataset.especialidad;
  });
});
all('[data-reserva-form]').forEach(form => {
  const update = () => {
    all('option[data-paciente]', form.elements.admision_id).forEach(option => {
      const matches = option.dataset.paciente === form.elements.paciente_id.value;
      option.hidden = !matches; option.disabled = !matches;
      if (!matches && option.selected) form.elements.admision_id.value = '';
    });
  };
  form.elements.paciente_id.addEventListener('change', update); update();
});
all('[data-document-form]').forEach(form => {
  const input = form.elements.archivo;
  input.addEventListener('change', () => {
    const file = input.files[0];
    let error = '';
    if (file && file.size > 5 * 1024 * 1024) error = 'El archivo supera los 5 MB. Selecciona uno más pequeño.';
    else if (file && !/\.(pdf|png|jpe?g)$/i.test(file.name)) error = 'Selecciona un archivo PDF, JPG o PNG.';
    input.setCustomValidity(error);
    one('[data-file-status]', form).textContent = error || (file ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB. Listo para adjuntar.` : 'Elige un PDF, JPG o PNG de hasta 5 MB.');
  });
});
all('[data-agenda-form]').forEach(form => {
  const preview = one('[data-agenda-preview]', form);
  const field = name => form.elements[name];
  const minutes = value => { const [h,m] = value.split(':').map(Number); return h*60+m; };
  const update = () => {
    const show = (message, invalid = false) => {
      one('p', preview).textContent = message;
      preview.classList.toggle('error', invalid);
    };
    const startDate = Date.parse(`${field('desde').value}T00:00:00Z`);
    const endDate = Date.parse(`${field('hasta').value}T00:00:00Z`);
    const start = minutes(field('inicio').value), end = minutes(field('fin').value);
    const duration = Number(field('minutos').value), capacity = Number(field('cupos').value);
    const days = all('[name="dias"]:checked', form).map(input => Number(input.value));
    if (![startDate,endDate,start,end].every(Number.isFinite) || !duration || !capacity) return show('Completa fechas, horario, duración y cupos para revisar la agenda.');
    const countDays = (endDate-startDate)/86400000+1;
    if (countDays < 1 || countDays > 31) return show('Elige un intervalo de 1 a 31 días.', true);
    if (end <= start || duration < 5 || duration > 240 || capacity < 1 || capacity > 20 || !Number.isInteger(duration) || !Number.isInteger(capacity)) return show('Revisa el horario, la duración (5 a 240 minutos) y los cupos (1 a 20).', true);
    if (!days.length) return show('Selecciona al menos un día de la semana.', true);
    const pauseStart = field('pausa_inicio').value, pauseEnd = field('pausa_fin').value;
    const ps = minutes(pauseStart), pe = minutes(pauseEnd);
    if (Boolean(pauseStart) !== Boolean(pauseEnd) || (pauseStart && (ps >= pe || ps < start || pe > end))) return show('Completa ambos horarios de pausa dentro de la jornada.', true);
    let blocks = 0, workDays = 0;
    for (let date = startDate; date <= endDate; date += 86400000) {
      if (!days.includes((new Date(date).getUTCDay()+6)%7)) continue;
      let daily = 0;
      for (let slot = start; slot + duration <= end; slot += duration) {
        if (!pauseStart || slot + duration <= ps || slot >= pe) daily++;
      }
      blocks += daily; if (daily) workDays++;
    }
    if (!blocks) return show('No se generan bloques completos. Revisa los días, la duración y la pausa.', true);
    if (blocks > 500) return show(`Se generarían ${blocks} bloques. Reduce el intervalo a un máximo de 500 bloques.`, true);
    show(`${workDays} día(s) con atención · ${blocks} bloques de ${duration} minutos · ${blocks*capacity} cupos en total. Se comprobarán los cruces de agenda al guardar.`);
  };
  field('tipo_id').addEventListener('change', () => {
    const option = field('tipo_id').selectedOptions[0];
    if (option.dataset.minutos) field('minutos').value = option.dataset.minutos;
    if (option.dataset.cupos) field('cupos').value = option.dataset.cupos;
    update();
  });
  form.addEventListener('input', update); form.addEventListener('change', update); update();
});
const error = one('.alert.error');
if (error) error.focus();
