"""
app.py — Frontend chatbot de rag-rack con Streamlit.

Interfaz de usuario que permite:
- Hacer consultas al sistema RAG.
- Ver las fuentes utilizadas en cada respuesta.
- Ingestar repositorios GitHub y URLs web desde la barra lateral.
- Verificar el estado del sistema.
"""

import os
import time
from typing import Optional

import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────────────────────

API_URL = os.getenv("FRONTEND_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="rag-rack — Chatbot RAG",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# Estilos CSS mínimos
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
.source-card {
    background-color: #f0f2f6;
    border-left: 3px solid #1f77b4;
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 4px;
    font-size: 0.85em;
}
.source-type-github { border-left-color: #333; }
.source-type-web { border-left-color: #1f77b4; }
.source-type-document { border-left-color: #2ca02c; }
.score-badge {
    display: inline-block;
    background: #1f77b4;
    color: white;
    padding: 1px 6px;
    border-radius: 10px;
    font-size: 0.75em;
    margin-left: 6px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Funciones de API
# ─────────────────────────────────────────────────────────────

def api_health() -> dict:
    """Consulta el endpoint /health de la API."""
    try:
        resp = requests.get(f"{API_URL}/health", timeout=10)
        return resp.json()
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def api_query(query: str, filter_type: Optional[str] = None) -> dict:
    """Envía una consulta al endpoint /query de la API."""
    payload = {"query": query}
    if filter_type and filter_type != "Todas":
        payload["filter_type"] = filter_type.lower()

    try:
        resp = requests.post(
            f"{API_URL}/query",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {"error": "Timeout: el modelo tardó demasiado en responder (>120s)."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"error": f"Error HTTP {e.response.status_code}: {detail}"}
    except Exception as e:
        return {"error": f"Error de conexión: {str(e)}"}


def api_ingest(source_type: str, urls: list = None, file_paths: list = None) -> dict:
    """Envía una solicitud de ingesta al endpoint /ingest de la API."""
    payload = {"source_type": source_type}
    if urls:
        payload["urls"] = urls
    if file_paths:
        payload["file_paths"] = file_paths

    try:
        resp = requests.post(
            f"{API_URL}/ingest",
            json=payload,
            timeout=600,  # La ingesta puede tardar varios minutos
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {"error": "Timeout: la ingesta tardó demasiado (>600s)."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"error": f"Error HTTP {e.response.status_code}: {detail}"}
    except Exception as e:
        return {"error": f"Error de conexión: {str(e)}"}



def api_ingest_upload(uploaded_files) -> dict:
    """Sube archivos al endpoint /ingest/upload de la API."""
    import io
    try:
        files = [("files", (uf.name, uf.getvalue(), uf.type or "application/octet-stream"))
                 for uf in uploaded_files]
        resp = requests.post(
            f"{API_URL}/ingest/upload",
            files=files,
            timeout=600,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {"error": "Timeout: la ingesta tardó demasiado (>600s)."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"error": f"Error HTTP {e.response.status_code}: {detail}"}
    except Exception as e:
        return {"error": f"Error de conexión: {str(e)}"}

# ─────────────────────────────────────────────────────────────
# Estado de sesión
# ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_sources" not in st.session_state:
    st.session_state.last_sources = []


# ─────────────────────────────────────────────────────────────
# Barra lateral
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ rag-rack")
    st.caption("Sistema RAG local con Qwen + Haystack + Qdrant")

    # Estado del sistema
    st.subheader("Estado del sistema")
    if st.button("🔄 Verificar estado", use_container_width=True):
        with st.spinner("Verificando..."):
            health = api_health()
        st.session_state["health"] = health

    if "health" in st.session_state:
        h = st.session_state["health"]
        status = h.get("status", "unknown")
        if status == "ok":
            st.success("✅ Sistema operativo")
        elif status == "degraded":
            st.warning("⚠️ Sistema degradado")
        else:
            st.error("❌ Sistema no disponible")

        comps = h.get("components", {})
        col1, col2, col3 = st.columns(3)
        col1.metric("Qdrant", "✅" if comps.get("qdrant") else "❌")
        col2.metric("Ollama", "✅" if comps.get("ollama") else "❌")
        col3.metric("SBERT", "✅" if comps.get("embedding_model") else "❌")

        if comps.get("ollama_models"):
            st.caption(f"Modelos: {', '.join(comps['ollama_models'][:3])}")

    st.divider()

    # Filtro de fuentes
    st.subheader("Filtro de consulta")
    filter_type = st.selectbox(
        "Buscar en:",
        options=["Todas", "GitHub", "Web", "Document"],
        index=0,
        help="Filtra los resultados por tipo de fuente.",
    )

    st.divider()

    # Ingesta de GitHub
    st.subheader("📦 Ingestar GitHub")
    github_urls_input = st.text_area(
        "URLs de repositorios (una por línea):",
        placeholder="https://github.com/usuario/repo",
        height=100,
        key="github_input",
    )
    if st.button("🚀 Ingestar repos", use_container_width=True):
        urls = [u.strip() for u in github_urls_input.strip().splitlines() if u.strip()]
        if not urls:
            st.error("Introduce al menos una URL de repositorio.")
        else:
            with st.spinner(f"Ingesta de {len(urls)} repo(s)... (puede tardar varios minutos)"):
                result = api_ingest("github", urls=urls)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success(
                    f"✅ {result.get('documents_processed', 0)} archivos | "
                    f"{result.get('chunks_indexed', 0)} chunks indexados"
                )
                if result.get("errors"):
                    with st.expander("Ver errores"):
                        for err in result["errors"]:
                            st.warning(err)

    st.divider()

    # Ingesta Web
    st.subheader("🌐 Ingestar URLs web")
    web_urls_input = st.text_area(
        "URLs (una por línea):",
        placeholder="https://ejemplo.com/docs",
        height=100,
        key="web_input",
    )
    if st.button("🚀 Ingestar webs", use_container_width=True):
        urls = [u.strip() for u in web_urls_input.strip().splitlines() if u.strip()]
        if not urls:
            st.error("Introduce al menos una URL.")
        else:
            with st.spinner(f"Crawleando {len(urls)} URL(s)..."):
                result = api_ingest("web", urls=urls)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success(
                    f"✅ {result.get('documents_processed', 0)} páginas | "
                    f"{result.get('chunks_indexed', 0)} chunks indexados"
                )

    st.divider()

    # Ingesta de documentos (subida directa)
    st.subheader("📄 Subir documentos")
    uploaded_files = st.file_uploader(
        "PDF, Word, PowerPoint, Excel, Markdown, TXT",
        type=["pdf", "docx", "pptx", "xlsx", "md", "txt"],
        accept_multiple_files=True,
        key="doc_upload",
    )
    if uploaded_files and st.button("🚀 Ingestar documentos", use_container_width=True):
        with st.spinner(f"Procesando {len(uploaded_files)} archivo(s)..."):
            result = api_ingest_upload(uploaded_files)
        if "error" in result:
            st.error(result["error"])
        else:
            st.success(
                f"✅ {result.get('documents_processed', 0)} docs | "
                f"{result.get('chunks_indexed', 0)} chunks indexados"
            )
            if result.get("errors"):
                with st.expander("Ver errores"):
                    for err in result["errors"]:
                        st.warning(err)
    st.divider()
        # Limpiar historial
    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_sources = []
        st.rerun()


# ─────────────────────────────────────────────────────────────
# Área principal — Chat
# ─────────────────────────────────────────────────────────────

st.title("🔍 rag-rack — Chatbot RAG")
st.caption(
    "Haz preguntas sobre el contenido indexado. "
    "Las respuestas se generan usando contexto real recuperado de los documentos."
)

# Mostrar historial de mensajes
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander(f"📚 Fuentes utilizadas ({len(msg['sources'])} chunks)"):
                for src in msg["sources"]:
                    src_type = src.get("type", "unknown")
                    type_class = f"source-type-{src_type}"
                    icon = {"github": "🐙", "web": "🌐", "document": "📄"}.get(src_type, "📎")
                    st.markdown(
                        f'<div class="source-card {type_class}">'
                        f'{icon} <strong>{src.get("file", "")}</strong>'
                        f'<span class="score-badge">{src.get("score", 0):.3f}</span><br>'
                        f'<small>{src.get("source", "")}</small>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

# Input del usuario
if prompt := st.chat_input("Escribe tu pregunta aquí..."):
    # Mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generar respuesta
    with st.chat_message("assistant"):
        with st.spinner("Buscando en el índice y generando respuesta..."):
            start_time = time.time()
            result = api_query(
                query=prompt,
                filter_type=filter_type if filter_type != "Todas" else None,
            )
            elapsed = time.time() - start_time

        if "error" in result:
            answer = f"❌ Error: {result['error']}"
            sources = []
        else:
            answer = result.get("answer", "Sin respuesta.")
            sources = result.get("sources", [])

        st.markdown(answer)
        st.caption(
            f"⏱️ {elapsed:.1f}s | "
            f"🧩 {result.get('chunks_used', 0)} chunks | "
            f"🤖 {result.get('model', 'N/A')}"
        )

        if sources:
            with st.expander(f"📚 Fuentes utilizadas ({len(sources)} chunks)"):
                for src in sources:
                    src_type = src.get("type", "unknown")
                    type_class = f"source-type-{src_type}"
                    icon = {"github": "🐙", "web": "🌐", "document": "📄"}.get(src_type, "📎")
                    st.markdown(
                        f'<div class="source-card {type_class}">'
                        f'{icon} <strong>{src.get("file", "")}</strong>'
                        f'<span class="score-badge">{src.get("score", 0):.3f}</span><br>'
                        f'<small>{src.get("source", "")}</small>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    # Guardar en historial
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
    })
