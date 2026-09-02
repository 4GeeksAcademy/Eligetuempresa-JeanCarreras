# Pruebas Manuales - Talent Pipeline Tracker

## Preparacion

1. Configurar `NEXT_PUBLIC_API_URL=http://localhost:8000` y, si aplica,
   `NEXT_PUBLIC_TRACKER_API_URL` en `.env.local`.
2. Ejecutar `npm run dev`.
3. Abrir `http://localhost:3000`.

## Casos felices

1. Listado inicial
- Esperado: aparece tabla con candidaturas, sin error.

2. Filtro por estado
- Accion: seleccionar estado en filtro.
- Esperado: URL actualiza query param `status` y la tabla se filtra.

3. Filtro por etapa
- Accion: seleccionar etapa en filtro.
- Esperado: URL actualiza query param `stage` y la tabla se filtra.

4. Busqueda por texto
- Accion: escribir parte del nombre o email.
- Esperado: tabla se filtra sin recargar pagina.

5. Alta de candidatura
- Accion: abrir formulario, completar campos requeridos y enviar.
- Esperado: mensaje de exito y nuevo registro visible en listado.

6. Navegacion a detalle
- Accion: abrir una candidatura desde el listado.
- Esperado: carga vista de detalle y permite volver al listado manteniendo contexto.

7. Cambio rapido de estado
- Accion: seleccionar otro estado en detalle.
- Esperado: mensaje de exito y dato actualizado.

8. Cambio rapido de etapa
- Accion: seleccionar otra etapa en detalle.
- Esperado: mensaje de exito y dato actualizado.

9. Edicion de candidatura
- Accion: cambiar uno o mas campos y guardar.
- Esperado: mensaje de exito y valores persistidos.

10. Agregar nota
- Accion: escribir nota y enviar.
- Esperado: nota aparece en el listado de notas.

11. Eliminar nota
- Accion: eliminar una nota existente.
- Esperado: nota desaparece y se muestra confirmacion.

## Casos de error

1. API caida o URL invalida
- Accion: cambiar `NEXT_PUBLIC_API_URL` por una URL invalida y recargar.
- Esperado: mensajes de error visibles en listado o detalle.

2. Validacion de formulario de alta
- Accion: intentar enviar sin campos requeridos.
- Esperado: navegador bloquea envio y marca campos obligatorios.

3. Validacion de formulario de edicion
- Accion: limpiar campo requerido y guardar.
- Esperado: navegador bloquea envio por campos requeridos.

4. Error al guardar cambios
- Accion: provocar fallo de red y guardar.
- Esperado: feedback visual de error, sin bloqueo silencioso.

## Criterio de salida

- Todos los casos felices cumplen comportamiento esperado.
- Los casos de error muestran feedback claro.
- `npm run lint` termina sin errores.
