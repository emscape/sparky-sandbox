"""Utility functions for the AI memory system."""

from typing import List
from openai import AsyncOpenAI
from config import config

async def get_embedding(text: str, client: AsyncOpenAI) -> List[float]:
    """Generate embedding for a given text."""
    text = text.strip()
    try:
        response = await client.embeddings.create(
            model=config.embedding_model,
            input=[text],
            encoding_format="float",
            dimensions=config.embedding_dimensions
        )
        return response.data[0].embedding
    except Exception as e:
        raise RuntimeError(f"Failed to get embedding: {e}")