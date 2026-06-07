# RAG PDF Extraction & Retrieval Pipeline

A production-grade pipeline for extracting content from PDF documents and building a RAG (Retrieval-Augmented Generation) system. Converts complex PDFs — with text, tables, images, formulas, and code — into clean Markdown/JSON, then chunks, embeds, and retrieves content using semantic search with reranking.

---

## Project Structure

```
├── extraction/                  # 📦 Stage 1: PDF Extraction
│   ├── docling_pipeline.py      #   Docling-only pipeline (fast, page-chunked)
│   ├── local_pdf_pipeline.py    #   Multi-layer pipeline (PyMuPDF + OCR + Vision)
│   └── merged_pipeline.py       #   Combined pipeline (Docling + fallback)
│
├── chunking/                    # 📦 Stage 2: Semantic Chunking
│   └── semantic_chunker.py      #   Heading-based semantic text chunker
│
├── embedding/                   # 📦 Stage 3: Vector Embedding
│   └── embedder.py              #   GTE multilingual embedding + ChromaDB
│
├── search/                      # 📦 Stage 4: Retrieval & Reranking
│   └── reranked_search.py       #   Two-stage search (vector + BGE reranker)
│
├── config/                      # ⚙️  Configuration
│   └── logo_hints.json          #   Logo detection heuristics
│
├── scripts/                     # 🛠️  Helper Scripts
│   └── process_content.ps1      #   Batch PDF processing (PowerShell)
│
├── docs/                        # 📖 Documentation
│   ├── technical_documentation.md
│   └── embedding_guide.md
│
├── content/                     # 📄 Input PDFs
│   └── *.pdf
│
└── data/                        # 📊 Generated Data (gitignored)
    ├── output/                  #   Extraction outputs (Markdown, JSON, reports)
    ├── chroma_db/               #   ChromaDB vector store
    └── reference_logos/         #   Detected logo images
```

---

## Pipeline Stages

### Stage 1: PDF Extraction
Three extraction approaches, each suited for different scenarios:

| Pipeline | Best For | Command |
|---|---|---|
| `docling_pipeline.py` | Speed, large PDFs, validation | `python -m extraction.docling_pipeline sample.pdf` |
| `local_pdf_pipeline.py` | Maximum content capture (images, vision) | `python -m extraction.local_pdf_pipeline sample.pdf` |
| `merged_pipeline.py` | Best of both (Docling + fallback OCR) | `python -m extraction.merged_pipeline sample.pdf` |

### Stage 2: Semantic Chunking
```bash
python -m chunking.semantic_chunker "data/output/Python Session 1.md"
```

### Stage 3: Embedding
```bash
python -m embedding.embedder "data/output/Python Session 1.md"
```

### Stage 4: Search
```bash
python -m search.reranked_search "why is Python popular?"
```

---

## Requirements

- Python 3.10+
- Core: `pip install docling pymupdf pillow tiktoken langchain-text-splitters`
- Embedding: `pip install chromadb sentence-transformers`
- Optional: `pip install easyocr paddleocr ollama`

### External Services (Optional)
- **Ollama** at `http://localhost:11434` for vision/LLM features
- GPU recommended for faster model inference

---

## Quick Start

```bash
# 1. Extract PDF content
python -m extraction.docling_pipeline "content/Math_Session_1.pdf"

# 2. Chunk the output
python -m chunking.semantic_chunker "data/output/Math_Session_1.md"

# 3. Embed chunks into ChromaDB
python -m embedding.embedder "data/output/Math_Session_1.md"

# 4. Search
python -m search.reranked_search "matrix multiplication"
```

---

## Documentation

- [Technical Documentation](docs/technical_documentation.md) — Full architecture, stage details, and API reference
- [Embedding Guide](docs/embedding_guide.md) — Model choices, challenges, and implementation deep-dive