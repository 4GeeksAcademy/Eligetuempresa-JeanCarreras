# Endurece accesos y documenta auditoria OWASP Top 10

PR en borrador: no desplegar ni hacer merge hasta cerrar los bloqueos de
servidor real y revision interna RAG.

## Alcance

- API central, frontends, asistente RAG y asistente ejecutivo evaluados por
  separado contra las diez categorias OWASP Top 10 2021.
- Retirada de credenciales publicas, revocacion de cuentas demo, comprobacion
  de cuentas activas y cierre de acceso anonimo a RAG/reportes internos.
- CORS y Qdrant acotados, validacion de telemetria y HTML dinamico sanitizado.
- Actualizacion de dependencias API y Next.js; politicas SSH, firewall y
  servicio no-root con runbook de aplicacion y verificacion.

## Evidencia de correcciones criticas

1. [SEC-01: tokens de rol](owasp-top10-audit.es.md#sec-01-tokens-de-rol): el token publico admin ya devuelve 401; no hay degradacion desde un
   Bearer invalido. Comando:
   `python scripts/security_access_check.py`.
2. [SEC-02: secretos de firma](owasp-top10-audit.es.md#sec-02-secretos-de-firma): el token firmado con el secreto HMAC publico ya devuelve 401 y los
   secretos publicos/ausentes se rechazan. Mismo comando reproducible.
3. [SEC-03: cuentas demo](owasp-top10-audit.es.md#sec-03-cuentas-demo): no se crean cuentas demo y un administrador demo existente queda
   inactivo. Mismo comando, almacenamiento temporal y sin proveedor real.
4. SEC-08: Next 16.2.10 -> 16.4.3; build/lint aprobados y
   `npm audit --omit=dev` sin avisos conocidos en el frontend de talento.

Codigo de evidencia: [scripts/security_access_check.py](../../scripts/security_access_check.py).
Informe con antes/despues y comandos: [owasp-top10-audit.es.md](owasp-top10-audit.es.md).
Evidencia XSS: [scripts/security_browser_check.cjs](../../scripts/security_browser_check.cjs).
Runbook: [infra/security/README.es.md](../../infra/security/README.es.md).

## Verificacion

41 pruebas Python existentes y 7 del cliente reporting aprobadas; comandos de
accesos y navegador aprobados; build Next, lint y escaneos focalizados ejecutados.
No se ejecuto la suite completa. Persisten 16 avisos moderados de desarrollo.

## Bloqueos

- Servidor objetivo no identificado: no hay evidencia de politicas efectivas,
  usuario operativo, permisos, firewall real ni TLS/proxy.
- Pipeline RAG bloqueado a lectura: no certificar prompt injection, egress,
  herramientas internas, procedencia de documentos ni API keys.
- GitHub impide crear el fork personal: HTTP 403, recurso no accesible para
  la integracion. Publicacion del PR pendiente de permisos/destino correcto.
- No se declara aprobacion ni se realiza merge automatico.