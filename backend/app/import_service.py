import os
import re
import json
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
        chinese_cols = [c for c in df.columns if any('一' <= ch <= '鿿' for ch in c)]
        ai_translations = {}
        if chinese_cols:
            ai_translations = self._ai_translate_columns(chinese_cols)
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
            name = ai_translations.get(col, self._to_snake_case(col))
            columns.append({
                "name": name,
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

    def _ai_translate_columns(self, chinese_cols: list[str]) -> dict[str, str]:
        """Call LLM to translate Chinese column names to English snake_case"""
        prompt = f"""You are a database naming assistant. Translate these Chinese column names to English snake_case identifiers suitable for MySQL columns.
Rules: use concise descriptive names, lowercase with underscores, no abbreviations that lose meaning.
Return ONLY a JSON object mapping original Chinese name to English snake_case name. No explanation.

Columns: {json.dumps(chinese_cols, ensure_ascii=False)}"""
        try:
            from app.llm_adapter import DashScopeProvider
            llm = DashScopeProvider()
            raw = llm.generate([{"role": "system", "content": "You are a helpful assistant. Always respond with valid JSON only."}, {"role": "user", "content": prompt}], temperature=0.1)
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        return {}

    def ai_map_columns(self, excel_columns: list[str], db_columns: list[dict]) -> list[dict]:
        """Call LLM to suggest optimal column mappings between Excel and DB"""
        db_info = [{"name": c["name"], "type": c.get("type", "unknown")} for c in db_columns]
        prompt = f"""You are a data mapping assistant. Given Excel column headers and database column definitions, suggest the best one-to-one mapping between them.

Excel columns: {json.dumps(excel_columns, ensure_ascii=False)}
Database columns: {json.dumps(db_info, ensure_ascii=False)}

Rules:
- Each Excel column maps to at most one DB column (one-to-one)
- Each DB column is used by at most one Excel column
- Use semantic matching, not just exact string match
- Consider context: Chinese business terms vs English DB names
- Return ONLY a JSON array of objects with keys: excel_column, db_column, confidence (0-1)
- For columns that cannot be mapped, set db_column to null

Example output:
[{{"excel_column": "销售额", "db_column": "revenue", "confidence": 0.95}}]"""
        try:
            from app.llm_adapter import DashScopeProvider
            llm = DashScopeProvider()
            raw = llm.generate([{"role": "system", "content": "You are a helpful assistant. Always respond with valid JSON only."}, {"role": "user", "content": prompt}], temperature=0.1)
            json_match = re.search(r'\[.*\]', raw, re.DOTALL)
            if json_match:
                ai_mappings = json.loads(json_match.group())
                # Build result combining AI suggestions with existing logic
                used_db = set()
                results = []
                for m in ai_mappings:
                    match_type = "ai" if m.get("confidence", 0) > 0.7 else "manual"
                    db_col = m.get("db_column")
                    if db_col and db_col not in used_db:
                        used_db.add(db_col)
                    results.append({
                        "excel_column": m.get("excel_column"),
                        "db_column": db_col,
                        "match_type": match_type
                    })
                # Add unmatched DB columns
                mapped_db = {m["db_column"] for m in results if m.get("db_column")}
                for c in db_columns:
                    if c["name"] not in mapped_db:
                        results.append({
                            "excel_column": None,
                            "db_column": c["name"],
                            "match_type": "unmatched"
                        })
                return results
        except Exception:
            pass
        return []

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
        batch_id: str = None,
        uploaded_by: str = "system"
    ) -> ImportRecord:
        record = ImportRecord(
            data_type_id=data_type_id,
            period=period,
            file_name=file_name,
            batch_id=batch_id,
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
            if batch_id:
                df["batch_id"] = batch_id

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
