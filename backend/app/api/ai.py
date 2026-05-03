import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DataType, AISession, AIMessage
from app.schemas import AIResponse, AIMessageRequest, AISessionCreate
from app.ai_engine import AIEngine

router = APIRouter()

@router.post("/sessions")
def create_session(req: AISessionCreate, db: Session = Depends(get_db)):
    # data_type_id=None means session without pre-selected table
    if req.data_type_id:
        dt = db.query(DataType).filter(DataType.id == req.data_type_id).first()
        if not dt:
            raise HTTPException(404, "数据表不存在")
    session_id = req.session_id or str(uuid.uuid4())
    session = AISession(session_id=session_id, data_type_id=req.data_type_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.session_id}

@router.post("/sessions/{session_id}/message", response_model=AIResponse)
def send_message(session_id: str, req: AIMessageRequest, db: Session = Depends(get_db)):
    session = db.query(AISession).filter(AISession.session_id == session_id).first()
    if not session:
        raise HTTPException(404, "会话不存在")
    messages = db.query(AIMessage).filter(AIMessage.session_id == session_id).order_by(AIMessage.created_at.asc()).all()
    conversation = [{"role": m.role, "content": m.content} for m in messages]
    user_msg = AIMessage(session_id=session_id, role="user", content=req.content)
    db.add(user_msg)
    db.commit()
    engine = AIEngine(db)

    if session.data_type_id:
        # Single-table session (existing behavior)
        dt = db.query(DataType).filter(DataType.id == session.data_type_id).first()
        if not dt:
            raise HTTPException(404, "数据表不存在")
        result = engine.parse_user_message(dt, conversation, req.content)
    else:
        # Multi-table session: load ALL tables as schema context
        all_types = db.query(DataType).all()
        if not all_types:
            raise HTTPException(404, "没有可用的数据表")
        result = engine.parse_user_message_multi(all_types, conversation, req.content)

    query_result = None
    sql_text = None
    if result.get("sql"):
        sql_text = result["sql"]
        try:
            if session.data_type_id:
                dt = db.query(DataType).filter(DataType.id == session.data_type_id).first()
                query_result = engine.execute_query(dt, sql_text)
            else:
                query_result = engine.execute_raw_sql(sql_text)
        except Exception as e:
            result["analysis"] = f"SQL执行出错: {e}"
    assistant_content = result.get("analysis") or result.get("clarification") or "好的，已收到你的问题。"
    assistant_msg = AIMessage(session_id=session_id, role="assistant", content=assistant_content, sql_query=sql_text, result_preview=query_result)
    db.add(assistant_msg)
    db.commit()
    return AIResponse(
        text=assistant_content,
        sql_query=sql_text,
        result_preview=query_result,
        follow_ups=result.get("follow_ups", []),
        used_tables=result.get("used_tables", [])
    )

@router.get("/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AISession).filter(AISession.session_id == session_id).first()
    if not session:
        raise HTTPException(404, "会话不存在")
    messages = db.query(AIMessage).filter(AIMessage.session_id == session_id).order_by(AIMessage.created_at.asc()).all()
    return {"session_id": session_id, "data_type_id": session.data_type_id, "messages": [{"role": m.role, "content": m.content, "result": m.result_preview} for m in messages]}
