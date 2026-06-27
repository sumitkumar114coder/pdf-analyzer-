import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models import User, Document, DocumentChunk, MCQ, HistoryLog
from backend.routes.auth import get_current_user
from backend.services.gemini import query_gemini_mcqs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcq", tags=["mcq"])

class MCQRequest(BaseModel):
    document_id: int
    num_questions: Optional[int] = 10
    difficulty: Optional[str] = "Medium"
    force_regenerate: Optional[bool] = False

@router.post("")
def generate_or_get_mcqs(
    req: MCQRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Verify document ownership
    doc = db.query(Document).filter(
        Document.id == req.document_id, 
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Validate inputs
    if not req.num_questions or req.num_questions < 1 or req.num_questions > 100:
        req.num_questions = 10
    if req.difficulty not in ["Easy", "Medium", "Hard"]:
        req.difficulty = "Medium"

    # 2. Check for cached MCQs for the same document and difficulty level
    existing_mcq = db.query(MCQ).filter(
        MCQ.document_id == doc.id,
        MCQ.difficulty == req.difficulty
    ).first()

    if existing_mcq and not req.force_regenerate:
        try:
            questions = json.loads(existing_mcq.questions_json)
            return {
                "document_id": doc.id,
                "difficulty": existing_mcq.difficulty,
                "questions": questions,
                "cached": True
            }
        except Exception as parse_err:
            logger.error(f"Error parsing existing MCQ JSON: {parse_err}")

    # 3. Concatenate text
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index.asc()).all()
    if not chunks:
        raise HTTPException(status_code=400, detail="Document has no text content to generate MCQs.")

    full_text = "\n".join([c.content for c in chunks])

    # 4. Generate MCQs using Gemini
    try:
        raw_mcq_response = query_gemini_mcqs(
            text=full_text,
            num_questions=req.num_questions,
            difficulty=req.difficulty,
            api_key=current_user.gemini_api_key
        )
    except Exception as e:
        logger.error(f"Error generating MCQs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate MCQs: {str(e)}")

    questions = raw_mcq_response.get("questions", [])

    # 5. Save/Update in DB
    if existing_mcq:
        existing_mcq.questions_json = json.dumps(questions)
    else:
        new_mcq = MCQ(
            document_id=doc.id,
            difficulty=req.difficulty,
            questions_json=json.dumps(questions)
        )
        db.add(new_mcq)

    db.commit()

    # Log action to history
    log = HistoryLog(
        user_id=current_user.id,
        action_type="mcq",
        description=f"Generated {req.num_questions} {req.difficulty} MCQs for document: {doc.filename}"
    )
    db.add(log)
    db.commit()

    return {
        "document_id": doc.id,
        "difficulty": req.difficulty,
        "questions": questions,
        "cached": False
    }
