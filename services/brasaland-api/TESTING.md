# Plan y ejecución de pruebas

Este documento cubre el ticket AUTH-088. Las pruebas llaman directamente a las
funciones de negocio de autenticación; no usan `TestClient` ni comprueban la
serialización HTTP de FastAPI.

## Plan de pruebas

| Endpoint / función | Camino feliz | Caso límite | Modo de fallo |
| --- | --- | --- | --- |
| `POST /auth/register` | Crea el usuario, guarda un hash verificable y devuelve una sesión válida. | Normaliza espacios y mayúsculas del email; acepta una contraseña de exactamente 8 caracteres. | Rechaza email vacío o inválido, contraseña corta y usuario duplicado. |
| `POST /auth/login` | Autentica credenciales válidas y emite una sesión para el usuario correcto. | Busca el email sin distinguir mayúsculas y elimina espacios externos. | Rechaza usuario inexistente, contraseña incorrecta y contraseña vacía. |
| `POST /auth/forgot-password` | Para una cuenta existente crea un token hasheado con expiración y solicita el correo. | Una cuenta inexistente obtiene el mismo mensaje opaco y no crea tokens. | Un email vacío no filtra la existencia de cuentas ni intenta enviar correo. |
| `POST /auth/reset-password` | Un token vigente cambia el hash de contraseña e invalida los tokens pendientes. | El token es de un solo uso. | Rechaza token malformado, expirado y contraseña nueva vacía/corta. |
| `POST /auth/change-password` | Con sesión y contraseña actual válidas cambia el hash e invalida resets pendientes. | La contraseña mínima de 8 caracteres es válida. | Rechaza contraseña actual incorrecta, contraseña nueva vacía/corta y sesión ausente, manipulada o expirada. |
| Token de sesión | Una firma válida y vigente recupera al usuario indicado por `sub`. | Un token cuyo vencimiento coincide con el instante actual ya no es válido. | Rechaza token malformado, firma manipulada, token expirado y usuario inexistente. |

Los datos se aíslan en una base SQLite temporal por prueba. Se inspeccionan los
efectos persistidos (hashes, expiración y consumo de tokens), no detalles del
framework.

## Casos sugeridos con asistencia de IA

La revisión asistida detectó dos casos que la suite anterior no cubría:

- Todos los tokens de recuperación todavía pendientes deben invalidarse después
  de cambiar la contraseña, no solo el token utilizado.
- Un token de sesión con firma correcta debe rechazarse si referencia un usuario
  que ya no existe.

También detectó que la prueba anterior atravesaba `TestClient`; se reemplaza por
pruebas directas para cumplir el requisito de probar decisiones de negocio.

## Ejecutar

Desde `services/brasaland-api`:

```bash
uv sync --dev
uv run pytest
uv run pytest --cov
```

La configuración exige al menos 70% de cobertura sobre la lógica de autenticación
de `src/brasaland_api/auth.py`; `coverage.py` devuelve error si el total baja de
ese umbral.

## Suites incluidas

- `test_register.py`: registro, normalización, contraseña mínima y duplicados.
- `test_login.py`: credenciales válidas, normalización y rechazos.
- `test_token.py`: sesiones SQLite válidas, expiradas, manipuladas y huérfanas.
- `test_forgot_password.py`: respuesta opaca, token hasheado y envío de enlace.
- `test_reset_password.py`: expiración, uso único, cambio e invalidación de tokens.
- `test_change_password.py`: contraseña actual, límites e invalidación de resets.
- `test_auth_jwt.py`: JWT, `/auth/me` y autorización por roles del router modular.
- `test_users_profiles.py`: usuarios y perfiles asociados a autenticación.

## Resultado verificado

Ejecutado el 9 de septiembre de 2026:

```text
61 passed
src/brasaland_api/auth.py: 291 statements, 15 missing, 95% coverage
```

El resultado supera el mínimo requerido de 70%. La suite usa bases SQLite y
TinyDB temporales para no leer ni modificar datos locales o de producción.

## TypeScript

La autenticación actual no contiene utilidades TypeScript: el frontend de auth
usa JavaScript y la lógica sensible reside en Python. Por ello Jest no aplica a
AUTH-088 en este repositorio.