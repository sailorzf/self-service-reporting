import pytest
import tempfile
import os
from openpyxl import Workbook
from app.import_service import ImportService

@pytest.fixture
def sample_excel(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["站点", "区域", "充电量", "月份"])
    ws.append(["A站", "华东", 100.5, "2024-01"])
    ws.append(["B站", "华南", 200.3, "2024-01"])
    path = str(tmp_path / "test.xlsx")
    wb.save(path)
    return path

def test_parse_excel(sample_excel):
    service = ImportService()
    columns, rows = service.parse(sample_excel)
    assert columns == ["站点", "区域", "充电量", "月份"]
    assert len(rows) == 2
    assert rows[0][0] == "A站"
    assert rows[1][1] == "华南"

def test_preview(sample_excel):
    service = ImportService()
    preview = service.preview(sample_excel)
    assert preview["row_count"] == 2
    assert len(preview["columns"]) == 4
    assert preview["rows"][0][0] == "A站"
