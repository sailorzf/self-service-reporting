from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.schemas import ReportConfig
from app.security import validate_sql, validate_aggregation, validate_filter_operator
from app.config import settings


class SQLBuilder:
    @staticmethod
    def escape_col(col: str) -> str:
        return f"`{col.strip('`')}`"

    @staticmethod
    def escape_val(val: Any) -> str:
        if val is None:
            return "NULL"
        if isinstance(val, (int, float)):
            return str(val)
        return f"'{str(val).replace(chr(39), chr(39)+chr(39))}'"

    @classmethod
    def build(cls, config: ReportConfig, table_name: str, database_name: str | None = None) -> str:
        full_table = f"`{database_name}`.`{table_name}`" if database_name else f"`{table_name}`"
        for col, func in config.aggregations.items():
            validate_aggregation(func)
        for f in config.filters:
            validate_filter_operator(f.op)

        select_cols = []
        for col in config.columns:
            col_clean = col.split(".")[-1].strip("`")
            if col_clean in config.aggregations:
                func = config.aggregations[col_clean]
                select_cols.append(
                    f"{func.upper()}({cls.escape_col(col_clean)}) AS {cls.escape_col(col_clean)}"
                )
            else:
                select_cols.append(cls.escape_col(col_clean))

        if not select_cols:
            select_cols = ["*"]

        sql_parts = [f"SELECT {', '.join(select_cols)}"]
        sql_parts.append(f"FROM {full_table}")

        if config.filters:
            conditions = []
            for f in config.filters:
                field = f.field.split(".")[-1].strip("`")
                op_upper = f.op.upper()
                if op_upper == "IN":
                    vals = ", ".join(
                        cls.escape_val(v)
                        for v in (f.value if isinstance(f.value, list) else [f.value])
                    )
                    conditions.append(f"{cls.escape_col(field)} IN ({vals})")
                elif op_upper == "BETWEEN":
                    if isinstance(f.value, list) and len(f.value) == 2:
                        conditions.append(
                            f"{cls.escape_col(field)} BETWEEN {cls.escape_val(f.value[0])} AND {cls.escape_val(f.value[1])}"
                        )
                    else:
                        conditions.append(
                            f"{cls.escape_col(field)} {f.op} {cls.escape_val(f.value)}"
                        )
                elif op_upper == "LIKE":
                    conditions.append(
                        f"{cls.escape_col(field)} LIKE {cls.escape_val(f'%{f.value}%')}"
                    )
                else:
                    conditions.append(
                        f"{cls.escape_col(field)} {f.op} {cls.escape_val(f.value)}"
                    )
            sql_parts.append(f"WHERE {' AND '.join(conditions)}")

        if config.group_by and config.aggregations:
            gb_cols = [cls.escape_col(c.split(".")[-1].strip("`")) for c in config.group_by]
            sql_parts.append(f"GROUP BY {', '.join(gb_cols)}")

        if config.sort:
            sort_col = config.sort["field"].split(".")[-1].strip("`")
            order = config.sort.get("order", "asc").upper()
            if order not in ("ASC", "DESC"):
                order = "ASC"
            sql_parts.append(f"ORDER BY {cls.escape_col(sort_col)} {order}")

        limit = min(config.limit, settings.max_result_rows)
        sql_parts.append(f"LIMIT {limit}")

        return " ".join(sql_parts)

    @classmethod
    def build_multi(cls, config: ReportConfig, table_map: dict[str, str]) -> str:
        if not config.tables or len(config.tables) < 1:
            raise ValueError("多表查询需要指定tables")
        if len(config.tables) > settings.max_joins + 1:
            raise ValueError(f"最多支持{settings.max_joins + 1}个表关联")

        for col, func in config.aggregations.items():
            validate_aggregation(func)
        for f in config.filters:
            validate_filter_operator(f.op)

        # Build SELECT columns
        select_cols = []
        for col in config.columns:
            parts = col.split(".")
            if len(parts) == 2:
                alias, col_name = parts
                col_name = col_name.strip("`")
                if col in config.aggregations:
                    func = config.aggregations[col]
                    select_cols.append(
                        f"{func.upper()}(`{alias}`.`{col_name}`) AS `{col_name}`"
                    )
                else:
                    select_cols.append(f"`{alias}`.`{col_name}`")
            else:
                col_name = col.strip("`")
                if col_name in config.aggregations:
                    func = config.aggregations[col_name]
                    select_cols.append(
                        f"{func.upper()}(`{col_name}`) AS `{col_name}`"
                    )
                else:
                    select_cols.append(f"`{col_name}`")

        if not select_cols:
            select_cols = ["*"]

        # Build FROM clause with primary table
        primary = config.tables[0]
        sql_parts = [
            f"FROM {cls.escape_col(table_map[primary.alias])} AS `{primary.alias}`"
        ]

        # Build JOIN clauses
        if config.joins:
            for join in config.joins:
                on_conditions = []
                for on_clause in join.on:
                    left_col = on_clause["left"]
                    right_col = on_clause["right"]
                    on_conditions.append(
                        f"`{join.left_table}`.`{left_col}` = `{join.right_table}`.`{right_col}`"
                    )
                join_type = join.join_type.upper()
                if join_type not in ("LEFT", "INNER", "RIGHT"):
                    join_type = "LEFT"

                # Find the right table spec
                right_alias = join.right_table
                right_table_name = table_map.get(right_alias)
                if not right_table_name:
                    raise ValueError(f"未找到表别名对应的表名: {right_alias}")

                sql_parts.append(
                    f"{join_type} JOIN {cls.escape_col(right_table_name)} AS `{right_alias}` "
                    f"ON {' AND '.join(on_conditions)}"
                )

        # Insert SELECT at the front
        sql_parts.insert(0, f"SELECT {', '.join(select_cols)}")

        # Build WHERE clause
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

                op_upper = f.op.upper()
                if op_upper == "IN":
                    vals = ", ".join(
                        cls.escape_val(v)
                        for v in (f.value if isinstance(f.value, list) else [f.value])
                    )
                    conditions.append(f"{cond_field} IN ({vals})")
                else:
                    conditions.append(f"{cond_field} {f.op} {cls.escape_val(f.value)}")
            sql_parts.append(f"WHERE {' AND '.join(conditions)}")

        # Build GROUP BY
        if config.group_by and config.aggregations:
            gb_cols = []
            for c in config.group_by:
                parts = c.split(".")
                if len(parts) == 2:
                    gb_cols.append(f"`{parts[0]}`.`{parts[1].strip('`')}`")
                else:
                    gb_cols.append(f"`{c.strip('`')}`")
            sql_parts.append(f"GROUP BY {', '.join(gb_cols)}")

        # Build ORDER BY
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

        limit = min(config.limit, settings.max_result_rows)
        sql_parts.append(f"LIMIT {limit}")

        return " ".join(sql_parts)


class DataFormatter:
    @staticmethod
    def to_table(headers: list[str], rows: list[list[Any]]) -> dict:
        return {"headers": headers, "rows": rows}

    @staticmethod
    def to_chart(
        headers: list[str], rows: list[list[Any]], chart_type: str = "bar"
    ) -> dict:
        if not rows:
            return {"categories": [], "series": []}

        # Detect long format: (time/dimension, group_name, value)
        # Aggregate and pivot to wide format: categories = unique first col, series = one per group
        if len(headers) == 3 and len(rows) > 0:
            col1, col2, col3 = headers
            # Check if col3 is numeric and col2 is categorical
            is_col3_numeric = True
            is_col2_categorical = False
            for row in rows:
                v = row[2]
                if v is not None and not isinstance(v, (int, float)):
                    try:
                        float(v)
                    except (ValueError, TypeError):
                        is_col3_numeric = False
                        break
            if is_col3_numeric:
                non_numeric_count = 0
                for row in rows:
                    v = row[1]
                    if not isinstance(v, (int, float)):
                        non_numeric_count += 1
                if non_numeric_count > len(rows) * 0.5:
                    is_col2_categorical = True

            if is_col3_numeric and is_col2_categorical:
                # Long format - pivot with aggregation (SUM)
                categories_map = {}
                category_list = []
                series_map = {}
                cat_order = 0
                for row in rows:
                    cat_key = str(row[0])
                    group = str(row[1])
                    val = row[2]
                    if val is None:
                        val = 0
                    elif isinstance(val, (int, float)):
                        pass
                    else:
                        try:
                            val = float(val)
                        except (ValueError, TypeError):
                            val = 0

                    if cat_key not in categories_map:
                        categories_map[cat_key] = cat_order
                        category_list.append(cat_key)
                        cat_order += 1
                    if group not in series_map:
                        series_map[group] = [0.0] * len(category_list)
                    while len(series_map[group]) < len(category_list):
                        series_map[group].append(0.0)
                    # Aggregate by SUM
                    series_map[group][categories_map[cat_key]] += val

                series = []
                for name, data in series_map.items():
                    series.append({
                        "name": name,
                        "data": [round(v, 2) if isinstance(v, float) else v for v in data[:len(category_list)]]
                    })

                return {"categories": category_list, "series": series}

        # Wide format: first column = categories, remaining columns = series
        categories = [str(row[0]) for row in rows]
        series = []
        for i, header in enumerate(headers[1:], 1):
            data = []
            for row in rows:
                val = row[i]
                if val is None:
                    data.append(0)
                elif isinstance(val, (int, float)):
                    data.append(val)
                else:
                    try:
                        data.append(float(val))
                    except (ValueError, TypeError):
                        data = None
                        break
            if data is not None:
                series.append({"name": header, "data": data})

        return {"categories": categories, "series": series}


class ReportEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def execute(self, config: ReportConfig, table_name: str, database_name: str | None = None) -> dict:
        sql = SQLBuilder.build(config, table_name, database_name)
        validate_sql(sql)
        result = self.db.execute(text(sql))
        rows = result.fetchall()
        headers = list(result.keys())
        formatted_rows = [list(r) for r in rows]
        return {
            "headers": headers,
            "rows": formatted_rows,
            "chart_data": DataFormatter.to_chart(
                headers, formatted_rows, config.chart_type
            ),
        }

    def execute_multi(self, config: ReportConfig, table_map: dict[str, str]) -> dict:
        sql = SQLBuilder.build_multi(config, table_map)
        validate_sql(sql)
        result = self.db.execute(text(sql))
        rows = result.fetchall()
        headers = list(result.keys())
        formatted_rows = [list(r) for r in rows]
        return {
            "headers": headers,
            "rows": formatted_rows,
            "chart_data": DataFormatter.to_chart(
                headers, formatted_rows, config.chart_type
            ),
        }
