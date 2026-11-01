# Auditoria de seguridad Brasaland

## Estado de entrega

Revision local con correcciones y evidencia reproducible. Los hallazgos criticos
SEC-01, SEC-02 y SEC-03 estan corregidos en codigo; Next.js fue actualizado para
cerrar tambien SEC-08. NO hay sign-off: falta validar el servidor real y revisar
el interior del pipeline RAG, cuya lectura bloquea el editor. No desplegar.
Fecha de registro: 2026-11-01 (fecha de la sesion, no reloj del servidor).
Commit de referencia: `6e0619e0ff3cc1863afad42b797cc77db9ba4115`.
Rama de trabajo: `feature/owasp-top10-audit`.

Se ejecuto `git pull --ff-only` con resultado `Already up to date` antes de crear
la rama. El arbol de trabajo estaba limpio.

## Alcance y fuentes

El briefing `docs/brasaland-BRIEFING.es.md` describe exclusivamente el modelo de
pronostico de ventas, no un inventario de aplicaciones. No basta para excluir
otros servicios. El alcance se complementa con `CONTEXT.md`,
`docs/BRASALAND-ARCHITECTURE.es.md` y `docs/BRASALAND-ROADMAP.es.md`.

Componentes que deben inventariarse y evaluarse por separado:

- Backend: API central en `services/brasaland-api/`, autenticacion, entidades,
  ingestion de eventos, reporting y trabajos automatizados.
- Frontend: aplicaciones en `uis/` y paginas HTML de la raiz y `src/`.
  Determinar cuales estan implementadas y cuales son solo documentacion.
- Sistema agentico: `agents/`, herramientas, rutas de asistentes/RAG en la API,
  permisos por usuario, fuentes recuperadas y conexiones externas.
- Datos y dependencias: Qdrant, almacenamiento, secretos, dependencias y
  artefactos del modelo de ventas. No cargar artefactos no confiables.
- Infraestructura: servidor real, SSH, usuario operativo, permisos, firewall,
  proxy/TLS y diferencia entre puertos publicados y accesibles externamente.

El inventario revisado comprende API central, usuarios/perfiles, telemetria,
reporting, dashboard ejecutivo, marketing, backoffice, asistente de conocimiento,
cliente de talento Next.js y formulario publico. `agents/_template/agent.py`
esta vacio y `agents/tools/` contiene documentacion: no son agentes ejecutables.
El sistema agentico real incluye `/knowledge/query` y
`GET /api/v1/executive/ask`. El segundo es un asistente determinista de metricas,
con consultas parametrizadas y fuentes, no un ejecutor de SQL generado por LLM.

El modelo de ventas del briefing es un proceso offline: el codigo revisado lee
CSV y genera `models.joblib`, no recibe uploads por HTTP. Su README advierte
que solo deben cargarse artefactos de confianza. Se audito el grafo de
dependencias declarado por el proyecto raiz; no se ejecuto entrenamiento.

No se ha confirmado que todos estos componentes esten desplegados. El editor
rechazo la lectura de `data/pipelines/rag.py` y de archivos `.env.example`.
No se eludieron esas restricciones: no se certifica el prompt, egress,
almacenamiento de claves ni comportamiento de herramientas dentro del pipeline.

## Linea base reproducible

Las consultas se ejecutaron en un Codespace de desarrollo, no en un servidor de
produccion. No se modificaron usuarios, SSH, firewall ni permisos del sistema.
No se ejecutaron escaneos contra sistemas externos.

| Evidencia | Resultado observado | Limite de la conclusion |
| --- | --- | --- |
| `id` | `uid=1000(codespace)`, grupo `docker` | Usuario local no-root; no demuestra usuario operativo dedicado en produccion. El grupo Docker suele permitir privilegios equivalentes a root. |
| `ss -lntup` | TCP `0.0.0.0:2000`, `0.0.0.0:2222` y equivalentes IPv6; otros listeners en loopback | Interfaces locales del contenedor; no demuestra exposicion publica ni identifica por si solo cada servicio. |
| `docker-compose.yml:2-9` | Qdrant `v1.14.1`, publicaciones `6333:6333` y `6334:6334`, volumen persistente | Compose publica en todas las interfaces por defecto; no prueba que Qdrant estuviera ejecutandose. |
| `docker-compose.yml:2-9` | Sin configuracion de API key o TLS en el servicio | Riesgo de acceso no autenticado si se despliega tal cual y la red permite acceso; explotabilidad y severidad pendientes. |
| `command -v sshd ufw nft iptables docker` | Disponibles `sshd`, `nft`, `iptables`, `docker`; `ufw` no encontrado | Ausencia de UFW no implica ausencia de firewall. Reglas efectivas pendientes. |
| Consulta filtrada de `sshd -T` | Filtro fallo: `bash: rg: command not found` | No hay evidencia valida sobre `PermitRootLogin` ni autenticacion por password. |
| `docker compose config --quiet` | Sin error visible | Solo valida sintaxis; no certifica seguridad ni estado del servicio. |

Para repetir las consultas sin depender de ripgrep:

```bash
git rev-parse HEAD
id
ss -lntup
docker compose config --quiet
sshd -T | grep -E '^(permitrootlogin|passwordauthentication|pubkeyauthentication|port) '
```

Consultar SSH en el servidor objetivo con privilegios autorizados. Si faltan
permisos o claves del host, registrar el error; no inferir una politica segura.
La politica efectiva debe considerar tambien bloques `Match` mediante
`sshd -T -C user=root,host=HOST,addr=IP_ORIGEN` con valores reales.

## Marco OWASP

Se usara OWASP Top 10 **2021**, con identificadores explicitos para no mezclar
ediciones: <https://owasp.org/Top10/2021/>. Es una seleccion explicita de version,
no una afirmacion de que sea la edicion mas reciente.

`Aplica` indica una superficie relevante, no necesariamente una vulnerabilidad
abierta. `No aplica` se limita al mecanismo indicado, no a toda la plataforma.
Las referencias E01-E12 se detallan debajo. Una limitacion de acceso no se
clasifica como segura ni como `no aplica`.

| Categoria | Backend | Frontend | Sistema agentico |
| --- | --- | --- | --- |
| A01 Broken Access Control | Aplica: SEC-01 y SEC-05; validacion central de rol y cuenta activa, y reporte interno protegido (E01, E02). | Aplica: roles/tokens incrustados retirados; la autorizacion efectiva reside en la API, no en la UI (E03). | Aplica: SEC-04; RAG exige admin/manager/operations/executive antes de llamar al pipeline; `/api/v1/executive/ask` solo executive/admin (E04, E05). |
| A02 Cryptographic Failures | Aplica: SEC-02; secretos JWT/HMAC conocidos retirados, secretos provisionados obligatorios; TLS real sin verificar (E01, E02). | Aplica: no secretos de servicio en JS; se rechaza enviar el Bearer a HTTP remoto o destinos no confiables. Persistencia localStorage sigue siendo riesgo ante XSS (E03, E06). | Aplica: Qdrant requiere clave; no se imprimen secretos. Provisionamiento y uso de claves por el pipeline estan bloqueados a inspeccion (E04, E07). |
| A03 Injection | Aplica: consultas revisadas usan parametros; reporting solo construye columnas/operadores de una lista fija. No se declaran seguras todas las consultas no inspeccionadas (E05, E08). | Aplica: SEC-07; 46 sinks HTML protegidos con DOMPurify y SRI; reporting y respuesta del asistente usan textContent (E03, E06, E08). | Aplica: riesgo de prompt injection en RAG no certificado por bloqueo de lectura. El asistente ejecutivo revisado selecciona reglas fijas y parametriza consultas, sin SQL generado (E04, E05). |
| A04 Insecure Design | Aplica: telemetria limita a 100 eventos validados; falta desplegar rate limiting global de autenticacion y limites de cuerpo en proxy (E02, E09, E10). | Aplica: formularios del sitio publico validan solo en cliente y no envian datos a un servicio; no asumir esa validacion como control servidor. La UI no concede roles (E11). | Aplica: RAG limita pregunta a 2000 caracteres y dos ejecuciones concurrentes por proceso. No equivale a cuota global, timeout del proveedor ni presupuesto; siguen pendientes (E04, E10). |
| A05 Security Misconfiguration | Aplica: SEC-06 y SEC-09; CORS acotado, cabeceras seguras, API de servicio en loopback y politica SSH/firewall preparada. Host real pendiente (E02, E07, E10). | Aplica: CDN fijado con SRI; no se inventa CSP/HSTS de un hosting no inspeccionado. Configuracion Next sin rewrites o proxy personalizados en el archivo revisado (E03, E12). | Aplica: no asumir aislamiento por estar dentro de API; unidad no-root sin capacidades, codigo solo lectura y concurrencia limitada. Aplicacion real de sandbox/egress pendiente (E04, E10). |
| A06 Vulnerable and Outdated Components | Aplica: FastAPI/Starlette/dotenv/pytest/certifi actualizados y JOSE sustituido por PyJWT. Grafo exportado del lockfile API y resolucion ML sin avisos conocidos en el escaneo realizado (E01, E12). | Aplica: SEC-08; Next 16.2.10 -> 16.4.3. Grafo de produccion sin avisos; quedan 16 moderados de desarrollo. DOMPurify 3.4.17 fijado (E03, E12). | Aplica: comparte dependencias de API y Qdrant. La imagen Qdrant no fue escaneada ni su estado de ejecucion verificado: no se certifica ausencia de CVEs de contenedor (E07, E12). |
| A07 Identification and Authentication Failures | Aplica: SEC-01/02/03/05; sin credenciales demo, sin fallback tras Bearer invalido, estado activo comprobado. Coexisten los flujos JWT/TinyDB y HMAC/SQLite; unificacion y revocacion general tras cambio de password quedan pendientes (E01, E02). | Aplica: login Next usa formulario OAuth2; las interfaces ya no suplantan roles con tokens estaticos. localStorage no es una cookie HttpOnly; riesgo residual documentado (E03, E06). | Aplica: 401 anonimo/inactivo y 403 por rol antes de RAG; no se ejecuta el proveedor al denegar. WebSocket deja de autenticar con tokens en query string (E02, E04). |
| A08 Software and Data Integrity Failures | Aplica: lockfiles conservados; telemetria ahora valida cada objeto y allowlist antes de persistir. Modelo joblib requiere procedencia confiable; no hay firma de artefactos ni CI certificada en esta revision (E09, E12). | Aplica: SRI verificado contra el artefacto servido por CDN; datos externos sanitizados antes de HTML y respuestas RAG presentadas como texto, no ejecutadas (E03, E06). | Aplica: documentos recuperados y salida del modelo son entradas no confiables. No se certifican controles internos de procedencia o instrucciones del pipeline bloqueado (E04). |
| A09 Security Logging and Monitoring Failures | Aplica: 401/403 generan evento estructurado sin cabeceras, cuerpo o query; existe write_audit_log. Retencion, alertas, proteccion y supervision central real pendientes (E02, E05). | Aplica: reporting muestra errores como texto y no registra credenciales. Telemetria del cliente no sustituye logs de autenticacion del servidor ni una alerta de seguridad (E08, E09). | Aplica: asistente ejecutivo registra accion/fuente; errores RAG solo registran tipo de excepcion, no documentos/secretos. Falta correlacion usuario-herramienta y monitoreo de prompt injection (E04, E05). |
| A10 Server-Side Request Forgery | Aplica: destinos de email/Supabase revisados son fijos o configurados por servidor, no URL libre del request; controlar configuracion y egress. Despliegue/proxy sin certificar (E02, E09, E10). | No aplica como SSRF en los scripts que solo ejecutan fetch del navegador; si aplica fuga de token por apiBase y fue corregida. Next es servidor: se actualizo por avisos SSRF/RCE del framework; revisar cada funcion desplegada (E03, E06, E12). | Aplica: pipeline RAG puede efectuar conexiones a proveedores; no se pudo inspeccionar allowlist, redirects ni acceso a metadata. Bloqueo de sign-off, no ausencia de vulnerabilidad (E04, E10). |

### Localizadores de evidencia

- E01: `services/brasaland-api/src/brasaland_api/auth.py:34` (secretos), `:215`
  (identidad/estado), `:520` (revocacion demo/bootstrap), `:706` (tokens
  provisionados), `:715` (roles y ausencia de degradacion). Evidencia ejecutable:
  `scripts/security_access_check.py`.
- E02: `services/brasaland-api/src/main.py:69` (CORS), `:87` (cabeceras/log de
  denegaciones), `:823` (HMAC), `:988` (`GET /telemetry/report`), `:1065`
  (firma de sesion), `:1150` (token de ingestion), `:2534` (WebSocket).
- E03: `uis/security.js` (`authHeaders`, `trustedApi`, `sanitizeHTML`),
  `uis/executive-dashboard/app.js` (`renderHrRequests`, fetch helpers),
  `uis/marketing-loyalty-app/app.js` (`renderRecommendations`) y sus HTML.
  Evidencia ejecutable: `scripts/security_browser_check.cjs`.
- E04: `services/brasaland-api/src/brasaland_api/knowledge.py:15` (dependencia
  de roles), `:41` (concurrencia/ejecucion), `KnowledgeQuery` (limite de entrada);
  `POST /knowledge/query`. El import de `data.pipelines.rag` confirma la
  dependencia, no el comportamiento interno del archivo bloqueado.
- E05: `services/brasaland-api/src/main.py:5624` (`GET /api/v1/executive/ask`),
  `:1184` (`write_audit_log`). Las consultas revisadas de ventas usan parametros
  y la respuesta incluye `sources`.
- E06: `uis/knowledge-assistant/index.html:249` (`POST /knowledge/query`, salida
  por `textContent`); `uis/talent-pipeline-tracker/services/authApi.ts:62`
  (login por formulario); `services/auth.ts:3` en el mismo frontend (localStorage).
- E07: `docker-compose.yml:2` (Qdrant: REST loopback, sin gRPC publicado,
  clave requerida, capacidades retiradas y no-new-privileges).
- E08: `services/reporting/api.py:49` (`GET /api/v1/reporting/kpis`, parametros
  y allowlist); `uis/backoffice/reporting/app.mjs:26` (`textContent`) y
  `loadReport` (validacion de destino antes de leer/enviar token).
- E09: `services/brasaland-api/src/brasaland_api/telemetry.py:104` (tipo y
  limite de lote), `:139` (`POST /telemetry/events`), `TelemetryEvent`
  (esquema, allowlist, tipos y fechas), `store_telemetry` (Supabase configurado
  por servidor). Los eventos del navegador no son identidad autenticada.
- E10: `infra/security/00-brasaland-ssh.conf`, `host-firewall.nft`,
  `brasaland-api.service`, `brasaland-firewall.service` y `README.es.md` en el
  mismo directorio. Son plantillas y procedimiento; no estado del servidor.
- E11: `uis/public-website/formulario.js:3` (validacion local y reset de
  formulario; no peticion a backend en el codigo revisado).
- E12: `services/brasaland-api/uv.lock`, su `pyproject.toml` y `requirements.txt`;
  `uis/talent-pipeline-tracker/package-lock.json`, `package.json` y
  `next.config.ts:3`; `pyproject.toml` raiz; `examples/sales-forecasting/forecast.py:29`
  y `:217`; `examples/sales-forecasting/README.es.md:150` (riesgo joblib).

## Criterios de cierre

- Evidencia del servidor real: usuario dedicado, `PermitRootLogin no` efectivo,
  acceso por clave comprobado antes de recargar SSH y sesion de respaldo abierta.
- Permisos explicitos y propietarios diferenciados para codigo, logs y secretos;
  el proceso de aplicacion no debe poder modificar codigo o leer secretos ajenos.
- Reglas de firewall verificadas para IPv4/IPv6, con solo los puertos necesarios;
  comprobar tambien publicaciones Docker, que pueden eludir reglas de UFW.
  Definir primero los puertos reales de SSH, proxy y servicios internos.
- Las 30 celdas OWASP completas, con evidencia y estado por componente.
- Cada hallazgo critico con escenario anterior, correccion y comando/evidencia
  posterior reproducible. No publicar secretos ni datos reales en la evidencia.
- Informe de dependencias y limitaciones de las comprobaciones realizadas.
- Commit y push de la entrega; PR al fork correcto con enlaces a por lo menos
  dos correcciones criticas reales, si se identifican. No inventar hallazgos
  para cumplir una cuota; justificarlo si se identifican menos de dos.
- Merge solo despues de aprobacion del PR. No desplegar antes del sign-off.

## Hallazgos de control de acceso (revision de codigo)

La tabla conserva la evidencia ANTERIOR del commit de referencia. La severidad
supone un despliegue con defaults; la exposicion real sigue sin comprobarse.
Los estados de correccion y evidencia posterior estan en la seccion siguiente.

| ID | Severidad | Componente / OWASP | Evidencia previa | Impacto y cierre requerido |
| --- | --- | --- | --- | --- |
| SEC-01 | Critica | Backend / A01, A07 | `services/brasaland-api/src/brasaland_api/auth.py:680` define tokens legacy publicos; `require_roles`, desde la linea 697, acepta `X-API-Role: admin` con `X-API-Token: brasaland-admin-token`. | Acceso administrativo sin identidad personal con configuracion por defecto. Eliminar credenciales conocidas; sin token provisionado debe rechazar. Un Bearer invalido no debe poder degradarse a otro mecanismo. |
| SEC-02 | Critica | Backend / A02, A07 | `services/brasaland-api/src/brasaland_api/auth.py:32` usa secreto JWT publico; `src/main.py:801` contiene otro secreto por defecto. | Firmas falsificables si se despliega sin secreto propio; verificar ambos emisores/validadores. Exigir secreto fuerte provisionado y rotar sesiones, no limitarse a cambiar el literal. |
| SEC-03 | Critica | Backend / A05, A07 | `services/brasaland-api/src/brasaland_api/auth.py:498-519` crea `admin@brasaland.com` con password `brasaland-admin` al vaciarse la tabla; `src/main.py:58` lo invoca durante el arranque. | Toma administrativa en una instalacion nueva. Deshabilitar seed por defecto y definir provisionamiento seguro. Revisar instalaciones existentes: quitar el seed no revoca cuentas ya creadas. |
| SEC-04 | Alta | Sistema agentico / A01, A04 | `services/brasaland-api/src/brasaland_api/knowledge.py:33-36` expone `POST /knowledge/query` sin dependencia de autenticacion; llama directamente a `query`. `tests/test_knowledge.py:10-16` espera HTTP 200 sin credenciales. | Acceso anonimo a conocimiento interno y posible consumo de recursos del proveedor. Autorizar antes de ejecutar el pipeline; verificar 401 anonimo, 403 para rol no permitido y ausencia de llamadas al pipeline en ambos casos. |
| SEC-05 | Alta | Backend / A01, A07 | `services/brasaland-api/src/brasaland_api/auth.py:203-227` recupera el usuario sin comprobar `is_active`; `require_roles` tampoco lo comprueba. | Una cuenta desactivada conserva acceso con token vigente. Rechazar usuarios inactivos tanto en OAuth2 como en el validador de roles. |
| SEC-06 | Media | Backend / A05 | `services/brasaland-api/src/main.py:68-75` configura origen `*`, credenciales y metodos/cabeceras abiertos. | Revisar origenes autorizados y comportamiento de preflight; CORS no sustituye autenticacion. No se afirma por esto solo una explotacion con cookies. |

### Verificacion intentada

Se intento una sonda con TinyDB temporal y un pipeline RAG simulado para no leer
datos reales ni llamar al proveedor. Se utilizo
`services/brasaland-api/.venv312/bin/python` y fallo antes de importar la API:

```text
ModuleNotFoundError: No module named 'fastapi'
```

Este fue un intento inicial fallido, no evidencia dinamica de explotacion.
Posteriormente se preparo el entorno Python 3.12 y se ejecuto la reproduccion
correctamente antes de editar el codigo. Sus resultados y las comprobaciones
posteriores se registran a continuacion. Se adaptaron pruebas existentes;
los dos scripts de evidencia usan datos temporales, no servicios reales.

## Correcciones y evidencia posterior

| ID | Estado local | Correccion / comprobacion |
| --- | --- | --- |
| SEC-01 Critica | Corregida | Sin tokens legacy por defecto; solo provisionados con al menos 32 bytes. Token publico -> 401. Bearer invalido mas servicio valido -> 401, sin degradacion. Integracion provisionada valida -> acceso permitido. |
| SEC-02 Critica | Corregida | Secretos JWT y HMAC obligatorios y distintos defaults eliminados. Firma con HMAC conocido -> 401; secretos conocidos/ausentes rechazados. PyJWT exige expiracion y algoritmo HS256. Rotar secretos en cada despliegue sigue siendo accion del operador. |
| SEC-03 Critica | Corregida | Arranque ya no crea cuentas demo; cuenta demo existente con password conocido se desactiva. Bootstrap admin solo explicito y en base vacia. Evidencia: cero cuentas por defecto y administrador demo desactivado. |
| SEC-04 Alta | Corregida en frontera API | RAG anonimo -> 401; rol no permitido -> 403 sin llamadas al pipeline; admin valido -> 200 con proveedor simulado. No certifica el interior del RAG. |
| SEC-05 Alta | Corregida | Cuenta inactiva -> 401 tambien con token vigente; prueba contra ruta RAG y validador central. |
| SEC-06 Media | Corregida en API | Preflight origen no confiable -> 400; puertos locales 3000/4173 autorizados -> 200. Sin wildcard de origen/credenciales. Scripts de API/dashboard en loopback por defecto; cabeceras nosniff, DENY, no-referrer y no-store comprobadas. |
| SEC-07 Alta | Corregida en clientes revisados | XSS almacenado potencial en `renderHrRequests` y otros HTML dinamicos. DOMPurify protege 39 sinks del dashboard y 7 de marketing; payload onerror/script filtrado en renders reales de laboratorio; SRI coincide con CDN. Backoffice y asistente usan texto. |
| SEC-08 Critica segun npm | Dependencia corregida | Next 16.2.10 contenia avisos de RCE/SSRF; no se ejecutaron exploits. Actualizado a 16.4.3 con lockfile; build y lint pasan; escaneo de produccion sin avisos. Criticidad del paquete no demuestra explotabilidad de todos los avisos en esta app. |
| SEC-09 Alta, condicionada a red | Configuracion corregida, despliegue pendiente | Compose antes publicaba 6333/6334 en todas las interfaces sin clave configurada. Ahora solo 127.0.0.1:6333, clave requerida y sin gRPC publicado. Configuracion estructurada comprobada; falta probar contenedor y consumidor RAG reales. |
| SEC-10 Alta | Corregida en API | Informe tecnico anonimo -> 401. Cada evento se valida antes de persistir, maximo 100 por lote; campo privado inesperado -> 422 sin reflejar contenido. Ingestion publica sigue necesitando limites en proxy. |

### SEC-01: tokens de rol

Antes: la sonda original acepto `brasaland-admin-token` como administrador.
Despues: `scripts/security_access_check.py` devuelve `public_admin_token: 401`
y `invalid_bearer_cannot_fallback: 401`, conservando el acceso de la integracion
provisionada. Las credenciales de servicio no se insertan en el navegador.

### SEC-02: secretos de firma

Antes: la sonda original confirmo el uso del secreto JWT publico y el codigo
mostraba otro secreto HMAC publico. Despues: la misma sonda devuelve
`public_hmac_secret_forgery: 401` y
`known_and_missing_signing_secrets: rejected`. Ambos mecanismos requieren
provisionamiento. La rotacion en el servidor objetivo sigue siendo obligatoria.

### SEC-03: cuentas demo

Antes: el seed permitia login administrativo con password conocido en una base
temporal nueva. Despues: la sonda devuelve `default_accounts_created: 0` y
`existing_demo_admin: disabled`; un administrador autorizado sigue accediendo.

### Resultados anteriores observados

Sonda ejecutada sobre el codigo original con TinyDB temporal y RAG simulado:

```json
{
  "legacy_public_admin_accepted": true,
  "anonymous_knowledge_status": 200,
  "default_seed_admin_login": true,
  "public_jwt_default_in_use": true
}
```

Escaneos previos: entorno API instalado desde requirements, 19 entradas de
vulnerabilidades en 5 paquetes; algunas entradas son aliases/duplicados, NO
19 vulnerabilidades unicas. npm completo: 1 paquete critico, 8 altos y 16
moderados. No confundir cantidad de paquetes con escenarios explotables.

Avisos criticos Next incluidos por npm: GHSA-2464-fhr4-w9xw (SVG image
optimization), GHSA-673q-mjm6-r5xr (use cache/typed arrays) y otros avisos RCE
condicionados a funciones/plataforma. Referencias:
<https://github.com/advisories/GHSA-2464-fhr4-w9xw> y
<https://github.com/advisories/GHSA-673q-mjm6-r5xr>.

### Reproduccion sin datos reales

Usar Python 3.12. El Python 3.14 del contenedor fallo con el pydantic-core
original: `configured Python interpreter version (3.14) is newer than PyO3's
maximum supported version (3.13)`. No se forzo una compilacion incompatible.

```bash
python3.12 -m venv /tmp/brasaland-security-venv
python -m pip --python /tmp/brasaland-security-venv/bin/python install -r services/brasaland-api/requirements.txt uv pip-audit
/tmp/brasaland-security-venv/bin/python scripts/security_access_check.py
DO_NOT_TRACK=1 /tmp/brasaland-security-venv/bin/python -m pytest services/brasaland-api/tests/test_auth_jwt.py services/brasaland-api/tests/test_knowledge.py -q
```

Si el host no incluye ensurepip, el administrador debe proveer soporte venv;
en esta sesion se completo el entorno 3.12 mediante el `pip --python` existente.
No instalar dependencias globalmente ni elevar permisos para ejecutar pruebas.

La sonda comprueba firma HMAC antigua rechazada, token admin publico rechazado,
ausencia de fallback tras Bearer invalido, servicio provisionado permitido,
RAG anonimo/inactivo rechazado, rol prohibido, admin permitido, ausencia de
seed, revocacion demo y rechazo de secretos publicos/ausentes. No imprime claves.
Tambien comprueba WebSocket con JWT autorizado (`snapshot`) y rechazo de token
en URL (`4403`). El servidor HTTP temporal del dashboard sirvio el helper
compartido por su enlace simbolico y devolvio 404 al intentar acceder a un
archivo del repositorio fuera de su webroot. No se amplio el webroot al monorepo.

Los scripts locales de arranque pasan `bash -n` y usan `127.0.0.1` por defecto.
Si se necesita otro bind, debe justificarse explicitamente y protegerse con
las politicas del servidor; no cambiarlo a `0.0.0.0` solo por conveniencia.

Pruebas existentes ejecutadas y aprobadas: 17 de JWT/RAG y 24 de
`test_token.py`, `test_change_password.py`, `test_users_profiles.py` (41 en total).
Las 7 pruebas existentes de `uis/backoffice/reporting/client.test.mjs` pasan.
No se ejecuto la suite completa. El archivo previo `test_telemetry.py` tiene
referencias a pytest/httpx/Mock sin import y expectativas contradictorias;
no se modifico ni se presenta como aprobado. Telemetria se comprobo mediante
sonda focalizada con SQLite temporal: lote valido 200, campo privado 422,
lote de 101 elementos 422 y reporte anonimo 401.

```bash
npm install --prefix /tmp/brasaland-security-js --no-audit --no-fund acorn@8.19.0 jsdom@30.1.3 dompurify@3.4.17
NODE_PATH=/tmp/brasaland-security-js/node_modules node scripts/security_browser_check.cjs
node --test uis/backoffice/reporting/client.test.mjs
```

Resultado del navegador: 39 + 7 sinks protegidos, payloads filtrados, SRI
coincidente, Bearer de sesion conservado y destinos no confiables rechazados.
Se utilizo JSDOM, no un navegador real ni escaneo DAST. No hay screenshots que
se presenten como evidencia de pruebas no realizadas.

```bash
/tmp/brasaland-security-venv/bin/uv export --project services/brasaland-api --locked --no-emit-project --format requirements-txt --output-file /tmp/brasaland-locked-requirements.txt
/tmp/brasaland-security-venv/bin/pip-audit -r /tmp/brasaland-locked-requirements.txt --no-deps --disable-pip
/tmp/brasaland-security-venv/bin/uv pip compile pyproject.toml --python-version 3.12 --output-file /tmp/brasaland-forecast-requirements.txt
/tmp/brasaland-security-venv/bin/pip-audit -r /tmp/brasaland-forecast-requirements.txt --no-deps --disable-pip
npm ci --prefix uis/talent-pipeline-tracker --ignore-scripts
NEXT_TELEMETRY_DISABLED=1 npm run build --prefix uis/talent-pipeline-tracker
npm run lint --prefix uis/talent-pipeline-tracker
npm audit --prefix uis/talent-pipeline-tracker --omit=dev
npm audit --prefix uis/talent-pipeline-tracker
```

Escaneos posteriores: API sin avisos conocidos en el grafo exportado; modelo
offline sin avisos en la resolucion realizada; Next produccion cero avisos y
grafo completo 16 moderados de desarrollo, cero altos/criticos. Los avisos
moderados restantes afectan minimatch y herramientas ESLint; npm propone una
degradacion incompatible con `--force`, que no se aplico. No son riesgo cero.
La resolucion ML usa rangos: el resultado es una fotografia, no un lockfile ML.

Build de produccion Next 16.4.3 y lint aprobados. Tras actualizar transitivas
compatibles se repitio lint; no se entro en un bucle de builds. Pylance no
detecto errores de sintaxis en `auth.py` ni `main.py`.

### Servidor: comprobaciones de plantillas

La politica SSH fue evaluada con una clave de host temporal de laboratorio,
no con claves del servidor. Resultado: `permitrootlogin no`,
`passwordauthentication no`, `kbdinteractiveauthentication no`,
`allowgroups brasaland-ops`, `authenticationmethods publickey`.

`nft --check` quedo bloqueado por `Operation not permitted` al inicializar
netlink. `systemd-analyze verify` encontro la ruta de despliegue inexistente
en el contenedor. No se declaran ambas comprobaciones aprobadas. Compose
se evaluo como JSON con una clave efimera: una sola publicacion REST en
loopback, sin gRPC, clave obligatoria. No se arranco Qdrant ni se simulo
que una plantilla fuese un firewall activo.

## Riesgos y bloqueos para sign-off

1. Falta servidor real: identidad no-root, permisos efectivos, SSH, firewall
  IPv4/IPv6/cloud, puertos externos, TLS/proxy y prueba tras reinicio.
2. Lectura interna RAG bloqueada: faltan prompt injection, procedencia de
  documentos, permisos reales de herramientas, egress/SSRF, manejo de API keys
  y compatibilidad del consumidor con Qdrant autenticado.
3. Falta desplegar limites de tasa/cuerpo/timeout y cuotas globales; el semaforo
  del asistente solo limita concurrencia dentro de cada proceso.
4. No se auditaron CVEs de la imagen Qdrant, dependencias instaladas en un
  servidor ni CI/artefactos firmados. Persisten avisos moderados de desarrollo.
5. Se mantienen dos mecanismos de identidad historicos (JWT y HMAC); hace falta
  unificacion y politica completa de revocacion/recuperacion. Las pruebas aqui
  no certifican el flujo completo de todas las interfaces en produccion.
6. GitHub devuelve 403 al crear el fork personal; no se puede publicar hacia un
  fork inexistente. No hacer PR al repositorio de la academia por sustitucion.
  No hacer merge hasta aprobar el PR y cerrar los bloqueos operativos.

## Entrega

El trabajo se mantiene en `feature/owasp-top10-audit`. La descripcion preparada
esta en `docs/security/pr-description.es.md`; enlaza evidencia de SEC-01,
SEC-02 y SEC-03, ademas de la actualizacion de Next. Los valores de estado
anteriores se refieren a esta revision local; el resultado del commit/push/PR
se comunica por separado y nunca se infiere de que exista la rama.

## Acceso al servidor objetivo

No se ha identificado un servidor objetivo ni su metodo de acceso en esta
sesion. No se conocen su IP, usuario, puertos imprescindibles ni reglas de red.
Por tanto, los requisitos de endurecimiento del servidor siguen sin verificar.
No compartir passwords, claves privadas ni tokens en el informe o en el chat.