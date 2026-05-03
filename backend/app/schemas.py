from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class DataTypeCreate(BaseModel):
    code: str
    name: str
    table_name: str
    columns_json: list[dict[str, Any]]

class DataTypeResponse(BaseModel):
    id: int
    code: str
    name: str
    table_name: str
    columns_json: list[dict[str, Any]]
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class ColumnMapping(BaseModel):
    excel_column: Optional[str] = None
    db_column: Optional[str] = None
    match_type: str

class ImportPreview(BaseModel):
    excel_columns: list[str]
    mappings: list[ColumnMapping]
    rows: list[list[Any]]
    row_count: int

class ImportConfirm(BaseModel):
    data_type_id: int
    period: str
    file_name: str
    data: list[dict[str, Any]]

class FilterSpec(BaseModel):
    field: str
    op: str
    value: Any

class JoinSpec(BaseModel):
    left_table: str
    right_table: str
    join_type: str = "LEFT"
    on: list[dict[str, str]]

class TableSpec(BaseModel):
    data_type_id: int
    alias: str

class ReportConfig(BaseModel):
    tables: Optional[list[TableSpec]] = None
    joins: Optional[list[JoinSpec]] = None
    columns: list[str]
    aggregations: dict[str, str] = {}
    group_by: list[str] = []
    filters: list[FilterSpec] = []
    sort: Optional[dict[str, str]] = None
    limit: int = 100
    chart_type: str = "table"

class ReportCreate(BaseModel):
    name: str
    data_type_id: Optional[int] = None
    config_json: Optional[Any] = None

class ReportResponse(BaseModel):
    id: int
    name: str
    data_type_id: Optional[int] = None
    config_json: Optional[dict[str, Any]] = None
    shared_token: Optional[str] = None
    token_expires: Optional[datetime] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class QueryExecute(BaseModel):
    data_type_id: Optional[int] = None
    config: Optional[ReportConfig] = None
    raw_sql: Optional[str] = None
    override_filters: list[FilterSpec] = []

class QueryResult(BaseModel):
    headers: list[str]
    rows: list[list[Any]]
    chart_data: Optional[dict[str, Any]] = None

class AIMessageRequest(BaseModel):
    content: str

class AIResponse(BaseModel):
    text: str
    sql_query: Optional[str] = None
    result_preview: Optional[dict[str, Any]] = None
    follow_ups: list[str] = []
    used_tables: list[str] = []

class AISessionCreate(BaseModel):
    data_type_id: Optional[int] = None
    session_id: Optional[str] = None

class ImportRecordResponse(BaseModel):
    id: int
    data_type_id: int
    period: str
    file_name: str
    row_count: int
    batch_id: Optional[str] = None
    status: str
    error_log: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    uploaded_by: str
    class Config:
        from_attributes = True

class CanvasComponent(BaseModel):
    id: str
    type: str  # "text" | "kpi" | "table" | "bar" | "line" | "pie"
    name: str = ""
    x: int = 16
    y: int = 16
    width: int = 260
    height: int = 180
    data_type_id: Optional[int] = None
    sql: str = ""
    chart_type: str = "table"
    theme_color: str = "#409eff"
    content: str = ""

class CanvasConfig(BaseModel):
    width: int = 1200
    height: int = 800

class ReportConfigCanvas(BaseModel):
    canvas: CanvasConfig = CanvasConfig()
    components: list[CanvasComponent] = []
