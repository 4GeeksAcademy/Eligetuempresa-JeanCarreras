# Endurecimiento del servidor Ubuntu

Estado: politicas preparadas, NO aplicadas ni verificadas en un servidor real.
No ejecutar estas instrucciones en el Codespace como sustituto del servidor.
Se requiere acceso autorizado a la consola del host y un inventario del despliegue.

## Precondiciones y prevencion de bloqueo

1. Registrar `id`, `ss -lntup`, politica SSH efectiva y reglas de firewall
   actuales. Revisar tambien reglas del proveedor, IPv6 y `docker ps`.
2. Confirmar si SSH usa el puerto 22. Si usa otro, adaptar tanto SSH como
   firewall y las reglas del proveedor antes de aplicar nada.
3. Mantener una consola de recuperacion fuera de SSH y la sesion actual abierta.
   Copiar las configuraciones actuales a una ubicacion protegida de respaldo.
4. Sustituir `192.0.2.10/32` y `2001:db8::10/128` del firewall por las redes
   administrativas reales. Son direcciones documentales, NO direcciones validas
   para este despliegue. Si no se usa IPv6 administrativo, quitar solo esa regla;
   el resto de IPv6 queda cerrado salvo ICMPv6 y HTTPS.
5. Revisar conflictos con otras reglas. La politica solo modifica su propia
   tabla y no abre puertos cerrados por otras tablas o por el proveedor.

Los comandos siguientes son para un administrador autorizado en el servidor;
no los ejecuta automaticamente el asistente. Instalar previamente OpenSSH,
nftables, systemd y Python 3.12 con soporte venv mediante el gestor del host.

## Usuarios y permisos

Desde la consola administrativa, tras comprobar que los usuarios no existen:

```bash
useradd --create-home --shell /bin/bash --user-group brasaland-ops
useradd --system --home-dir /var/lib/brasaland --shell /usr/sbin/nologin --user-group brasaland
install -d -o brasaland-ops -g brasaland-ops -m 0700 /home/brasaland-ops/.ssh
install -o brasaland-ops -g brasaland-ops -m 0600 /RUTA/CLAVE_PUBLICA_APROBADA /home/brasaland-ops/.ssh/authorized_keys
install -d -o root -g brasaland -m 0750 /srv/brasaland
install -d -o brasaland -g brasaland -m 0750 /var/lib/brasaland /var/log/brasaland
install -d -o root -g root -m 0700 /etc/brasaland
```

No copiar una clave privada al servidor. El usuario operativo no debe pertenecer
a `root`, `sudo` o `docker` por defecto. El usuario de servicio no tiene shell.
Las tareas administrativas siguen requiriendo un canal aprobado de elevacion;
no conceder sudo irrestricto al usuario operativo para resolverlo.

Desplegar una release revisada en `/srv/brasaland/current`, propiedad
`root:brasaland`: directorios 0750, archivos de codigo/configuracion no sensible
0640 y ejecutables 0750. Preservar el bit ejecutable necesario del venv, no
aplicar `chmod -R 640` al arbol completo. El servicio no puede modificar codigo.
Solo `/var/lib/brasaland` y `/var/log/brasaland` son escribibles para el servicio.
Migrar los datos existentes con el servicio detenido y un backup verificado;
no arrancar sobre una base vacia si ya existe informacion de produccion.

## Secretos y arranque

Crear `/etc/brasaland/api.env` como `root:root`, modo 0600. Systemd lee el archivo
y entrega las variables al proceso sin hacerlo legible para el usuario operativo.
No guardar un `.env` con secretos dentro del checkout ni incluirlo en evidencias.

Variables obligatorias:

- `BRASALAND_JWT_SECRET` y `BRASALAND_AUTH_SECRET`: valores distintos, aleatorios,
  de al menos 32 bytes. Generarlos en el gestor de secretos o en la consola
  privada del operador. La API rechaza valores ausentes y defaults conocidos.
- `BRASALAND_CORS_ORIGINS`: origenes HTTPS exactos del frontend, separados por
  comas; no incluir `*`. CORS no es un control de autorizacion.
- `QDRANT_API_KEY`: secreto aleatorio compartido solo con los clientes RAG
  autorizados. Compose exige provisionarlo para arrancar Qdrant.
- Credenciales de proveedores necesarias, solo para el servicio correspondiente.

Opcionales: tokens `BRASALAND_<ROL>_TOKEN` para integraciones de servicio
concretas; ninguno se habilita por defecto. No ponerlos en JavaScript del navegador.
Para el primer administrador de una base vacia, provisionar temporalmente
`BRASALAND_BOOTSTRAP_ADMIN_EMAIL` y `BRASALAND_BOOTSTRAP_ADMIN_PASSWORD`
(password unico de 16 caracteres o mas); retirar ambas tras el bootstrap.
En una base existente usar un procedimiento de recuperacion aprobado, no borrarla.

Rotar todos los secretos antes de desplegar; los antiguos tokens firmados con
defaults no deben seguir funcionando. El arranque desactiva cuentas demo que
conservan su password conocido; revisar tambien las cuentas ya existentes.

Instalar `brasaland-api.service` y `brasaland-firewall.service` en
`/etc/systemd/system/`, modo 0644. Instalar el firewall adaptado en
`/etc/brasaland/host-firewall.nft`, modo 0600. No habilitar todavia el firewall.
La unidad API espera un venv instalado como parte de una release de confianza.

## SSH y firewall

Primero probar en una SEGUNDA terminal `ssh brasaland-ops@HOST` con la clave
aprobada. No deshabilitar root hasta que ese acceso funcione y la consola de
recuperacion este disponible.

Instalar `00-brasaland-ssh.conf` en `/etc/ssh/sshd_config.d/`, modo 0644.
Comprobar que el archivo principal incluye los drop-ins, revisar orden y `Match`.
No basta con que el archivo contenga `PermitRootLogin no`:

```bash
sshd -t
sshd -T -C user=root,host=HOST_REAL,addr=IP_ADMIN_REAL
sshd -T -C user=brasaland-ops,host=HOST_REAL,addr=IP_ADMIN_REAL
nft --check --file /etc/brasaland/host-firewall.nft
systemd-analyze verify /etc/systemd/system/brasaland-api.service /etc/systemd/system/brasaland-firewall.service
```

La salida efectiva debe mostrar `permitrootlogin no`, `passwordauthentication no`,
`kbdinteractiveauthentication no`, `authenticationmethods publickey` y el grupo
operativo permitido. Tras comprobarlo, el administrador puede recargar SSH y
repetir el acceso no-root antes de cerrar ninguna sesion.

Activar la unidad de firewall solo con confirmacion del administrador y la
configuracion adaptada. No usar `flush ruleset`: borraria reglas ajenas.
Verificar despues `nft list ruleset`, `ss -lntup` y persistencia tras reinicio.

Puertos de entrada previstos: 443 publico y SSH solo desde redes administrativas.
El puerto 80 permanece cerrado; si se necesita ACME HTTP-01, justificarlo y
habilitarlo de forma controlada, o usar DNS-01. API 8000 y Qdrant 6333 son internos.
No publicar gRPC 6334. Revisar reglas de forwarding y Docker, ya que el trafico
a puertos publicados de contenedores puede no atravesar el hook `input`.
Aplicar la misma lista de puertos en el firewall del proveedor/cloud.

## Proxy y limites

Proveer un proxy HTTPS con certificado valido, TLS 1.2/1.3, cabeceras CSP y HSTS
solo tras comprobar HTTPS en todos los dominios. La API escucha en loopback.
El proxy debe limitar cuerpo a 16 KiB en autenticacion/RAG, tasa de login y
consultas al agente, tiempo de respuesta y conexiones concurrentes. Para cargas
legitimas mas grandes de ingestion, definir un limite separado y documentarlo.
El firewall aqui definido no limita salidas: aplicar allowlist de egress para
proveedores cuando se termine de inventariar el pipeline RAG.

Los clientes estaticos cargan DOMPurify fijado con SRI desde jsDelivr. Si la
politica impide CDN, servir el mismo artefacto revisado localmente y conservar
la comprobacion de integridad. No relajar CSP a `*` ni habilitar `unsafe-eval`.
Revisar los scripts inline existentes antes de fijar CSP con hashes/nonces.

## Evidencia requerida para sign-off

- Salidas de identidad del usuario operativo y del proceso API, sin secretos.
- Politica SSH efectiva por usuario/origen y prueba fallida de login root.
- `stat` de codigo, logs, datos y configuracion con propietario, grupo y modo.
- Firewall efectivo IPv4/IPv6, reglas cloud y escaneo externo autorizado: solo
  HTTPS publico; SSH permitido desde la red administrativa y cerrado desde otra.
- Acceso externo fallido a 8000, 6333 y 6334; prueba local de Qdrant sin clave
  rechazada y con clave aceptada, sin exponerla en historial, capturas o logs.
- Servicio no-root y acceso permitido/denegado a las herramientas del agente.
- Pruebas posteriores al reinicio y procedimiento de recuperacion revisado.

No hay sign-off hasta adjuntar estos resultados del host real. Las plantillas
y sus comprobaciones locales no sustituyen esa evidencia.