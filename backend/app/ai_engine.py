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
1. 理解用户意图，提取: 时间范围、筛选条件、聚合指标、分组维度
2. 信息不完整或不明确时，在 "clarification" 字段中提出追问（最多一个）
3. 信息足够时，生成 MySQL 查询语句放在 "sql" 字段中
4. 对查询结果做简要分析，放在 "analysis" 字段中
5. 生成3-4个后续建议放在 "follow_ups" 列表中

你必须输出严格JSON，格式如下:
{{"clarification": "追问内容或null", "sql": "SELECT语句或null", "analysis": "分析文字或null", "follow_ups": ["建议1", "建议2", "建议3"]}}

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

    def execute_query(self, data_type: DataType, sql: str) -> dict:
        validate_sql(sql)
        if "LIMIT" not in sql.upper():
            sql = f"{sql.rstrip(';')} LIMIT {settings.max_result_rows}"
        from sqlalchemy import text
        result = self.db.execute(text(sql))
        return {"headers": list(result.keys()), "rows": [list(r) for r in result.fetchall()]}
