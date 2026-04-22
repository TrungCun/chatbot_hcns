# import time
# import uuid
# from typing import Any, Dict, List, Optional, Tuple

# from qdrant_client import QdrantClient, models
# from qdrant_client.models import QueryResponse

# from app import get_logger

# from .embed import EmbedTools
# from .helper import HelperTools
# from .redis import RedisTools

# QDRANT_URL = RedisTools.get_config("qdrant").get("QDRANT_URL")
# QDRANT_API_KEY = RedisTools.get_config("qdrant").get("QDRANT_API_KEY")

# client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, port=6333, https=False)

# logger = get_logger(__name__)


# class QdrantTools:
#     @staticmethod
#     def create_collection(collection_name: str) -> None:
#         if not client.collection_exists(collection_name=collection_name):
#             client.create_collection(
#                 collection_name=collection_name,
#                 vectors_config={
#                     "dense-embedding": models.VectorParams(
#                         size=EmbedTools.get_embedding_dimension(),
#                         distance=models.Distance.COSINE,
#                     )
#                 },
#                 sparse_vectors_config={
#                     "sparse-embedding": models.SparseVectorParams(
#                         index=models.SparseIndexParams(on_disk=False)
#                     )
#                 },
#             )

#     @staticmethod
#     def add_vectors(
#         collection_name: str,
#         dense_vectors: List[List[float]],
#         sparse_vectors: List[Tuple[List[int], List[float]]],
#         grants_data: List[dict],
#     ) -> None:
#         if not (len(dense_vectors) == len(sparse_vectors) == len(grants_data)):
#             raise ValueError(
#                 "Lengths of dense_vectors, sparse_vectors, and grants_data must match."
#             )

#         QdrantTools.create_collection(collection_name)

#         points = []

#         for dense_vector, (indices, values), grant in zip(
#             dense_vectors, sparse_vectors, grants_data
#         ):
#             payload = {}
#             for key, value in grant.items():
#                 cleaned_key = HelperTools.clean_field_name(key)
#                 cleaned_value = HelperTools.clean_text_for_payload(value)
#                 payload[cleaned_key] = cleaned_value

#             description = " ".join(
#                 str(v) for v in payload.values() if isinstance(v, str)
#             )
#             payload["description"] = description.strip()

#             points.append(
#                 models.PointStruct(
#                     id=str(uuid.uuid4()),
#                     vector={
#                         "dense-embedding": dense_vector,
#                         "sparse-embedding": models.SparseVector(
#                             indices=indices, values=values
#                         ),
#                     },
#                     payload=payload,
#                 )
#             )

#         client.upsert(collection_name=collection_name, points=points, wait=True)

#         for field_name in payload.keys():
#             try:
#                 client.create_payload_index(
#                     collection_name=collection_name,
#                     field_name=field_name,
#                     field_schema=models.PayloadSchemaType.TEXT,
#                 )
#             except Exception as e:
#                 print(f"Skipped index for {field_name}: {e}")

#     @staticmethod
#     def retrieve(
#         collection_name: str,
#         query: List[float],
#         query_indices: List[int],
#         query_values: List[float],
#         limit: int,
#         filters: dict = None,
#     ) -> List[QueryResponse]:
#         grant_filter = None
#         if filters:
#             should_conditions = []
#             for field, values in filters.items():
#                 field_conditions = [
#                     models.FieldCondition(key=field, match=models.MatchText(text=v))
#                     for v in values
#                 ]
#                 should_conditions.append(models.Filter(should=field_conditions))
#             grant_filter = models.Filter(should=should_conditions)

#         search_result = client.query_batch_points(
#             collection_name=collection_name,
#             requests=[
#                 models.QueryRequest(
#                     query=query,
#                     using="dense-embedding",
#                     limit=limit,
#                     with_payload=True,
#                     filter=grant_filter,
#                 ),
#                 models.QueryRequest(
#                     query=models.SparseVector(
#                         indices=query_indices,
#                         values=query_values,
#                     ),
#                     using="sparse-embedding",
#                     limit=limit,
#                     with_payload=True,
#                     filter=grant_filter,
#                 ),
#             ],
#         )

#         return search_result

#     @staticmethod
#     def get_all_grant_ids(collection_name: str) -> List[str]:
#         try:
#             QdrantTools.create_collection(collection_name)

#             all_ids = []
#             next_page = None
#             while True:
#                 scroll_result, next_page = client.scroll(
#                     collection_name=collection_name,
#                     with_payload=True,
#                     with_vectors=False,
#                     offset=next_page,
#                     limit=100,
#                 )

#                 for point in scroll_result:
#                     grant_id = point.payload.get("id")
#                     if grant_id:
#                         all_ids.append(grant_id)

#                 if not next_page:
#                     break
#             logger.info(f"Ids from collection '{collection_name}': {all_ids}")
#             return all_ids
#         except Exception as e:
#             logger.info(f"Error getting ids from collection '{collection_name}': {e}")

#     @staticmethod
#     def delete_grants_by_ids(collection_name: str, ids: List[str]) -> int:
#         if not ids:
#             logger.warning("No grant IDs provided for deletion.")
#             return []

#         try:
#             before = set(QdrantTools.get_all_grant_ids(collection_name=collection_name))

#             id_filter = models.Filter(
#                 should=[
#                     models.FieldCondition(
#                         key="id", match=models.MatchText(text=grant_id)
#                     )
#                     for grant_id in ids
#                 ]
#             )

#             client.delete(
#                 collection_name=collection_name,
#                 points_selector=models.FilterSelector(filter=id_filter),
#                 wait=True,
#             )

#             after = set(QdrantTools.get_all_grant_ids(collection_name=collection_name))

#             deleted_ids = list(before - after)

#             logger.info(
#                 f"Deleted {len(deleted_ids)} grants from '{collection_name}' successfully."
#             )
#             logger.debug(f"Deleted grant IDs: {deleted_ids}")

#             return deleted_ids

#         except Exception as e:
#             logger.exception(f"Error deleting grants from '{collection_name}': {e}")
#             return []

#     @staticmethod
#     def get_grants_by_ids(
#         collection_name: str,
#         ids: List[str],
#         reasonings: List[str],
#         confidence_scores: List[float],
#         cosine_similarity_scores: List[float],
#     ) -> List[Dict[str, Any]]:
#         start_time = time.perf_counter()

#         try:
#             if not ids:
#                 return []

#             if not (
#                 len(ids)
#                 == len(reasonings)
#                 == len(confidence_scores)
#                 == len(cosine_similarity_scores)
#             ):
#                 raise ValueError("List lengths must match.")

#             QdrantTools.create_collection(collection_name)

#             # Create maps
#             reasoning_map = dict(zip(ids, reasonings))
#             confidence_map = dict(zip(ids, confidence_scores))
#             cosine_map = dict(zip(ids, cosine_similarity_scores))

#             # Build OR filter
#             id_filter = models.Filter(
#                 should=[
#                     models.FieldCondition(
#                         key="id", match=models.MatchText(text=str(grant_id))
#                     )
#                     for grant_id in ids
#                 ]
#             )

#             # SCAN QDRANT
#             grants = []
#             next_page = None

#             while True:
#                 results, next_page = client.scroll(
#                     collection_name=collection_name,
#                     with_payload=True,
#                     with_vectors=False,
#                     offset=next_page,
#                     limit=100,
#                     scroll_filter=id_filter,
#                 )

#                 for point in results:
#                     payload = dict(point.payload)

#                     gid = str(payload.get("id"))  # normalize ID to string

#                     payload.pop("description", None)
#                     payload["reasoning"] = reasoning_map.get(gid, "")
#                     payload["confidence_score"] = confidence_map.get(gid, 0)
#                     payload["cosine_score"] = cosine_map.get(gid, 0)

#                     grants.append(payload)

#                 if not next_page:
#                     break

#             # Sort AFTER population
#             grants.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)

#             return grants

#         except Exception as e:
#             logger.exception(f"Error retrieving grants: {e}")
#             return []

#         finally:
#             elapsed = (time.perf_counter() - start_time) * 1000
#             logger.info(f"get_grants_by_ids took {elapsed:.2f} ms")

#     @staticmethod
#     def find_grant_by_id(
#         collection_name: str, grant_id: str
#     ) -> Optional[Dict[str, Any]]:
#         """
#         Look up a single grant by its payload ID field.
#         Returns the payload (dict) or None if not found.
#         """
#         try:
#             id_filter = models.Filter(
#                 must=[
#                     models.FieldCondition(
#                         key="id", match=models.MatchText(text=str(grant_id))
#                     )
#                 ]
#             )

#             next_page = None
#             while True:
#                 points, next_page = client.scroll(
#                     collection_name=collection_name,
#                     with_payload=True,
#                     with_vectors=False,
#                     offset=next_page,
#                     limit=100,
#                     scroll_filter=id_filter,
#                 )

#                 for point in points:
#                     return dict(point.payload)

#                 if not next_page:
#                     break

#             return None

#         except Exception as e:
#             logger.error(f"Error finding grant id={grant_id}: {e}")
#             return None
