import os
import math
from dotenv import load_dotenv

from services.openai_http_client import create_embedding

load_dotenv()

EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def get_embedding(text: str):
    if not text:
        text = ""
    return create_embedding(model=EMBEDDING_MODEL, text=text)


def cosine_similarity(vec1, vec2):
    if not vec1 or not vec2:
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot / (norm1 * norm2)
