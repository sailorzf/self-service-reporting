from datetime import datetime, date
from decimal import Decimal
from jinja2 import Template
from sqlalchemy import text
from app.report_engine import DataFormatter

HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{{ report_name }}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; padding: 20px; }
  .report-header { text-align: center; margin-bottom: 20px; }
  .report-header h2 { font-size: 20px; color: #333; }
  .report-header .meta { font-size: 12px; color: #999; margin-top: 4px; }
  .canvas-container { position: relative; margin: 0 auto; background: #fff; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
  .comp { position: absolute; border: 1px solid #e4e7ed; border-radius: 4px; padding: 12px; overflow: hidden; }
  .comp-header { font-size: 14px; font-weight: bold; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #eee; }
  .comp-text { font-size: 13px; line-height: 1.6; white-space: pre-wrap; }
  .comp-kpi { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; }
  .comp-kpi .value { font-size: 32px; font-weight: bold; color: #333; }
  .comp-kpi .label { font-size: 12px; color: #999; margin-top: 4px; }
  .comp-table { height: calc(100% - 28px); overflow: auto; }
  .comp-table table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .comp-table th, .comp-table td { border: 1px solid #e4e7ed; padding: 4px 8px; text-align: left; }
  .comp-table th { background: #f5f7fa; font-weight: bold; }
  .comp-table tr:nth-child(even) { background: #fafafa; }
  .chart-container { width: 100%; height: calc(100% - 28px); }
  .print-btn { position: fixed; top: 10px; right: 20px; padding: 8px 16px; background: #409eff; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
  .print-btn:hover { background: #337ecc; }
  @media print { .print-btn { display: none; } body { padding: 0; background: #fff; } .canvas-container { box-shadow: none; } }
</style>
</head>
<body>
<button class="print-btn" onclick="window.print()">打印 / PDF</button>
<div class="report-header">
  <h2>{{ report_name }}</h2>
  <div class="meta">导出时间: {{ export_time }}</div>
</div>
<div class="canvas-container" style="width:{{ canvas_width }}px; height:{{ canvas_height }}px;">
{% for comp in components %}
  <div class="comp" style="left:{{ comp.x }}px; top:{{ comp.y }}px; width:{{ comp.width }}px; height:{{ comp.height }}px;">
    <div class="comp-header" style="color:{{ comp.theme_color }}">{{ comp.name or comp.type }}</div>
    {% if comp.type == 'text' %}
      <div class="comp-text">{{ comp.content }}</div>
    {% elif comp.type == 'kpi' %}
      <div class="comp-kpi">
        <div class="value">{{ comp.kpi_value }}</div>
        <div class="label">{{ comp.name }}</div>
      </div>
    {% elif comp.type == 'table' %}
      <div class="comp-table">
        <table>
          <thead><tr>{% for h in comp.headers %}<th>{{ h }}</th>{% endfor %}</tr></thead>
          <tbody>
          {% for row in comp.rows %}
            <tr>{% for v in row %}<td>{{ v }}</td>{% endfor %}</tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    {% else %}
      <div class="chart-container" id="chart-{{ comp.id }}"></div>
    {% endif %}
  </div>
{% endfor %}
</div>
<script>
{% for comp in components %}
{% if comp.type in ('bar', 'line', 'pie') and comp.chart_data and comp.chart_data.series %}
(function() {
  var chart = echarts.init(document.getElementById('chart-{{ comp.id }}'));
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: {{ comp.chart_data.categories | tojson }} },
    yAxis: { type: 'value' },
    series: {{ comp.chart_data.series | tojson }},
    grid: { left: '10%', right: '5%', bottom: '10%', top: '10%' }
  });
})();
{% endif %}
{% endfor %}
</script>
</body>
</html>""")


def serialize_value(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def generate_html_report(report, db):
    config = report.config_json
    canvas = config.get("canvas", {}) if isinstance(config, dict) else {}
    components = config.get("components", []) if isinstance(config, dict) else []

    rendered_comps = []
    for comp in components:
        c = {
            "id": comp.get("id", ""),
            "type": comp.get("type", "text"),
            "name": comp.get("name", ""),
            "x": comp.get("x", 0),
            "y": comp.get("y", 0),
            "width": comp.get("width", 260),
            "height": comp.get("height", 180),
            "theme_color": comp.get("theme_color", "#409eff"),
            "content": comp.get("content", ""),
        }

        if c["type"] == "text":
            rendered_comps.append(c)
            continue

        sql = comp.get("sql", "").strip().rstrip(";")
        if not sql:
            c["headers"] = []
            c["rows"] = []
            c["chart_data"] = {"categories": [], "series": []}
            c["kpi_value"] = "-"
            rendered_comps.append(c)
            continue

        try:
            result = db.execute(text(sql))
            rows = result.fetchall()
            headers = list(result.keys())
            data_rows = [[serialize_value(v) for v in r] for r in rows]

            c["headers"] = headers
            c["rows"] = data_rows[:50]
            c["chart_data"] = DataFormatter.to_chart(headers, data_rows) if data_rows else {"categories": [], "series": []}
            c["kpi_value"] = str(data_rows[0][0]) if data_rows else "-"
        except Exception as e:
            c["headers"] = ["错误"]
            c["rows"] = [[str(e)]]
            c["chart_data"] = {"categories": [], "series": []}
            c["kpi_value"] = "错误"

        rendered_comps.append(c)

    return HTML_TEMPLATE.render(
        report_name=report.name,
        export_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        canvas_width=canvas.get("width", 1200),
        canvas_height=canvas.get("height", 800),
        components=rendered_comps,
    )
