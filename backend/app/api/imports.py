import os
import uuid
import json
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DataType, ImportRecord
from app.schemas import ImportPreview, ImportRecordResponse
from app.import_service import ImportService

router = APIRouter()
service = ImportService()

@router.post("/infer-schema")
async def infer_schema(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "仅支持Excel文件(.xlsx, .xls)")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        return service.infer_schema(tmp_path, file.filename)
    except Exception as e:
        raise HTTPException(400, f"文件解析失败: {e}")
    finally:
        os.unlink(tmp_path)

@router.post("/upload", response_model=ImportPreview)
async def upload_preview(
    file: UploadFile = File(...),
    data_type_id: int = Form(default=None),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "仅支持Excel文件(.xlsx, .xls)")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        columns_json = None
        if data_type_id:
            dt = db.query(DataType).filter(DataType.id == data_type_id).first()
            if dt:
                columns_json = dt.columns_json
        preview = service.preview(tmp_path, columns_json)
        return preview
    except Exception as e:
        raise HTTPException(400, f"文件解析失败: {e}")
    finally:
        os.unlink(tmp_path)

@router.post("/ai-map")
def ai_column_map(
    excel_columns: str = Form(...),
    db_columns: str = Form(...)
):
    import json
    excel_cols = json.loads(excel_columns)
    db_cols = json.loads(db_columns)
    mappings = service.ai_map_columns(excel_cols, db_cols)
    return {"mappings": mappings}

@router.post("/confirm")
def confirm_import(
    data_type_id: int = Form(...),
    period: str = Form(...),
    file_name: str = Form(...),
    column_mappings: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    data_type = db.query(DataType).filter(DataType.id == data_type_id).first()
    if not data_type:
        raise HTTPException(404, "数据表不存在")
    mappings = json.loads(column_mappings)
    batch_id = str(uuid.uuid4())
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    try:
        record = service.import_file(
            db=db, file_path=tmp_path, data_type_id=data_type_id,
            period=period, file_name=file_name, table_name=data_type.table_name,
            column_mappings=mappings, batch_id=batch_id
        )
        return {"message": "导入成功", "row_count": record.row_count, "batch_id": batch_id, "record_id": record.id}
    except Exception as e:
        raise HTTPException(400, f"导入失败: {e}")
    finally:
        os.unlink(tmp_path)

@router.get("/", response_model=list[ImportRecordResponse])
def list_imports(db: Session = Depends(get_db)):
    return db.query(ImportRecord).order_by(ImportRecord.uploaded_at.desc()).all()

@router.get("/{record_id}/data")
def get_import_data(record_id: int, db: Session = Depends(get_db)):
    record = db.query(ImportRecord).filter(ImportRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "导入记录不存在")
    if not record.batch_id:
        raise HTTPException(400, "该记录没有批次标识")
    data_type = db.query(DataType).filter(DataType.id == record.data_type_id).first()
    if not data_type:
        raise HTTPException(404, "数据表不存在")
    from sqlalchemy import text
    sql = f"SELECT * FROM `{data_type.table_name}` WHERE batch_id = :bid"
    result = db.execute(text(sql), {"bid": record.batch_id})
    headers = list(result.keys())
    rows = [list(r) for r in result.fetchall()]
    return {"headers": headers, "rows": rows, "row_count": len(rows)}
