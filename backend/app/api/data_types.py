from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DataType
from app.schemas import DataTypeCreate, DataTypeResponse
from app.ddl import create_table_if_not_exists, drop_table_if_exists

router = APIRouter()

@router.post("/", response_model=DataTypeResponse)
def create_data_type(data: DataTypeCreate, db: Session = Depends(get_db)):
    existing = db.query(DataType).filter(DataType.code == data.code).first()
    if existing:
        raise HTTPException(400, f"数据表标识 '{data.code}' 已存在")
    db_name = data.database_name or ""
    check_db = db_name if db_name else text("DATABASE()")
    if db_name:
        result = db.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = :db AND table_name = :tn"), {"db": db_name, "tn": data.table_name})
    else:
        result = db.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = :tn"), {"tn": data.table_name})
    if result.scalar() > 0:
        raise HTTPException(400, f"物理表名 '{data.table_name}' 已存在")
    dt = DataType(code=data.code, name=data.name, database_name=data.database_name, table_name=data.table_name, columns_json=data.columns_json)
    db.add(dt)
    db.commit()
    db.refresh(dt)
    try:
        create_table_if_not_exists(data.table_name, data.columns_json, db_name or None)
    except Exception as e:
        db.delete(dt)
        db.commit()
        raise HTTPException(400, f"创建物理表失败: {e}")
    return dt

@router.get("/", response_model=list[DataTypeResponse])
def list_data_types(db: Session = Depends(get_db)):
    return db.query(DataType).order_by(DataType.created_at.desc()).all()

@router.get("/{type_id}", response_model=DataTypeResponse)
def get_data_type(type_id: int, db: Session = Depends(get_db)):
    dt = db.query(DataType).filter(DataType.id == type_id).first()
    if not dt:
        raise HTTPException(404, "数据表不存在")
    return dt

@router.delete("/{type_id}")
def delete_data_type(type_id: int, db: Session = Depends(get_db)):
    dt = db.query(DataType).filter(DataType.id == type_id).first()
    if not dt:
        raise HTTPException(404, "数据表不存在")
    table_name = dt.table_name
    db.delete(dt)
    db.commit()
    try:
        drop_table_if_exists(table_name)
    except Exception:
        pass
    return {"message": "已删除"}
