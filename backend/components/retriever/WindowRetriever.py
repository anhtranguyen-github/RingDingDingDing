from backend.components.interfaces import Retriever
from backend.components.types import InputConfig
from typing import List, Dict, Optional, Any

class WindowRetriever(Retriever):
    """
    WindowRetriever that retrieves chunks and their surrounding context depending on the window size.
    Supports multiple vector databases.
    """

    def __init__(self):
        super().__init__()
        self.description = "Retrieve relevant chunks from Vector Database"
        self.name = "Advanced"

        self.config["Search Mode"] = InputConfig(
            type="dropdown",
            value="Hybrid Search",
            description="Switch between search types.",
            values=["Hybrid Search"],
        )
        self.config["Limit Mode"] = InputConfig(
            type="dropdown",
            value="Autocut",
            description="Method for limiting the results. Autocut decides automatically how many chunks to retrieve, while fixed sets a fixed limit.",
            values=["Autocut", "Fixed"],
        )
        self.config["Limit/Sensitivity"] = InputConfig(
            type="number",
            value=1,
            description="Value for limiting the results. Value controls Autocut sensitivity and Fixed Size",
            values=[],
        )
        self.config["Chunk Window"] = InputConfig(
            type="number",
            value=1,
            description="Number of surrounding chunks of retrieved chunks to add to context",
            values=[],
        )
        self.config["Threshold"] = InputConfig(
            type="number",
            value=80,
            description="Threshold of chunk score to apply window technique (1-100)",
            values=[],
        )

    async def retrieve(
        self,
        query: str,
        vector: List[float],
        config: Dict[str, InputConfig],
        vector_db_manager: Any,  # Generic vector database manager
        embedder: Any,
        labels: Optional[List[str]] = None,
        document_uuids: Optional[List[str]] = None,
    ):
        """
        Retrieve chunks from the vector database using the specified configuration.
        """
        search_mode = config["Search Mode"].value
        limit_mode = config["Limit Mode"].value
        limit = int(config["Limit/Sensitivity"].value)

        window = max(0, min(10, int(config["Chunk Window"].value)))
        window_threshold = max(0, min(100, int(config["Threshold"].value)))
        window_threshold /= 100

        # Perform search based on the search mode
        if search_mode == "Hybrid Search":
            chunks = await vector_db_manager.hybrid_chunks(
                query, vector, limit_mode, limit, labels, document_uuids
            )
        # TODO: Add other search methods (e.g., vector search, keyword search)

        if len(chunks) == 0:
            return ([], "We couldn't find any chunks to the query")

        # Group chunks by document and sum scores
        doc_map = {}
        scores = [0]
        for chunk in chunks:
            if chunk["doc_uuid"] not in doc_map:
                document = await vector_db_manager.get_document(chunk["doc_uuid"])
                if document is None:
                    continue
                doc_map[chunk["doc_uuid"]] = {
                    "title": document["title"],
                    "chunks": [],
                    "score": 0,
                    "metadata": document["metadata"],
                }
            doc_map[chunk["doc_uuid"]]["chunks"].append(
                {
                    "uuid": str(chunk["uuid"]),
                    "score": chunk["score"],
                    "chunk_id": chunk["chunk_id"],
                    "content": chunk["content"],
                }
            )
            doc_map[chunk["doc_uuid"]]["score"] += chunk["score"]
            scores.append(chunk["score"])
        min_score = min(scores)
        max_score = max(scores)

        def normalize_value(value, max_value, min_value):
            return (value - min_value) / (max_value - min_value)

        def generate_window_list(value, window):
            value = int(value)
            window = int(window)
            return [i for i in range(value - window, value + window + 1) if i != value]

        documents = []
        context_documents = []

        for doc in doc_map:
            additional_chunk_ids = []
            chunks_above_threshold = 0
            for chunk in doc_map[doc]["chunks"]:
                normalized_score = normalize_value(
                    float(chunk["score"]), float(max_score), float(min_score)
                )
                if window_threshold <= normalized_score:
                    chunks_above_threshold += 1
                    additional_chunk_ids += generate_window_list(
                        chunk["chunk_id"], window
                    )
            unique_chunk_ids = set(additional_chunk_ids)

            if len(unique_chunk_ids) > 0:
                additional_chunks = await vector_db_manager.get_chunk_by_ids(
                    doc, unique_chunk_ids
                )
                existing_chunk_ids = set(
                    chunk["chunk_id"] for chunk in doc_map[doc]["chunks"]
                )
                for chunk in additional_chunks:
                    if chunk["chunk_id"] not in existing_chunk_ids:
                        doc_map[doc]["chunks"].append(
                            {
                                "uuid": str(chunk["uuid"]),
                                "score": 0,
                                "chunk_id": chunk["chunk_id"],
                                "content": chunk["content"],
                            }
                        )
                        existing_chunk_ids.add(chunk["chunk_id"])

            _chunks = [
                {
                    "uuid": str(chunk["uuid"]),
                    "score": chunk["score"],
                    "chunk_id": chunk["chunk_id"],
                    "embedder": embedder,
                }
                for chunk in doc_map[doc]["chunks"]
            ]
            context_chunks = [
                {
                    "uuid": str(chunk["uuid"]),
                    "score": chunk["score"],
                    "content": chunk["content"],
                    "chunk_id": chunk["chunk_id"],
                    "embedder": embedder,
                }
                for chunk in doc_map[doc]["chunks"]
            ]
            _chunks_sorted = sorted(_chunks, key=lambda x: x["chunk_id"])
            context_chunks_sorted = sorted(context_chunks, key=lambda x: x["chunk_id"])

            documents.append(
                {
                    "title": doc_map[doc]["title"],
                    "chunks": _chunks_sorted,
                    "score": doc_map[doc]["score"],
                    "metadata": doc_map[doc]["metadata"],
                    "uuid": str(doc),
                }
            )

            context_documents.append(
                {
                    "title": doc_map[doc]["title"],
                    "chunks": context_chunks_sorted,
                    "score": doc_map[doc]["score"],
                    "uuid": str(doc),
                    "metadata": doc_map[doc]["metadata"],
                }
            )

        sorted_context_documents = sorted(
            context_documents, key=lambda x: x["score"], reverse=True
        )
        sorted_documents = sorted(documents, key=lambda x: x["score"], reverse=True)

        context = self.combine_context(sorted_context_documents)
        return (sorted_documents, context)

    def combine_context(self, documents: List[Dict]) -> str:
        context = ""

        for document in documents:
            context += f"Document Title: {document['title']}\n"
            if len(document["metadata"]) > 0:
                context += f"Document Metadata: {document['metadata']}\n"
            for chunk in document["chunks"]:
                context += f"Chunk: {int(chunk['chunk_id'])+1}\n"
                if chunk["score"] > 0:
                    context += f"High Relevancy: {chunk['score']:.2f}\n"
                context += f"{chunk['content']}\n"
            context += "\n\n"

        return context