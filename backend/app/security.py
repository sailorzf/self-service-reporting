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
