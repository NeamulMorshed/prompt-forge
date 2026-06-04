from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams


@dataclass
class PatternPoint:
    id: str
    domain: str
    structure: str
    abstraction: str
    quality_score: float
    vector: list[float]


class QdrantPatternStore:
    def __init__(self, client: QdrantClient, collection: str = "patterns"):
        self._client = client
        self._collection = collection

    def ensure_collection(self, vector_size: int = 384) -> None:
        try:
            self._client.get_collection(self._collection)
        except Exception:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def upsert(self, points: list[PatternPoint]) -> None:
        self._client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(
                    id=abs(hash(p.id)) % (2**63),
                    vector=p.vector,
                    payload={
                        "pattern_id": p.id,
                        "domain": p.domain,
                        "structure": p.structure,
                        "abstraction": p.abstraction,
                        "quality_score": p.quality_score,
                    },
                )
                for p in points
            ],
        )

    def search(
        self,
        query_vector: list[float],
        domain: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        results = self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            query_filter=Filter(
                must=[FieldCondition(key="domain", match=MatchValue(value=domain))]
            ),
            limit=limit,
        )
        return [
            {**hit.payload, "score": hit.score}
            for hit in results
        ]


def build_store(url: str = "http://localhost:6333") -> QdrantPatternStore:
    client = QdrantClient(url=url)
    return QdrantPatternStore(client=client)
