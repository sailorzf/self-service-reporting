import uuid
import io
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook
from app.database import get_db
from app.models import Report, DataType
from app.schemas import ReportCreate, ReportResponse, QueryExecute, QueryResult, ReportConfig
from app.report_engine import ReportEngine, DataFormatter

router = APIRouter()

@router.post("/", response_model=ReportResponse)
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    dt = db.query(DataType).filter(DataType.id == report.data_type_id).first()
    if not dt:
        raise HTTPException(404, "数据类型不存在")
    r = Report(name=report.name, data_type_id=report.data_type_id, config_json=report.config_json.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

@router.get("/", response_model=list[ReportResponse])
def list_reports(db: Session = Depends(get_db)):
    return db.query(Report).order_by(Report.updated_at.desc()).all()

@router.post("/execute", response_model=QueryResult)
def execute_query(query: QueryExecute, db: Session = Depends(get_db)):
    engine = ReportEngine(db)
    if query.config.tables and len(query.config.tables) > 1:
        table_map = {}
        for t in query.config.tables:
            dt = db.query(DataType).filter(DataType.id == t.data_type_id).first()
            if not dt:
                raise HTTPException(404, f"数据类型 {t.data_type_id} 不存在")
            table_map[t.alias] = dt.table_name
        return engine.execute_multi(query.config, table_map)
    if query.data_type_id:
        dt = db.query(DataType).filter(DataType.id == query.data_type_id).first()
        if not dt:
            raise HTTPException(404, "数据类型不存在")
        return engine.execute(query.config, dt.table_name)
    raise HTTPException(400, "需要指定data_type_id或tables")

@router.post("/{report_id}/execute", response_model=QueryResult)
def execute_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise HTTPException(404, "报表不存在")
    dt = db.query(DataType).filter(DataType.id == r.data_type_id).first()
    if not dt:
        raise HTTPException(404, "数据类型不存在")
    engine = ReportEngine(db)
    config = ReportConfig(**r.config_json)
    return engine.execute(config, dt.table_name)

@router.post("/{report_id}/share")
def share_report(report_id: int, days: int = Query(default=7), db: Session = Depends(get_db)):
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise HTTPException(404, "报表不存在")
    r.shared_token = str(uuid.uuid4())
    r.token_expires = datetime.now() + timedelta(days=days)
    db.commit()
    return {"share_url": f"/share/{r.shared_token}", "expires": r.token_expires}

@router.get("/{report_id}/export")
def export_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise HTTPException(404, "报表不存在")
    dt = db.query(DataType).filter(DataType.id == r.data_type_id).first()
    engine = ReportEngine(db)
    config = ReportConfig(**r.config_json)
    result = engine.execute(config, dt.table_name)
    wb = Workbook()
    ws = wb.active
    ws.append(result["headers"])
    for row in result["rows"]:
        ws.append(row)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={r.name}.xlsx"}
    )
