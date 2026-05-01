import pytest
from app.security import validate_sql, validate_fields

def test_valid_select_passes():
    sql = "SELECT `站点`, SUM(`充电量`) FROM `data_operation` GROUP BY `站点`"
    assert validate_sql(sql) is True

def test_delete_blocked():
    with pytest.raises(ValueError, match="DELETE"):
        validate_sql("DELETE FROM `data_operation`")

def test_insert_blocked():
    with pytest.raises(ValueError, match="INSERT"):
        validate_sql("INSERT INTO `data_operation` VALUES (1)")

def test_update_blocked():
    with pytest.raises(ValueError, match="UPDATE"):
        validate_sql("UPDATE `data_operation` SET `充电量` = 100")

def test_drop_blocked():
    with pytest.raises(ValueError, match="DROP"):
        validate_sql("DROP TABLE `data_operation`")

def test_select_with_subquery_blocked():
    with pytest.raises(ValueError):
        validate_sql("SELECT * FROM `data_operation` WHERE id IN (SELECT id FROM other)")

def test_validate_field_against_schema():
    schema_fields = {"站点", "区域", "充电量", "金额"}
    assert validate_fields(["站点", "充电量"], schema_fields) is True

def test_validate_field_unknown_rejected():
    schema_fields = {"站点", "区域", "充电量"}
    with pytest.raises(ValueError, match="未知字段"):
        validate_fields(["未知字段"], schema_fields)
