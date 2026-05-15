// Validación de formulario de aplicación Brasaland

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('aplicacionForm');
  if (!form) return;
  const fields = [
    'nombre', 'email', 'telefono', 'pais', 'fecha_disponibilidad', 'experiencia', 'puesto', 'mensaje'
  ];

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    let valid = true;

    // Limpiar errores previos
    fields.forEach(field => {
      const input = form[field];
      const error = document.getElementById('error-' + field);
      if (error) {
        error.textContent = '';
        error.classList.add('hidden');
      }
      if (input) {
        input.setAttribute('aria-invalid', 'false');
      }
    });

    document.getElementById('form-success').classList.add('hidden');

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

    // País
    const pais = form.pais.value;
    if (!pais) {
      showError('pais', 'Selecciona un país.');
      valid = false;
    }

    // Teléfono con regla por país (operación CO/US)
    const telefono = form.telefono.value.trim();
    const telefonoLimpio = telefono.replace(/\D/g, '');
    if (!/^[0-9\-\+\s]{7,}$/.test(telefono)) {
      showError('telefono', 'Ingresa un teléfono válido.');
      valid = false;
      } else if (pais === 'Colombia') {
        const esMovilCO = /^3\d{9}$/.test(telefonoLimpio) || /^(57)?3\d{9}$/.test(telefonoLimpio);
      if (!esMovilCO) {
        showError('telefono', 'Para Colombia usa un número móvil válido (ej. 3XXXXXXXXX o +57 3XXXXXXXXX).');
        valid = false;
      }
    } else if (pais === 'Estados Unidos') {
      const esValidoUS = /^\d{10}$/.test(telefonoLimpio) || /^1\d{10}$/.test(telefonoLimpio);
      if (!esValidoUS) {
        showError('telefono', 'Para Estados Unidos usa un número válido de 10 dígitos (opcional prefijo +1).');
        valid = false;
      }
    }

    // Fecha de disponibilidad
    const fechaDisponibilidad = form.fecha_disponibilidad.value;
    if (!fechaDisponibilidad) {
      showError('fecha_disponibilidad', 'Selecciona una fecha de disponibilidad.');
      valid = false;
    } else {
      const hoy = new Date();
      hoy.setHours(0, 0, 0, 0);
      const fechaInicio = new Date(fechaDisponibilidad + 'T00:00:00');
      if (fechaInicio < hoy) {
        showError('fecha_disponibilidad', 'La fecha de disponibilidad no puede ser anterior a hoy.');
        valid = false;
      }
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

    // Validación en tiempo real
  fields.forEach(field => {
    const input = form[field];
    if (input) {
      input.addEventListener('input', () => {
        const error = document.getElementById('error-' + field);
        if (error) {
          error.textContent = '';
          error.classList.add('hidden');
        }
        input.setAttribute('aria-invalid', 'false');
      });
      input.addEventListener('blur', () => {
          // Validar solo el campo en blur, sin disparar submit global.
          validateField(field);
      });
    }
  });

  form.addEventListener('reset', () => {
    fields.forEach(field => {
      const input = form[field];
      const error = document.getElementById('error-' + field);
      if (error) {
        error.textContent = '';
        error.classList.add('hidden');
      }
      if (input) {
        input.setAttribute('aria-invalid', 'false');
      }
    });
    document.getElementById('form-success').classList.add('hidden');
  });

  function showError(field, message) {
    const error = document.getElementById('error-' + field);
    error.textContent = message;
    error.classList.remove('hidden');
    const input = form[field];
    if (input) {
      input.setAttribute('aria-invalid', 'true');
    }
  }

    function validateField(field) {
      const input = form[field];
      if (!input) return true;

      const clearError = () => {
        const error = document.getElementById('error-' + field);
        if (error) {
          error.textContent = '';
          error.classList.add('hidden');
        }
        input.setAttribute('aria-invalid', 'false');
      };

      clearError();

      if (field === 'nombre') {
        if (form.nombre.value.trim().length < 3) {
          showError('nombre', 'El nombre debe tener al menos 3 caracteres.');
          return false;
        }
        return true;
      }

      if (field === 'email') {
        if (!/^\S+@\S+\.\S+$/.test(form.email.value.trim())) {
          showError('email', 'Ingresa un correo electrónico válido.');
          return false;
        }
        return true;
      }

      if (field === 'pais') {
        if (!form.pais.value) {
          showError('pais', 'Selecciona un país.');
          return false;
        }
        return true;
      }

      if (field === 'telefono') {
        const telefono = form.telefono.value.trim();
        const telefonoLimpio = telefono.replace(/\D/g, '');
        const pais = form.pais.value;

        if (!/^[0-9\-\+\s]{7,}$/.test(telefono)) {
          showError('telefono', 'Ingresa un teléfono válido.');
          return false;
        }

        if (pais === 'Colombia') {
          const esMovilCO = /^3\d{9}$/.test(telefonoLimpio) || /^(57)?3\d{9}$/.test(telefonoLimpio);
          if (!esMovilCO) {
            showError('telefono', 'Para Colombia usa un número móvil válido (ej. 3XXXXXXXXX o +57 3XXXXXXXXX).');
            return false;
          }
        }

        if (pais === 'Estados Unidos') {
          const esValidoUS = /^\d{10}$/.test(telefonoLimpio) || /^1\d{10}$/.test(telefonoLimpio);
          if (!esValidoUS) {
            showError('telefono', 'Para Estados Unidos usa un número válido de 10 dígitos (opcional prefijo +1).');
            return false;
          }
        }
        return true;
      }

      if (field === 'fecha_disponibilidad') {
        const fechaDisponibilidad = form.fecha_disponibilidad.value;
        if (!fechaDisponibilidad) {
          showError('fecha_disponibilidad', 'Selecciona una fecha de disponibilidad.');
          return false;
        }
        const hoy = new Date();
        hoy.setHours(0, 0, 0, 0);
        const fechaInicio = new Date(fechaDisponibilidad + 'T00:00:00');
        if (fechaInicio < hoy) {
          showError('fecha_disponibilidad', 'La fecha de disponibilidad no puede ser anterior a hoy.');
          return false;
        }
        return true;
      }

      if (field === 'experiencia') {
        const experiencia = parseInt(form.experiencia.value, 10);
        if (isNaN(experiencia) || experiencia < 0 || experiencia > 40) {
          showError('experiencia', 'Ingresa un número de años válido (0-40).');
          return false;
        }
        return true;
      }

      if (field === 'puesto') {
        if (!form.puesto.value) {
          showError('puesto', 'Selecciona un puesto de interés.');
          return false;
        }
        return true;
      }

      if (field === 'mensaje') {
        if (form.mensaje.value.trim().length < 10) {
          showError('mensaje', 'Cuéntanos brevemente tu motivación (mínimo 10 caracteres).');
          return false;
        }
        return true;
      }

      return true;
    }
});
