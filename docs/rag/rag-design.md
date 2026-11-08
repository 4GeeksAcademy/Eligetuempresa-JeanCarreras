# Diseño RAG de Brasaland

## Alcance y audiencia

El asistente responde a gerentes de local con la voz de un vendedor entrenado. El alcance de conocimiento es exclusivamente el corpus oficial del briefing:

- `brasaland-loyalty-program.es.md` (5 chunks)
- `brasaland-waste-protocol.es.md` (5 chunks)
- `brasaland-menu-allergens.es.md` (4 chunks)
- `brasaland-supplier-ordering.es.md` (4 chunks)

El RAG consulta documentos en cada pregunta; no es memoria conversacional. La implementación no usa LangChain ni LlamaIndex.

## Flujo de extremo a extremo

1. Los cuatro documentos fuente viven en `docs/company-knowledge-base/`.
2. `data/process/rag_index.py` valida que estén los cuatro archivos, divide cada Markdown por bloques semánticos, agrega el encabezado de sección al texto y genera embeddings.
3. `setup()` prepara los vectores y recrea la colección de desarrollo `brasaland_knowledge` en Qdrant con distancia COSINE. Cada point incluye `company`, `source_document`, `section`, `language`, `chunk_index` y `text`.
4. Ante una consulta, `retrieve()` usa la misma función `embed()` que se usó al indexar, pide hasta 5 vecinos y descarta los que tengan score menor que `RAG_MIN_SCORE`.
5. `generate_answer()` arma el prompt con pregunta y payloads recuperados, y llama al modelo de generación. Si no hay contexto suficiente, instruye al modelo a admitirlo.
6. `query()` compone retrieval y generación. FastAPI expone el resultado únicamente como `{ "answer": "..." }` en `POST /knowledge/query`.
7. La interfaz estática `uis/knowledge-assistant/index.html` consume ese endpoint y presenta estados de carga, error y respuesta.

## Chunking

El parser conserva el árbol de encabezados Markdown como `section` y utiliza los bloques delimitados por líneas en blanco como unidades de contenido. Las listas contiguas y los pasos numerados se mantienen juntos; no se fragmenta por número fijo de caracteres ni por línea. Cada chunk incluye su encabezado, lo que mantiene el contexto del bloque. Con el corpus actual el resultado es 5, 5, 4 y 4 chunks, respectivamente (18 total). `setup()` falla si una fuente produce menos de tres chunks.

## Embeddings y generación

`RAG_EMBEDDING_MODEL` configura el modelo dedicado de embeddings y `RAG_GENERATION_MODEL` el modelo de chat; la aplicación exige que sean IDs diferentes. Ambos deben ser modelos disponibles en el acceso estudiantil de 4Geeks. `LLM_API_BASE_URL` y `LLM_API_KEY` se configuran según ese proveedor compatible con OpenAI. No se incluyen credenciales ni se inventan IDs porque el entorno del repositorio no especifica cuáles asignó 4Geeks.

`embed(text)` es la única ruta de vectorización, compartida por indexación y consultas. El texto fuente se lee como UTF-8, sin normalizar ni reescribir cifras o advertencias. El vector debe tener dimensión constante; `setup()` obtiene la dimensión de la respuesta del modelo y configura Qdrant con ese tamaño. La dimensión concreta queda determinada por el modelo de embeddings configurado y debe registrarse aquí tras ejecutar la primera indexación con credenciales reales.

Qdrant usa distancia COSINE. El umbral inicial es `RAG_MIN_SCORE=0.35` en el rango de score coseno de Qdrant; es una configuración inicial, no un umbral calibrado sobre resultados reales. `data/eval/evaluate_retrieval.py` calcula Recall@3 con el umbral configurado. Antes de declarar el 80% de Recall@3, se debe ejecutar contra el Qdrant y el modelo de embeddings reales y ajustar el umbral con esos resultados.

## Alternativa Local Con Groq

Para usar embeddings sin otra clave de proveedor, la pasarela
`services/brasaland-api/src/brasaland_api/local_llm.py` expone `/v1/embeddings`
con FastEmbed en CPU y `/v1/chat/completions` con Groq. Escucha solo en
`127.0.0.1` y exige `BRASALAND_LOCAL_LLM_KEY` como Bearer. No acepta streaming.

Modelo local verificado: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`,
384 dimensiones. La primera ejecucion descarga aproximadamente 241 MB; despues
reutiliza la cache. No se reportan consumos de tokens inventados para el modelo local.
`BRASALAND_EMBED_CACHE` permite fijar una cache persistente.

Configurar estas variables en el entorno de los procesos, sin pegar claves en
el chat ni incorporarlas a Git:

```sh
export BRASALAND_LOCAL_LLM_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export LLM_API_KEY="$BRASALAND_LOCAL_LLM_KEY"
export LLM_API_BASE_URL=http://127.0.0.1:8010/v1
export RAG_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
# Configurar GROQ_API_KEY de forma privada y elegir un modelo disponible en Groq.
# RAG_GENERATION_MODEL y GROQ_GENERATION_MODEL deben indicar ese modelo real.
bash scripts/run_local_llm.sh
```

La API, el indexador y la pasarela deben compartir esa configuracion. Los exports
de un terminal no se propagan automaticamente a otros terminales ni a servidores
ya iniciados. Para clientes que usan las variables estandar del SDK OpenAI,
configurar `OPENAI_BASE_URL` con la misma URL local y `OPENAI_API_KEY` con la
misma clave local, no con la clave de Groq. `GROQ_GENERATION_MODEL` permite
dirigir los nombres de modelo de esos clientes al modelo real de Groq.

Cambiar de modelo invalida la compatibilidad con vectores previos. Reindexar el
corpus oficial solo en una coleccion de desarrollo confirmada: `setup()` elimina
y recrea la coleccion. No se ejecuto esa operacion ni se tocaron archivos de
`data/` para implementar la pasarela. Despues de reindexar, volver a evaluar
Recall@3 y calibrar el umbral; las 384 dimensiones no implican calidad de retrieval
validada. La conexion real a Groq requiere la clave y el modelo de la cuenta.

## Idempotencia y seguridad de respuesta

En desarrollo, `setup()` calcula los embeddings antes de cambiar la colección; luego elimina y recrea `brasaland_knowledge`. Los IDs de points son UUID5 deterministas basados en `source_document` y `chunk_index`, por lo que repetir la carga no duplica puntos. Esta estrategia de recreación no debe ejecutarse en una colección productiva con datos ajenos al corpus.

El prompt solo utiliza contexto recuperado, solicita citas por documento/sección, prohíbe añadir cifras no presentes y conserva COP/USD sin conversiones. Para alérgenos debe respetar literalmente la advertencia de que nunca se garantiza “cero riesgo de contaminación cruzada” y no debe afirmar “sin riesgo”. El endpoint no expone scores, chunks ni errores internos.

## Ejecución local

```sh
# Copiar las variables de rag.env.example a services/brasaland-api/.env
# Completar .env con los datos provistos por 4Geeks
uv sync --project services/brasaland-api
docker compose up -d qdrant
uv run --project services/brasaland-api python -c "from data.process.rag_index import setup; print(setup())"
uv run --project services/brasaland-api python -m pytest tests/pipelines/test_rag.py
uv run --project services/brasaland-api python -m data.eval.evaluate_retrieval
```

Levanta la API con `bash scripts/run_api_local.sh`. Para la interfaz, desde `uis/knowledge-assistant/`, ejecuta `python3 -m http.server 4175 --bind 0.0.0.0` y abre `http://localhost:4175`.
