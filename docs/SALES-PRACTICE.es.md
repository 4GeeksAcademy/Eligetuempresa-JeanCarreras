# Ventas sinteticas de Brasaland para practica

## Alcance y procedencia

Estos datos son inventados con autorizacion del usuario para practicar regresion.
No son ventas reales ni el dataset oficial del curso. No satisfacen el requisito
original de usar el historico provisto y no permiten concluir que sea viable
predecir ventas reales de Brasaland. No deben usarse para decisiones financieras.

El contexto de negocio de referencia es `CONTEXT.md`: restaurantes en Colombia
y Florida, con operacion en COP y USD. Ese documento no especifica un historico
ni una estacionalidad; todos los supuestos numericos siguientes son sinteticos.
No se modifica el contexto corporativo para presentar estos supuestos como hechos.

## Generacion reproducible

Desde la raiz del monorepo:

```sh
python3 scripts/generate_sales_practice.py
```

El generador usa solo la biblioteca estandar de Python y semilla 42. No requiere
instalar dependencias. Rechaza sobrescribir un archivo existente. Para regenerar
sin reemplazar el anterior, usar `--output` con una ruta nueva.

Salida: `examples/sales-forecasting/brasaland_sales_synthetic.csv`.
Contiene 240 filas: 120 meses por cada uno de dos mercados, sin valores nulos.

## Contrato de datos

| Columna | Significado |
| --- | --- |
| `month` | Primer dia del mes, formato ISO YYYY-MM-DD |
| `country` | CO: Colombia; US: Estados Unidos (Florida) |
| `currency` | COP para CO; USD para US |
| `sales` | Ventas mensuales sinteticas del mercado, en su moneda nativa |
| `is_synthetic` | Siempre true; marca de procedencia, no variable predictora |

No sumar COP y USD ni calcular un error monetario agregado entre ambas series.
Evaluar y visualizar cada mercado por separado. No se dispone de tipos de cambio.

## Supuestos inventados

- Periodo completo: enero de 2016 a diciembre de 2025.
- Base mensual antes de estacionalidad y ruido: 900 millones COP y 180 mil USD.
- Crecimiento compuesto anual de 4.5%, aplicado mensualmente.
- Factores estacionales de enero a diciembre: 0.88, 0.90, 0.98, 1.00, 1.05,
  1.02, 1.08, 1.00, 0.94, 1.01, 1.10 y 1.25.
- Ruido multiplicativo normal de media 1 y desviacion 0.06, limitado por debajo
  a 0.1 para garantizar ventas positivas.
- Mismo patron estacional para ambos mercados, sin cierres, pandemia, aperturas,
  inflacion diferenciada ni cambios estructurales. Es una simplificacion didactica.
- Ventas = base del mercado * crecimiento * factor estacional * ruido.

## Division temporal para el siguiente paso

- Entrenamiento: 2016-01-01 a 2023-12-01, 96 meses y 192 filas.
- Prueba: 2024-01-01 a 2025-12-01, 24 meses y 48 filas.
- Clave unica: (`month`, `country`). Una fecha no debe aparecer en ambos conjuntos.
- No usar ventas de prueba para ajustar variables, hiperparametros o intervalos.
- Las variables de tendencia y mes se conocen de antemano; no usar `sales`
  del mismo mes como entrada. Random Forest no extrapola bien tendencias nuevas:
  contrastar su resultado con una referencia estacional y reportar esa limitacion.

La implementacion, instrucciones de ejecucion, metricas y limitaciones estan en
[el README del experimento](../examples/sales-forecasting/README.es.md).
El pipeline entrena un modelo por mercado, genera bandas aproximadas y evalua
los dos anos de prueba. Las pruebas del split estan en `tests/pipelines/`.