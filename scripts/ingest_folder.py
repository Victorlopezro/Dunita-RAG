"""
ingest_folder.py — Ingesta batch de documentos desde una carpeta local.

Uso:
    python scripts/ingest_folder.py --folder ./data/raw
    python scripts/ingest_folder.py --folder ./data/raw --api http://localhost:8000

Envía los archivos al endpoint /ingest de la API.
"""

import argparse
import sys
import os
from pathlib import Path

import httpx
from loguru import logger

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".md", ".txt"}


def get_files(folder: Path) -> list:
    """Obtiene todos los archivos soportados en la carpeta."""
    files = [
        str(f) for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return files


def ingest_via_api(file_paths: list, api_url: str) -> dict:
    """Envía los archivos al endpoint /ingest de la API."""
    payload = {
        "source_type": "document",
        "file_paths": file_paths,
    }
    try:
        resp = httpx.post(
            f"{api_url}/ingest",
            json=payload,
            timeout=600,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Ingesta batch de documentos desde una carpeta."
    )
    parser.add_argument(
        "--folder",
        type=str,
        required=True,
        help="Ruta a la carpeta con documentos a ingestar.",
    )
    parser.add_argument(
        "--api",
        type=str,
        default="http://localhost:8000",
        help="URL base de la API (default: http://localhost:8000).",
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        logger.error(f"La carpeta no existe: {folder}")
        sys.exit(1)

    files = get_files(folder)
    if not files:
        logger.warning(f"No se encontraron archivos soportados en: {folder}")
        sys.exit(0)

    logger.info(f"Encontrados {len(files)} archivos en {folder}")
    for f in files:
        logger.info(f"  - {f}")

    logger.info(f"Enviando a API: {args.api}/ingest")
    result = ingest_via_api(files, args.api)

    if "error" in result:
        logger.error(f"Error durante la ingesta: {result['error']}")
        sys.exit(1)

    logger.info(f"✅ Ingesta completada:")
    logger.info(f"   Documentos procesados: {result.get('documents_processed', 0)}")
    logger.info(f"   Chunks indexados: {result.get('chunks_indexed', 0)}")
    if result.get("errors"):
        logger.warning(f"   Errores: {len(result['errors'])}")
        for err in result["errors"]:
            logger.warning(f"     - {err}")


if __name__ == "__main__":
    main()
