import os
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session
import pandas as pd
from app.models import ImportRecord

class ImportService:
    def parse(self, file_path: str) -> tuple[list[str], list[list[Any]]]:
        df = pd.read_excel(file_path, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        return list(df.columns), df.values.tolist()

    def preview(self, file_path: str, max_rows: int = 10) -> dict:
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
        record = ImportRecord(
            data_type_id=data_type_id,
            period=period,
            file_name=file_name,
            uploaded_by=uploaded_by
        )
        try:
            df = pd.read_excel(file_path, engine="openpyxl")
            df.columns = [str(c).strip() for c in df.columns]
            df["period"] = period
            df["source_file"] = file_name
            df["uploaded_at"] = datetime.now()
            df["uploaded_by"] = uploaded_by
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
