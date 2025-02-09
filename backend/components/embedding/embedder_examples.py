


import asyncio
from backend.components.embedding.SentenceTransformersEmbedder import SentenceTransformersEmbedder
from backend.components.types import InputConfig
from sentence_transformers import SentenceTransformer

async def run_embedder_example():
    # Initialize the SentenceTransformersEmbedder
    embedder = SentenceTransformersEmbedder()

    # Sample text content to vectorize
    sample_texts = [
        "This is a sample text file content.",
        "SentenceTransformers are great for embedding text.",
        "HuggingFace provides many pre-trained models.",
    ]

    # Vectorize the text content
    if SentenceTransformer:
        config = {"Model": InputConfig(type="dropdown", value="all-MiniLM-L6-v2", description="", values=[])}
        embeddings = await embedder.vectorize(config, sample_texts)
        for i, embedding in enumerate(embeddings):
            print(f"Embedding for text {i + 1}: {embedding[:5]}...")  # Print first 5 dimensions for brevity
    else:
        msg.fail("sentence-transformers is not installed. Cannot perform embedding.")


# Run the example
asyncio.run(run_embedder_example())