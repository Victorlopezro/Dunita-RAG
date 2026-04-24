"""
crawl4ai_worker.py — Ingesta de páginas web con Crawl4AI.

Crawl4AI extrae el contenido de páginas web y lo devuelve como
Markdown limpio, optimizado para su uso en sistemas RAG.

Flujo:
1. Recibir lista de URLs.
2. Para cada URL, hacer crawl con AsyncWebCrawler.
3. Extraer el Markdown limpio del resultado.
4. Devolver lista de dicts {source, path, file, content}.
"""

from __future__ import annotations

import asyncio
from typing import List
from urllib.parse import urlparse

from loguru import logger


def _url_to_filename(url: str) -> str:
    """Convierte una URL en un nombre de archivo legible."""
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_") or "index"
    return f"{parsed.netloc}_{path}"[:100]


async def _crawl_url(url: str) -> dict | None:
    """
    Realiza el crawl de una URL y devuelve el contenido como Markdown.

    Args:
        url: URL a rastrear.

    Returns:
        Dict con source, type, path, file, content; o None si falla.
    """
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        browser_cfg = BrowserConfig(headless=True, verbose=False)
        run_cfg = CrawlerRunConfig(
            word_count_threshold=10,       # Ignorar páginas con muy poco texto
            remove_overlay_elements=True,  # Eliminar popups y banners
            excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
        )

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)

        if not result.success:
            logger.warning(f"Crawl fallido para {url}: {result.error_message}")
            return None

        content = result.markdown_v2.raw_markdown if result.markdown_v2 else result.markdown
        if not content or not content.strip():
            logger.warning(f"Contenido vacío para {url}")
            return None

        parsed = urlparse(url)
        return {
            "source": url,
            "type": "web",
            "path": parsed.path or "/",
            "file": _url_to_filename(url),
            "content": content.strip(),
        }

    except Exception as e:
        logger.error(f"Error durante crawl de {url}: {e}")
        return None


async def _crawl_urls_async(urls: List[str]) -> List[dict]:
    """Crawlea múltiples URLs de forma concurrente (máx. 5 simultáneas)."""
    semaphore = asyncio.Semaphore(5)

    async def bounded_crawl(url: str) -> dict | None:
        async with semaphore:
            return await _crawl_url(url)

    tasks = [bounded_crawl(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return [r for r in results if r is not None]


def ingest_web_urls(urls: List[str]) -> List[dict]:
    """
    Función principal: crawlea una lista de URLs y devuelve su contenido.

    Maneja correctamente la ejecución dentro de un event loop existente
    (como el de FastAPI) usando un thread separado si es necesario.

    Args:
        urls: Lista de URLs a rastrear.

    Returns:
        Lista de dicts con contenido y metadatos de cada página.
    """
    if not urls:
        return []

    logger.info(f"Iniciando crawl de {len(urls)} URLs...")

    try:
        # Intentar obtener el event loop actual
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Estamos dentro de un contexto async (FastAPI): usar run_in_executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _crawl_urls_async(urls))
                results = future.result(timeout=300)
        else:
            results = loop.run_until_complete(_crawl_urls_async(urls))
    except RuntimeError:
        # No hay event loop: crear uno nuevo
        results = asyncio.run(_crawl_urls_async(urls))

    logger.info(f"Crawl completado: {len(results)}/{len(urls)} URLs procesadas.")
    return results


async def ingest_web_urls_async(urls: List[str]) -> List[dict]:
    """
    Versión async de ingest_web_urls para uso directo en contextos async.

    Args:
        urls: Lista de URLs a rastrear.

    Returns:
        Lista de dicts con contenido y metadatos de cada página.
    """
    if not urls:
        return []

    logger.info(f"Iniciando crawl async de {len(urls)} URLs...")
    results = await _crawl_urls_async(urls)
    logger.info(f"Crawl async completado: {len(results)}/{len(urls)} URLs procesadas.")
    return results
