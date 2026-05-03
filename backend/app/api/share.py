from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import Report
from app.report_engine import DataFormatter

router = APIRouter()


def serialize_value(v):
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


@router.get("/{token}")
def view_share(token: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.shared_token == token).first()
    if not report:
        raise HTTPException(404, "分享链接无效")
    if report.token_expires and report.token_expires < datetime.now():
        raise HTTPException(403, "分享链接已过期")

    config = report.config_json

    # Canvas format
    if isinstance(config, dict) and "canvas" in config and "components" in config:
        component_data = {}
        for comp in config["components"]:
            comp_id = comp["id"]
            sql = comp.get("sql", "").strip().rstrip(";")
            if not sql or comp.get("type") == "text":
                component_data[comp_id] = {"headers": [], "rows": [], "chart_data": None}
                continue
            try:
                result = db.execute(text(sql))
                rows = result.fetchall()
                headers = list(result.keys())
                data_rows = [[serialize_value(v) for v in r] for r in rows]
                component_data[comp_id] = {
                    "headers": headers,
                    "rows": data_rows,
                    "chart_data": DataFormatter.to_chart(headers, data_rows) if data_rows else None,
                }
            except Exception:
                component_data[comp_id] = {"headers": ["错误"], "rows": [["查询失败"]], "chart_data": None}

        return {
            "report_name": report.name,
            "config": config,
            "component_data": component_data,
        }

    # Legacy format
    raise HTTPException(400, "旧版报表格式不支持分享预览")
