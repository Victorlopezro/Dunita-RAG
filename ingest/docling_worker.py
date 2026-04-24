"""
docling_worker.py — Extracción de texto de documentos con Docling.

Soporta: PDF, DOCX, PPTX y otros formatos documentales.

Flujo:
1. Recibir ruta de archivo o lista de rutas.
2. Usar Docling para extraer texto estructurado.
3. Devolver lista de dicts {source, path, file, content}.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from loguru import logger


# Extensiones soportadas por Docling
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".md", ".txt"}


def _extract_with_docling(file_path: Path) -> str | None:
    """
    Extrae texto de un archivo usando Docling.

    Args:
        file_path: Ruta al archivo a procesar.

    Returns:
        Texto extraído como string, o None si falla.
    """
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(file_path))
        text = result.document.export_to_markdown()

        if not text or not text.strip():
            logger.warning(f"Docling devolvió contenido vacío para: {file_path}")
            return None

        return text.strip()

    except Exception as e:
        logger.error(f"Error de Docling procesando {file_path}: {e}")
        return None


def ingest_document(file_path: str | Path, source_label: str | None = None) -> dict | None:
    """
    Procesa un único documento y devuelve su contenido con metadatos.

    Args:
        file_path: Ruta al archivo.
        source_label: Etiqueta de fuente opcional (por defecto usa la ruta).

    Returns:
        Dict con source, type, path, file, content; o None si falla.
    """
    path = Path(file_path)

    if not path.exists():
        logger.error(f"Archivo no encontrado: {path}")
        return None

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        logger.warning(f"Extensión no soportada: {path.suffix} ({path})")
        return None

    logger.info(f"Procesando documento con Docling: {path.name}")
    content = _extract_with_docling(path)

    if content is None:
        return None

    return {
        "source": source_label or str(path),
        "type": "document",
        "path": str(path.parent),
        "file": path.name,
        "content": content,
    }


def ingest_documents(file_paths: List[str | Path]) -> List[dict]:
    """
    Procesa múltiples documentos y devuelve los que se extrajeron correctamente.

    Args:
        file_paths: Lista de rutas a archivos.

    Returns:
        Lista de dicts con contenido y metadatos.
    """
    if not file_paths:
        return []

    results: List[dict] = []
    for fp in file_paths:
        doc = ingest_document(fp)
        if doc:
            results.append(doc)

    logger.info(
        f"Ingesta documental completada: {len(results)}/{len(file_paths)} documentos procesados."
    )
    return results


def ingest_folder(folder_path: str | Path) -> List[dict]:
    """
    Procesa todos los documentos soportados en una carpeta.

    Args:
        folder_path: Ruta a la carpeta.

    Returns:
        Lista de dicts con contenido y metadatos.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        logger.error(f"No es un directorio válido: {folder}")
        return []

    files = [
        f for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    logger.info(f"Encontrados {len(files)} documentos en {folder}")
    return ingest_documents(files)
