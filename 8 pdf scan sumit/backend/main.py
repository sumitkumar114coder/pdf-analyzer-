import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import engine
from backend.models import Base
from backend.routes import auth, upload, chat, summary, mcq, flashcards, history

# Initialize Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Research Assistant API")

# Add CORS Middleware to support hosting frontend separately (e.g. Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(summary.router)
app.include_router(mcq.router)
app.include_router(flashcards.router)
app.include_router(history.router)

# Base directories
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BACKEND_DIR, "..", "frontend"))

# Create required backend directories
os.makedirs(os.path.join(BACKEND_DIR, "uploads"), exist_ok=True)
os.makedirs(os.path.join(BACKEND_DIR, "uploads", "indices"), exist_ok=True)
os.makedirs(os.path.join(BACKEND_DIR, "generated"), exist_ok=True)

# Mount the assets directory (CSS/JS) if it exists
assets_dir = os.path.join(FRONTEND_DIR, "assets")
os.makedirs(assets_dir, exist_ok=True)
os.makedirs(os.path.join(assets_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(assets_dir, "js"), exist_ok=True)

app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# Direct page routing for easy navigation
@app.get("/")
def serve_home():
    home_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(home_path):
        return FileResponse(home_path)
    return {"message": "AI Research Assistant API is running. Frontend static pages are not yet created."}

@app.get("/{page_name}")
@app.get("/{page_name}.html")
def serve_page(page_name: str):
    # Sanitize and serve page
    clean_name = page_name.replace(".html", "")
    page_path = os.path.join(FRONTEND_DIR, f"{clean_name}.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    raise HTTPException(status_code=404, detail="Page not found")
