import os
import uuid
import shutil
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models import User, Document, DocumentChunk, HistoryLog, Summary, MCQ, Flashcard
from backend.routes.auth import get_current_user
from backend.services.pdf import extract_pdf_content
from backend.services.rag import chunk_text, build_faiss_index
from backend.services.gemini import query_gemini_summary, query_gemini_mcqs, query_gemini_flashcards

logger = logging.getLogger(__name__)

# Define router. In main.py we will register this
router = APIRouter(tags=["documents"])

# Create relative backend paths
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BACKEND_DIR, "uploads")
INDEX_DIR = os.path.join(UPLOAD_DIR, "indices")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# Maximum file size: 100MB
MAX_FILE_SIZE = 100 * 1024 * 1024

class RenameDocumentRequest(BaseModel):
    filename: str

@router.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Validation
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )

    # Read a portion of file to check size
    contents = await file.read()
    file_size = len(contents)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the maximum size limit of 100MB."
        )

    # 2. Save file to disk
    file_uuid = uuid.uuid4().hex
    safe_filename = f"{file_uuid}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        logger.error(f"Failed to write file to disk: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file.")

    # 3. Extract text
    try:
        extracted_pages = extract_pdf_content(file_path, use_ocr_fallback=True)
    except Exception as e:
        # Cleanup file if extraction fails entirely
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Text extraction failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF: {str(e)}")

    # 4. Save Document Metadata
    page_count = len(extracted_pages)
    new_doc = Document(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        page_count=page_count
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # 5. Chunk and save chunks
    db_chunks = []
    chunk_index_counter = 0
    all_chunks_for_faiss = []

    for page_data in extracted_pages:
        page_num = page_data["page_number"]
        page_text = page_data["text"]

        # Chunk the page text
        page_chunks = chunk_text(page_text, page_num)
        
        for c in page_chunks:
            new_chunk = DocumentChunk(
                document_id=new_doc.id,
                chunk_index=chunk_index_counter,
                content=c["content"],
                page_number=c["page_number"]
            )
            db.add(new_chunk)
            
            # Keep trace for FAISS index build
            all_chunks_for_faiss.append({
                "content": c["content"],
                "chunk_index": chunk_index_counter
            })
            chunk_index_counter += 1

    db.commit()

    # 6. Build FAISS Vector Index
    faiss_filename = f"{new_doc.id}.index"
    faiss_path = os.path.join(INDEX_DIR, faiss_filename)

    try:
        # Pass the user's custom key if configured
        build_faiss_index(all_chunks_for_faiss, faiss_path, api_key=current_user.gemini_api_key)
        new_doc.faiss_index_path = faiss_path
        db.commit()
    except Exception as index_err:
        # We delete the document from db and disk to prevent invalid states
        db.delete(new_doc)
        db.commit()
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(faiss_path):
            os.remove(faiss_path)
            
        logger.error(f"FAISS indexing failed: {index_err}")
        raise HTTPException(
            status_code=500,
            detail=f"Vector Indexing failed: {str(index_err)}. Please verify your Gemini API Key in Settings."
        )

    # 7. Automatically generate Summary, MCQ, and Flashcards by default
    import json
    full_text = "\n".join([c["content"] for c in all_chunks_for_faiss])

    # A. Generate Summary
    try:
        logger.info(f"Auto-generating summaries for document: {new_doc.filename}")
        raw_summary_response = query_gemini_summary(full_text, api_key=current_user.gemini_api_key)
        keyword_items = raw_summary_response.get("keywords", [])
        summaries_dict = {
            "short": raw_summary_response.get("short", ""),
            "medium": raw_summary_response.get("medium", ""),
            "detailed": raw_summary_response.get("detailed", ""),
            "bullets": raw_summary_response.get("bullets", []),
            "chapter_wise": raw_summary_response.get("chapter_wise", []),
            "simple_language": raw_summary_response.get("simple_language", ""),
            "revision": raw_summary_response.get("revision", "")
        }
        new_summary = Summary(
            document_id=new_doc.id,
            summary_data=json.dumps(summaries_dict),
            keywords=json.dumps(keyword_items)
        )
        db.add(new_summary)
        db.commit()
        logger.info("Auto summary generation completed successfully.")
    except Exception as sum_err:
        logger.error(f"Auto summary generation failed during upload: {sum_err}")

    # B. Generate default MCQs (10 questions, Medium difficulty)
    try:
        logger.info(f"Auto-generating 10 Medium MCQs for document: {new_doc.filename}")
        raw_mcq_response = query_gemini_mcqs(full_text, num_questions=10, difficulty="Medium", api_key=current_user.gemini_api_key)
        questions = raw_mcq_response.get("questions", [])
        new_mcq = MCQ(
            document_id=new_doc.id,
            difficulty="Medium",
            questions_json=json.dumps(questions)
        )
        db.add(new_mcq)
        db.commit()
        logger.info("Auto MCQ generation completed successfully.")
    except Exception as mcq_err:
        logger.error(f"Auto MCQ generation failed during upload: {mcq_err}")

    # C. Generate default Flashcards (Medium difficulty)
    try:
        logger.info(f"Auto-generating Medium flashcards for document: {new_doc.filename}")
        raw_flashcard_response = query_gemini_flashcards(full_text, difficulty="Medium", api_key=current_user.gemini_api_key)
        cards = raw_flashcard_response.get("cards", [])
        new_flashcard = Flashcard(
            document_id=new_doc.id,
            difficulty="Medium",
            cards_json=json.dumps(cards)
        )
        db.add(new_flashcard)
        db.commit()
        logger.info("Auto flashcards generation completed successfully.")
    except Exception as fc_err:
        logger.error(f"Auto flashcards generation failed during upload: {fc_err}")


    # Log to action history
    log = HistoryLog(
        user_id=current_user.id,
        action_type="upload",
        description=f"Uploaded and indexed document: {file.filename} ({page_count} pages)"
    )
    db.add(log)
    db.commit()

    return {
        "id": new_doc.id,
        "filename": new_doc.filename,
        "page_count": new_doc.page_count,
        "file_size": new_doc.file_size,
        "upload_date": new_doc.upload_date.isoformat()
    }

@router.get("/api/documents")
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.upload_date.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_size": d.file_size,
            "page_count": d.page_count,
            "upload_date": d.upload_date.isoformat()
        } for d in docs
    ]

@router.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove files from disk
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.error(f"Error removing PDF file: {e}")

    if doc.faiss_index_path and os.path.exists(doc.faiss_index_path):
        try:
            os.remove(doc.faiss_index_path)
        except Exception as e:
            logger.error(f"Error removing FAISS index file: {e}")

    filename = doc.filename
    db.delete(doc)
    db.commit()

    # Log action
    log = HistoryLog(
        user_id=current_user.id,
        action_type="delete",
        description=f"Deleted document: {filename}"
    )
    db.add(log)
    db.commit()

    return {"message": "Document deleted successfully."}

@router.put("/api/documents/{doc_id}/rename")
def rename_document(
    doc_id: int, 
    req: RenameDocumentRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    old_filename = doc.filename
    new_filename = req.filename.strip()
    
    if not new_filename.endswith(".pdf"):
        new_filename += ".pdf"
        
    doc.filename = new_filename
    db.commit()

    # Log action
    log = HistoryLog(
        user_id=current_user.id,
        action_type="rename",
        description=f"Renamed document from {old_filename} to {new_filename}"
    )
    db.add(log)
    db.commit()

    return {"message": "Document renamed successfully.", "filename": doc.filename}
