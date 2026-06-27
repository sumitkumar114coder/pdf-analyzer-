import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models import User, Document, DocumentChunk, Flashcard, HistoryLog
from backend.routes.auth import get_current_user
from backend.services.gemini import query_gemini_flashcards

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])

class FlashcardRequest(BaseModel):
    document_id: int
    difficulty: Optional[str] = "Medium"
    force_regenerate: Optional[bool] = False

@router.post("")
def generate_or_get_flashcards(
    req: FlashcardRequest,
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
    if req.difficulty not in ["Easy", "Medium", "Hard"]:
        req.difficulty = "Medium"

    # 2. Check for cached flashcards for the same document and difficulty level
    existing_cards = db.query(Flashcard).filter(
        Flashcard.document_id == doc.id,
        Flashcard.difficulty == req.difficulty
    ).first()

    if existing_cards and not req.force_regenerate:
        try:
            cards = json.loads(existing_cards.cards_json)
            return {
                "document_id": doc.id,
                "difficulty": existing_cards.difficulty,
                "cards": cards,
                "cached": True
            }
        except Exception as parse_err:
            logger.error(f"Error parsing existing Flashcard JSON: {parse_err}")

    # 3. Concatenate text
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index.asc()).all()
    if not chunks:
        raise HTTPException(status_code=400, detail="Document has no text content to generate Flashcards.")

    full_text = "\n".join([c.content for c in chunks])

    # 4. Generate Flashcards using Gemini
    try:
        raw_flashcard_response = query_gemini_flashcards(
            text=full_text,
            difficulty=req.difficulty,
            api_key=current_user.gemini_api_key
        )
    except Exception as e:
        logger.error(f"Error generating Flashcards: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate Flashcards: {str(e)}")

    cards = raw_flashcard_response.get("cards", [])

    # 5. Save/Update in DB
    if existing_cards:
        existing_cards.cards_json = json.dumps(cards)
    else:
        new_flashcard = Flashcard(
            document_id=doc.id,
            difficulty=req.difficulty,
            cards_json=json.dumps(cards)
        )
        db.add(new_flashcard)

    db.commit()

    # Log action to history
    log = HistoryLog(
        user_id=current_user.id,
        action_type="flashcards",
        description=f"Generated {req.difficulty} difficulty flashcards for document: {doc.filename}"
    )
    db.add(log)
    db.commit()

    return {
        "document_id": doc.id,
        "difficulty": req.difficulty,
        "cards": cards,
        "cached": False
    }
