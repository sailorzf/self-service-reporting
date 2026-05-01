import pytest
from app.report_engine import SQLBuilder
from app.schemas import ReportConfig, FilterSpec, JoinSpec, TableSpec

def test_build_simple_select():
    config = ReportConfig(
        columns=["站点", "充电量"],
        aggregations={"充电量": "sum"},
        group_by=["站点"],
        filters=[],
        sort=None,
        limit=100,
        chart_type="bar"
    )
    sql = SQLBuilder.build(config, table_name="data_operation")
    assert "SELECT" in sql
    assert "`站点`" in sql
    assert "SUM(`充电量`)" in sql
    assert "FROM `data_operation`" in sql
    assert "GROUP BY" in sql
    assert "LIMIT 100" in sql

def test_build_with_filters():
    config = ReportConfig(
        columns=["区域", "充电量"],
        aggregations={"充电量": "sum"},
        group_by=["区域"],
        filters=[
            FilterSpec(field="区域", op="=", value="华东"),
            FilterSpec(field="时间", op=">=", value="2024-01")
        ],
        sort={"field": "充电量", "order": "desc"},
        limit=50,
        chart_type="bar"
    )
    sql = SQLBuilder.build(config, table_name="data_operation")
    assert "`区域` = '华东'" in sql
    assert "`时间` >= '2024-01'" in sql
    assert "ORDER BY `充电量` DESC" in sql
    assert "LIMIT 50" in sql

def test_build_with_joins():
    config = ReportConfig(
        tables=[
            TableSpec(data_type_id=1, alias="op"),
            TableSpec(data_type_id=2, alias="fc")
        ],
        joins=[
            JoinSpec(
                left_table="op",
                right_table="fc",
                join_type="LEFT",
                on=[{"left": "站点", "right": "站点"}]
            )
        ],
        columns=["op.站点", "op.充电量", "fc.预估充电量"],
        aggregations={"op.充电量": "sum", "fc.预估充电量": "sum"},
        group_by=["op.站点"],
        filters=[FilterSpec(field="op.月份", op=">=", value="2024-01")],
        sort=None,
        limit=100,
        chart_type="bar"
    )
    sql = SQLBuilder.build_multi(config, {
        "op": "data_operation",
        "fc": "data_forecast"
    })
    assert "FROM `data_operation` AS `op`" in sql
    assert "LEFT JOIN `data_forecast` AS `fc`" in sql
    assert "ON `op`.`站点` = `fc`.`站点`" in sql

def test_data_formatter_to_chart():
    from app.report_engine import DataFormatter
    headers = ["区域", "充电量"]
    rows = [["华东", 12340.50], ["华南", 8920.30]]
    result = DataFormatter.to_chart(headers, rows)
    assert result["categories"] == ["华东", "华南"]
    assert len(result["series"]) == 1
    assert result["series"][0]["name"] == "充电量"
    assert result["series"][0]["data"] == [12340.50, 8920.30]
