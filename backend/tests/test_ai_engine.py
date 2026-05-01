import pytest
from unittest.mock import patch, MagicMock
from app.ai_engine import AIEngine
from app.models import DataType

@pytest.fixture
def mock_data_type():
    return DataType(
        id=1, code="operation", name="运营数据", table_name="data_operation",
        columns_json=[
            {"name": "站点", "type": "varchar"},
            {"name": "区域", "type": "varchar"},
            {"name": "充电量", "type": "decimal"},
            {"name": "月份", "type": "varchar"}
        ]
    )

def test_build_system_prompt(mock_data_type):
    engine = AIEngine.__new__(AIEngine)
    prompt = engine.build_system_prompt(mock_data_type, [])
    assert "运营数据" in prompt
    assert "站点" in prompt
    assert "充电量" in prompt

@patch("app.ai_engine.DashScopeProvider")
def test_parse_user_message(mock_provider, mock_data_type):
    mock_instance = MagicMock()
    mock_instance.generate.return_value = '{"sql": "SELECT SUM(`充电量`) FROM `data_operation`", "analysis": "总充电量1000度", "clarification": null, "follow_ups": ["按站点拆分"]}'
    mock_provider.return_value = mock_instance
    db_mock = MagicMock()
    engine = AIEngine(db_mock)
    engine.llm = mock_instance
    result = engine.parse_user_message(mock_data_type, [], "总充电量多少")
    assert result["sql"] is not None
    assert "SELECT" in result["sql"]
    assert "按站点拆分" in result["follow_ups"]
