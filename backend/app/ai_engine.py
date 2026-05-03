import json
import re
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
        fields = [f['name'] for f in data_type.columns_json]
        fields_str = ", ".join(fields)
        history = ""
        for msg in conversation[-6:]:
            history += f"- {msg['role']}: {msg['content'][:200]}\n"
        return f"""你是数据分析助手。用户正在查询数据集 "{data_type.name}" ({data_type.table_name})。
可用字段: {fields_str}

当前对话上下文:
{history if history else "新对话"}

任务:
1. 理解用户意图，提取: 时间范围、筛选条件、指标字段、分组维度
2. 对于图表展示需求，SQL应查询原始明细数据，不做GROUP BY聚合。
   前端会自动按时间和分组维度进行聚合和作图。
   例如用户说"各充电站的服务费收入折线图"，SQL应为:
   SELECT statistics_date, station_name, service_fee FROM data_test_data ORDER BY statistics_date
   而不是 GROUP BY 聚合后的数据。只需 SELECT 时间列、分组列、指标列即可。
3. 信息不完整或不明确时，在 "clarification" 字段中提出追问（最多一个）
4. 信息足够时，生成 MySQL 查询语句放在 "sql" 字段中
5. 对查询结果做简要分析，放在 "analysis" 字段中
6. 生成3-4个后续建议放在 "follow_ups" 列表中

你必须输出严格JSON，格式如下:
{{"clarification": "追问内容或null", "sql": "SELECT语句或null", "analysis": "分析文字或null", "follow_ups": ["建议1", "建议2", "建议3"]}}

安全限制:
- 只生成SELECT语句
- 不允许DELETE/UPDATE/INSERT/DROP
- 最多返回1000行"""

    def build_system_prompt_multi(self, data_types: list[DataType], conversation: list[dict]) -> str:
        tables_info = []
        for dt in data_types:
            fields = [f['name'] for f in dt.columns_json]
            tables_info.append(f"- 表名: {dt.table_name} ({dt.name}), 字段: {', '.join(fields)}")
        tables_str = "\n".join(tables_info)
        history = ""
        for msg in conversation[-6:]:
            history += f"- {msg['role']}: {msg['content'][:200]}\n"
        return f"""你是数据分析助手。以下是可用的数据表及其字段：

{tables_str}

当前对话上下文:
{history if history else "新对话"}

任务:
1. 根据用户问题，自动选择最相关的数据表
2. 理解用户意图，提取: 时间范围、筛选条件、指标字段、分组维度
3. 对于图表展示需求，SQL应查询原始明细数据，不做GROUP BY聚合。
   前端会自动按时间和分组维度进行聚合和作图。
   例如: SELECT statistics_date, station_name, service_fee FROM data_test_data ORDER BY statistics_date
4. 信息不完整或不明确时，在 "clarification" 字段中提出追问（最多一个）
5. 信息足够时，生成 MySQL 查询语句放在 "sql" 字段中
6. 对查询结果做简要分析，放在 "analysis" 字段中
7. 生成3-4个后续建议放在 "follow_ups" 列表中
8. 在 "used_tables" 字段中列出你使用的表名（table_name）

你必须输出严格JSON，格式如下:
{{"clarification": "追问内容或null", "sql": "SELECT语句或null", "analysis": "分析文字或null", "follow_ups": ["建议1", "建议2", "建议3"], "used_tables": ["表名1"]}}

安全限制:
- 只生成SELECT语句
- 不允许DELETE/UPDATE/INSERT/DROP
- 最多返回1000行"""

    def parse_user_message(self, data_type: DataType, conversation: list[dict], user_message: str) -> dict:
        system_prompt = self.build_system_prompt(data_type, conversation)
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        raw = self.llm.generate(messages)
        try:
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"analysis": raw, "sql": None, "clarification": None, "follow_ups": ["继续分析"]}
        except json.JSONDecodeError:
            result = {"analysis": raw, "sql": None, "clarification": None, "follow_ups": ["继续分析"]}
        return result

    def parse_user_message_multi(self, data_types: list[DataType], conversation: list[dict], user_message: str) -> dict:
        system_prompt = self.build_system_prompt_multi(data_types, conversation)
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        raw = self.llm.generate(messages)
        try:
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"analysis": raw, "sql": None, "clarification": None, "follow_ups": ["继续分析"], "used_tables": []}
        except json.JSONDecodeError:
            result = {"analysis": raw, "sql": None, "clarification": None, "follow_ups": ["继续分析"], "used_tables": []}
        return result

    def execute_query(self, data_type: DataType, sql: str) -> dict:
        validate_sql(sql)
        if "LIMIT" not in sql.upper():
            sql = f"{sql.rstrip(';')} LIMIT {settings.max_result_rows}"
        from sqlalchemy import text
        result = self.db.execute(text(sql))
        return {"headers": list(result.keys()), "rows": [list(r) for r in result.fetchall()]}

    def execute_raw_sql(self, sql: str) -> dict:
        validate_sql(sql)
        if "LIMIT" not in sql.upper():
            sql = f"{sql.rstrip(';')} LIMIT {settings.max_result_rows}"
        from sqlalchemy import text
        result = self.db.execute(text(sql))
        return {"headers": list(result.keys()), "rows": [list(r) for r in result.fetchall()]}
