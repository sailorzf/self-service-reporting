# 自助报表系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-service reporting system with Excel import, drag-and-drop report designer, and AI-powered conversational analysis.

**Architecture:** Vue3 SPA frontend + Python FastAPI backend + MySQL 8.x. Backend handles Excel parsing, dynamic SQL generation from JSON configs, and AI query translation via DashScope Qwen.

**Tech Stack:** Python FastAPI, SQLAlchemy, Vue3, Element Plus, ECharts, DashScope (Qwen), openpyxl, MySQL 8.x

---

## File Structure Map

### Backend (`backend/`)

| File | Responsibility |
|------|---------------|
| `backend/app/main.py` | FastAPI app entry, CORS, route registration |
| `backend/app/config.py` | Settings (DB URL, DashScope API key, max joins) |
| `backend/app/database.py` | SQLAlchemy engine, session factory |
| `backend/app/models.py` | ORM models: DataType, Report, ImportRecord, AISession, AIMessage |
| `backend/app/schemas.py` | Pydantic schemas for API request/response |
| `backend/app/api/imports.py` | Excel upload, parse preview, confirm import |
| `backend/app/api/reports.py` | Report CRUD, execute, export, share |
| `backend/app/api/ai.py` | AI session management, message handling |
| `backend/app/api/data_types.py` | Data type CRUD |
| `backend/app/api/share.py` | Public share endpoint |
| `backend/app/report_engine.py` | Core: config parser → SQL builder → executor → formatter |
| `backend/app/import_service.py` | Excel parsing, table creation, data import |
| `backend/app/ai_engine.py` | AI query pipeline: intent → SQL → execute → analyze |
| `backend/app/llm_adapter.py` | LLM provider abstraction (DashScope default) |
| `backend/app/security.py` | SQL validation, sanitization |
| `backend/tests/test_report_engine.py` | Report engine unit tests |
| `backend/tests/test_import_service.py` | Import service tests |
| `backend/tests/test_ai_engine.py` | AI engine tests (mocked LLM) |
| `backend/tests/test_security.py` | SQL security tests |
| `backend/requirements.txt` | Python dependencies |

### Frontend (`frontend/`)

| File | Responsibility |
|------|---------------|
| `frontend/index.html` | HTML entry |
| `frontend/package.json` | npm dependencies |
| `frontend/vite.config.js` | Vite configuration |
| `frontend/src/main.js` | Vue app entry |
| `frontend/src/App.vue` | Root component with layout |
| `frontend/src/api/index.js` | API client (fetch wrapper) |
| `frontend/src/views/ImportView.vue` | Data import page |
| `frontend/src/views/ReportListView.vue` | Report list page |
| `frontend/src/views/ReportDesigner.vue` | Drag-and-drop designer + AI panel |
| `frontend/src/views/ShareView.vue` | Public share view |
| `frontend/src/components/ChartRenderer.vue` | ECharts wrapper |
| `frontend/src/components/TableRenderer.vue` | Data table display |
| `frontend/src/components/AIPanel.vue` | AI chat panel with follow-up buttons |
| `frontend/src/components/ReportPreview.vue` | Report preview component |

---

## Task Breakdown

### Task 1: Project Scaffolding + Backend Foundation

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/models.py`
- Create: `backend/app/schemas.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi>=0.115.0
uvicorn>=0.30.0
sqlalchemy>=2.0.0
pymysql>=1.1.0
openpyxl>=3.1.0
pandas>=2.0.0
httpx>=0.27.0
pydantic>=2.0.0
python-multipart>=0.0.9
```

- [ ] **Step 2: Create config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://root:password@localhost:3306/report_db"
    dashscope_api_key: str = ""
    dashscope_model: str = "qwen-plus"
    max_joins: int = 3
    sql_timeout: int = 5
    max_result_rows: int = 1000

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 3: Create database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = DeclarativeBase()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Create models.py**

```python
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
    session_id = Column(String(64), ForeignKey("ai_sessions.session_id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sql_query = Column(Text, nullable=True)
    result_preview = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 5: Create schemas.py**

```python
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

# Data Type
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

# Import
class ImportPreview(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int

class ImportConfirm(BaseModel):
    data_type_id: int
    period: str
    file_name: str
    data: list[dict[str, Any]]

# Report
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
    data_type_id: int
    config_json: ReportConfig

class ReportResponse(BaseModel):
    id: int
    name: str
    data_type_id: int
    config_json: dict[str, Any]
    shared_token: Optional[str] = None
    token_expires: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Query execution
class QueryExecute(BaseModel):
    data_type_id: Optional[int] = None
    config: ReportConfig
    override_filters: list[FilterSpec] = []

class QueryResult(BaseModel):
    headers: list[str]
    rows: list[list[Any]]
    chart_data: Optional[dict[str, Any]] = None

# AI
class AIMessageRequest(BaseModel):
    content: str

class AIResponse(BaseModel):
    text: str
    sql_query: Optional[str] = None
    result_preview: Optional[dict[str, Any]] = None
    follow_ups: list[str] = []

class AISessionCreate(BaseModel):
    data_type_id: int
    session_id: Optional[str] = None

# Import Record
class ImportRecordResponse(BaseModel):
    id: int
    data_type_id: int
    period: str
    file_name: str
    row_count: int
    status: str
    error_log: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    uploaded_by: str

    class Config:
        from_attributes = True
```

- [ ] **Step 6: Create main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.api import data_types, imports, reports, ai, share

Base.metadata.create_all(bind=engine)

app = FastAPI(title="自助报表系统", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data_types.router, prefix="/api/data-types", tags=["data-types"])
app.include_router(imports.router, prefix="/api/imports", tags=["imports"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(share.router, prefix="/api/share", tags=["share"])

@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Create empty API modules**

```python
# backend/app/api/__init__.py (empty)
# backend/app/__init__.py (empty)
```

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend foundation - FastAPI, SQLAlchemy, models, schemas"
```

---

### Task 2: SQL Security Layer

**Files:**
- Create: `backend/app/security.py`
- Create: `backend/tests/test_security.py`

- [ ] **Step 1: Write failing test for SQL validation**

```python
# backend/tests/test_security.py
import pytest
from app.security import validate_sql

def test_valid_select_passes():
    sql = "SELECT `站点`, SUM(`充电量`) FROM `data_operation` GROUP BY `站点`"
    assert validate_sql(sql) is True

def test_delete_blocked():
    with pytest.raises(ValueError, match="DELETE"):
        validate_sql("DELETE FROM `data_operation`")

def test_insert_blocked():
    with pytest.raises(ValueError, match="INSERT"):
        validate_sql("INSERT INTO `data_operation` VALUES (1)")

def test_update_blocked():
    with pytest.raises(ValueError, match="UPDATE"):
        validate_sql("UPDATE `data_operation` SET `充电量` = 100")

def test_drop_blocked():
    with pytest.raises(ValueError, match="DROP"):
        validate_sql("DROP TABLE `data_operation`")

def test_select_with_subquery_blocked():
    # Block subqueries for safety
    with pytest.raises(ValueError):
        validate_sql("SELECT * FROM `data_operation` WHERE id IN (SELECT id FROM other)")

def test_validate_field_against_schema():
    from app.security import validate_fields
    schema_fields = {"站点", "区域", "充电量", "金额"}
    assert validate_fields(["站点", "充电量"], schema_fields) is True

def test_validate_field_unknown_rejected():
    from app.security import validate_fields
    schema_fields = {"站点", "区域", "充电量"}
    with pytest.raises(ValueError, match="未知字段"):
        validate_fields(["未知字段"], schema_fields)
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd backend && python -m pytest tests/test_security.py -v
```
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement security.py**

```python
# backend/app/security.py
import re

FORBIDDEN_KEYWORDS = re.compile(
    r'\b(DELETE|INSERT|UPDATE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE)\b',
    re.IGNORECASE
)

ALLOWED_AGGREGATIONS = {"SUM", "AVG", "COUNT", "MAX", "MIN"}

def validate_sql(sql: str) -> bool:
    """Validate SQL is a safe SELECT-only query."""
    if FORBIDDEN_KEYWORDS.search(sql):
        forbidden = FORBIDDEN_KEYWORDS.findall(sql)[0].upper()
        raise ValueError(f"禁止操作: {forbidden}。只允许SELECT查询")

    # Block subqueries
    subquery_pattern = re.compile(r'\(\s*SELECT\b', re.IGNORECASE)
    if subquery_pattern.search(sql):
        raise ValueError("不支持子查询")

    return True

def validate_fields(fields: list[str], schema_fields: set[str]) -> bool:
    """Validate all fields exist in the schema."""
    for field in fields:
        # Strip alias prefix like "op."
        clean_field = field.split(".")[-1].strip("`")
        if clean_field not in schema_fields:
            raise ValueError(f"未知字段: {field}")
    return True

def validate_aggregation(func_name: str) -> bool:
    """Validate aggregation function is allowed."""
    if func_name.upper() not in ALLOWED_AGGREGATIONS:
        raise ValueError(f"不支持的聚合函数: {func_name}。仅支持: {', '.join(sorted(ALLOWED_AGGREGATIONS))}")
    return True

def validate_filter_operator(op: str) -> bool:
    """Validate filter operator is safe."""
    allowed = {"=", "!=", ">", "<", ">=", "<=", "IN", "LIKE", "BETWEEN"}
    if op.upper() not in allowed:
        raise ValueError(f"不支持的操作符: {op}")
    return True
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd backend && python -m pytest tests/test_security.py -v
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/security.py backend/tests/test_security.py
git commit -m "feat: add SQL security validation layer"
```

---

### Task 3: Report Engine (Core)

**Files:**
- Create: `backend/app/report_engine.py`
- Create: `backend/tests/test_report_engine.py`

- [ ] **Step 1: Write failing test for SQL generation**

```python
# backend/tests/test_report_engine.py
import pytest
from app.report_engine import SQLBuilder, ReportEngine
from app.schemas import ReportConfig, FilterSpec, JoinSpec, TableSpec

def test_build_simple_select():
    config = ReportConfig(
        columns=["站点", "充电量"],
        aggregations={"充电量": "sum"},
        group_by=["站点"],
        filters=[],
        sort=None,
        limit=100,
        chart_type="bar"
    )
    sql = SQLBuilder.build(config, table_name="data_operation")
    assert "SELECT" in sql
    assert "`站点`" in sql
    assert "SUM(`充电量`)" in sql
    assert "FROM `data_operation`" in sql
    assert "GROUP BY" in sql
    assert "LIMIT 100" in sql

def test_build_with_filters():
    config = ReportConfig(
        columns=["区域", "充电量"],
        aggregations={"充电量": "sum"},
        group_by=["区域"],
        filters=[
            FilterSpec(field="区域", op="=", value="华东"),
            FilterSpec(field="时间", op=">=", value="2024-01")
        ],
        sort={"field": "充电量", "order": "desc"},
        limit=50,
        chart_type="bar"
    )
    sql = SQLBuilder.build(config, table_name="data_operation")
    assert "`区域` = '华东'" in sql
    assert "`时间` >= '2024-01'" in sql
    assert "ORDER BY `充电量` DESC" in sql
    assert "LIMIT 50" in sql

def test_build_with_joins():
    config = ReportConfig(
        tables=[
            TableSpec(data_type_id=1, alias="op"),
            TableSpec(data_type_id=2, alias="fc")
        ],
        joins=[
            JoinSpec(
                left_table="op",
                right_table="fc",
                join_type="LEFT",
                on=[{"left": "站点", "right": "站点"}]
            )
        ],
        columns=["op.站点", "op.充电量", "fc.预估充电量"],
        aggregations={"op.充电量": "sum", "fc.预估充电量": "sum"},
        group_by=["op.站点"],
        filters=[FilterSpec(field="op.月份", op=">=", value="2024-01")],
        sort=None,
        limit=100,
        chart_type="bar"
    )
    sql = SQLBuilder.build_multi(config, {
        "op": "data_operation",
        "fc": "data_forecast"
    })
    assert "FROM `data_operation` AS `op`" in sql
    assert "LEFT JOIN `data_forecast` AS `fc`" in sql
    assert "ON `op`.`站点` = `fc`.`站点`" in sql
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd backend && python -m pytest tests/test_report_engine.py -v
```
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement report_engine.py**

```python
# backend/app/report_engine.py
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.schemas import ReportConfig
from app.security import validate_sql, validate_fields, validate_aggregation, validate_filter_operator
from app.config import settings

class SQLBuilder:
    @staticmethod
    def escape_col(col: str) -> str:
        """Escape a column name with backticks."""
        return f"`{col.strip('`')}`"

    @staticmethod
    def escape_val(val: Any) -> str:
        """Escape a value for SQL (use parameterized queries in real impl)."""
        if val is None:
            return "NULL"
        if isinstance(val, (int, float)):
            return str(val)
        return f"'{str(val).replace(chr(39), chr(39)+chr(39))}'"

    @classmethod
    def build(cls, config: ReportConfig, table_name: str) -> str:
        """Build SQL for single-table query."""
        # Validate aggregations
        for col, func in config.aggregations.items():
            validate_aggregation(func)

        # Validate filters
        for f in config.filters:
            validate_filter_operator(f.op)

        # Build SELECT columns
        select_cols = []
        for col in config.columns:
            col_clean = col.split(".")[-1].strip("`")
            if col_clean in config.aggregations:
                func = config.aggregations[col_clean]
                select_cols.append(f"{func.upper()}({cls.escape_col(col_clean)}) AS {cls.escape_col(col_clean)}")
            elif col_clean not in config.aggregations:
                select_cols.append(cls.escape_col(col_clean))

        if not select_cols:
            select_cols = ["*"]

        sql_parts = [f"SELECT {', '.join(select_cols)}"]
        sql_parts.append(f"FROM {cls.escape_col(table_name)}")

        # WHERE
        if config.filters:
            conditions = []
            for f in config.filters:
                field = f.field.split(".")[-1].strip("`")
                if f.op.upper() == "IN":
                    vals = ", ".join(cls.escape_val(v) for v in (f.value if isinstance(f.value, list) else [f.value]))
                    conditions.append(f"{cls.escape_col(field)} IN ({vals})")
                elif f.op.upper() == "BETWEEN":
                    if isinstance(f.value, list) and len(f.value) == 2:
                        conditions.append(f"{cls.escape_col(field)} BETWEEN {cls.escape_val(f.value[0])} AND {cls.escape_val(f.value[1])}")
                    else:
                        conditions.append(f"{cls.escape_col(field)} {f.op} {cls.escape_val(f.value)}")
                elif f.op.upper() == "LIKE":
                    conditions.append(f"{cls.escape_col(field)} LIKE {cls.escape_val(f'%{f.value}%')}")
                else:
                    conditions.append(f"{cls.escape_col(field)} {f.op} {cls.escape_val(f.value)}")
            sql_parts.append(f"WHERE {' AND '.join(conditions)}")

        # GROUP BY
        if config.group_by and config.aggregations:
            gb_cols = [cls.escape_col(c.split(".")[-1].strip("`")) for c in config.group_by]
            sql_parts.append(f"GROUP BY {', '.join(gb_cols)}")

        # ORDER BY
        if config.sort:
            sort_col = config.sort["field"].split(".")[-1].strip("`")
            order = config.sort.get("order", "asc").upper()
            if order not in ("ASC", "DESC"):
                order = "ASC"
            sql_parts.append(f"ORDER BY {cls.escape_col(sort_col)} {order}")

        # LIMIT
        limit = min(config.limit, settings.max_result_rows)
        sql_parts.append(f"LIMIT {limit}")

        return " ".join(sql_parts)

    @classmethod
    def build_multi(cls, config: ReportConfig, table_map: dict[str, str]) -> str:
        """Build SQL for multi-table query with JOINs."""
        if not config.tables or len(config.tables) < 1:
            raise ValueError("多表查询需要指定tables")
        if len(config.tables) > settings.max_joins + 1:
            raise ValueError(f"最多支持{settings.max_joins + 1}个表关联")

        # Validate aggregations
        for col, func in config.aggregations.items():
            validate_aggregation(func)

        # Validate filters
        for f in config.filters:
            validate_filter_operator(f.op)

        # Build SELECT columns (with aliases)
        select_cols = []
        for col in config.columns:
            parts = col.split(".")
            if len(parts) == 2:
                alias, col_name = parts
                col_name = col_name.strip("`")
                if col in config.aggregations:
                    func = config.aggregations[col]
                    select_cols.append(f"{func.upper()}(`{alias}`.`{col_name}`) AS `{col_name}`")
                else:
                    select_cols.append(f"`{alias}`.`{col_name}`")
            else:
                col_name = col.strip("`")
                if col_name in config.aggregations:
                    func = config.aggregations[col_name]
                    select_cols.append(f"{func.upper()}(`{col_name}`) AS `{col_name}`")
                else:
                    select_cols.append(f"`{col_name}`")

        if not select_cols:
            select_cols = ["*"]

        # FROM + JOINs
        primary = config.tables[0]
        sql_parts = [f"FROM {cls.escape_col(table_map[primary.alias])} AS `{primary.alias}`"]

        if config.joins:
            for join in config.joins:
                right_table = config.tables[1] if len(config.tables) > 1 else None
                if not right_table:
                    raise ValueError("JOIN 需要指定第二个表")
                on_conditions = []
                for on_clause in join.on:
                    left_col = on_clause["left"]
                    right_col = on_clause["right"]
                    on_conditions.append(f"`{join.left_table}`.`{left_col}` = `{join.right_table}`.`{right_col}`")
                join_type = join.join_type.upper()
                if join_type not in ("LEFT", "INNER", "RIGHT"):
                    join_type = "LEFT"
                sql_parts.insert(0, f"SELECT {', '.join(select_cols)}")
                right_alias = right_table.alias
                sql_parts.append(f"{join_type} JOIN {cls.escape_col(table_map[right_alias])} AS `{right_alias}` ON {' AND '.join(on_conditions)}")
                break

        # If no joins were added, add SELECT at the front
        if not sql_parts[0].startswith("SELECT"):
            sql_parts.insert(0, f"SELECT {', '.join(select_cols)}")

        # WHERE
        if config.filters:
            conditions = []
            for f in config.filters:
                parts = f.field.split(".")
                if len(parts) == 2:
                    alias, field = parts
                    field = field.strip("`")
                    cond_field = f"`{alias}`.`{field}`"
                else:
                    field = f.field.strip("`")
                    cond_field = f"`{field}`"

                if f.op.upper() == "IN":
                    vals = ", ".join(cls.escape_val(v) for v in (f.value if isinstance(f.value, list) else [f.value]))
                    conditions.append(f"{cond_field} IN ({vals})")
                else:
                    conditions.append(f"{cond_field} {f.op} {cls.escape_val(f.value)}")
            sql_parts.append(f"WHERE {' AND '.join(conditions)}")

        # GROUP BY
        if config.group_by and config.aggregations:
            gb_cols = []
            for c in config.group_by:
                parts = c.split(".")
                if len(parts) == 2:
                    gb_cols.append(f"`{parts[0]}`.`{parts[1].strip('`')}`")
                else:
                    gb_cols.append(f"`{c.strip('`')}`")
            sql_parts.append(f"GROUP BY {', '.join(gb_cols)}")

        # ORDER BY
        if config.sort:
            parts = config.sort["field"].split(".")
            if len(parts) == 2:
                sort_col = f"`{parts[0]}`.`{parts[1].strip('`')}`"
            else:
                sort_col = f"`{config.sort['field'].strip('`')}`"
            order = config.sort.get("order", "asc").upper()
            if order not in ("ASC", "DESC"):
                order = "ASC"
            sql_parts.append(f"ORDER BY {sort_col} {order}")

        # LIMIT
        limit = min(config.limit, settings.max_result_rows)
        sql_parts.append(f"LIMIT {limit}")

        return " ".join(sql_parts)


class DataFormatter:
    @staticmethod
    def to_table(headers: list[str], rows: list[list[Any]]) -> dict:
        return {"headers": headers, "rows": rows}

    @staticmethod
    def to_chart(headers: list[str], rows: list[list[Any]], chart_type: str = "bar") -> dict:
        """Format data for ECharts."""
        if not rows:
            return {"categories": [], "series": []}

        categories = [str(row[0]) for row in rows]
        series = []
        for i, header in enumerate(headers[1:], 1):
            series.append({
                "name": header,
                "data": [row[i] if isinstance(row[i], (int, float)) else float(row[i]) for row in rows]
            })

        return {"categories": categories, "series": series}


class ReportEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def execute(self, config: ReportConfig, table_name: str) -> dict:
        """Execute a single-table report query."""
        sql = SQLBuilder.build(config, table_name)
        validate_sql(sql)
        result = self.db.execute(text(sql))
        rows = result.fetchall()
        headers = list(result.keys())
        formatted_rows = [list(r) for r in rows]
        return {
            "headers": headers,
            "rows": formatted_rows,
            "chart_data": DataFormatter.to_chart(headers, formatted_rows, config.chart_type),
        }

    def execute_multi(self, config: ReportConfig, table_map: dict[str, str]) -> dict:
        """Execute a multi-table report query."""
        sql = SQLBuilder.build_multi(config, table_map)
        validate_sql(sql)
        result = self.db.execute(text(sql))
        rows = result.fetchall()
        headers = list(result.keys())
        formatted_rows = [list(r) for r in rows]
        return {
            "headers": headers,
            "rows": formatted_rows,
            "chart_data": DataFormatter.to_chart(headers, formatted_rows, config.chart_type),
        }
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd backend && python -m pytest tests/test_report_engine.py -v
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/report_engine.py backend/tests/test_report_engine.py
git commit -m "feat: implement report engine with SQL builder and data formatter"
```

---

### Task 4: Import Service

**Files:**
- Create: `backend/app/import_service.py`
- Create: `backend/tests/test_import_service.py`
- Create: `backend/app/api/imports.py`

- [ ] **Step 1: Write failing test for Excel parsing**

```python
# backend/tests/test_import_service.py
import pytest
import tempfile
import os
from openpyxl import Workbook
from app.import_service import ImportService

@pytest.fixture
def sample_excel(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["站点", "区域", "充电量", "月份"])
    ws.append(["A站", "华东", 100.5, "2024-01"])
    ws.append(["B站", "华南", 200.3, "2024-01"])
    path = str(tmp_path / "test.xlsx")
    wb.save(path)
    return path

def test_parse_excel(sample_excel):
    service = ImportService()
    columns, rows = service.parse(sample_excel)
    assert columns == ["站点", "区域", "充电量", "月份"]
    assert len(rows) == 2
    assert rows[0][0] == "A站"
    assert rows[1][1] == "华南"

def test_import_to_db(sample_excel, db_session):
    service = ImportService()
    record = service.import_file(
        db=db_session,
        file_path=sample_excel,
        data_type_id=1,
        period="2024-01",
        file_name="test.xlsx",
        table_name="data_operation"
    )
    assert record.status == "success"
    assert record.row_count == 2
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd backend && python -m pytest tests/test_import_service.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement import_service.py**

```python
# backend/app/import_service.py
import os
from datetime import datetime
from typing import Any
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
import pandas as pd
from app.models import ImportRecord

class ImportService:
    def parse(self, file_path: str) -> tuple[list[str], list[list[Any]]]:
        """Parse Excel file and return (columns, rows)."""
        df = pd.read_excel(file_path, engine="openpyxl")
        # Normalize column names (strip whitespace)
        df.columns = [str(c).strip() for c in df.columns]
        columns = list(df.columns)
        rows = df.values.tolist()
        return columns, rows

    def preview(self, file_path: str, max_rows: int = 10) -> dict:
        """Parse Excel and return preview data."""
        columns, rows = self.parse(file_path)
        return {
            "columns": columns,
            "rows": rows[:max_rows],
            "row_count": len(rows)
        }

    def import_file(
        self,
        db: Session,
        file_path: str,
        data_type_id: int,
        period: str,
        file_name: str,
        table_name: str,
        uploaded_by: str = "system"
    ) -> ImportRecord:
        """Import Excel data into the specified table."""
        record = ImportRecord(
            data_type_id=data_type_id,
            period=period,
            file_name=file_name,
            uploaded_by=uploaded_by
        )

        try:
            df = pd.read_excel(file_path, engine="openpyxl")
            df.columns = [str(c).strip() for c in df.columns]

            # Add metadata columns
            df["period"] = period
            df["source_file"] = file_name
            df["uploaded_at"] = datetime.now()
            df["uploaded_by"] = uploaded_by

            # Write to database
            df.to_sql(table_name, db.get_bind(), if_exists="append", index=False)

            record.status = "success"
            record.row_count = len(df)
            db.add(record)
            db.commit()
            db.refresh(record)
        except Exception as e:
            db.rollback()
            record.status = "failed"
            record.error_log = str(e)
            db.add(record)
            db.commit()
            db.refresh(record)
            raise

        return record
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_import_service.py -v
```
Expected: PASS (may need DB setup for full integration test)

- [ ] **Step 5: Create imports API**

```python
# backend/app/api/imports.py
import os
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DataType, ImportRecord
from app.schemas import ImportPreview, ImportRecordResponse
from app.import_service import ImportService

router = APIRouter()
service = ImportService()

@router.post("/upload", response_model=ImportPreview)
async def upload_preview(file: UploadFile = File(...)):
    """Upload Excel and return preview without importing."""
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
    """Confirm import: re-upload file + metadata to import."""
    data_type = db.query(DataType).filter(DataType.id == data_type_id).first()
    if not data_type:
        raise HTTPException(404, "数据类型不存在")

    import tempfile, os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    try:
        record = service.import_file(
            db=db,
            file_path=tmp_path,
            data_type_id=data_type_id,
            period=period,
            file_name=file_name,
            table_name=data_type.table_name
        )
        return {"message": "导入成功", "row_count": record.row_count}
    except Exception as e:
        raise HTTPException(400, f"导入失败: {e}")
    finally:
        os.unlink(tmp_path)

@router.get("/", response_model=list[ImportRecordResponse])
def list_imports(db: Session = Depends(get_db)):
    return db.query(ImportRecord).order_by(ImportRecord.uploaded_at.desc()).all()
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/import_service.py backend/app/api/imports.py backend/tests/test_import_service.py
git commit -m "feat: add Excel import service and API endpoints"
```

---

### Task 5: Data Types API

**Files:**
- Create: `backend/app/api/data_types.py`

- [ ] **Step 1: Create data_types API**

```python
# backend/app/api/data_types.py
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

    dt = DataType(
        code=data.code,
        name=data.name,
        table_name=data.table_name,
        columns_json=data.columns_json
    )
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/data_types.py
git commit -m "feat: add data types CRUD API"
```

---

### Task 6: Reports API

**Files:**
- Create: `backend/app/api/reports.py`

- [ ] **Step 1: Create reports API**

```python
# backend/app/api/reports.py
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Report, DataType
from app.schemas import ReportCreate, ReportResponse, QueryExecute, QueryResult
from app.report_engine import ReportEngine, DataFormatter

router = APIRouter()

@router.post("/", response_model=ReportResponse)
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    dt = db.query(DataType).filter(DataType.id == report.data_type_id).first()
    if not dt:
        raise HTTPException(404, "数据类型不存在")

    r = Report(
        name=report.name,
        data_type_id=report.data_type_id,
        config_json=report.config_json.model_dump()
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

@router.get("/", response_model=list[ReportResponse])
def list_reports(db: Session = Depends(get_db)):
    return db.query(Report).order_by(Report.updated_at.desc()).all()

@router.post("/execute", response_model=QueryResult)
def execute_query(query: QueryExecute, db: Session = Depends(get_db)):
    """Execute a report config without saving (preview mode)."""
    engine = ReportEngine(db)

    # Multi-table query
    if query.config.tables and len(query.config.tables) > 1:
        table_map = {}
        for t in query.config.tables:
            dt = db.query(DataType).filter(DataType.id == t.data_type_id).first()
            if not dt:
                raise HTTPException(404, f"数据类型 {t.data_type_id} 不存在")
            table_map[t.alias] = dt.table_name
        return engine.execute_multi(query.config, table_map)

    # Single-table query
    if query.data_type_id:
        dt = db.query(DataType).filter(DataType.id == query.data_type_id).first()
        if not dt:
            raise HTTPException(404, "数据类型不存在")
        return engine.execute(query.config, dt.table_name)

    raise HTTPException(400, "需要指定data_type_id或tables")

@router.post("/{report_id}/execute", response_model=QueryResult)
def execute_report(report_id: int, db: Session = Depends(get_db)):
    """Execute a saved report."""
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
    """Generate a share link for a report."""
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise HTTPException(404, "报表不存在")

    r.shared_token = str(uuid.uuid4())
    r.token_expires = datetime.now() + timedelta(days=days)
    db.commit()
    return {"share_url": f"/share/{r.shared_token}", "expires": r.token_expires}

@router.get("/{report_id}/export")
def export_report(report_id: int, db: Session = Depends(get_db)):
    """Export report data as Excel."""
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise HTTPException(404, "报表不存在")

    dt = db.query(DataType).filter(DataType.id == r.data_type_id).first()
    engine = ReportEngine(db)
    config = ReportConfig(**r.config_json)
    result = engine.execute(config, dt.table_name)

    # Generate Excel
    import io
    from openpyxl import Workbook
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/reports.py
git commit -m "feat: add reports CRUD, execute, export, and share API"
```

---

### Task 7: LLM Adapter + AI Engine

**Files:**
- Create: `backend/app/llm_adapter.py`
- Create: `backend/app/ai_engine.py`
- Create: `backend/app/api/ai.py`
- Create: `backend/tests/test_ai_engine.py`

- [ ] **Step 1: Create LLM adapter**

```python
# backend/app/llm_adapter.py
from abc import ABC, abstractmethod
from openai import OpenAI
from app.config import settings

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: list[dict], temperature: float = 0.3) -> str:
        pass

class DashScopeProvider(LLMProvider):
    """Qwen via DashScope (OpenAI compatible)."""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = settings.dashscope_model

    def generate(self, messages: list[dict], temperature: float = 0.3) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content
```

- [ ] **Step 2: Create AI engine**

```python
# backend/app/ai_engine.py
import json
import re
from typing import Any
from sqlalchemy.orm import Session
from app.llm_adapter import DashScopeProvider
from app.models import DataType
from app.security import validate_sql
from app.config import settings

class AIEngine:
    def __init__(self, db: Session):
        self.db = db
        self.llm = DashScopeProvider()

    def build_system_prompt(self, data_type: DataType, conversation: list[dict]) -> str:
        """Build system prompt with schema and context."""
        fields = [f['name'] for f in data_type.columns_json]
        fields_str = ", ".join(fields)

        history = ""
        for msg in conversation[-6:]:  # Last 6 messages for context
            history += f"- {msg['role']}: {msg['content'][:200]}\n"

        return f"""你是数据分析助手。用户正在查询数据集 "{data_type.name}" ({data_type.table_name})。
可用字段: {fields_str}

当前对话上下文:
{history if history else "新对话"}

任务:
1. 理解用户意图，提取: 时间范围、筛选条件、聚合指标、分组维度
2. 信息不完整或不明确时，在 "clarification" 字段中提出追问（最多一个）
3. 信息足够时，生成 MySQL 查询语句放在 "sql" 字段中
4. 对查询结果做简要分析，放在 "analysis" 字段中
5. 生成3-4个后续建议放在 "follow_ups" 列表中

你必须输出严格JSON，格式如下:
{{
    "clarification": "追问内容或null",
    "sql": "SELECT语句或null",
    "analysis": "分析文字或null",
    "follow_ups": ["建议1", "建议2", "建议3"]
}}

安全限制:
- 只生成SELECT语句
- 不允许DELETE/UPDATE/INSERT/DROP
- 最多返回1000行"""

    def parse_user_message(self, data_type: DataType, conversation: list[dict], user_message: str) -> dict:
        """Process user NL and return structured response."""
        system_prompt = self.build_system_prompt(data_type, conversation)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        raw = self.llm.generate(messages)

        # Extract JSON from response
        try:
            # Try to find JSON block
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"analysis": raw, "sql": None, "clarification": None, "follow_ups": ["继续分析"]}
        except json.JSONDecodeError:
            result = {"analysis": raw, "sql": None, "clarification": None, "follow_ups": ["继续分析"]}

        return result

    def execute_query(self, data_type: DataType, sql: str) -> dict:
        """Execute AI-generated SQL safely."""
        validate_sql(sql)

        # Auto-append LIMIT
        if "LIMIT" not in sql.upper():
            sql = f"{sql.rstrip(';')} LIMIT {settings.max_result_rows}"

        from sqlalchemy import text
        result = self.db.execute(text(sql))
        rows = result.fetchall()
        headers = list(result.keys())
        formatted_rows = [list(r) for r in rows]

        return {
            "headers": headers,
            "rows": formatted_rows,
        }
```

- [ ] **Step 3: Create AI API**

```python
# backend/app/api/ai.py
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
    dt = db.query(DataType).filter(DataType.id == req.data_type_id).first()
    if not dt:
        raise HTTPException(404, "数据类型不存在")

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

    dt = db.query(DataType).filter(DataType.id == session.data_type_id).first()
    if not dt:
        raise HTTPException(404, "数据类型不存在")

    # Get conversation history
    messages = db.query(AIMessage).filter(
        AIMessage.session_id == session_id
    ).order_by(AIMessage.created_at.asc()).all()

    conversation = [{"role": m.role, "content": m.content} for m in messages]

    # Save user message
    user_msg = AIMessage(session_id=session_id, role="user", content=req.content)
    db.add(user_msg)
    db.commit()

    # Process with AI
    engine = AIEngine(db)
    result = engine.parse_user_message(dt, conversation, req.content)

    # Execute SQL if generated
    query_result = None
    sql_text = None
    if result.get("sql"):
        sql_text = result["sql"]
        try:
            query_result = engine.execute_query(dt, sql_text)
        except Exception as e:
            result["analysis"] = f"SQL执行出错: {e}"

    # Save assistant response
    assistant_content = result.get("analysis", result.get("clarification", ""))
    assistant_msg = AIMessage(
        session_id=session_id,
        role="assistant",
        content=assistant_content,
        sql_query=sql_text,
        result_preview=query_result
    )
    db.add(assistant_msg)
    db.commit()

    return AIResponse(
        text=assistant_content,
        sql_query=sql_text,
        result_preview=query_result,
        follow_ups=result.get("follow_ups", [])
    )

@router.get("/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AISession).filter(AISession.session_id == session_id).first()
    if not session:
        raise HTTPException(404, "会话不存在")

    messages = db.query(AIMessage).filter(
        AIMessage.session_id == session_id
    ).order_by(AIMessage.created_at.asc()).all()

    return {
        "session_id": session_id,
        "data_type_id": session.data_type_id,
        "messages": [{"role": m.role, "content": m.content, "result": m.result_preview} for m in messages]
    }
```

- [ ] **Step 4: Write AI engine tests (mocked)**

```python
# backend/tests/test_ai_engine.py
import pytest
from unittest.mock import patch, MagicMock
from app.ai_engine import AIEngine
from app.models import DataType

@pytest.fixture
def mock_data_type():
    return DataType(
        id=1,
        code="operation",
        name="运营数据",
        table_name="data_operation",
        columns_json=[
            {"name": "站点", "type": "varchar"},
            {"name": "区域", "type": "varchar"},
            {"name": "充电量", "type": "decimal"},
            {"name": "月份", "type": "varchar"}
        ]
    )

def test_build_system_prompt(mock_data_type):
    engine = AIEngine.__new__(AIEngine)  # Skip __init__ for unit test
    prompt = engine.build_system_prompt(mock_data_type, [])
    assert "运营数据" in prompt
    assert "站点" in prompt
    assert "充电量" in prompt

@patch("app.ai_engine.DashScopeProvider")
def test_parse_user_message(mock_provider, mock_data_type):
    mock_instance = MagicMock()
    mock_instance.generate.return_value = '{"sql": "SELECT SUM(`充电量`) FROM `data_operation`", "analysis": "总充电量1000度", "clarification": null, "follow_ups": ["按站点拆分"]}'
    mock_provider.return_value = mock_instance

    db_mock = MagicMock()
    engine = AIEngine(db_mock)
    engine.llm = mock_instance

    result = engine.parse_user_message(mock_data_type, [], "总充电量多少")
    assert result["sql"] is not None
    assert "SELECT" in result["sql"]
    assert "按站点拆分" in result["follow_ups"]
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm_adapter.py backend/app/ai_engine.py backend/app/api/ai.py backend/tests/test_ai_engine.py
git commit -m "feat: add AI engine with LLM adapter and chat API"
```

---

### Task 8: Share API

**Files:**
- Create: `backend/app/api/share.py`

- [ ] **Step 1: Create share API**

```python
# backend/app/api/share.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Report, DataType
from app.schemas import QueryResult
from app.report_engine import ReportEngine
from app.schemas import ReportConfig

router = APIRouter()

@router.get("/{token}", response_model=QueryResult)
def view_share(token: str, db: Session = Depends(get_db)):
    """View a shared report by token."""
    report = db.query(Report).filter(Report.shared_token == token).first()
    if not report:
        raise HTTPException(404, "分享链接无效")

    if report.token_expires and report.token_expires < datetime.now():
        raise HTTPException(403, "分享链接已过期")

    dt = db.query(DataType).filter(DataType.id == report.data_type_id).first()
    if not dt:
        raise HTTPException(404, "数据类型不存在")

    engine = ReportEngine(db)
    config = ReportConfig(**report.config_json)
    return engine.execute(config, dt.table_name)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/share.py
git commit -m "feat: add public share endpoint with token and expiry"
```

---

### Task 9: Frontend Scaffolding

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/api/index.js`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "report-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "element-plus": "^2.7.0",
    "echarts": "^5.5.0",
    "vue-echarts": "^7.0.0",
    "@element-plus/icons-vue": "^2.3.0",
    "vue-draggable-plus": "^0.5.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 2: Create vite.config.js**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 3: Create index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>自助报表系统</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

- [ ] **Step 4: Create main.js**

```javascript
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

const app = createApp(App)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus)
app.mount('#app')
```

- [ ] **Step 5: Create App.vue**

```vue
<template>
  <el-container style="height: 100vh;">
    <el-header style="background: #fff; border-bottom: 1px solid #eee; display: flex; align-items: center;">
      <h2 style="margin: 0;">自助报表系统</h2>
      <el-menu mode="horizontal" :ellipsis="false" style="margin-left: 40px;">
        <router-link to="/import" custom v-slot="{ navigate }">
          <el-menu-item @click="navigate">数据导入</el-menu-item>
        </router-link>
        <router-link to="/reports" custom v-slot="{ navigate }">
          <el-menu-item @click="navigate">报表中心</el-menu-item>
        </router-link>
      </el-menu>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
</script>
```

- [ ] **Step 6: Create router/index.js**

```javascript
// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/reports' },
  { path: '/import', component: () => import('../views/ImportView.vue') },
  { path: '/reports', component: () => import('../views/ReportListView.vue') },
  { path: '/reports/new', component: () => import('../views/ReportDesigner.vue') },
  { path: '/share/:token', component: () => import('../views/ShareView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
```

- [ ] **Step 6b: Update main.js to use router**

```javascript
// Replace frontend/src/main.js content
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import router from './router'

const app = createApp(App)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus)
app.use(router)
app.mount('#app')
```

- [ ] **Step 7: Create api/index.js**

```javascript
const BASE_URL = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || '请求失败')
  }
  return res.json()
}

export const api = {
  // Data Types
  getDataTypes: () => request('/data-types/'),
  createDataType: (data) => request('/data-types/', { method: 'POST', body: JSON.stringify(data) }),

  // Imports
  uploadPreview: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${BASE_URL}/imports/upload`, { method: 'POST', body: formData })
    return res.json()
  },

  // Reports
  getReports: () => request('/reports/'),
  createReport: (data) => request('/reports/', { method: 'POST', body: JSON.stringify(data) }),
  executeQuery: (data) => request('/reports/execute', { method: 'POST', body: JSON.stringify(data) }),
  executeReport: (id) => request(`/reports/${id}/execute`, { method: 'POST' }),
  shareReport: (id, days = 7) => request(`/reports/${id}/share?days=${days}`, { method: 'POST' }),

  // AI
  createAISession: (data) => request('/ai/sessions', { method: 'POST', body: JSON.stringify(data) }),
  sendAIMessage: (sessionId, content) =>
    request(`/ai/sessions/${sessionId}/message`, { method: 'POST', body: JSON.stringify({ content }) }),
  getAISession: (sessionId) => request(`/ai/sessions/${sessionId}`),

  // Share
  viewShare: (token) => request(`/share/${token}`),
}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Vue3 frontend with Element Plus and API client"
```

---

### Task 10: Frontend Views

**Files:**
- Create: `frontend/src/views/ImportView.vue`
- Create: `frontend/src/views/ReportListView.vue`
- Create: `frontend/src/views/ReportDesigner.vue`
- Create: `frontend/src/views/ShareView.vue`
- Create: `frontend/src/components/ChartRenderer.vue`
- Create: `frontend/src/components/TableRenderer.vue`
- Create: `frontend/src/components/AIPanel.vue`
- Create: `frontend/src/components/ReportPreview.vue`

- [ ] **Step 1: Create TableRenderer.vue**

```vue
<template>
  <el-table :data="tableData" border stripe style="width: 100%;">
    <el-table-column
      v-for="header in data.headers"
      :key="header"
      :prop="header"
      :label="header"
    />
  </el-table>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, required: true }
})

const tableData = computed(() =>
  props.data.rows.map(row => {
    const obj = {}
    props.data.headers.forEach((h, i) => { obj[h] = row[i] })
    return obj
  })
)
</script>
```

- [ ] **Step 2: Create ChartRenderer.vue**

```vue
<template>
  <div ref="chartRef" style="width: 100%; height: 400px;"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  chartData: { type: Object, required: true },
  chartType: { type: String, default: 'bar' }
})

const chartRef = ref(null)
let chart = null

onMounted(() => {
  chart = echarts.init(chartRef.value)
  renderChart()
})

watch(() => props.chartData, renderChart, { deep: true })

function renderChart() {
  if (!chart || !props.chartData) return

  const option = {
    title: { text: '报表结果' },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: props.chartData.categories || []
    },
    yAxis: { type: 'value' },
    series: props.chartData.series?.map(s => ({
      ...s,
      type: props.chartType === 'bar' ? 'bar' : props.chartType === 'line' ? 'line' : 'pie'
    })) || []
  }

  chart.setOption(option, true)
}
</script>
```

- [ ] **Step 3: Create AIPanel.vue**

```vue
<template>
  <div class="ai-panel">
    <h4>AI 分析</h4>
    <div class="messages" ref="msgRef">
      <div v-for="(msg, i) in messages" :key="i" :class="['msg', msg.role]">
        <div class="text">{{ msg.content }}</div>
        <div v-if="msg.result" class="result">
          <TableRenderer v-if="msg.result.headers" :data="msg.result" />
        </div>
      </div>
    </div>
    <div class="follow-ups" v-if="followUps.length">
      <el-button
        v-for="(fu, i) in followUps"
        :key="i"
        size="small"
        @click="sendFollowUp(fu)"
      >{{ fu }}</el-button>
    </div>
    <div class="input-area">
      <el-input
        v-model="input"
        placeholder="输入你的问题..."
        @keyup.enter="sendMessage"
        :disabled="loading"
      />
      <el-button type="primary" @click="sendMessage" :loading="loading">发送</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api'
import TableRenderer from './TableRenderer.vue'

const props = defineProps({
  sessionId: { type: String, required: true }
})

const emit = defineEmits(['query-complete'])

const messages = ref([])
const followUps = ref([])
const input = ref('')
const loading = ref(false)

async function sendMessage(text) {
  if (!text) text = input.value
  if (!text) return

  loading.value = true
  messages.value.push({ role: 'user', content: text })

  try {
    const res = await api.sendAIMessage(props.sessionId, text)
    messages.value.push({ role: 'assistant', content: res.text, result: res.result_preview })
    followUps.value = res.follow_ups || []
    emit('query-complete', res)
  } catch (e) {
    messages.value.push({ role: 'assistant', content: `错误: ${e.message}` })
  } finally {
    loading.value = false
    input.value = ''
  }
}

function sendFollowUp(text) {
  sendMessage(text)
}

defineExpose({ sendMessage })
</script>

<style scoped>
.ai-panel { display: flex; flex-direction: column; height: 100%; }
.messages { flex: 1; overflow-y: auto; padding: 10px; }
.msg { margin-bottom: 12px; }
.msg.user { text-align: right; }
.msg.assistant { text-align: left; }
.follow-ups { padding: 8px; display: flex; gap: 8px; flex-wrap: wrap; }
.input-area { display: flex; gap: 8px; padding: 8px; }
</style>
```

- [ ] **Step 4: Create ReportPreview.vue**

```vue
<template>
  <div>
    <div v-if="data && data.headers" style="margin-bottom: 16px;">
      <ChartRenderer v-if="data.chart_data && props.chartType !== 'table'" :chart-data="data.chart_data" :chart-type="props.chartType" />
      <TableRenderer :data="data" />
    </div>
    <el-empty v-else description="暂无数据" />
  </div>
</template>

<script setup>
import TableRenderer from './TableRenderer.vue'
import ChartRenderer from './ChartRenderer.vue'

const props = defineProps({
  data: { type: Object, default: null },
  chartType: { type: String, default: 'table' }
})
</script>
```

- [ ] **Step 5: Create ImportView.vue**

```vue
<template>
  <div>
    <h3>数据导入</h3>
    <el-form label-width="100px">
      <el-form-item label="数据类型">
        <el-select v-model="dataTypeId" placeholder="选择数据类型">
          <el-option v-for="dt in dataTypes" :key="dt.id" :label="dt.name" :value="dt.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="月份">
        <el-input v-model="period" placeholder="如: 2024-01" />
      </el-form-item>
      <el-form-item label="上传文件">
        <el-upload
          action=""
          :auto-upload="false"
          :on-change="handleFile"
          accept=".xlsx,.xls"
        >
          <el-button>选择Excel文件</el-button>
        </el-upload>
      </el-form-item>
    </el-form>

    <div v-if="preview" style="margin-top: 16px;">
      <h4>预览 (前10行)</h4>
      <el-table :data="previewRows" border>
        <el-table-column v-for="col in preview.columns" :key="col" :prop="col" :label="col" />
      </el-table>
      <p>共 {{ preview.row_count }} 行</p>
      <el-button type="primary" @click="confirmImport">确认导入</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const dataTypes = ref([])
const dataTypeId = ref(null)
const period = ref('')
const file = ref(null)
const preview = ref(null)

onMounted(async () => {
  dataTypes.value = await api.getDataTypes()
})

const previewRows = computed(() =>
  preview.value?.rows?.map(row => {
    const obj = {}
    preview.value.columns.forEach((c, i) => { obj[c] = row[i] })
    return obj
  }) || []
)

async function handleFile(uploadFile) {
  file.value = uploadFile.raw
  preview.value = await api.uploadPreview(file.value)
}

async function confirmImport() {
  if (!dataTypeId.value || !period.value || !file.value) {
    ElMessage.warning('请填写完整信息')
    return
  }
  const formData = new FormData()
  formData.append('file', file.value)
  formData.append('data_type_id', dataTypeId.value)
  formData.append('period', period.value)
  formData.append('file_name', file.value.name)

  try {
    const res = await fetch('/api/imports/confirm', { method: 'POST', body: formData })
    const result = await res.json()
    ElMessage.success(`导入成功，共 ${result.row_count} 行`)
    preview.value = null
    period.value = ''
    file.value = null
  } catch (e) {
    ElMessage.error('导入失败')
  }
}
</script>
```

- [ ] **Step 6: Create ReportListView.vue**

```vue
<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h3>报表中心</h3>
      <router-link to="/reports/new">
        <el-button type="primary">新建报表</el-button>
      </router-link>
    </div>
    <el-table :data="reports" border>
      <el-table-column prop="name" label="报表名称" />
      <el-table-column prop="created_at" label="创建时间" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="executeReport(row.id)">执行</el-button>
          <el-button size="small" @click="shareReport(row.id)">分享</el-button>
          <el-button size="small" @click="exportReport(row.id)">导出</el-button>
        </template>
      </el-table-column>
    </el-table>
    <ReportPreview :data="result" :chart-type="currentChartType" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import ReportPreview from '../components/ReportPreview.vue'

const reports = ref([])
const result = ref(null)
const currentChartType = ref('table')

onMounted(async () => {
  reports.value = await api.getReports()
})

async function executeReport(id) {
  result.value = await api.executeReport(id)
}

async function shareReport(id) {
  const res = await api.shareReport(id)
  ElMessage.success(`分享链接: ${res.share_url}`)
}

async function exportReport(id) {
  window.open(`/api/reports/${id}/export`)
}
</script>
```

- [ ] **Step 7: Create ReportDesigner.vue**

```vue
<template>
  <div class="designer">
    <el-row :gutter="16" style="height: calc(100vh - 100px);">
      <!-- Left: Field Panel -->
      <el-col :span="5">
        <el-card>
          <template #header>字段面板</template>
          <el-select v-model="dataTypeId" placeholder="选择数据类型" style="margin-bottom: 12px;">
            <el-option v-for="dt in dataTypes" :key="dt.id" :label="dt.name" :value="dt.id" />
          </el-select>
          <el-checkbox-group v-model="selectedColumns">
            <el-checkbox v-for="col in availableColumns" :key="col" :value="col">{{ col }}</el-checkbox>
          </el-checkbox-group>
          <el-divider />
          <el-form size="small">
            <el-form-item label="聚合">
              <el-select v-model="aggregation" placeholder="选择聚合函数">
                <el-option label="SUM" value="sum" />
                <el-option label="AVG" value="avg" />
                <el-option label="COUNT" value="count" />
                <el-option label="MAX" value="max" />
                <el-option label="MIN" value="min" />
              </el-select>
            </el-form-item>
            <el-form-item label="图表类型">
              <el-select v-model="chartType">
                <el-option label="表格" value="table" />
                <el-option label="柱状图" value="bar" />
                <el-option label="折线图" value="line" />
                <el-option label="饼图" value="pie" />
              </el-select>
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="runQuery" :loading="loading" style="width: 100%;">查询</el-button>
          <el-button @click="saveReport" style="width: 100%; margin-top: 8px;">保存报表</el-button>
        </el-card>
      </el-col>

      <!-- Center: Preview -->
      <el-col :span="12">
        <el-card style="height: 100%;">
          <template #header>预览</template>
          <ReportPreview :data="result" :chart-type="chartType" />
        </el-card>
      </el-col>

      <!-- Right: AI Panel -->
      <el-col :span="7">
        <el-card style="height: 100%;">
          <AIPanel v-if="aiSessionId" :session-id="aiSessionId" @query-complete="onAIQueryComplete" />
          <div v-else>
            <el-button @click="initAISession" type="primary">开启AI分析</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import AIPanel from '../components/AIPanel.vue'
import ReportPreview from '../components/ReportPreview.vue'

const dataTypes = ref([])
const dataTypeId = ref(null)
const selectedColumns = ref([])
const aggregation = ref('')
const chartType = ref('table')
const result = ref(null)
const loading = ref(false)
const aiSessionId = ref(null)

const availableColumns = computed(() => {
  const dt = dataTypes.value.find(d => d.id === dataTypeId.value)
  return dt ? dt.columns_json.map(c => c.name) : []
})

onMounted(async () => {
  dataTypes.value = await api.getDataTypes()
})

async function runQuery() {
  if (!dataTypeId.value || selectedColumns.value.length === 0) {
    ElMessage.warning('请选择数据类型和字段')
    return
  }

  loading.value = true
  const config = {
    columns: selectedColumns.value,
    aggregations: aggregation.value && selectedColumns.value[0]
      ? { [selectedColumns.value[0]]: aggregation.value }
      : {},
    group_by: selectedColumns.value.filter(c => c !== selectedColumns.value[0]),
    filters: [],
    chart_type: chartType.value,
    limit: 100
  }

  try {
    result.value = await api.executeQuery({
      data_type_id: dataTypeId.value,
      config
    })
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function initAISession() {
  if (!dataTypeId.value) {
    ElMessage.warning('请先选择数据类型')
    return
  }
  const res = await api.createAISession({ data_type_id: dataTypeId.value })
  aiSessionId.value = res.session_id
}

function onAIQueryComplete(res) {
  if (res.result_preview) {
    result.value = res.result_preview
  }
}

async function saveReport() {
  const name = prompt('报表名称:')
  if (!name) return

  await api.createReport({
    name,
    data_type_id: dataTypeId.value,
    config_json: {
      columns: selectedColumns.value,
      aggregations: aggregation.value && selectedColumns.value[0]
        ? { [selectedColumns.value[0]]: aggregation.value }
        : {},
      group_by: [],
      filters: [],
      chart_type: chartType.value,
      limit: 100
    }
  })
  ElMessage.success('报表已保存')
}
</script>

<style scoped>
.designer { padding: 16px; }
</style>
```

- [ ] **Step 8: Create ShareView.vue**

```vue
<template>
  <div>
    <h3>分享报表</h3>
    <ReportPreview v-if="result" :data="result" chart-type="bar" />
    <el-alert v-if="error" :title="error" type="error" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import ReportPreview from '../components/ReportPreview.vue'

const route = useRoute()
const result = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    result.value = await api.viewShare(route.params.token)
  } catch (e) {
    error.value = e.message
  }
})
</script>
```

- [ ] **Step 9: Commit**

```bash
git add frontend/src/
git commit -m "feat: implement all frontend views and components"
```

---

### Task 11: .env Template + README + Database Init

**Files:**
- Create: `backend/.env.example`
- Create: `backend/README.md`
- Create: `frontend/README.md`

- [ ] **Step 1: Create .env.example**

```
# backend/.env.example
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/report_db
DASHSCOPE_API_KEY=your-api-key-here
DASHSCOPE_MODEL=qwen-plus
MAX_JOINS=3
SQL_TIMEOUT=5
MAX_RESULT_ROWS=1000
```

- [ ] **Step 2: Create backend README**

```markdown
# Backend - 自助报表系统

## Setup

```bash
cp .env.example .env
# Edit .env with your MySQL credentials and DashScope API key

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## API Docs

Visit http://localhost:8000/docs for Swagger UI.
```

- [ ] **Step 3: Create frontend README**

```markdown
# Frontend - 自助报表系统

## Setup

```bash
npm install
npm run dev
```

Visit http://localhost:3000. API proxy to backend at :8000.
```

- [ ] **Step 4: Commit**

```bash
git add backend/.env.example backend/README.md frontend/README.md
git commit -m "docs: add setup instructions for backend and frontend"
```

---
