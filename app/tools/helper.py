import heapq
import re
import time
import traceback
from typing import Any, Dict, List
from qdrant_client.models import QueryResponse

from app import get_logger
logger = get_logger(__name__)

MAX_CHARS = 100_000


class HelperTools:
    @staticmethod
    def reciprocal_rank_fusion(
        points: List["QueryResponse"] = None, n_points: int = None, k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combines dense and sparse retrieval results using Reciprocal Rank Fusion (RRF)
        and returns a list of dicts with {id, context}.
        """
        start_time = time.perf_counter()
        try:
            if not points or len(points) < 2:
                raise ValueError(
                    "Expected two sets of points: dense and sparse results."
                )

            dense_results = points[0].points
            sparse_results = points[1].points

            dense_scores = {str(r.id): r.score for r in dense_results}
            sparse_scores = {str(r.id): r.score for r in sparse_results}
            all_doc_ids = dense_scores.keys() | sparse_scores.keys()
            doc_lookup = {
                str(result.id): result for result in dense_results + sparse_results
            }

            dense_ranked = sorted(
                dense_scores.items(), key=lambda x: x[1], reverse=True
            )
            sparse_ranked = sorted(
                sparse_scores.items(), key=lambda x: x[1], reverse=True
            )
            dense_ranks = {
                doc_id: rank + 1 for rank, (doc_id, _) in enumerate(dense_ranked)
            }
            sparse_ranks = {
                doc_id: rank + 1 for rank, (doc_id, _) in enumerate(sparse_ranked)
            }

            rrf_scores = {
                doc_id: (1 / (k + dense_ranks.get(doc_id, len(dense_results) + 1)))
                + (1 / (k + sparse_ranks.get(doc_id, len(sparse_results) + 1)))
                for doc_id in all_doc_ids
            }

            if n_points and n_points < len(rrf_scores):
                top_doc_ids = [
                    doc_id
                    for doc_id, _ in heapq.nlargest(
                        n_points, rrf_scores.items(), key=lambda x: x[1]
                    )
                ]
            else:
                top_doc_ids = sorted(
                    rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True
                )[:n_points]

            results = []
            for doc_id in top_doc_ids:
                doc = doc_lookup[doc_id]
                results.append(
                    {
                        "id": doc.payload.get("id"),
                        "summary": doc.payload.get("summaryEN"),
                        "notes": doc.payload.get("notesSV"),
                        "externalUrl": doc.payload.get("externalUrl"),
                        "title": doc.payload.get("title"),
                        "titleEN": doc.payload.get("titleEN"),
                        "prerequisite": doc.payload.get("prerequisite"),
                        "postSelectionRequirements": doc.payload.get(
                            "postSelectionRequirements"
                        ),
                        "cosine_score": rrf_scores[doc_id],
                    }
                )

            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"RRF fusion latency: {latency_ms:.2f} ms "
                f"(dense={len(dense_results)}, sparse={len(sparse_results)}, top={len(results)})"
            )
            logger.info(f"Top {len(results)} results: {[r['id'] for r in results]}")
            return results

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"RRF fusion failed after {latency_ms:.2f} ms: {e}",
                exc_info=True,
            )
            traceback.print_exc()
            return [{"error": str(e)}]

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean extracted text by normalizing whitespace, removing noise, and fixing encoding issues."""
        if not text:
            return ""

        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
        text = text.replace("–", "-").replace("—", "-")
        text = text.replace("“", '"').replace("”", '"').replace("’", "'")

        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n\n...[TRUNCATED]..."

        return text.strip()

    @staticmethod
    def clean_field_name(name: str) -> str:
        import re

        """Convert field names to safe Qdrant-compatible keys."""
        name = re.sub(
            r"[^\w]", "_", name.strip()
        )  # Replace spaces/symbols with underscores
        name = re.sub(r"_+", "_", name)  # Collapse multiple underscores
        return name.strip("_")

    @staticmethod
    def clean_text_for_payload(value) -> str:
        """Normalize text values for payload."""
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def flatten_field(value):
        if value is None:
            return None
        if isinstance(value, list):
            if not value:
                return None
            return "; ".join(map(str, value))
        if isinstance(value, str):
            if not value:
                return None
            return value.strip() or None
        return value
