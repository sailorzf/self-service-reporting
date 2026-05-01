import os
import re
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

    def infer_schema(self, file_path: str, original_filename: str) -> dict:
        df = pd.read_excel(file_path, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        columns = []
        for col in df.columns:
            series = df[col].dropna()
            if len(series) == 0:
                col_type = "varchar"
                length = 255
            else:
                col_type = self._infer_column_type(series)
                length = 255
                if col_type == "varchar":
                    max_len = int(series.astype(str).str.len().max())
                    length = min(max(max_len * 2, 50), 500)
                elif col_type == "decimal":
                    max_val = series.max()
                    max_str_len = len(str(max_val).replace('.', '').replace('-', ''))
                    length = max(max_str_len, 10)
            columns.append({
                "name": self._to_snake_case(col),
                "type": col_type,
                "length": length if col_type == "varchar" else None,
                "precision": length if col_type == "decimal" else None,
                "scale": 2 if col_type == "decimal" else None,
                "nullable": True,
                "original_name": col
            })
        return {
            "columns": columns,
            "suggested_table_name": "data_" + self._to_snake_case(os.path.splitext(original_filename)[0]),
            "row_count": len(df),
            "preview": df.values.tolist()[:5],
            "preview_columns": list(df.columns)
        }

    def _infer_column_type(self, series: pd.Series) -> str:
        non_null = series.dropna()
        if len(non_null) == 0:
            return "varchar"
        # Try datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"
        # Try int
        if pd.api.types.is_integer_dtype(series):
            return "int"
        # Try float/decimal
        if pd.api.types.is_float_dtype(series):
            return "decimal"
        # Try parsing as number
        numeric_count = 0
        for v in non_null.head(20):
            try:
                float(str(v).replace(',', ''))
                numeric_count += 1
            except (ValueError, TypeError):
                pass
        if numeric_count == len(non_null.head(20)):
            return "decimal"
        # Try datetime parsing
        date_count = 0
        for v in non_null.head(20):
            try:
                pd.to_datetime(str(v))
                date_count += 1
            except (ValueError, TypeError):
                pass
        if date_count == len(non_null.head(20)):
            return "datetime"
        # Default to varchar
        max_len = non_null.astype(str).str.len().max()
        if max_len > 500:
            return "text"
        return "varchar"

    def _to_snake_case(self, text: str) -> str:
        text = re.sub(r'[（）()，,.\s]+', '_', text)
        text = re.sub(r'[^a-zA-Z0-9_一-鿿]', '', text)
        text = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', text)
        text = re.sub(r'_+', '_', text).lower().strip('_')
        if not text or text[0].isdigit():
            text = 'col_' + text
        return text

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
