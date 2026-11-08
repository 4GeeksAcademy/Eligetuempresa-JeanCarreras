# Informes de negocio

## Recepcion de RFP

La bandeja de intake está disponible en `/uis/backoffice/rfp-intake/`. Requiere
una sesión iniciada y consulta el router `/rfp-intake` del mismo backend. Acepta
PDF de hasta 25 MB, crea un ticket `analizando` y refresca su estado hasta
`analisis_completo` o `descartado`. El resultado muestra metadatos, métricas,
aspectos por departamento, responsables y el handoff de Ventas.

Antes de usarla, aplicar `services/brasaland-api/migrations/002_rfp_intake.sql`
en Supabase y configurar las variables del API. El detalle del pipeline y su
proceso de reproceso están en `services/brasaland-api/RFP_INTAKE.es.md`.

Vista disponible en `/uis/backoffice/reporting/`, para direccion y operaciones.
Consume exclusivamente `GET /api/v1/reporting/kpis` de la Parte 2. No contiene
datos de demostracion, no consulta tablas operativas ni ejecuta el pipeline.

## Ejecutar

Desde la raiz del monorepo:

```bash
npm ci --prefix uis/talent-pipeline-tracker
bash scripts/run_dashboard_local.sh
```

Abrir http://localhost:4173/platform/backoffice/. El script sirve las UIs
estaticas en el puerto interno 5510 y Next.js en 4173. Next.js expone los modulos
estaticos bajo `/platform/`, Talento en `/` y las utilidades en `/data-utils`.
La API se alcanza por `/backend/` en el mismo origen del navegador.
`DASHBOARD_PORT`, `STATIC_PORT` y `API_PORT` permiten cambiar los puertos.

El menu comun conecta Inicio, Direccion, Informes, RFP, Conocimiento,
Fidelizacion, Talento, Utilidades y el sitio publico. Mi cuenta conserva el
destino de retorno. El login sincroniza las claves de sesion existentes
`brasaland_token` y `brasaland_access_token`, sin tokens en las URLs.
El cierre de sesion borra ambas claves. Los destinos de retorno son del mismo origen.
El endpoint exige uno de los roles `executive`, `finance` o `admin`.
Talento usa `/api/v1/talent/records` y requiere `admin` o `manager`; ya no usa
el servicio externo de practicas por defecto. La vista de utilidades importa
las funciones de `src/utils/` y separa los resumenes por pais y moneda.

Provisionar `BRASALAND_JWT_SECRET` y `BRASALAND_AUTH_SECRET` en el entorno
de la API. Para una base vacia, el bootstrap de una cuenta administradora requiere
`BRASALAND_BOOTSTRAP_ADMIN_EMAIL` y `BRASALAND_BOOTSTRAP_ADMIN_PASSWORD`.
No hay cuentas ni passwords fijas. Consultar la configuracion de la API para
Supabase, RAG/LLM y correo; las pruebas temporales no sustituyen estos servicios.
Configurar `FRONTEND_BASE_URL` con el origen publicado y `/platform/auth`
para que los enlaces enviados por correo apunten a la aplicacion correcta.

## Contrato y limites

- Respuesta esperada: `{"rows": [...], "count": 0}`.
- Dimensiones verificadas del endpoint: `metric_date`, `store_id`, `country`.
- Cada campo numerico no identificador tiene una tabla con sus valores diarios.
- Se conserva el valor recibido: no se infieren porcentajes, monedas, formulas
  ni conversiones. No se suman paises ni se promedian porcentajes.
- El periodo inicial es la ultima semana completa de lunes a domingo (UTC).
- El endpoint limita la respuesta a 500 filas y no ofrece paginacion. Al alcanzar
  ese limite se advierte de posible truncamiento; reducir periodo o filtrar pais.
- La falta de datos, el fallo de conexion y los errores de permisos tienen estados
  distintos. Nunca se sustituyen valores ausentes por cero.

## Validacion

```bash
node --test uis/backoffice/reporting/client.test.mjs
```

Estas pruebas del consumidor son adicionales; no sustituyen los tests de las
tasks Python requeridos en `tests/pipelines/test_pipeline.py`.

## Estado y limites de validacion

El router de reporting y los endpoints de respuesta RFP de Parte 2 estan
registrados en la API. La UI de RFP conecta generacion, consulta de borradores,
evaluaciones, decisiones por departamento, arbitraje, trazabilidad y descarga
del documento final como JSON. Las decisiones requieren confirmacion explicita.
La ejecucion real de RFP requiere Supabase, sus migraciones y el proveedor LLM.
El acceso de Copilot a `data/` esta excluido por politica empresarial: no se han
modificado ni leido los archivos protegidos para construir esta pagina.

Los titulos actuales derivan de los nombres de columnas, reemplazando guiones
bajos por espacios. Falta contrastarlos con los nombres y unidades exactos del
diseno de KPIs antes de considerar esta vista una entrega final de negocio.
La navegacion por clics, el login y logout se verificaron en Chromium con una
cuenta y bases temporales. El home se verifico visualmente en escritorio y movil.
Tambien se ejecutaron las pruebas existentes de reporting, passwords y respuesta
RFP, y comprobaciones aisladas de CRUD de Talento y renderizado de RFP.
Quedan pendientes las pruebas con datos y servicios reales. No se afirma
cobertura de todos los KPIs del documento excluido ni cierre del capstone en produccion.