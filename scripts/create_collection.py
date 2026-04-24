"""
create_collection.py - Crea la coleccion vectorial en Qdrant.

Script autocontenido: lee variables de entorno directamente,
sin depender de pydantic_settings ni de api.config.
Funciona incluso antes de instalar todas las dependencias.

Uso:
    python scripts/create_collection.py
"""
import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


def load_env():
    """Carga .env sin dependencias externas."""
    for candidate in [
        os.path.join(ROOT_DIR, ".env"),
        os.path.join(ROOT_DIR, "env_windows.txt"),
    ]:
        if os.path.exists(candidate):
            with open(candidate, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and key not in os.environ:
                            os.environ[key] = value
            break


load_env()

QDRANT_HOST       = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT       = int(os.environ.get("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "rag_rack")
OLLAMA_HOST       = os.environ.get("OLLAMA_HOST", "localhost")
OLLAMA_PORT       = int(os.environ.get("OLLAMA_PORT", "11434"))
OLLAMA_MODEL      = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
EMBEDDING_MODEL   = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM     = int(os.environ.get("EMBEDDING_DIM", "384"))

QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
OLLAMA_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"


def log(msg, level="INFO"):
    tag = {"INFO": "[OK]  ", "WARN": "[!]   ", "ERROR": "[ERR] "}.get(level, "[...] ")
    print(f"{tag}{msg}", flush=True)


def http_get(url, timeout=10):
    """GET simple usando urllib (sin dependencias externas)."""
    import urllib.request
    req = urllib.request.urlopen(url, timeout=timeout)
    import json
    body = req.read().decode().strip()
    if not body:
        return {}
    return json.loads(body)


def http_get_raw(url, timeout=10):
    """GET que solo verifica que el servidor responde (codigo 2xx), sin parsear JSON."""
    import urllib.request
    resp = urllib.request.urlopen(url, timeout=timeout)
    resp.read()  # consumir la respuesta
    return resp.status


def http_post(url, data, timeout=60):
    """POST simple usando urllib."""
    import urllib.request, json
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                  headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=timeout)


def check_qdrant() -> bool:
    # Intentar primero con qdrant-client (mas fiable)
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=10)
        client.get_collections()  # llamada de prueba
        log(f"Qdrant disponible en {QDRANT_URL}")
        return True
    except ImportError:
        pass  # qdrant-client no instalado aun, usar urllib
    except Exception as e:
        log(f"Qdrant no disponible: {e}", "ERROR")
        return False

    # Fallback: verificar via HTTP sin parsear JSON
    try:
        # /healthz devuelve texto plano, no JSON
        http_get_raw(f"{QDRANT_URL}/healthz")
        log(f"Qdrant disponible en {QDRANT_URL}")
        return True
    except Exception:
        # Intentar con /collections como alternativa
        try:
            http_get(f"{QDRANT_URL}/collections")
            log(f"Qdrant disponible en {QDRANT_URL}")
            return True
        except Exception as e:
            log(f"Qdrant no disponible: {e}", "ERROR")
            return False


def check_ollama() -> bool:
    try:
        data = http_get(f"{OLLAMA_URL}/api/tags")
        models = [m["name"] for m in data.get("models", [])]
        log(f"Ollama disponible. Modelos: {models}")
        model_ok = any(OLLAMA_MODEL in m for m in models)
        if not model_ok:
            log(f"Modelo '{OLLAMA_MODEL}' no encontrado. Descargando...", "WARN")
            log(f"Esto puede tardar varios minutos segun tu conexion...", "WARN")
            try:
                http_post(f"{OLLAMA_URL}/api/pull",
                          {"name": OLLAMA_MODEL, "stream": False},
                          timeout=1800)
                log(f"Modelo '{OLLAMA_MODEL}' descargado.")
            except Exception as e:
                log(f"Error descargando modelo: {e}", "ERROR")
        else:
            log(f"Modelo '{OLLAMA_MODEL}' disponible.")
        return True
    except Exception as e:
        log(f"Ollama no disponible: {e}", "ERROR")
        return False


def create_collection() -> None:
    """Crea la coleccion en Qdrant usando qdrant-client."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
    except ImportError:
        log("qdrant-client no instalado. Ejecuta: pip install qdrant-client", "ERROR")
        sys.exit(1)

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    existing = [c.name for c in client.get_collections().collections]

    if QDRANT_COLLECTION in existing:
        log(f"Coleccion '{QDRANT_COLLECTION}' ya existe.")
    else:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        log(f"Coleccion '{QDRANT_COLLECTION}' creada (dim={EMBEDDING_DIM}, cosine).")

    info = client.get_collection(QDRANT_COLLECTION)
    log(f"Coleccion '{QDRANT_COLLECTION}': {info.points_count} puntos indexados.")


def main():
    print()
    print("=" * 50)
    print("  rag-rack - Inicializacion del sistema")
    print("=" * 50)
    print(f"  Qdrant     : {QDRANT_URL}")
    print(f"  Ollama     : {OLLAMA_URL}")
    print(f"  Modelo LLM : {OLLAMA_MODEL}")
    print(f"  Embeddings : {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Coleccion  : {QDRANT_COLLECTION}")
    print("=" * 50)
    print()

    errors = []
    if not check_qdrant():
        errors.append("Qdrant no disponible")
    if not check_ollama():
        errors.append("Ollama no disponible")

    if errors:
        print()
        for err in errors:
            log(err, "ERROR")
        log("Asegurate de que Qdrant y Ollama estan corriendo.", "ERROR")
        sys.exit(1)

    print()
    log("Creando coleccion en Qdrant...")
    create_collection()

    print()
    print("=" * 50)
    log("Sistema inicializado correctamente.")
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()
