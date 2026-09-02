# Brasaland - Pipeline de Candidaturas

Frontend en Next.js para el equipo interno de Personas y Cultura de Brasaland.

## Objetivo

Permite gestionar postulaciones con flujo completo:

- Listado con filtros por estado y etapa usando query params.
- Busqueda por nombre o correo sin recarga de pagina.
- Ficha de candidatura con actualizacion rapida de estado y etapa.
- Formulario de alta de postulacion.
- Formulario de edicion de candidatura.
- Notas internas por candidatura (alta y eliminacion).

La interfaz esta adaptada a operacion multipais (Colombia y Florida) y mantiene los valores tecnicos requeridos por el tracker backend.

## Rutas

- `/` listado de candidaturas.
- `/candidates/[id]` detalle de candidatura.
- `/login` inicio de sesion.
- `/register` registro de usuarios.
- `/account/profile` consulta y edicion del perfil actual.

## Endpoints usados

- `GET /records`
- `POST /records`
- `GET /records/:id`
- `PUT /records/:id`
- `PATCH /records/:id`
- `GET /records/:id/notes`
- `POST /records/:id/notes`
- `DELETE /records/:id/notes/:note_id`

## Configuracion

Crear `.env.local` con:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_TRACKER_API_URL=https://playground.4geeks.com/tracker/api/v1
```

`NEXT_PUBLIC_API_URL` debe apuntar a la API de Brasaland para `POST /users`,
`POST /auth/login`, `GET /auth/me` y `PUT /profiles/me`.
`NEXT_PUBLIC_TRACKER_API_URL` identifica el backend de candidaturas. Tras iniciar sesion,
el token se guarda en `localStorage` y se envia como `Authorization: Bearer <token>` en
ambas APIs.

## Desarrollo local

```bash
npm install
npm run dev
```

Aplicacion en `http://localhost:3000`.

## Validacion de calidad

```bash
npm run lint
```

## Smoke test rapido

Con el servidor local corriendo, ejecutar:

```bash
npm run smoke:ui
```

El script valida:

- Respuesta 200 en `/`
- Respuesta 200 en `/candidates/:id` con un id real de la API
- Ciclo temporal de datos: `POST /records`, `PATCH /records/:id`, `PUT /records/:id`
- Notas temporales: `POST /records/:id/notes`, `GET /records/:id/notes`, `DELETE /records/:id/notes/:note_id`
- Limpieza final: `DELETE /records/:id`

El smoke crea un registro temporal y lo elimina al final (incluye cleanup automatico si hay fallo).

## Pruebas manuales

Ver checklist en [MANUAL-TEST.es.md](MANUAL-TEST.es.md).
