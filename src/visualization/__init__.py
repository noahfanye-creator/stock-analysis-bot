"""
可视化模块
提供图表生成和PDF报告生成功能
"""

from .charts import create_candle_chart, create_indices_charts, create_intraday_timeshare_chart

from .pdf_generator import create_pdf_with_market_analysis

from .report_templates import _format_range, _get_trend_status, _build_report_summary, _build_parameters_table

__all__ = [
    # 图表生成
    "create_candle_chart",
    "create_indices_charts",
    "create_intraday_timeshare_chart",
    # PDF生成
    "create_pdf_with_market_analysis",
    # 报告模板
    "_format_range",
    "_get_trend_status",
    "_build_report_summary",
    "_build_parameters_table",
]
