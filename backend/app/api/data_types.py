from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DataType
from app.schemas import DataTypeCreate, DataTypeResponse

router = APIRouter()

@router.post("/", response_model=DataTypeResponse)
def create_data_type(data: DataTypeCreate, db: Session = Depends(get_db)):
    existing = db.query(DataType).filter(DataType.code == data.code).first()
    if existing:
        raise HTTPException(400, f"数据类型代码 '{data.code}' 已存在")
    dt = DataType(code=data.code, name=data.name, table_name=data.table_name, columns_json=data.columns_json)
    db.add(dt)
    db.commit()
    db.refresh(dt)
    return dt

@router.get("/", response_model=list[DataTypeResponse])
def list_data_types(db: Session = Depends(get_db)):
    return db.query(DataType).order_by(DataType.created_at.desc()).all()

@router.get("/{type_id}", response_model=DataTypeResponse)
def get_data_type(type_id: int, db: Session = Depends(get_db)):
    dt = db.query(DataType).filter(DataType.id == type_id).first()
    if not dt:
        raise HTTPException(404, "数据类型不存在")
    return dt

@router.delete("/{type_id}")
def delete_data_type(type_id: int, db: Session = Depends(get_db)):
    dt = db.query(DataType).filter(DataType.id == type_id).first()
    if not dt:
        raise HTTPException(404, "数据类型不存在")
    db.delete(dt)
    db.commit()
    return {"message": "已删除"}
