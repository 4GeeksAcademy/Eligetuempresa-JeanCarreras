// Validación de formulario de aplicación Brasaland

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('aplicacionForm');
  const fields = [
    'nombre', 'email', 'telefono', 'pais', 'experiencia', 'puesto', 'mensaje'
  ];

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    let valid = true;

    // Limpiar errores previos
    fields.forEach(field => {
      document.getElementById('error-' + field).classList.add('hidden');
    });

    // Validaciones
    // Nombre
    const nombre = form.nombre.value.trim();
    if (nombre.length < 3) {
      showError('nombre', 'El nombre debe tener al menos 3 caracteres.');
      valid = false;
    }

    // Email
    const email = form.email.value.trim();
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      showError('email', 'Ingresa un correo electrónico válido.');
      valid = false;
    }

    // Teléfono
    const telefono = form.telefono.value.trim();
    if (!/^[0-9\-\+\s]{7,}$/.test(telefono)) {
      showError('telefono', 'Ingresa un teléfono válido.');
      valid = false;
    }

    // País
    if (!form.pais.value) {
      showError('pais', 'Selecciona un país.');
      valid = false;
    }

    // Experiencia
    const experiencia = parseInt(form.experiencia.value, 10);
    if (isNaN(experiencia) || experiencia < 0 || experiencia > 40) {
      showError('experiencia', 'Ingresa un número de años válido (0-40).');
      valid = false;
    }

    // Puesto
    if (!form.puesto.value) {
      showError('puesto', 'Selecciona un puesto de interés.');
      valid = false;
    }

    // Mensaje
    const mensaje = form.mensaje.value.trim();
    if (mensaje.length < 10) {
      showError('mensaje', 'Cuéntanos brevemente tu motivación (mínimo 10 caracteres).');
      valid = false;
    }

    if (valid) {
      form.reset();
      document.getElementById('form-success').classList.remove('hidden');
      setTimeout(() => {
        document.getElementById('form-success').classList.add('hidden');
      }, 4000);
    }
  });

  function showError(field, message) {
    const error = document.getElementById('error-' + field);
    error.textContent = message;
    error.classList.remove('hidden');
  }
});
