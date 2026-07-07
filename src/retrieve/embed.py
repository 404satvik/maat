"""Chunking and embedding for judgment retrieval.

Judgments are long, so documents are split into overlapping word chunks;
retrieval happens at chunk level and aggregates to documents by max
chunk score. Two embedders: MiniLM (primary, trained for similarity)
and InLegalBERT mean-pooled (domain-matched comparison arm; the 3d eval
decides which is used going forward).
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

MINILM = "sentence-transformers/all-MiniLM-L6-v2"
INLEGALBERT = "law-ai/InLegalBERT"
CHUNK_WORDS = 200
CHUNK_OVERLAP = 40


def chunk_words(text: str, size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks of roughly size words."""
    words = text.split()
    if len(words) <= size:
        return [" ".join(words)]
    chunks: list[str] = []
    step = size - overlap
    for start in range(0, len(words), step):
        piece = words[start : start + size]
        if len(piece) < overlap and chunks:
            break
        chunks.append(" ".join(piece))
    return chunks


@lru_cache(maxsize=1)
def _minilm_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MINILM)


@lru_cache(maxsize=1)
def _inlegalbert_model():
    from transformers import AutoModel, AutoTokenizer

    from src.intake.transformer import pick_device

    device = pick_device()
    tokenizer = AutoTokenizer.from_pretrained(INLEGALBERT)
    model = AutoModel.from_pretrained(INLEGALBERT).to(device)
    model.eval()
    return tokenizer, model, device


def embed_minilm(texts: list[str], batch_size: int = 64) -> np.ndarray:
    """L2-normalized MiniLM sentence embeddings."""
    model = _minilm_model()
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vectors.astype(np.float32)


def embed_inlegalbert(texts: list[str], batch_size: int = 16, max_length: int = 256) -> np.ndarray:
    """L2-normalized mean-pooled InLegalBERT embeddings."""
    import torch

    tokenizer, model, device = _inlegalbert_model()
    out: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(texts), batch_size):
            batch = tokenizer(
                texts[start : start + batch_size],
                truncation=True,
                max_length=max_length,
                padding=True,
                return_tensors="pt",
            ).to(device)
            hidden = model(**batch).last_hidden_state
            mask = batch["attention_mask"].unsqueeze(-1).float()
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
            out.append(pooled.cpu().numpy())
    vectors = np.vstack(out).astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.clip(norms, 1e-9, None)


EMBEDDERS = {"minilm": embed_minilm, "inlegalbert": embed_inlegalbert}
