"""Build and persist the chunk-level retrieval indexes.

Chunks every filtered PredEx judgment, embeds with both embedders
(MiniLM primary, InLegalBERT comparison arm), and writes to index/:

    chunks.parquet   chunk_id, doc_id, chunk_pos, text
    docs.parquet     doc_id, case_name, label, issue_area,
                     expert_explanation, text (full judgment)
    minilm.faiss / inlegalbert.faiss
    manifest.json    corpus counts, models, chunk parameters

Deterministic given the corpus snapshot. Run from the repo root:

    python -m src.retrieve.build_index
"""

from __future__ import annotations

import json
from pathlib import Path

import faiss
import pandas as pd

from src.retrieve.corpus import build_filtered_corpus
from src.retrieve.embed import CHUNK_OVERLAP, CHUNK_WORDS, EMBEDDERS, chunk_words

INDEX_DIR = Path("index")


def build_chunks(docs: pd.DataFrame) -> pd.DataFrame:
    """Explode documents into overlapping chunks with stable ids."""
    rows: list[dict] = []
    for doc in docs.itertuples(index=False):
        for pos, chunk in enumerate(chunk_words(doc.text)):
            rows.append(
                {
                    "chunk_id": f"{doc.doc_id}-c{pos}",
                    "doc_id": doc.doc_id,
                    "chunk_pos": pos,
                    "text": chunk,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    """Build the corpus, chunk it, embed with both models, persist all."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    docs = build_filtered_corpus()
    chunks = build_chunks(docs)
    print(f"docs: {len(docs)}, chunks: {len(chunks)}")

    docs.to_parquet(INDEX_DIR / "docs.parquet", index=False)
    chunks.to_parquet(INDEX_DIR / "chunks.parquet", index=False)

    dims: dict[str, int] = {}
    for name, embedder in EMBEDDERS.items():
        print(f"embedding with {name}...")
        vectors = embedder(chunks["text"].tolist())
        dims[name] = vectors.shape[1]
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        faiss.write_index(index, str(INDEX_DIR / f"{name}.faiss"))
        print(f"  {name}: {index.ntotal} vectors, dim {vectors.shape[1]}")

    manifest = {
        "corpus": "L-NLProc/PredEx (official)",
        "coverage_note": (
            "Supreme Court appellate judgments only; consumer-forum and "
            "rent-court level outcomes are not in this corpus"
        ),
        "n_docs": len(docs),
        "n_chunks": len(chunks),
        "per_area": docs["issue_area"].value_counts().to_dict(),
        "chunk_words": CHUNK_WORDS,
        "chunk_overlap": CHUNK_OVERLAP,
        "embedders": {
            "minilm": "sentence-transformers/all-MiniLM-L6-v2",
            "inlegalbert": "law-ai/InLegalBERT mean-pooled (comparison arm)",
        },
        "dims": dims,
    }
    (INDEX_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("wrote manifest:", json.dumps(manifest["per_area"]))


if __name__ == "__main__":
    main()
