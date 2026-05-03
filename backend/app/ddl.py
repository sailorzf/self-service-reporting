from sqlalchemy import create_engine, text
from app.config import settings


def mysql_type(col: dict) -> str:
    t = col['type']
    if t == 'varchar':
        return f"VARCHAR({col.get('length', 255)})"
    elif t == 'decimal':
        return f"DECIMAL({col.get('precision', 10)},{col.get('scale', 2)})"
    elif t == 'int':
        return "INT"
    elif t == 'datetime':
        return "DATETIME"
    elif t == 'text':
        return "TEXT"
    return "VARCHAR(255)"


def _full_table_name(table_name: str, database_name: str | None = None) -> str:
    if database_name:
        return f"`{database_name}`.`{table_name}`"
    return f"`{table_name}`"


def columns_to_mysql_ddl(columns_json: list[dict], table_name: str, database_name: str | None = None) -> str:
    lines = []
    for col in columns_json:
        col_def = f"  `{col['name']}` {mysql_type(col)}"
        if not col.get('nullable', True):
            col_def += " NOT NULL"
        lines.append(col_def)
    lines.append("  `period` VARCHAR(20) DEFAULT NULL")
    lines.append("  `source_file` VARCHAR(255) DEFAULT NULL")
    lines.append("  `uploaded_at` DATETIME DEFAULT NULL")
    lines.append("  `uploaded_by` VARCHAR(100) DEFAULT NULL")
    lines.append("  `batch_id` VARCHAR(64) DEFAULT NULL")
    return f"CREATE TABLE IF NOT EXISTS {_full_table_name(table_name, database_name)} (\n" + ",\n".join(lines) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"


def create_table_if_not_exists(table_name: str, columns_json: list[dict], database_name: str | None = None):
    engine = create_engine(settings.database_url)
    ddl = columns_to_mysql_ddl(columns_json, table_name, database_name)
    with engine.connect() as conn:
        conn.execute(text(ddl))
        conn.commit()


def drop_table_if_exists(table_name: str, database_name: str | None = None):
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {_full_table_name(table_name, database_name)}"))
        conn.commit()
