import os
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models import User, Document, DocumentChunk, ChatSession, ChatMessage, HistoryLog
from backend.routes.auth import get_current_user
from backend.services.embeddings import generate_embedding
from backend.services.rag import search_faiss_index
from backend.services.gemini import query_gemini_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Pydantic Request schemas
class ChatQueryRequest(BaseModel):
    document_id: int
    session_id: Optional[int] = None
    question: str

@router.post("")
def chat_with_document(
    req: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Verify document belongs to current user
    doc = db.query(Document).filter(Document.id == req.document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # 2. Get or create Chat Session
    if req.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == req.session_id, 
            ChatSession.user_id == current_user.id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found.")
    else:
        # Create a new session
        title = req.question[:40] + ("..." if len(req.question) > 40 else "")
        session = ChatSession(
            user_id=current_user.id,
            document_id=doc.id,
            title=title
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # 3. Retrieve chat history
    db_messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
    chat_history = [
        {"sender": msg.sender, "message": msg.message}
        for msg in db_messages
    ]

    # 4. Vector Search using FAISS
    # A. Generate embedding for query
    try:
        query_embed = generate_embedding(req.question, api_key=current_user.gemini_api_key)
    except Exception as e:
        logger.error(f"Error generating query embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # B. Query FAISS
    if not doc.faiss_index_path or not os.path.exists(doc.faiss_index_path):
        raise HTTPException(status_code=400, detail="Document vector index is missing. Try re-uploading the file.")

    matched_indices = search_faiss_index(query_embed, doc.faiss_index_path, top_k=5)
    
    # C. Retrieve chunks
    context_chunks = []
    if matched_indices:
        db_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc.id,
            DocumentChunk.chunk_index.in_(matched_indices)
        ).all()
        
        for c in db_chunks:
            context_chunks.append({
                "content": c.content,
                "page_number": c.page_number
            })

    # 5. Query Gemini with history and context chunks
    ai_response = query_gemini_chat(
        question=req.question,
        context_chunks=context_chunks,
        chat_history=chat_history,
        api_key=current_user.gemini_api_key
    )

    # 6. Save message exchange in SQLite
    user_msg = ChatMessage(
        session_id=session.id,
        sender="user",
        message=req.question
    )
    
    # Find context matching source texts for references
    citation_pages = ai_response.get("citations", [])
    sources_data = []
    for chunk in context_chunks:
        if chunk["page_number"] in citation_pages:
            sources_data.append({
                "page": chunk["page_number"],
                "text": chunk["content"][:200] + "..."
            })

    ai_msg = ChatMessage(
        session_id=session.id,
        sender="ai",
        message=ai_response["answer"],
        sources=json.dumps(sources_data),
        confidence=ai_response.get("confidence", 80.0)
    )

    db.add(user_msg)
    db.add(ai_msg)
    db.commit()

    # Log action to history log
    log = HistoryLog(
        user_id=current_user.id,
        action_type="chat",
        description=f"Asked question in chat session: '{session.title}'"
    )
    db.add(log)
    db.commit()

    return {
        "session_id": session.id,
        "session_title": session.title,
        "response": {
            "id": ai_msg.id,
            "sender": "ai",
            "message": ai_msg.message,
            "sources": sources_data,
            "confidence": ai_msg.confidence,
            "created_at": ai_msg.created_at.isoformat()
        }
    }

@router.get("/sessions")
def list_chat_sessions(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(ChatSession).filter(
        ChatSession.document_id == document_id,
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.created_at.desc()).all()

    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat()
        } for s in sessions
    ]

@router.get("/history/{session_id}")
def get_chat_history(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    db_messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()

    formatted_messages = []
    for msg in db_messages:
        sources_list = []
        if msg.sources:
            try:
                sources_list = json.loads(msg.sources)
            except Exception:
                sources_list = []
                
        formatted_messages.append({
            "id": msg.id,
            "sender": msg.sender,
            "message": msg.message,
            "sources": sources_list,
            "confidence": msg.confidence,
            "created_at": msg.created_at.isoformat()
        })

    return formatted_messages
