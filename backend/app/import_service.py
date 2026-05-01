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

    def preview(self, file_path: str, columns_json: list[dict] = None, max_rows: int = 10) -> dict:
        df = pd.read_excel(file_path, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        excel_columns = list(df.columns)

        mappings = []
        if columns_json:
            defined_names = {c['name']: c for c in columns_json}
            for excel_col in excel_columns:
                if excel_col in defined_names:
                    mappings.append({"excel_column": excel_col, "db_column": excel_col, "match_type": "exact"})
                    continue
                normalized = excel_col.lower().replace(' ', '').replace('_', '').replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                matched = None
                for def_name in defined_names:
                    def_normalized = def_name.lower().replace(' ', '').replace('_', '').replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                    if normalized == def_normalized:
                        matched = def_name
                        break
                if matched:
                    mappings.append({"excel_column": excel_col, "db_column": matched, "match_type": "fuzzy"})
                else:
                    mappings.append({"excel_column": excel_col, "db_column": None, "match_type": "manual"})

            matched_db_cols = {m["db_column"] for m in mappings if m["db_column"]}
            for def_col in columns_json:
                if def_col['name'] not in matched_db_cols:
                    mappings.append({"excel_column": None, "db_column": def_col['name'], "match_type": "unmatched"})
        else:
            for excel_col in excel_columns:
                mappings.append({"excel_column": excel_col, "db_column": None, "match_type": "manual"})

        return {
            "excel_columns": excel_columns,
            "mappings": mappings,
            "rows": df.values.tolist()[:max_rows],
            "row_count": len(df)
        }

    def import_file(
        self,
        db: Session,
        file_path: str,
        data_type_id: int,
        period: str,
        file_name: str,
        table_name: str,
        column_mappings: list[dict],
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

            rename_map = {}
            for m in column_mappings:
                if m.get("excel_column") and m.get("db_column"):
                    rename_map[m["excel_column"]] = m["db_column"]
            df = df.rename(columns=rename_map)

            db_columns = [m["db_column"] for m in column_mappings if m.get("db_column")]
            keep_cols = [c for c in db_columns if c in df.columns]
            df = df[keep_cols]

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
