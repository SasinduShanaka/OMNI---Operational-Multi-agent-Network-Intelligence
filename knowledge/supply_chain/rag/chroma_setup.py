"""
chroma_setup.py
Reads the 3 PDF supplier contracts and indexes them into a local
ChromaDB vector store for use by Agent 1 (Sourcing & RAG Compliance).

Run once after create_contracts.py:
    python knowledge/rag/chroma_setup.py
"""

import os
import sys
from pathlib import Path

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

RAG_DIR      = Path(__file__).parent
CONTRACTS_DIR = RAG_DIR.parent / "contracts"
CHROMA_DIR   = RAG_DIR / "chroma_store"

# ------------------------------------------------------------------
# PDF → Text extraction
# ------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


# ------------------------------------------------------------------
# Contract → supplier name mapping
# ------------------------------------------------------------------

CONTRACT_SUPPLIER_MAP = {
    "ecoweave_contract.pdf":       "EcoWeave Bangladesh",
    "textiles_lanka_contract.pdf": "Textiles Lanka",
    "zipper_king_contract.pdf":    "Zipper King China",
}


# ------------------------------------------------------------------
# Build ChromaDB collection
# ------------------------------------------------------------------

def build_chroma_store():
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    print("Initializing ChromaDB...")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Drop and recreate collection for a clean build
    try:
        client.delete_collection("supplier_contracts")
    except Exception:
        pass

    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    collection = client.create_collection(
        name="supplier_contracts",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )

    documents = []
    metadatas = []
    ids = []

    for pdf_file, supplier_name in CONTRACT_SUPPLIER_MAP.items():
        pdf_path = CONTRACTS_DIR / pdf_file

        if not pdf_path.exists():
            print(f"  WARNING: {pdf_file} not found — skipping.")
            continue

        text = extract_text_from_pdf(pdf_path)

        # Split into ~500-char chunks with 50-char overlap
        chunk_size = 500
        overlap    = 50
        chunks     = []
        start      = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start += chunk_size - overlap

        for i, chunk in enumerate(chunks):
            chunk_id = f"{supplier_name.lower().replace(' ', '_')}_{i}"
            documents.append(chunk)
            metadatas.append({"supplier_name": supplier_name, "source": pdf_file})
            ids.append(chunk_id)

        print(f"  Indexed {len(chunks)} chunks from: {pdf_file} ({supplier_name})")

    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print(f"\nChromaDB store built at: {CHROMA_DIR}")
    print(f"Total chunks indexed: {len(documents)}")
    return collection


# ------------------------------------------------------------------
# Query helper (used by sourcing_agent.py)
# ------------------------------------------------------------------

def get_collection():
    """Return the persisted ChromaDB collection."""
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_collection(
        name="supplier_contracts",
        embedding_function=embedding_fn
    )


def check_supplier_compliance(
    supplier_name: str,
    keywords: list[str],
    n_results: int = 5
) -> dict:
    """
    Query ChromaDB for a supplier's contract and check if it
    contains all required compliance keywords.

    Returns:
        {
            "compliant": bool,
            "matched_keywords": list[str],
            "missing_keywords": list[str],
            "proof_excerpt": str   # first matching chunk
        }
    """
    collection = get_collection()

    matched  = []
    missing  = []
    excerpts = []

    for keyword in keywords:
        results = collection.query(
            query_texts=[keyword],
            n_results=n_results,
            where={"supplier_name": supplier_name}
        )

        docs = results.get("documents", [[]])[0]
        found = any(keyword.lower() in doc.lower() for doc in docs)

        if found:
            matched.append(keyword)
            # Keep the most relevant excerpt
            for doc in docs:
                if keyword.lower() in doc.lower():
                    excerpts.append(doc[:300])
                    break
        else:
            missing.append(keyword)

    return {
        "compliant":        len(missing) == 0,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "proof_excerpt":    excerpts[0] if excerpts else "",
    }


if __name__ == "__main__":
    build_chroma_store()
