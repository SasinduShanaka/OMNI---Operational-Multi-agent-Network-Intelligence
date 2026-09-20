"""
retriever.py
Shared retrieval layer for the OMNI knowledge corpora.

One ChromaDB collection per corpus, one embedding model loaded once
for the whole process. Agents call search() and get back chunks that
carry enough metadata to cite the source clause.

Build or rebuild the indexes with:
    python knowledge/build_index.py
"""

import os
import re
from pathlib import Path


# ============================================================
# PATHS AND CONFIGURATION
# ============================================================

KNOWLEDGE_DIR = Path(__file__).parent
CHROMA_DIR    = KNOWLEDGE_DIR / "chroma_store"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Chunks are sized to hold a whole procedure step or paragraph.
# Larger than the 500 chars used for contracts because SOP clauses
# lose their meaning when the conditions are split from the rule.
CHUNK_SIZE    = 900
CHUNK_OVERLAP = 150


# Registry of corpora. Adding a corpus means adding an entry here
# and dropping markdown files into its folder.

CORPORA = {
    "production_sops": {
        "path":        KNOWLEDGE_DIR / "production" / "sop",
        "description": "Standard operating procedures and quality manuals for the production floor",
    },
    "market_context": {
        "path":        KNOWLEDGE_DIR / "market",
        "description": "Buyer calendars, promotion plans and market notes behind demand movements",
    },
}


# ============================================================
# EMBEDDING FUNCTION — loaded once per process
# ============================================================

_client = None
_embedding_fn = None


def _get_embedding_fn():
    """
    The sentence-transformer model takes seconds to load, so it is
    cached at module level. Loading it per query was what made the
    supplier compliance check so slow.
    """

    global _embedding_fn

    if _embedding_fn is None:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        _embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

    return _embedding_fn


def _get_client():

    global _client

    if _client is None:
        import chromadb
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    return _client


# ============================================================
# DOCUMENT PARSING
# ============================================================

def parse_document(path: Path) -> dict:
    """
    Read a markdown document with a simple `key: value` front matter
    block delimited by `---`. Everything after the block is body text.
    """

    raw = path.read_text(encoding="utf-8")

    front_matter = {}
    body = raw

    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            for line in raw[3:end].strip().splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    front_matter[key.strip()] = value.strip()
            body = raw[end + 3:].lstrip()

    # The H1 repeats the title from the front matter; drop it so it does
    # not land inside the first section's text.
    if body.startswith("# "):
        body = body.split("\n", 1)[1].lstrip() if "\n" in body else ""

    return {"front_matter": front_matter, "body": body, "filename": path.name}


def split_into_sections(body: str) -> list[tuple[str, str]]:
    """
    Split on markdown `##` headings so a chunk never merges two
    unrelated procedures. Returns (section_title, section_text).
    """

    sections = []
    current_title = "Overview"
    current_lines = []

    for line in body.splitlines():

        if line.startswith("## "):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    return [(title, text) for title, text in sections if text]


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Size-bounded chunks that break on a sentence or line boundary
    rather than mid-word, so a retrieved excerpt can be quoted as-is.
    """

    text = text.strip()

    if len(text) <= size:
        return [text] if text else []

    chunks = []
    start = 0

    while start < len(text):

        end = min(start + size, len(text))

        if end < len(text):
            # Prefer a paragraph break, then a sentence end, then a space.
            window = text[start:end]
            for marker in ("\n\n", ". ", "\n", " "):
                cut = window.rfind(marker)
                if cut > size * 0.5:
                    end = start + cut + len(marker)
                    break

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return chunks


# ============================================================
# PDF EXTRACTION
# ------------------------------------------------------------
# The markdown is the source of truth for metadata; the PDF is
# what gets indexed, so retrieval runs on the same kind of
# document as the supplier contract corpus.
# ============================================================

def load_manifest(corpus_dir: Path) -> dict:
    """Section-to-page map written by render_pdfs.py."""

    manifest_path = corpus_dir / "pdf" / "manifest.json"

    if not manifest_path.exists():
        return {}

    import json
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def extract_pdf_sections(pdf_path: Path, section_titles: list[str]) -> list[tuple[str, str]]:
    """
    Read a rendered PDF and slice its text back into sections using
    the headings we know it was rendered with.

    Returns [(section_title, section_text)] in document order.
    """

    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    # Locate each heading in the extracted text; PDF extraction can
    # introduce line breaks, so match on a whitespace-tolerant pattern.
    positions = []

    for title in section_titles:
        pattern = re.compile(r"\s+".join(re.escape(word) for word in title.split()))
        match = pattern.search(text)
        if match:
            positions.append((match.start(), match.end(), title))

    positions.sort()

    sections = []

    for index, (start, end, title) in enumerate(positions):
        stop = positions[index + 1][0] if index + 1 < len(positions) else len(text)
        body = text[end:stop].strip()
        if body:
            sections.append((title, body))

    return sections


# ============================================================
# INDEXING
# ============================================================

def build_corpus(corpus: str, verbose: bool = True) -> int:
    """
    (Re)build one corpus from its markdown files. Returns the number
    of chunks indexed.
    """

    if corpus not in CORPORA:
        raise ValueError(f"Unknown corpus '{corpus}'. Known: {list(CORPORA)}")

    config = CORPORA[corpus]
    source_dir = config["path"]

    files = sorted(source_dir.glob("*.md"))

    if not files:
        raise FileNotFoundError(f"No markdown documents found in {source_dir}")

    client = _get_client()

    try:
        client.delete_collection(corpus)
    except Exception:
        pass

    collection = client.create_collection(
        name=corpus,
        embedding_function=_get_embedding_fn(),
        metadata={"hnsw:space": "cosine", "description": config["description"]},
    )

    documents, metadatas, ids = [], [], []

    manifest = load_manifest(source_dir)

    for path in files:

        parsed = parse_document(path)
        front = parsed["front_matter"]
        doc_id = front.get("doc_id", path.stem)

        md_sections = split_into_sections(parsed["body"])
        section_titles = [title for title, _ in md_sections]

        # Index the rendered PDF when one exists, falling back to the
        # markdown body if it has not been rendered yet.
        entry = manifest.get(path.name)
        pdf_path = (source_dir / "pdf" / entry["pdf"]) if entry else None
        page_map = entry.get("pages", {}) if entry else {}

        if pdf_path and pdf_path.exists():
            sections = extract_pdf_sections(pdf_path, section_titles) or md_sections
            source_name = pdf_path.name
        else:
            sections = md_sections
            source_name = path.name

        chunk_index = 0

        for section_title, section_text in sections:

            for chunk in chunk_text(section_text):

                # The heading travels with the chunk so the embedding
                # carries the context the body text assumes.
                embedded_text = f"{front.get('title', doc_id)} — {section_title}\n{chunk}"

                metadata = {
                    "doc_id":   doc_id,
                    "title":    front.get("title", doc_id),
                    "section":  section_title,
                    "source":   source_name,
                    "doc_type": front.get("doc_type", "document"),
                }

                if page_map.get(section_title):
                    metadata["page"] = page_map[section_title]

                # Optional scoping fields — only set when present, so
                # a `where` filter on them stays meaningful.
                for key in ("sku", "skus", "buyer", "category", "line_id", "effective_date"):
                    if front.get(key):
                        metadata[key] = front[key]

                documents.append(embedded_text)
                metadatas.append(metadata)
                ids.append(f"{doc_id}_{chunk_index}")
                chunk_index += 1

        if verbose:
            print(f"  {path.name}: {chunk_index} chunks")

    collection.add(documents=documents, metadatas=metadatas, ids=ids)

    if verbose:
        print(f"  -> collection '{corpus}': {len(documents)} chunks from {len(files)} documents")

    return len(documents)


def get_collection(corpus: str, auto_build: bool = True):
    """
    Return a corpus collection, building it on first use when the
    store is empty. This is what stops a missing index from silently
    degrading an agent's answer.
    """

    client = _get_client()

    try:
        return client.get_collection(name=corpus, embedding_function=_get_embedding_fn())

    except Exception:

        if not auto_build:
            raise

        print(f"[retriever] Collection '{corpus}' missing — building it now.")
        build_corpus(corpus, verbose=False)
        return client.get_collection(name=corpus, embedding_function=_get_embedding_fn())


# ============================================================
# SEARCH
# ============================================================

def search(
    query: str,
    corpus: str,
    filters: dict | None = None,
    k: int = 4,
    max_distance: float | None = 0.85,
) -> list[dict]:
    """
    Retrieve the passages most relevant to `query`.

    filters      -- metadata equality filters, e.g. {"sku": "GAR-001"}
    max_distance -- drop weak matches; cosine distance, lower is closer.
                    Without this the store always returns k results
                    however unrelated they are.

    Returns a list of {text, score, doc_id, title, section, source, ...}.
    """

    if not query or not query.strip():
        return []

    collection = get_collection(corpus)

    where = None

    if filters:
        clean = {key: value for key, value in filters.items() if value}
        if len(clean) == 1:
            where = clean
        elif len(clean) > 1:
            where = {"$and": [{key: value} for key, value in clean.items()]}

    results = collection.query(
        query_texts=[query],
        n_results=k,
        where=where,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    passages = []

    for text, metadata, distance in zip(documents, metadatas, distances):

        if max_distance is not None and distance > max_distance:
            continue

        # The heading prefix was added to give the embedding context;
        # strip it so the passage can be quoted as written.
        prefix = f"{metadata.get('title', '')} — {metadata.get('section', '')}\n"
        body = text[len(prefix):] if text.startswith(prefix) else text

        passages.append({
            "text":     body.strip(),
            "score":    round(1 - distance, 3),
            "distance": round(distance, 3),
            **metadata,
        })

    return passages


def summarise(passage: dict, limit: int = 220) -> str:
    """
    Trim a passage to a quotable sentence or two, breaking on a
    sentence end rather than mid-word.
    """

    text = " ".join(passage.get("text", "").split())

    if len(text) <= limit:
        return text

    window = text[:limit]
    cut = max(window.rfind(". "), window.rfind("; "))

    if cut > limit * 0.4:
        return window[:cut + 1]

    return window.rsplit(" ", 1)[0] + "…"


def cite(passage: dict) -> str:
    """Render a passage as a short human-readable citation."""

    reference = passage.get("doc_id", "document")

    if passage.get("page"):
        reference += f" p.{passage['page']}"

    section = passage.get("section")

    return f"{reference} § {section}" if section else reference


# ============================================================
# STATUS
# ============================================================

def index_status() -> dict:
    """Report what is indexed — used by the build script and tests."""

    status = {}

    for corpus in CORPORA:
        try:
            collection = _get_client().get_collection(
                name=corpus, embedding_function=_get_embedding_fn()
            )
            status[corpus] = {"indexed": True, "chunks": collection.count()}
        except Exception:
            status[corpus] = {"indexed": False, "chunks": 0}

    return status
