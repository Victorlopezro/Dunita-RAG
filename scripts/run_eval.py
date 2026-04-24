"""
run_eval.py — Evaluación del sistema RAG con Ragas.

Uso:
    python scripts/run_eval.py --dataset ./data/eval/dataset.json
    python scripts/run_eval.py --generate-sample

El dataset debe ser un JSON con esta estructura:
[
  {
    "question": "¿Qué hace la función X?",
    "ground_truth": "La función X hace Y."
  },
  ...
]

Ragas evaluará:
- faithfulness: ¿La respuesta es fiel al contexto recuperado?
- answer_relevancy: ¿La respuesta es relevante para la pregunta?
- context_recall: ¿El contexto recuperado contiene la respuesta correcta?
- context_precision: ¿El contexto recuperado es preciso?
"""

import argparse
import json
import sys
import os
from pathlib import Path

import httpx
from loguru import logger

# Asegurar que el directorio raíz está en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


SAMPLE_DATASET = [
    {
        "question": "¿Qué tecnologías usa este sistema RAG?",
        "ground_truth": "El sistema usa Qwen, Ollama, Haystack, Qdrant, SBERT, FastAPI y Streamlit.",
    },
    {
        "question": "¿Cómo se indexa el contenido en el sistema?",
        "ground_truth": "El contenido se divide en chunks, se vectoriza con SBERT y se almacena en Qdrant.",
    },
]


def query_system(question: str, api_url: str) -> dict:
    """Consulta el sistema RAG y devuelve la respuesta con contexto."""
    try:
        resp = httpx.post(
            f"{api_url}/query",
            json={"query": question},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def run_evaluation(dataset: list, api_url: str) -> None:
    """Ejecuta la evaluación Ragas sobre el dataset."""
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_recall,
            context_precision,
        )
    except ImportError:
        logger.error("Ragas no está instalado. Ejecuta: pip install ragas datasets")
        sys.exit(1)

    logger.info(f"Evaluando {len(dataset)} preguntas...")

    questions = []
    answers = []
    contexts = []
    ground_truths = []

    for item in dataset:
        question = item["question"]
        ground_truth = item.get("ground_truth", "")

        logger.info(f"Consultando: {question[:60]}...")
        result = query_system(question, api_url)

        if "error" in result:
            logger.warning(f"Error en consulta: {result['error']}")
            continue

        answer = result.get("answer", "")
        sources = result.get("sources", [])
        context_texts = [s.get("text", "") for s in sources if s.get("text")]

        questions.append(question)
        answers.append(answer)
        contexts.append(context_texts if context_texts else [""])
        ground_truths.append(ground_truth)

    if not questions:
        logger.error("No se pudieron obtener respuestas para evaluar.")
        sys.exit(1)

    # Crear dataset Ragas
    eval_dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

    logger.info("Ejecutando evaluación Ragas...")
    try:
        results = evaluate(
            eval_dataset,
            metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
        )

        logger.info("=" * 50)
        logger.info("RESULTADOS DE EVALUACIÓN RAGAS")
        logger.info("=" * 50)
        for metric, score in results.items():
            logger.info(f"  {metric}: {score:.4f}")
        logger.info("=" * 50)

        # Guardar resultados
        output_path = Path("data/eval/ragas_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(dict(results), f, indent=2)
        logger.info(f"Resultados guardados en: {output_path}")

    except Exception as e:
        logger.error(f"Error durante la evaluación Ragas: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Evaluación del sistema RAG con Ragas.")
    parser.add_argument(
        "--dataset",
        type=str,
        help="Ruta al dataset JSON de evaluación.",
    )
    parser.add_argument(
        "--generate-sample",
        action="store_true",
        help="Genera un dataset de muestra y lo guarda.",
    )
    parser.add_argument(
        "--api",
        type=str,
        default="http://localhost:8000",
        help="URL base de la API (default: http://localhost:8000).",
    )
    args = parser.parse_args()

    if args.generate_sample:
        output_path = Path("data/eval/sample_dataset.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(SAMPLE_DATASET, f, indent=2, ensure_ascii=False)
        logger.info(f"Dataset de muestra generado: {output_path}")
        logger.info("Edítalo con preguntas reales y ejecuta:")
        logger.info(f"  python scripts/run_eval.py --dataset {output_path}")
        return

    if not args.dataset:
        parser.print_help()
        sys.exit(1)

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        logger.error(f"Dataset no encontrado: {dataset_path}")
        sys.exit(1)

    with open(dataset_path) as f:
        dataset = json.load(f)

    run_evaluation(dataset, args.api)


if __name__ == "__main__":
    main()
