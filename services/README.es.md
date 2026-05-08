# Carpeta `services`

Esta carpeta contiene **todos los servicios backend** (APIs y workers en segundo plano) relacionados con la compañía para el proyecto transversal de AI Engineering.

Cada subcarpeta dentro de `services/` debe corresponder a **un servicio concreto** (por ejemplo `admin-api`, `data-processor-worker`) e incluir su propia documentación técnica y funcional.

- **Propósito principal**: centralizar toda la lógica backend, APIs y consumidores de colas que dan soporte a los casos de uso de la compañía.
- **Recomendación**: documenta en este archivo (o en sub-READMEs) los servicios que vayas añadiendo, su objetivo, tecnología usada y cómo ejecutarlos.

## Servicios actuales

### `brasaland-api`

API central MVP para Brasaland.

- Objetivo: exponer endpoints base de salud, locales y resumen de ventas para habilitar dashboards y automatizaciones.
- Stack: FastAPI + Uvicorn.
- Documentacion (ES): `services/brasaland-api/README.es.md`.
- Documentation (EN): `services/brasaland-api/README.md`.
