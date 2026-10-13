# 🎓 AI Study Buddy — Zero-Cost AI Learning Platform

An intelligent, zero-cost, privacy-first study assistant powered by 100% local AI. AI Study Buddy lets students upload PDF notes and textbooks, chat with their study materials using local Retrieval-Augmented Generation (RAG), generate interactive quizzes, study with smart flashcards, and track progress over time.

---

## ⚡ Zero-Cost Architecture Highlights

- **Total Budget:** ₹0 (Zero subscription costs, zero paid APIs)
- **Local LLM:** [Ollama](https://ollama.com/) with `llama3.2:3b`
- **Document Retrieval:** Local embeddings (`sentence-transformers/all-MiniLM-L6-v2`) + Vector Index ([FAISS-CPU](https://github.com/facebookresearch/faiss))
- **Backend:** Python 3.12 + FastAPI + SQLite
- **Frontend:** React + Vite + TypeScript + Vanilla CSS Design System
- **Privacy First:** All notes, embeddings, and chat interactions remain strictly on your local machine.

---

## 🔄 Document Upload & RAG Architecture

```
┌─────────────────┐      1. Upload PDF
│  Student / Web  │ ─────────────────────────►  FastAPI Backend (/api/documents/upload)
│    Interface    │                                   │
└─────────────────┘                                   ▼
         │                              2. Text Extraction & Cleaning (PyPDF)
         │                                    │  - Preserves 1-based page numbers
         │                                    │  - Detects scanned/empty files
         │                                    ▼
         │                              3. Overlapping Chunking (600 chars, 100 overlap)
         │                                    │
         │                                    ▼
         │                              4. SQLite Storage (Document & Chunks)
         │                                    │
         │                                    ▼
         │                              5. Local Embeddings (all-MiniLM-L6-v2, 384-dim)
         │                                    │
         │                                    ▼
         │                              6. FAISS-CPU Index (IndexIDMap2 + IndexFlatIP)
         │
         │ 7. Question (/api/chat/ask)
         ▼
┌──────────────────┐    8. Embed Query
│  RAG Controller  │ ────────────────────────►  FAISS Vector Search (Cosine Similarity)
└──────────────────┘                                   │
         │                                             ▼
         │ 9. Context Assembly            Top-K Matching Chunks + Citations
         ▼
┌──────────────────┐
│   Ollama Local   │ ◄───────────────────────── Prompt + Context + Citations
│   llama3.2:3b    │
└──────────────────┘
         │ 10. Accurate Answer with Page Citations (Zero Hallucination)
         ▼
┌──────────────────┐
│  Student Answer  │ (Includes Document Name, Page #, Supporting Excerpt, Similarity Score)
└──────────────────┘
```

---

## 📁 Repository Structure

```
ai-study-buddy/
├── backend/                  # FastAPI Python backend
│   ├── app/
│   │   ├── api/              # REST API endpoints (ai, documents, chat)
│   │   ├── core/             # Configuration and environment settings
│   │   ├── database/         # SQLite connection & session manager
│   │   ├── models/           # SQLAlchemy ORM models (Document, Chunk, Quiz, Flashcard)
│   │   ├── schemas/          # Pydantic validation schemas
│   │   ├── services/         # PDF parser, FAISS vectorstore, Ollama & RAG services
│   │   └── main.py           # FastAPI entrypoint & router assembly
│   ├── tests/                # Test suite (31 automated unit & integration tests)
│   └── requirements.txt      # Python 3.12 dependencies
├── frontend/                 # React + TypeScript frontend
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── hooks/            # Custom React hooks
│   │   ├── pages/            # View pages (Dashboard, Chat, Quiz, Flashcards, Progress)
│   │   ├── services/         # API clients
│   │   └── types/            # TypeScript interfaces
│   └── package.json
├── data/                     # Local data (gitignored)
│   ├── uploads/              # Uploaded PDF files
│   ├── vectorstore/          # FAISS index files (faiss_index.bin, vector_metadata.json)
│   └── study_buddy.db        # SQLite relational database
├── .env.example              # Sample environment configuration
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.12+**
- **Node.js 18+ & npm**
- **Ollama** installed with `llama3.2:3b` pulled:
  ```powershell
  ollama pull llama3.2:3b
  ```

### 2. Backend Setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Caching the Embedding Model for 100% Offline Use
The `all-MiniLM-L6-v2` model (~90 MB) is automatically downloaded upon first use and cached locally under `~/.cache/huggingface/hub/`. To pre-cache it explicitly before disconnecting from the internet:
```powershell
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2'); print('Embedding model cached successfully!')"
```
Once cached, all text extraction, vector embeddings, similarity search, and AI inference run **100% locally and offline without an internet connection**.

### 4. Running the Backend Server
From the workspace root:
```powershell
.\backend\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --app-dir backend
```
Or from the `backend/` directory:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Running the React Frontend Dashboard (Phase 6)
From the `frontend/` directory:
```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
Open your browser to [http://127.0.0.1:5173/](http://127.0.0.1:5173/) to access the **AI Study Buddy** dashboard.

### 6. Starting Both Services Concurrently
For the best development workflow, run the services in two separate PowerShell windows:
- **Terminal 1 (Backend):** `cd backend; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000`
- **Terminal 2 (Frontend):** `cd frontend; npm run dev`


---

## 📡 API Endpoints

### 🩺 Health & Local AI Core
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Service root and metadata |
| `GET` | `/api/health` | Comprehensive health check (FastAPI, SQLite, Ollama) |
| `GET` | `/api/ai/status` | Ollama connectivity & model presence (`llama3.2:3b`) |
| `POST` | `/api/ai/chat` | Direct prompt generation with local LLM |

### 📚 Documents & Vector RAG
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/documents/upload` | Upload PDF, extract text, chunk, embed, and index in FAISS |
| `GET` | `/api/documents` | List all uploaded documents with chunk counts |
| `GET` | `/api/documents/{id}` | Retrieve document metadata |
| `DELETE` | `/api/documents/{id}` | Safely delete document, chunks, file, and FAISS vectors |
| `POST` | `/api/chat/ask` | Ask questions over uploaded notes with verified page citations |

### 🧠 AI Quizzes (Phase 5)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/quizzes/generate` | Generate multiple-choice quiz grounded in selected documents |
| `GET` | `/api/quizzes` | List all created quizzes |
| `GET` | `/api/quizzes/{quiz_id}` | Retrieve quiz questions (correct answers hidden prior to submission) |
| `POST` | `/api/quizzes/{quiz_id}/submit` | Submit answers, calculate score on backend, persist attempt, reveal explanations |
| `GET` | `/api/quizzes/{quiz_id}/attempts` | View attempt history and scores for a quiz |

### 🗂️ Smart Flashcards & Spaced Repetition (Phase 5)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/flashcards/generate` | Generate question-answer flashcard pairs from documents |
| `GET` | `/api/flashcards` | List all flashcards (with optional `document_id` query filter) |
| `GET` | `/api/flashcards/due` | Retrieve flashcards currently due for spaced review |
| `POST` | `/api/flashcards/{flashcard_id}/review` | Record review rating (`Easy`, `Medium`, `Hard`) and advance schedule |
| `DELETE` | `/api/flashcards/{flashcard_id}` | Permanently delete a flashcard |

### 📊 Study Progress Dashboard (Phase 5)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/progress/summary` | Real-time aggregate metrics: documents, quizzes, attempts, averages, due cards |

---

## ⏱️ Spaced Repetition Scheduling Logic

The Flashcards system uses an intuitive interval multiplier schedule based on the student's rating of their recall difficulty:

- **Easy**: `interval_days = min(30.0, 4.0 * (1.5 ** review_count))`  
  *(Initial review in 4 days, then 6, 9, 13.5 days, capped at 30 days)*
- **Medium**: `interval_days = min(14.0, 2.0 * (1.2 ** review_count))`  
  *(Initial review in 2 days, then 2.4, 2.9 days, capped at 14 days)*
- **Hard**: `interval_days = 1.0`  
  *(Immediate next-day review; interval resets to 1 day to reinforce mastery)*

> [!NOTE]
> **Algorithm Limitations & Scope:** This schedule is an empirical, lightweight rule-based spaced repetition implementation suitable for local offline study without external services. It does not claim to implement the full SuperMemo SM-2, SM-18, or Free Spaced Repetition Scheduler (FSRS) cognitive decay models, nor does it track fractional forgetting indexes across multi-month gaps.

---

## 💻 Example PowerShell Commands

### 1. Check Service Health
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health"
```

### 2. Upload a PDF Note
```powershell
curl.exe -F "file=@path\to\your_notes.pdf" http://127.0.0.1:8000/api/documents/upload
```

### 3. Ask a Question About Your Notes (RAG)
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/chat/ask" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{ question = "What is the primary function of mitochondria?" } | ConvertTo-Json) `
  | ConvertTo-Json -Depth 5
```

### 4. Generate an AI Quiz Grounded in Document Notes
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/quizzes/generate" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{
    document_ids = @(1)
    title = "Cell Biology Mastery Quiz"
    difficulty = "Medium"
    num_questions = 5
  } | ConvertTo-Json) | ConvertTo-Json -Depth 5
```

### 5. Submit Quiz Answers (Privacy-Safe Backend Grading)
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/quizzes/1/submit" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{
    answers = @{
      "1" = "Phospholipid bilayer"
      "2" = "Active transport"
    }
  } | ConvertTo-Json) | ConvertTo-Json -Depth 5
```

### 6. Generate Flashcards from Notes
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/flashcards/generate" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{
    document_ids = @(1)
    num_cards = 5
  } | ConvertTo-Json) | ConvertTo-Json -Depth 5
```

### 7. Review a Flashcard with Spaced Repetition Rating
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/flashcards/1/review" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{ rating = "Easy" } | ConvertTo-Json) | ConvertTo-Json -Depth 5
```

### 8. View Study Progress Analytics
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/progress/summary" | ConvertTo-Json -Depth 5
```

### 9. Run the Full Automated Test Suite (31 Tests)
```powershell
.\backend\.venv\Scripts\pytest backend\tests -v
```

---

## ⚠️ Current Limitations

- **Scanned / Image-Only PDFs:** In accordance with the ₹0 budget and lightweight offline architecture, OCR is not bundled by default. If an image-only PDF is uploaded, the system detects it and gracefully returns `scanned_pdf_no_ocr` with an actionable message rather than hallucinating empty content.
- **Model Context Window:** Answers and generation prompts are grounded in retrieved passages (top-k chunk retrieval) to ensure fast local inference on standard consumer laptops.
- **Scheduling Model:** Spaced repetition uses fixed-step multiplier scheduling rather than continuous neuro-cognitive modeling.

## 🛠️ Troubleshooting

### 1. Ollama Connection Error (`Ollama model unavailable` or `ECONNREFUSED`)
- Ensure Ollama is running:
  ```powershell
  ollama serve
  ```
- Verify the target model is installed:
  ```powershell
  ollama list
  ollama pull llama3.2:3b
  ```
- Test direct inference:
  ```powershell
  ollama run llama3.2:3b "Hello Study Buddy"
  ```

### 2. CORS Errors in Browser
- Ensure the backend is running with CORS configured for `http://127.0.0.1:5173` and `http://localhost:5173`.
- Verify the frontend `.env` points to `VITE_API_BASE_URL=http://127.0.0.1:8000`.

### 3. PDF Upload Returns `scanned_pdf_no_ocr`
- AI Study Buddy extracts native text layers using PyPDF for 100% offline, zero-cost processing. If your PDF consists of scanned pictures or flat photos, export it with selectable text or use an OCR utility to convert it into a text-searchable PDF before uploading.

### 4. Port Conflicts (Port 8000 or 5173 Already in Use)
- Check and terminate existing processes if needed:
  ```powershell
  Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process
  ```

---

## 📝 License
MIT License - Zero-cost open-source educational project.
