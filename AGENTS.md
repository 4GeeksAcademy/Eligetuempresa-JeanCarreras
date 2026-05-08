# AGENTS - Brasaland Digital

## Proposito

Este repositorio implementa capacidades de AI Engineering para Brasaland.
Todo agente o automatizacion debe priorizar impacto operativo medible y consistencia multipais.

## Contexto obligatorio

Antes de diseñar o modificar agentes, revisar:

- CONTEXT.md
- docs/BRASALAND-ROADMAP.es.md
- docs/BRASALAND-ARCHITECTURE.es.md

## Objetivos de agentes (prioridad)

1. Operaciones: visibilidad de ventas y alertas de inactividad por local.
2. Formacion: acceso rapido a recetas y procedimientos estandar.
3. Ejecutiva: consultas en lenguaje natural sobre metricas de cadena.
4. RRHH: soporte a onboarding y consultas recurrentes internas.

## Principios de diseño

- Respuestas accionables para usuarios no tecnicos.
- Trazabilidad: toda recomendacion debe incluir datos fuente.
- Seguridad por defecto: no exponer datos sensibles sin permiso.
- Robustez multipais: soportar COP/USD y diferencias horarias.

## Memoria y conocimiento

- Fuentes candidatas: recetas, SOPs, reportes operativos, catalogo de proveedores, KPIs.
- Mantener versionado de documentos de politica y procedimientos.
- Evitar respuestas inventadas cuando falte informacion.

## Guardrails

- Nunca recomendar acciones que incumplan normas laborales o sanitarias.
- Si faltan datos para una decision critica, devolver "informacion insuficiente" y pedir datos puntuales.
- No ejecutar acciones irreversibles sin confirmacion explicita.

## Definicion de listo por agente

- Objetivo y usuario final claramente definidos.
- Prompt system documentado.
- Herramientas declaradas y limitadas por caso de uso.
- Metrica de calidad y plan de evaluacion.
- Guia de despliegue y runbook operativo.
