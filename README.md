# rag-rack

Sistema RAG (Retrieval-Augmented Generation) local, gratuito y modular.
Permite ingestar repositorios GitHub, páginas web y documentos, y consultarlos
mediante un chatbot con respuestas basadas en contexto real.

## Stack tecnológico

| Capa | Herramienta |
|---|---|
| LLM | Qwen 2.5 (7B) |
| Runtime LLM | Ollama |
| Framework RAG | Haystack 2.x |
| Base vectorial | Qdrant |
| Extracción documental | Docling |
| Extracción web | Crawl4AI |
| Embeddings | SBERT (`all-MiniLM-L6-v2`) |
| API | FastAPI |
| Frontend | Streamlit |
| Evaluación | Ragas |

## Arquitectura

```
Consulta: Frontend (Streamlit) → FastAPI → Haystack → Qdrant + Ollama/Qwen

Ingesta:  GitHub / URLs / Docs → Workers → Chunking → SBERT → Qdrant
```

## Estructura del proyecto

```
rag-rack/
├─ docker-compose.yml       # Orquestación de servicios
├─ .env                     # Variables de entorno
├─ requirements.txt         # Dependencias Python
├─ README.md
│
├─ api/
│   ├─ main.py              # FastAPI entry point
│   ├─ config.py            # Configuración centralizada
│   ├─ routes/
│   │   ├─ health.py        # GET /health
│   │   ├─ ingest.py        # POST /ingest
│   │   └─ query.py         # POST /query
│   ├─ services/
│   │   ├─ ingest_service.py
│   │   └─ query_service.py
│   └─ pipelines/
│       └─ rag_pipeline.py  # Pipeline RAG principal
│
├─ ingest/
│   ├─ github_worker.py     # Ingesta de repos GitHub
│   ├─ crawl4ai_worker.py   # Ingesta de páginas web
│   ├─ docling_worker.py    # Ingesta de documentos
│   ├─ chunking.py          # Chunking con overlap
│   ├─ embedding.py         # SBERT embeddings
│   └─ indexer.py           # Upsert en Qdrant
│
├─ frontend/
│   └─ app.py               # Streamlit chatbot
│
├─ scripts/
│   ├─ create_collection.py # Inicialización del sistema
│   ├─ ingest_folder.py     # Ingesta batch de documentos
│   └─ run_eval.py          # Evaluación con Ragas
│
├─ data/
│   ├─ raw/                 # Archivos originales
│   ├─ parsed/              # Texto extraído
│   ├─ chunks/              # Chunks generados
│   └─ eval/                # Datasets de evaluación
│
└─ tests/                   # Tests unitarios e integración
```

## Requisitos

- Docker y Docker Compose
- Python 3.11+ (para scripts locales)
- 16 GB RAM mínimo (32 GB recomendado)
- 60 GB disco (para modelos y datos)

## Inicio rápido

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/rag-rack.git
cd rag-rack
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env si necesitas cambiar algún valor
```

### 3. Levantar servicios base

```bash
docker compose up -d qdrant ollama
```

### 4. Inicializar el sistema (descarga el modelo y crea la colección)

```bash
pip install -r requirements.txt
python scripts/create_collection.py
```

> Este paso descarga el modelo `qwen2.5:7b` (~4.7 GB). Puede tardar varios minutos.

### 5. Levantar la API y el frontend

```bash
docker compose up -d api frontend
```

### 6. Acceder al chatbot

Abrir en el navegador: **http://localhost:8501**

La documentación de la API está disponible en: **http://localhost:8000/docs**

---

## Uso de la API

### Verificar estado del sistema

```bash
curl http://localhost:8000/health
```

### Ingestar un repositorio GitHub

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "github",
    "urls": ["https://github.com/usuario/repositorio"]
  }'
```

### Ingestar páginas web

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "web",
    "urls": ["https://ejemplo.com/docs", "https://ejemplo.com/api"]
  }'
```

### Hacer una consulta

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "¿Cómo funciona el sistema de autenticación?"
  }'
```

**Respuesta:**
```json
{
  "answer": "El sistema de autenticación funciona mediante...",
  "sources": [
    {
      "file": "auth.py",
      "source": "https://github.com/usuario/repo",
      "type": "github",
      "path": "src/auth.py",
      "score": 0.9234,
      "chunk_id": 3
    }
  ],
  "query": "¿Cómo funciona el sistema de autenticación?",
  "model": "qwen2.5:7b",
  "chunks_used": 5
}
```

---

## Scripts de utilidad

### Ingestar documentos desde una carpeta

```bash
python scripts/ingest_folder.py --folder ./data/raw
```

### Evaluar el sistema con Ragas

```bash
# Generar dataset de muestra
python scripts/run_eval.py --generate-sample

# Editar data/eval/sample_dataset.json con preguntas reales

# Ejecutar evaluación
python scripts/run_eval.py --dataset data/eval/sample_dataset.json
```

---

## Ejecutar tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

---

## Parámetros configurables (.env)

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `OLLAMA_MODEL` | `qwen2.5:7b` | Modelo LLM a usar |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Modelo SBERT |
| `EMBEDDING_DIM` | `384` | Dimensión del vector |
| `CHUNK_SIZE` | `600` | Tokens por chunk |
| `CHUNK_OVERLAP` | `75` | Tokens de solapamiento |
| `TOP_K` | `5` | Chunks a recuperar por consulta |
| `QDRANT_COLLECTION` | `rag_rack` | Nombre de la colección |

---

## Criterios de éxito

El sistema es válido si:

- Responde preguntas sobre repositorios y webs ingeridas.
- Usa contexto real (no respuestas genéricas).
- Las respuestas incluyen referencias a las fuentes.
- Es escalable sin rehacer la base.

---

## Ruta de evolución

1. **v1 (actual)**: Base funcional con ingesta, consulta y chatbot.
2. **v2**: Reranking, filtros avanzados, autenticación.
3. **v3**: Múltiples colecciones, agentes especializados, observabilidad.

---

## Licencia

MIT
