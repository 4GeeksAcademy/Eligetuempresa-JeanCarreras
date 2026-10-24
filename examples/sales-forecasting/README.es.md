# Prediccion de ventas de Brasaland: practica sintetica

## Alcance

Experimento didactico completo, no un modelo validado para Finanzas.
El usuario autorizo simular datos porque no estaba disponible el historico oficial.
Esto es una excepcion explicita al enunciado original, no su cumplimiento literal.
Se conserva la procedencia sintetica en el CSV, los resultados y la grafica.

El contexto corporativo es [CONTEXT.md](../../CONTEXT.md). Operamos por separado
Colombia/COP y Florida/USD; no sumamos monedas sin tipos de cambio.
El contrato y los supuestos inventados estan en
[docs/SALES-PRACTICE.es.md](../../docs/SALES-PRACTICE.es.md).

## Reproducir

Desde la raiz del monorepo, con uv instalado:

```sh
uv sync --project examples/sales-forecasting --locked
uv run --project examples/sales-forecasting python examples/sales-forecasting/forecast.py
uv run --project examples/sales-forecasting pytest -c examples/sales-forecasting/pyproject.toml tests/pipelines/test_sales_forecast.py -q
```

Si uv no esta en el PATH, usar `~/.local/bin/uv`. El proyecto tiene un entorno
aislado de la API y un lockfile. No se usa pip. La semilla del generador y del
bosque es 42; `n_jobs=1` limita variaciones por paralelismo. Las versiones exactas
estan en `uv.lock`; pueden existir diferencias numericas entre plataformas.

El CSV ya esta incluido. Para generar una copia independiente:

```sh
python3 scripts/generate_sales_practice.py --output /tmp/brasaland_sales_synthetic.csv
```

El generador rechaza sobrescribir datos existentes.

## Preparacion y ausencia de fuga

- Esquema exacto: `month`, `country`, `currency`, `sales`, `is_synthetic`.
- Se validan fechas, claves unicas, moneda, cobertura mensual y ventas positivas
  finitas. Se rechazan valores nulos o vacios antes del entrenamiento con un
  mensaje explicito: no imputamos ventas objetivo que no conocemos.
- Entrenamiento: enero de 2016 a diciembre de 2023, 96 meses por mercado.
- Prueba: enero de 2024 a diciembre de 2025, 24 meses por mercado.
- La ordenacion temporal se aplica aunque el CSV llegue desordenado. No hay split
  aleatorio, fechas compartidas ni objetivos de prueba usados para ajustar.
- Solo entran como predictores el calendario y una tendencia estimada en train.
  Pais selecciona el modelo; la moneda y la marca sintetica no son predictores.
- No se escalan variables: los cortes de los arboles no requieren estandarizacion.
  El logaritmo del objetivo estabiliza ruido multiplicativo, no mezcla monedas.
- No hay busqueda de hiperparametros con test. Los parametros se fijaron antes
  de observar resultados. La prueba automatizada esta en
  [tests/pipelines/test_sales_forecast.py](../../tests/pipelines/test_sales_forecast.py).

## Eleccion del modelo

Elegimos Random Forest frente a XGBoost por las 96 observaciones de entrenamiento
por mercado, el objetivo de una primera prueba explicable y el tiempo limitado
para ajustar. Promedia 200 arboles, con minimo dos muestras por hoja, y aprende
el patron mensual. No afirmamos que sea mas preciso que XGBoost: no lo comparamos.

Un bosque puro no extrapola una tendencia creciente. Por eso este es un modelo
hibrido: se estima por minimos cuadrados una tendencia en log-ventas con controles
mensuales; se separa su componente lineal temporal y el bosque aprende los
residuos estacionales. Ambos componentes se ajustan exclusivamente con train.
Al predecir se suman tendencia y residuo, y se aplica la exponencial.
La inversion del logaritmo no corrige el sesgo de retransformation: no se interpreta
automaticamente como una esperanza monetaria insesgada.

La referencia repite cada mes observado en 2023 tanto para 2024 como para 2025.
No usa ventas reales de 2024 para predecir 2025: es una comparacion de origen fijo.

## Intervalo de variabilidad

Se hacen dos validaciones temporales dentro de los primeros ocho anos:
entrenar hasta 2021 y predecir 2022; entrenar hasta 2022 y predecir 2023.
Se obtienen 24 errores absolutos en escala logaritmica por mercado. El radio usa
el orden estadistico `ceil((24 + 1) * 0.90)`, sin consultar los anos de prueba.
Para una prediccion `p`, la banda es `[p * exp(-radio), p * exp(radio)]`.
El modelo final se ajusta con todos los anos 2016-2023.

Es una banda aproximada puntual inspirada en calibracion conformal, no un
intervalo de confianza de la media ni una garantia conformal formal: los errores
temporales no son necesariamente intercambiables y el modelo final se reajusta.
Tampoco garantiza contener simultaneamente todos los meses. Se informa cobertura
observada y anchura, sin ajustar la banda con test para mejorar su apariencia.

## Metricas de prueba

| Metrica | CO / COP | US / USD |
| --- | ---: | ---: |
| MSE (moneda al cuadrado) | 1.480974e16 | 351757580.07 |
| MAE (moneda nativa) | 101312772.25 | 13981.56 |
| R2 / K2 interpretado provisionalmente | 0.6659 | 0.5042 |
| Gini normalizado | 0.8368 | 0.8659 |
| PSI de predicciones train frente a test | 2.0097 | 1.8013 |
| MAE de referencia estacional | 120123512.02 | 21720.83 |
| Reduccion de MAE frente a referencia | 15.7% | 35.6% |
| Cobertura observada del rango nominal 90% | 87.5% (21/24) | 83.3% (20/24) |

- **MSE:** promedio del error al cuadrado. Penaliza mucho errores grandes y sus
  unidades son moneda al cuadrado; no es intuitivo ni comparable entre COP y USD.
- **MAE:** promedio de la distancia absoluta entre venta y prediccion. Para Finanzas:
  "en los meses de prueba, nos desviamos unos 101.3 millones COP o 14 mil USD
  por mes, respectivamente". No significa que cada error quede dentro de ese valor.
- **R2:** mejora cuadratica respecto a predecir la media del objetivo en prueba.
  Puede ser negativo; 1 significa ajuste perfecto, no certeza futura.
- **K2 Score:** no es una metrica estandar de regresion identificada en el enunciado.
  Se reporta `k2_score_assumed_r2` como alias provisional de R2, sin inventar una
  definicion ni afirmar que sean equivalentes. Debe confirmarse con el docente.
- **Gini normalizado de regresion:** ordenamos ventas reales por prediccion
  descendente y medimos concentracion acumulada; dividimos por el mismo indice
  con orden perfecto. Mide calidad de ordenacion, no exactitud monetaria ni el
  Gini de clasificacion `2*AUC-1`. Los empates mantienen orden temporal estable.
- **PSI:** compara proporciones de predicciones en train y test usando cinco
  intervalos de cuantiles fijados con predicciones de train, extremos abiertos
  y pseudoconteos 0.5 para evitar logaritmos de cero. Es la suma
  `(proporcion_test - proporcion_train) * log(proporcion_test / proporcion_train)`.
  Incluye predicciones de test, pero requiere train como referencia: no es un
  error supervisado calculable solo con los objetivos de test. Un valor alto
  alerta de desplazamiento, aqui asociado al crecimiento; no demuestra por si
  solo fallo del modelo. Solo hay 24 observaciones de test por mercado.

Un MSE bajo no basta: puede ocultar fuga temporal, una referencia mejor, monedas
incompatibles, sesgos, cambios de distribucion o bandas mal calibradas. El modelo
mejora esta referencia, pero no alcanza la cobertura nominal en ninguno de los
mercados. Finanzas no definio un umbral de MAE aceptable: no se declara aprobada
la viabilidad, y menos aun con datos sinteticos.

## Artefactos

En `artifacts/` se generan:

- `metrics.json`: metricas completas, periodos, semilla y SHA-256 del CSV.
- `REPORT.es.md`: tabla de resultados generada automaticamente.
- `forecast_test.png`: observaciones sinteticas, predicciones, referencia y banda.
- `predictions_test.csv`: 48 predicciones evaluadas con limites y ventas observadas.
- `models.joblib`: dos bosques, coeficientes de tendencia y radios de calibracion.
- `forecast_2026.csv`: seis meses futuros por mercado, sin ventas observadas.

El pronostico enero-junio de 2026 es una extension exploratoria desde el modelo
ajustado hasta diciembre de 2023: horizonte 25-30 meses, mayor que el de calibracion.
Su banda tiene mas incertidumbre no cuantificada; no es un pronostico evaluado.
No se reentrena con 2024-2025 para mantener esta entrega claramente separada.

Para cargar los modelos desde este directorio:

```python
import joblib
from forecast import SalesModel

bundle = joblib.load("artifacts/models.joblib")
saved = bundle["models"]["CO"]
model = SalesModel(saved["intercept"], saved["slope"], saved["forest"])
```

Cargar solo archivos joblib de confianza: su deserializacion puede ejecutar codigo.
No hay servidor, dashboard, credenciales o integracion con la API en este experimento.

## Entrega y limites

Titulo sugerido de PR: `Modelo didactico de ventas: Random Forest y evaluacion temporal`.
La descripcion debe indicar que el dataset es sintetico autorizado, justificar
Random Forest y adjuntar la tabla de metricas y la grafica. La sustitucion por
el dataset oficial y la definicion de K2 quedan pendientes para una entrega que
cumpla literalmente el enunciado. No se crean commits ni se publica un PR
automaticamente desde el experimento.