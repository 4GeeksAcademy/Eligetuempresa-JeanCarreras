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
python -m http.server 5510 --bind 0.0.0.0 --directory uis
```

Abrir http://localhost:5510/backoffice/reporting/?apiBase=http://localhost:8000
con la API de la Parte 2 ejecutandose en el puerto 8000. En Codespaces se deriva
el host del puerto 8000; `apiBase` permite indicar otra direccion.

La pagina usa el token `brasaland_token` de la sesion existente, sin credenciales
fijas ni tokens en la URL. Iniciar sesion desde Mi cuenta en el mismo origen web.
El endpoint exige uno de los roles `executive`, `finance` o `admin`.
El origen del dashboard debe estar permitido por la configuracion CORS de la API.

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

## Pendientes de integracion

La rama de Parte 3 no incluye aun el servicio de reporting de Parte 2.
Hasta integrarlo, la pagina mostrara un estado de servicio no disponible.
El acceso de Copilot a `data/` esta excluido por politica empresarial: no se han
modificado ni leido los archivos protegidos para construir esta pagina.

Los titulos actuales derivan de los nombres de columnas, reemplazando guiones
bajos por espacios. Falta contrastarlos con los nombres y unidades exactos del
diseno de KPIs antes de considerar esta vista una entrega final de negocio.
Tambien quedan pendientes las pruebas con datos reales y la verificacion visual
en navegador. No se afirma cobertura de todos los KPIs del documento excluido.