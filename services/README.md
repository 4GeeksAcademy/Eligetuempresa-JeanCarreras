# `services` folder

This folder contains **all the backend services** (APIs and background workers) related to the company for the cross-functional AI Engineering project.

Each subfolder inside `services/` must correspond to **one specific service** (for example: `admin-api`, `data-processor-worker`) and include its own technical and functional documentation.

- **Main purpose**: to centralize all the backend logic, APIs, and queue consumers that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the services you add, their objective, the technology used, and how to run them.

## Current services

### `brasaland-api`

MVP central API for Brasaland.

- Objective: expose baseline health, stores, and sales summary endpoints to enable dashboards and automations.
- Stack: FastAPI + Uvicorn.
- Documentation (EN): `services/brasaland-api/README.md`.
- Documentation (ES): `services/brasaland-api/README.es.md`.

> _Spanish version: [README.es.md](./README.es.md)._
