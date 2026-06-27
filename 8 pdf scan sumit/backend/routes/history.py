import os
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models import User, Document, HistoryLog, Summary, MCQ, Flashcard
from backend.routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["history_downloads"])

@router.get("/api/history")
def get_history_logs(
    query: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns user action history log. Allows filtering by query keyword.
    """
    log_query = db.query(HistoryLog).filter(HistoryLog.user_id == current_user.id)
    if query and query.strip():
        log_query = log_query.filter(HistoryLog.description.ilike(f"%{query.strip()}%"))
        
    logs = log_query.order_by(HistoryLog.created_at.desc()).all()
    
    return [
        {
            "id": l.id,
            "action_type": l.action_type,
            "description": l.description,
            "created_at": l.created_at.isoformat()
        } for l in logs
    ]

@router.delete("/api/history/{log_id}")
def delete_history_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a specific log entry.
    """
    log = db.query(HistoryLog).filter(HistoryLog.id == log_id, HistoryLog.user_id == current_user.id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found.")
        
    db.delete(log)
    db.commit()
    return {"message": "Log entry cleared."}

@router.delete("/api/history")
def clear_all_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clear all history logs for the current user.
    """
    db.query(HistoryLog).filter(HistoryLog.user_id == current_user.id).delete()
    db.commit()
    return {"message": "All history logs cleared."}

@router.get("/api/download/{export_type}/{doc_id}")
def download_study_material(
    export_type: str,  # 'summary', 'mcq', 'flashcards'
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates study materials as beautifully structured Markdown download files.
    """
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    content = ""
    safe_filename_prefix = doc.filename.replace(".pdf", "").replace(" ", "_")
    filename = f"{safe_filename_prefix}_{export_type}.md"

    if export_type == "summary":
        summary_record = db.query(Summary).filter(Summary.document_id == doc.id).first()
        if not summary_record:
            raise HTTPException(status_code=404, detail="Summary not generated yet.")
        
        summary_data = json.loads(summary_record.summary_data)
        keywords = json.loads(summary_record.keywords)

        content = f"# Study Summary: {doc.filename}\n\n"
        content += f"## Quick Overview\n{summary_data.get('short', '')}\n\n"
        content += f"## Medium Summary\n{summary_data.get('medium', '')}\n\n"
        content += f"## Detailed Breakdown\n{summary_data.get('detailed', '')}\n\n"
        
        content += "## Key Takeaways\n"
        for bullet in summary_data.get("bullets", []):
            content += f"- {bullet}\n"
        content += "\n"

        content += "## Chapter-wise / Section Summary\n"
        for chap in summary_data.get("chapter_wise", []):
            content += f"- {chap}\n"
        content += "\n"

        content += f"## Simple Explanation (ELI5)\n{summary_data.get('simple_language', '')}\n\n"
        content += f"## Revision Notes\n{summary_data.get('revision', '')}\n\n"

        content += "## Important Concepts, Terms & Formulas\n"
        for item in keywords:
            content += f"### {item.get('term')} ({item.get('type')})\n"
            content += f"**Definition:** {item.get('definition')}\n\n"

    elif export_type == "mcq":
        mcq_record = db.query(MCQ).filter(MCQ.document_id == doc.id).first()
        if not mcq_record:
            raise HTTPException(status_code=404, detail="MCQ quiz not generated yet.")
            
        questions = json.loads(mcq_record.questions_json)
        content = f"# Practice Quiz: {doc.filename}\n"
        content += f"Difficulty Level: {mcq_record.difficulty.capitalize()}\n\n"
        content += "---\n\n"

        for idx, item in enumerate(questions):
            content += f"### Q{idx + 1}. {item.get('question')}\n\n"
            for option in item.get("options", []):
                content += f"- {option}\n"
            content += f"\n**Correct Answer:** {item.get('correct_answer')}\n"
            content += f"**Explanation:** {item.get('explanation')}\n\n"
            content += "---\n\n"

    elif export_type == "flashcards":
        flashcard_record = db.query(Flashcard).filter(Flashcard.document_id == doc.id).first()
        if not flashcard_record:
            raise HTTPException(status_code=404, detail="Flashcards not generated yet.")
            
        cards = json.loads(flashcard_record.cards_json)
        content = f"# Study Flashcards: {doc.filename}\n"
        content += f"Difficulty Level: {flashcard_record.difficulty.capitalize()}\n\n"
        content += "---\n\n"

        for idx, card in enumerate(cards):
            content += f"### Card {idx + 1}\n"
            content += f"**Front (Prompt):** {card.get('front')}\n\n"
            content += f"**Back (Response):** {card.get('back')}\n\n"
            content += "---\n\n"
    else:
        raise HTTPException(status_code=400, detail="Invalid export type requested.")

    # Log action to history
    log = HistoryLog(
        user_id=current_user.id,
        action_type="download",
        description=f"Exported and downloaded {export_type} for document: {doc.filename}"
    )
    db.add(log)
    db.commit()

    return Response(
        content=content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )
