from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class DataType(Base):
    __tablename__ = "data_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    table_name = Column(String(255), nullable=False)
    columns_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    data_type_id = Column(Integer, ForeignKey("data_types.id"), nullable=False)
    config_json = Column(JSON, nullable=False)
    shared_token = Column(String(64), nullable=True)
    token_expires = Column(DateTime, nullable=True)
    created_by = Column(String(50), default="system")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class ImportRecord(Base):
    __tablename__ = "import_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_type_id = Column(Integer, ForeignKey("data_types.id"), nullable=False)
    period = Column(String(7), nullable=False)
    file_name = Column(String(255), nullable=False)
    row_count = Column(Integer, default=0)
    status = Column(String(20), default="success")
    error_log = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())
    uploaded_by = Column(String(50), default="system")

class AISession(Base):
    __tablename__ = "ai_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False)
    data_type_id = Column(Integer, ForeignKey("data_types.id"), nullable=False)
    user = Column(String(50), default="anonymous")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class AIMessage(Base):
    __tablename__ = "ai_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("ai_sessions.session_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sql_query = Column(Text, nullable=True)
    result_preview = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
