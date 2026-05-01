import os
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DataType
from app.schemas import ImportPreview, ImportRecordResponse
from app.import_service import ImportService

router = APIRouter()
service = ImportService()

@router.post("/upload", response_model=ImportPreview)
async def upload_preview(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "仅支持Excel文件(.xlsx, .xls)")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        preview = service.preview(tmp_path)
        return preview
    except Exception as e:
        raise HTTPException(400, f"文件解析失败: {e}")
    finally:
        os.unlink(tmp_path)

@router.post("/confirm")
def confirm_import(
    data_type_id: int = Form(...),
    period: str = Form(...),
    file_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    data_type = db.query(DataType).filter(DataType.id == data_type_id).first()
    if not data_type:
        raise HTTPException(404, "数据类型不存在")
    import tempfile as tf
    with tf.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    try:
        record = service.import_file(
            db=db, file_path=tmp_path, data_type_id=data_type_id,
            period=period, file_name=file_name, table_name=data_type.table_name
        )
        return {"message": "导入成功", "row_count": record.row_count}
    except Exception as e:
        raise HTTPException(400, f"导入失败: {e}")
    finally:
        os.unlink(tmp_path)

@router.get("/", response_model=list[ImportRecordResponse])
def list_imports(db: Session = Depends(get_db)):
    return db.query(ImportRecord).order_by(ImportRecord.uploaded_at.desc()).all()
