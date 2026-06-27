import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models import User, Document, DocumentChunk, Summary, HistoryLog
from backend.routes.auth import get_current_user
from backend.services.gemini import query_gemini_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/summary", tags=["summary"])

class SummaryRequest(BaseModel):
    document_id: int
    force_regenerate: Optional[bool] = False

@router.post("")
def get_or_generate_summary(
    req: SummaryRequest,
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

    # 2. Check for existing summary cache
    existing_summary = db.query(Summary).filter(Summary.document_id == doc.id).first()
    if existing_summary and not req.force_regenerate:
        try:
            summary_data = json.loads(existing_summary.summary_data)
            keywords = json.loads(existing_summary.keywords)
            return {
                "document_id": doc.id,
                "summary": summary_data,
                "keywords": keywords,
                "cached": True
            }
        except Exception as parse_err:
            logger.error(f"Error parsing existing summary JSON: {parse_err}")
            # If parsing fails, regenerate

    # 3. Concatenate document chunks for summary context
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index.asc()).all()
    if not chunks:
        raise HTTPException(status_code=400, detail="Document has no text content to summarize.")

    full_text = "\n".join([c.content for c in chunks])

    # 4. Generate summaries via Gemini
    try:
        raw_summary_response = query_gemini_summary(full_text, api_key=current_user.gemini_api_key)
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")

    # Extract keyword list and standard summaries
    keyword_items = raw_summary_response.get("keywords", [])
    
    # Save fields in structured dict
    summaries_dict = {
        "short": raw_summary_response.get("short", ""),
        "medium": raw_summary_response.get("medium", ""),
        "detailed": raw_summary_response.get("detailed", ""),
        "bullets": raw_summary_response.get("bullets", []),
        "chapter_wise": raw_summary_response.get("chapter_wise", []),
        "simple_language": raw_summary_response.get("simple_language", ""),
        "revision": raw_summary_response.get("revision", "")
    }

    # 5. Write to database
    if existing_summary:
        existing_summary.summary_data = json.dumps(summaries_dict)
        existing_summary.keywords = json.dumps(keyword_items)
    else:
        new_summary = Summary(
            document_id=doc.id,
            summary_data=json.dumps(summaries_dict),
            keywords=json.dumps(keyword_items)
        )
        db.add(new_summary)

    db.commit()

    # Log action to history
    log = HistoryLog(
        user_id=current_user.id,
        action_type="summary",
        description=f"Generated AI summary for document: {doc.filename}"
    )
    db.add(log)
    db.commit()

    return {
        "document_id": doc.id,
        "summary": summaries_dict,
        "keywords": keyword_items,
        "cached": False
    }
