"""
github_worker.py — Ingesta de repositorios GitHub.

Flujo:
1. Clonar el repositorio en un directorio temporal.
2. Recorrer el árbol de archivos con whitelist de extensiones.
3. Ignorar directorios y archivos de ruido.
4. Devolver lista de dicts {path, file, content}.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import List

import git
from loguru import logger


# Extensiones de archivo que se consideran útiles para RAG
ALLOWED_EXTENSIONS = {
    ".py", ".md", ".txt", ".rst", ".js", ".ts", ".jsx", ".tsx",
    ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
    ".html", ".css", ".sh", ".bash", ".sql", ".go", ".rs",
    ".java", ".kt", ".rb", ".php", ".c", ".cpp", ".h",
}

# Directorios que se deben ignorar completamente
IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "target", "vendor", "bower_components",
    ".idea", ".vscode", "eggs", "*.egg-info",
}

# Archivos que se deben ignorar por nombre
IGNORED_FILES = {
    "package-lock.json", "yarn.lock", "poetry.lock", "Pipfile.lock",
    "Cargo.lock", "composer.lock", ".DS_Store", "Thumbs.db",
}

# Tamaño máximo de archivo a procesar (bytes) — evita archivos enormes
MAX_FILE_SIZE_BYTES = 500_000  # 500 KB


def clone_repo(repo_url: str, target_dir: str) -> str:
    """
    Clona un repositorio Git en `target_dir`.

    Args:
        repo_url: URL del repositorio (https o ssh).
        target_dir: Directorio destino para el clone.

    Returns:
        Ruta al directorio clonado.

    Raises:
        RuntimeError: Si el clone falla.
    """
    logger.info(f"Clonando repositorio: {repo_url} → {target_dir}")
    try:
        git.Repo.clone_from(repo_url, target_dir, depth=1)
        logger.info(f"Clone completado: {target_dir}")
        return target_dir
    except git.exc.GitCommandError as e:
        raise RuntimeError(f"Error al clonar {repo_url}: {e}") from e


def _should_ignore_dir(dir_name: str) -> bool:
    """Comprueba si un directorio debe ser ignorado."""
    return dir_name in IGNORED_DIRS or dir_name.startswith(".")


def _should_process_file(file_path: Path) -> bool:
    """Comprueba si un archivo debe ser procesado."""
    if file_path.name in IGNORED_FILES:
        return False
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False
    if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
        logger.debug(f"Archivo demasiado grande, omitido: {file_path}")
        return False
    return True


def extract_repo_files(repo_dir: str, repo_url: str) -> List[dict]:
    """
    Recorre el repositorio clonado y extrae el contenido de los archivos útiles.

    Args:
        repo_dir: Ruta al directorio del repositorio clonado.
        repo_url: URL original del repositorio (para metadatos).

    Returns:
        Lista de dicts con claves: source, path, file, content.
    """
    repo_path = Path(repo_dir)
    extracted: List[dict] = []
    skipped = 0

    for root, dirs, files in os.walk(repo_path):
        # Filtrar directorios ignorados in-place (modifica la lista para os.walk)
        dirs[:] = [d for d in dirs if not _should_ignore_dir(d)]

        for filename in files:
            file_path = Path(root) / filename

            if not _should_process_file(file_path):
                skipped += 1
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                if not content.strip():
                    continue

                # Ruta relativa dentro del repositorio
                relative_path = str(file_path.relative_to(repo_path))

                extracted.append(
                    {
                        "source": repo_url,
                        "type": "github",
                        "path": relative_path,
                        "file": filename,
                        "content": content,
                    }
                )
            except Exception as e:
                logger.warning(f"Error leyendo {file_path}: {e}")
                skipped += 1

    logger.info(
        f"Extracción completada: {len(extracted)} archivos procesados, "
        f"{skipped} omitidos."
    )
    return extracted


def ingest_github_repo(repo_url: str) -> List[dict]:
    """
    Función principal: clona el repo, extrae archivos y limpia el directorio temporal.

    Args:
        repo_url: URL del repositorio GitHub.

    Returns:
        Lista de dicts con contenido y metadatos de cada archivo.
    """
    tmp_dir = tempfile.mkdtemp(prefix="rag_rack_github_")
    try:
        clone_repo(repo_url, tmp_dir)
        files = extract_repo_files(tmp_dir, repo_url)
        return files
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.debug(f"Directorio temporal eliminado: {tmp_dir}")
