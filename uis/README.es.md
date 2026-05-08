# Carpeta `uis`

Esta carpeta contiene **todas las interfaces de usuario** relacionadas con la compañía para el proyecto transversal de AI Engineering (por ejemplo: aplicaciones web, dashboards internos, portales de clientes, apps de Streamlit/Gradio, etc.).

Cada subcarpeta dentro de `uis/` debe corresponder a **una interfaz de usuario concreta** (por ejemplo `website`, `backoffice`) e incluir su propia documentación técnica y funcional.

- **Propósito principal**: centralizar en un único lugar todas las aplicaciones frontend que dan soporte a los casos de uso de la compañía.
- **Recomendación**: documenta en este archivo (o en sub-READMEs) las aplicaciones que vayas añadiendo, su objetivo, tecnología usada y cómo ejecutarlas.

## Interfaces actuales

### `executive-dashboard`

Dashboard ejecutivo MVP para Brasaland.

- Objetivo: mostrar ventas semanales, ticket promedio y comparativo por mercado para direccion.
- Stack: HTML + CSS + JavaScript.
- Documentacion (ES): `uis/executive-dashboard/README.es.md`.
- Documentation (EN): `uis/executive-dashboard/README.md`.
