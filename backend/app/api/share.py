from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Report, DataType
from app.schemas import QueryResult, ReportConfig
from app.report_engine import ReportEngine

router = APIRouter()

@router.get("/{token}", response_model=QueryResult)
def view_share(token: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.shared_token == token).first()
    if not report:
        raise HTTPException(404, "分享链接无效")
    if report.token_expires and report.token_expires < datetime.now():
        raise HTTPException(403, "分享链接已过期")
    dt = db.query(DataType).filter(DataType.id == report.data_type_id).first()
    if not dt:
        raise HTTPException(404, "数据表不存在")
    engine = ReportEngine(db)
    config = ReportConfig(**report.config_json)
    return engine.execute(config, dt.table_name)
