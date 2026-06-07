# Raaed Graduation Project

A production-grade RAG (Retrieval-Augmented Generation) pipeline for extracting content from PDF documents, processing them with semantic chunking, embedding into vector stores, and retrieving relevant content using two-stage search with reranking. Built with **FastAPI**, **MongoDB**, **ChromaDB**, and multilingual support (Arabic/English).

---

## 🏗️ Architecture

```
├── src/                             # 🚀 Main Application
│   ├── main.py                      #   FastAPI entry point
│   ├── controllers/                 #   Business logic layer
│   │   ├── DataController.py        #     File upload & data management
│   │   ├── NLPController.py         #     RAG search & answer generation
│   │   ├── ProcessController.py     #     PDF processing pipeline
│   │   └── ProjectController.py     #     Project CRUD operations
│   ├── routes/                      #   API endpoints
│   │   ├── base.py                  #     Health check & welcome
│   │   ├── data.py                  #     /api/v1/data/*
│   │   └── nlp.py                   #     /api/v1/nlp/*
│   ├── models/                      #   Data models & DB schemas
│   │   ├── db_schemes/              #     MongoDB document schemas
│   │   └── enums/                   #     Enum definitions
│   ├── stores/                      #   External service integrations
│   │   ├── llm/                     #     LLM providers (OpenAI, Cohere, Local)
│   │   └── vectordb/               #     Vector DB providers (ChromaDB, Qdrant)
│   ├── extraction/                  #   PDF extraction pipelines
│   │   ├── docling_pipeline.py      #     Docling-based extraction
│   │   ├── local_pdf_pipeline.py    #     PyMuPDF + OCR + Vision
│   │   └── merged_pipeline.py       #     Combined pipeline with fallback
│   ├── chunking/                    #   Semantic text chunking
│   ├── embedding/                   #   Vector embedding (GTE multilingual)
│   ├── search/                      #   Two-stage retrieval + BGE reranking
│   └── helpers/                     #   Configuration & utilities
│
├── pipeline_reference/              #   📖 Reference implementations & docs
│   ├── docs/                        #     Technical documentation
│   ├── extraction/                  #     Original extraction scripts
│   ├── chunking/                    #     Original chunking scripts
│   ├── embedding/                   #     Original embedding scripts
│   └── search/                      #     Original search scripts
│
├── requirements.txt                 #   Python dependencies
├── .env.example                     #   Environment variables template
└── LICENSE                          #   AGPL-3.0 License
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Gohar-Hany/Raaed-Graduation-Project.git
cd Raaed-Graduation-Project
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and database settings
```

### 3. Start MongoDB

```bash
mongod --dbpath ./mongodb_data
```

### 4. Run the Server

```bash
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

### 5. Access the API

- **Swagger UI**: http://localhost:5000/docs
- **Health Check**: http://localhost:5000/api/v1

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1` | Health check & welcome |
| `POST` | `/api/v1/data/upload/{project_id}` | Upload PDF file |
| `POST` | `/api/v1/data/process/{project_id}` | Process uploaded PDF (extract → chunk → embed) |
| `GET` | `/api/v1/nlp/search/{project_id}` | Semantic search with reranking |
| `GET` | `/api/v1/nlp/answer/{project_id}` | RAG-based question answering |

---

## 🔧 Pipeline Stages

### Stage 1: PDF Extraction
Three extraction approaches for different scenarios:

| Pipeline | Best For |
|----------|----------|
| **Docling** | Speed, large PDFs, structured content |
| **Local (PyMuPDF)** | Maximum content capture (images, OCR, vision) |
| **Merged** | Best of both with automatic fallback |

### Stage 2: Semantic Chunking
Heading-based semantic text splitting with configurable chunk sizes.

### Stage 3: Vector Embedding
GTE multilingual embedding model with ChromaDB or Qdrant vector storage.

### Stage 4: Retrieval & Reranking
Two-stage search: vector similarity retrieval → BGE reranker for precision.

---

## ⚙️ Requirements

- **Python** 3.10+
- **MongoDB** 6.0+
- **Dependencies**: `pip install -r requirements.txt`

### External Services (Optional)
- **Ollama** at `http://localhost:11434` for vision/LLM features
- **OpenAI API** or **Cohere API** for LLM-based answer generation
- GPU recommended for faster model inference

---

## 📖 Documentation

- [Technical Documentation](pipeline_reference/docs/technical_documentation.md) — Full architecture, stage details, and API reference
- [Embedding Guide](pipeline_reference/docs/embedding_guide.md) — Model choices, challenges, and implementation deep-dive

---

## 📄 License

This project is licensed under the [AGPL-3.0 License](LICENSE).