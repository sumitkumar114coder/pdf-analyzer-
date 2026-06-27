# AI Research Assistant

AI Research Assistant is a production-quality, responsive SaaS-style web application where users can upload study materials (PDFs, textbooks, notes) and interact with them using a RAG (Retrieval-Augmented Generation) pipeline powered by FastAPI, SQLite, FAISS, and the Gemini API.

## Features

- **Double-Pane Sidebar & Unified Portal Layout**: Navigate seamlessly between views (Dashboard, Uploader, Chat Q&A, Summaries, MCQs, History, and Settings).
- **RAG Chat Q&A**: Query uploaded documents directly. AI answers questions **strictly** using document contents and provides clickable page citations like `[Page X]`.
- **Automatic Summary Suite**: Auto-compiles short, medium, and detailed summaries, bullet takeaways, section breakdowns, simplified (ELI5) text, and revision outlines.
- **Concepts & Formulas Extractor**: Automatically parses text to list important terms, definitions, and equations in structured study cards.
- **Interactive MCQ Generator**: Generates 10, 20, or 50 multiple-choice quizzes with timer controls, dynamic scoring, and correct choice explanations.
- **3D Flip Study Flashcards**: Automatically creates cards with flip transitions. Supports shuffling decks and difficulty configurations (Easy, Medium, Hard).
- **Blob File Exports**: Export summaries, flashcards, or quizzes as styled Markdown documents directly.
- **History Audit Trails**: Audit trails logging uploads, searches, and study actions, with a live filter search and deletion controls.
- **Secure Authentication & Theme Toggling**: Secure signup/login using native bcrypt password hashing, JWT authentication, and Light/Dark mode appearance.

---

## Tech Stack

- **Frontend**: HTML5, Vanilla JavaScript, Custom CSS3 (no external layouts/Tailwind to ensure light rendering, custom 3D animations).
- **Backend Framework**: Python, FastAPI.
- **Database**: SQLite (SQLAlchemy ORM) - modularized to allow migration to PostgreSQL later.
- **Vector Database**: FAISS (Facebook AI Similarity Search) CPU.
- **Large Language Model (LLM)**: Gemini API (`gemini-1.5-flash` for high-speed context answers and JSON structured output formatting).
- **Embeddings API**: Gemini Embedding API (`models/text-embedding-004`).
- **PDF Text Parsing**: PyMuPDF (`fitz`).
- **OCR Engine (Scanned PDF Fallback)**: PyTesseract OCR.

---

## Installation & Setup

Follow these steps to run the application locally on your Windows machine:

### Prerequisites
- **Python 3.9 to 3.12** installed on your system.
- **Tesseract OCR Engine** (Optional, required for scanned images/PDFs text extraction).
  - Download and install Tesseract for Windows.
  - Add the installation path (usually `C:\Program Files\Tesseract-OCR`) to your system environment variables `PATH`.

### Step 1: Open project directory
Open your shell/terminal inside the project root folder:
```powershell
cd "c:\Users\soura\OneDrive\Desktop\working stuff\sumit workings\making websites\8 pdf scan sumit"
```

### Step 2: Install dependencies
Install all required libraries using pip:
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Gemini API Key
To query the AI, the application needs a Gemini API Key. You can set it as a system environment variable or leave it empty and input your key in the **Settings** page of the web app.

To set it via terminal:
- **Windows (Command Prompt)**:
  ```cmd
  set GEMINI_API_KEY=your_gemini_api_key_here
  ```
- **Windows (PowerShell)**:
  ```powershell
  $env:GEMINI_API_KEY="your_gemini_api_key_here"
  ```

### Step 4: Generate a Test PDF File
We have included a script to build a sample astronomy PDF containing planetary facts and equations to test the pipeline out of the box:
```powershell
python backend/create_test_pdf.py
```
This will create a structured file called `backend/test_solar_system.pdf`.

### Step 5: Start the FastAPI Server
Run the FastAPI application using Uvicorn:
```powershell
uvicorn backend.main:app --reload
```

### Step 6: Open the Web Application
Open your web browser and navigate to:
```
http://localhost:8000
```
Register a new account (all passwords hashed locally using `bcrypt`), log in, upload `backend/test_solar_system.pdf` on the **Upload** page, and start exploring the study tools!

---

## Code Structure

```
8 pdf scan sumit/
├── frontend/                 # Static files served by FastAPI
│   ├── index.html            # Landing page
│   ├── login.html            # Login screen
│   ├── signup.html           # User registration
│   ├── dashboard.html        # Main indicators & recent uploads
│   ├── upload.html           # PDF Drag-and-drop
│   ├── chat.html             # Document Q&A (RAG)
│   ├── summary.html          # Tabs summary & keywords
│   ├── mcq.html              # Quizzes & timers
│   ├── flashcards.html       # 3D interactive flashcards
│   ├── history.html          # Global activity logs
│   ├── settings.html         # Keys & profile details
│   └── assets/
│       ├── css/              # style.css, dashboard.css, chat.css
│       └── js/               # auth.js, app.js, upload.js, study.js
├── backend/                  # FastAPI Application codebase
│   ├── main.py               # Server launcher & routes registry
│   ├── database.py           # SQLite connection helper
│   ├── models.py             # SQLAlchemy models schemas
│   ├── routes/               # API endpoints routers
│   ├── services/             # PyMuPDF, OCR, Embeddings, FAISS, Gemini SDK
│   ├── uploads/              # Raw PDFs uploads and FAISS indices
│   ├── generated/            # Temporary downloads
│   └── database/             # SQLite DB file
├── requirements.txt          # Python dependencies manifest
└── README.md                 # Project guide
```
