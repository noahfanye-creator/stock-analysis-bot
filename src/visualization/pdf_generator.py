"""
PDF报告生成模块
生成包含市场指数分析的PDF报告
"""

import os
from datetime import datetime
from typing import Any, Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import pandas as pd

from src.utils.font_setup import setup_fonts
from src.utils.logger import get_logger
from src.utils.exceptions import ReportGenerationError

logger = get_logger(__name__)

# 获取字体名称
FONT_NAME = setup_fonts()
from src.data.fetchers import format_beijing_time  # noqa: E402
from .report_templates import _get_trend_status, _build_report_summary, _build_parameters_table  # noqa: E402


def create_pdf_with_market_analysis(
    stock_code: str,
    stock_name: str,
    stock_data_map: Dict[str, Any],
    indices_data: Dict[str, Any],
    save_path: str,
    temp_dir: str,
) -> bool:
    """创建包含市场指数分析的PDF报告（增强版）

    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        stock_data_map: 股票数据字典，包含不同周期的K线数据
        indices_data: 市场指数数据字典
        save_path: PDF保存路径
        temp_dir: 临时目录（存放图表）

    Returns:
        bool: 是否生成成功
    """
    try:
        doc = SimpleDocTemplate(save_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name="MainTitle", parent=styles["Title"], fontName=FONT_NAME, fontSize=22, alignment=1, spaceAfter=15
        )

        subtitle_style = ParagraphStyle(
            name="SubTitle", parent=styles["Heading2"], fontName=FONT_NAME, fontSize=16, alignment=1, spaceAfter=20
        )

        price_style = ParagraphStyle(
            name="PriceStyle", parent=styles["Heading2"], fontName=FONT_NAME, fontSize=18, alignment=1, spaceAfter=8
        )

        change_style = ParagraphStyle(
            name="ChangeStyle", parent=styles["Heading2"], fontName=FONT_NAME, fontSize=14, alignment=1, spaceAfter=15
        )

        section_style = ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName=FONT_NAME,
            fontSize=14,
            alignment=0,
            spaceAfter=10,
            spaceBefore=20,
        )

        normal_style = ParagraphStyle(
            name="NormalText", parent=styles["Normal"], fontName=FONT_NAME, fontSize=10, leading=14, spaceAfter=6
        )

        # 判断是否为行业指数报告（BK开头）
        is_sector_report = stock_code.startswith("BK")

        # 封面页
        story.append(Spacer(1, 50))
        if is_sector_report:
            story.append(Paragraph(f"{stock_name}行业板块指数分析报告", title_style))
        else:
            story.append(Paragraph(f"{stock_name}技术分析报告", title_style))
        story.append(Paragraph(f"({stock_code})", subtitle_style))
        story.append(Spacer(1, 20))

        # 封面最新价、涨跌幅：均按报告生成/数据获取时点（as_of）的数据，非完整日线
        day_df = stock_data_map.get("day")
        latest_price = None
        data_time = None
        as_of_ts = None
        prev_close = None

        # 优先用 1m -> 5m -> day 最后一条的 Close 作为最新价（数据已按 as_of 裁剪）
        df_1m = stock_data_map.get("1m")
        if df_1m is not None and not df_1m.empty:
            latest_price = df_1m.iloc[-1].get("Close", 0)
            as_of_ts = df_1m.index[-1]
            data_time = format_beijing_time(as_of_ts)
        else:
            df_5m = stock_data_map.get("5m")
            if df_5m is not None and not df_5m.empty:
                latest_price = df_5m.iloc[-1].get("Close", 0)
                as_of_ts = df_5m.index[-1]
                data_time = format_beijing_time(as_of_ts)
            elif day_df is not None and not day_df.empty:
                latest_price = day_df.iloc[-1].get("Close", 0)
                as_of_ts = day_df.index[-1]
                data_time = format_beijing_time(as_of_ts)

        # 涨跌幅：相对于前一日收盘，均取自 as_of 时点的日线
        if latest_price is not None and day_df is not None and len(day_df) >= 2:
            if as_of_ts is not None:
                as_of_date = pd.Timestamp(as_of_ts).date()
                mask = day_df.index.date < as_of_date
                if mask.any():
                    prev_close = day_df.loc[mask].iloc[-1].get("Close", latest_price)
                else:
                    prev_close = day_df.iloc[-2].get("Close", latest_price)
            else:
                prev_close = day_df.iloc[-2].get("Close", latest_price)
            change = latest_price - prev_close
            change_percent = (change / prev_close * 100) if prev_close else 0

            story.append(Paragraph(f"最新价格: {latest_price:.2f}", price_style))
            if change >= 0:
                change_style.textColor = colors.red
                change_text = f"涨跌幅: +{change:.2f} (+{change_percent:.2f}%)"
            else:
                change_style.textColor = colors.green
                change_text = f"涨跌幅: {change:.2f} ({change_percent:.2f}%)"
            story.append(Paragraph(change_text, change_style))
            if data_time:
                story.append(Paragraph(f"数据时间: {data_time}", normal_style))
        elif latest_price is not None:
            story.append(Paragraph(f"最新价格: {latest_price:.2f}", price_style))
            if data_time:
                story.append(Paragraph(f"数据时间: {data_time}", normal_style))
        else:
            story.append(Paragraph("最新价格数据获取中...", normal_style))

        story.append(Spacer(1, 10))
        gen_time = (stock_data_map.get("_meta") or {}).get("generated_at")
        if not gen_time:
            gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"生成时间: {gen_time}", normal_style))
        story.append(Spacer(1, 15))

        # 结构化摘要与参数信息（移到第一页）
        story.append(Paragraph("报告摘要", section_style))
        for line in _build_report_summary(stock_name, stock_code, stock_data_map, indices_data):
            story.append(Paragraph(line, normal_style))
        story.append(Spacer(1, 8))

        meta = stock_data_map.get("_meta", {})
        if meta:
            story.append(Paragraph("数据与参数", section_style))
            params_table = _build_parameters_table(meta, stock_data_map, indices_data)
            params_table_obj = Table(params_table, colWidths=[110, 400])
            params_table_obj.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(params_table_obj)

        story.append(PageBreak())

        # 分离市场指数和行业指数
        market_indices = {k: v for k, v in indices_data.items() if v.get("type") != "SECTOR"}
        sector_indices = {k: v for k, v in indices_data.items() if v.get("type") == "SECTOR"}

        # 第一部分：市场指数综合分析（表格形式）- 第二页开始
        story.append(Paragraph("一、市场指数综合分析", section_style))
        story.append(Spacer(1, 8))

        # 构建市场指数综合分析表格
        if market_indices:
            market_table_data = [["指数名称", "现价", "MA5", "MA10", "趋势", "RSI", "MACD", "KDJ"]]

            for code, info in market_indices.items():
                df = info["data"]
                name = info["name"]

                if df is not None and not df.empty and len(df) >= 20:
                    last = df.iloc[-1]

                    # 趋势判断
                    trend = "横盘"
                    if "MA5" in last and "MA10" in last and "MA20" in last:
                        if last["MA5"] > last["MA10"] > last["MA20"]:
                            trend = "多头"
                        elif last["MA5"] < last["MA10"] < last["MA20"]:
                            trend = "空头"

                    # RSI状态
                    rsi_str = f"{last['RSI']:.1f}" if "RSI" in last else "N/A"
                    if "RSI" in last:
                        if last["RSI"] > 70:
                            rsi_str += "(超买)"
                        elif last["RSI"] < 30:
                            rsi_str += "(超卖)"

                    # MACD
                    macd_str = f"{last['MACD']:.3f}" if "MACD" in last else "N/A"

                    # KDJ
                    kdj_str = "N/A"
                    if "K" in last and "D" in last and "J" in last:
                        kdj_str = f"K:{last['K']:.1f} D:{last['D']:.1f} J:{last['J']:.1f}"

                    market_table_data.append(
                        [
                            name,
                            f"{last['Close']:.2f}" if "Close" in last else "N/A",
                            f"{last['MA5']:.2f}" if "MA5" in last else "N/A",
                            f"{last['MA10']:.2f}" if "MA10" in last else "N/A",
                            trend,
                            rsi_str,
                            macd_str,
                            kdj_str,
                        ]
                    )

            if len(market_table_data) > 1:
                market_table = Table(market_table_data, colWidths=[70, 50, 50, 50, 40, 60, 55, 85])
                market_table.setStyle(
                    TableStyle(
                        [
                            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                            ("FONTSIZE", (0, 0), (-1, -1), 7),  # 使用更小的字体以适应更多列
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                            ("LEFTPADDING", (0, 0), (-1, -1), 3),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ]
                    )
                )
                story.append(market_table)
            else:
                story.append(Paragraph("市场指数数据获取失败", normal_style))
        else:
            story.append(Paragraph("市场指数数据获取失败", normal_style))

        # 添加市场指数图表（单独一页）
        story.append(PageBreak())
        story.append(Paragraph("主要指数日线图", section_style))
        story.append(Spacer(1, 10))

        index_charts = []
        for code, info in market_indices.items():
            img_path = os.path.join(temp_dir, f"index_{code}.png")
            if os.path.exists(img_path):
                try:
                    from PIL import Image as PILImage

                    pil_img = PILImage.open(img_path)
                    img_width, img_height = pil_img.size
                    ratio = min(250 / img_width, 150 / img_height)

                    img = Image(img_path, width=img_width * ratio, height=img_height * ratio)

                    # 获取指数数据，计算点位和涨跌幅
                    df = info.get("data")
                    name_text = info["name"]
                    price_text = "N/A"
                    change_text = "N/A"

                    if df is not None and not df.empty and len(df) >= 2:
                        last = df.iloc[-1]
                        prev = df.iloc[-2]
                        current_price = last.get("Close", 0)
                        prev_price = prev.get("Close", current_price)
                        change = current_price - prev_price
                        change_percent = (change / prev_price * 100) if prev_price else 0

                        price_text = f"{current_price:.2f}"
                        if change >= 0:
                            change_text = f"+{change:.2f} (+{change_percent:.2f}%)"
                        else:
                            change_text = f"{change:.2f} ({change_percent:.2f}%)"

                    # 创建包含名称、点位、涨跌幅的文本块
                    # 使用HTML格式组合成一个Paragraph
                    change_color = "red" if change >= 0 else "green"
                    text_content = (
                        f"<b>{name_text}</b><br/><font size=9>{price_text}</font>"
                        f"<br/><font size=8 color={change_color}>{change_text}</font>"
                    )

                    name_style = ParagraphStyle(
                        name="IndexName",
                        parent=normal_style,
                        fontSize=10,
                        alignment=1,  # 居中
                        leading=11,
                        spaceAfter=0,
                    )

                    text_block = Paragraph(text_content, name_style)

                    index_charts.append([text_block, img])
                except Exception as e:
                    logger.warning("处理指数图表失败 %s: %s", code, e)
                    continue

        if index_charts:
            rows = []
            for i in range(0, len(index_charts), 2):
                row = []
                row.append(index_charts[i][0])  # 文本块（名称+点位+涨跌幅）
                row.append(index_charts[i][1])  # 图表
                if i + 1 < len(index_charts):
                    row.append(index_charts[i + 1][0])
                    row.append(index_charts[i + 1][1])
                else:
                    row.append(Paragraph("", normal_style))
                    row.append(Paragraph("", normal_style))
                rows.append(row)

            if rows:
                table = Table(rows, colWidths=[70, 220, 70, 220])
                table.setStyle(
                    TableStyle(
                        [
                            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 5),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    )
                )
                story.append(table)

        # 如果有行业指数，单独展示
        if sector_indices:
            story.append(PageBreak())
            story.append(Paragraph("一.五、行业板块指数分析", section_style))
            story.append(Spacer(1, 10))

            for code, info in sector_indices.items():
                df = info["data"]
                name = info["name"]
                if df is not None and len(df) >= 20:
                    last = df.iloc[-1]
                    trend = _get_trend_status(last)
                    rsi_status = "中性"
                    if "RSI" in last:
                        rsi_status = "超买" if last["RSI"] > 70 else ("超卖" if last["RSI"] < 30 else "中性")

                    story.append(Paragraph(f"{name}:", normal_style))
                    story.append(
                        Paragraph(f"  现价: {last['Close']:.2f}, 趋势: {trend}, RSI: {rsi_status}", normal_style)
                    )
                    story.append(Spacer(1, 5))

            # 添加行业指数图表
            story.append(Spacer(1, 10))
            story.append(Paragraph("行业板块指数日线图:", normal_style))

            sector_charts = []
            for code, info in sector_indices.items():
                img_path = os.path.join(temp_dir, f"index_{code}.png")
                if os.path.exists(img_path):
                    try:
                        from PIL import Image as PILImage

                        pil_img = PILImage.open(img_path)
                        img_width, img_height = pil_img.size
                        ratio = min(250 / img_width, 150 / img_height)

                        img = Image(img_path, width=img_width * ratio, height=img_height * ratio)
                        sector_charts.append([Paragraph(info["name"], normal_style), img])
                    except Exception:
                        continue

            if sector_charts:
                rows = []
                for i in range(0, len(sector_charts), 2):
                    row = []
                    row.append(sector_charts[i][0])
                    row.append(sector_charts[i][1])
                    if i + 1 < len(sector_charts):
                        row.append(sector_charts[i + 1][0])
                        row.append(sector_charts[i + 1][1])
                    else:
                        row.append(Paragraph("", normal_style))
                        row.append(Paragraph("", normal_style))
                    rows.append(row)

                if rows:
                    table = Table(rows, colWidths=[60, 220, 60, 220])
                    table.setStyle(
                        TableStyle(
                            [
                                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                                ("FONTSIZE", (0, 0), (-1, -1), 8),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ]
                        )
                    )
                    story.append(table)

        # 第二部分：市场情绪分析（表格形式，与市场指数综合分析放在同一页）
        # 注意：市场指数图表已单独一页，所以这里回到市场分析页面
        story.append(PageBreak())
        story.append(Paragraph("二、市场情绪分析", section_style))
        story.append(Spacer(1, 8))

        # 构建市场情绪分析表格
        if market_indices:
            sentiment_table_data = []

            # 统计市场宽度
            up_count = 0
            down_count = 0
            overbought_count = 0
            oversold_count = 0

            for code, info in market_indices.items():
                df = info["data"]
                if df is not None and len(df) >= 2:
                    last = df.iloc[-1]
                    prev = df.iloc[-2]

                    if last["Close"] > prev["Close"]:
                        up_count += 1
                    else:
                        down_count += 1

                    if "RSI" in last:
                        if last["RSI"] > 70:
                            overbought_count += 1
                        elif last["RSI"] < 30:
                            oversold_count += 1

            total = up_count + down_count
            if total > 0:
                up_ratio = (up_count / total) * 100
                sentiment_table_data.append(["市场宽度指标", "数量", "占比"])
                sentiment_table_data.append(["上涨指数", f"{up_count}个", f"{up_ratio:.1f}%"])
                sentiment_table_data.append(["下跌指数", f"{down_count}个", f"{100-up_ratio:.1f}%"])

            # 情绪极值
            if overbought_count > 0 or oversold_count > 0:
                if sentiment_table_data:
                    sentiment_table_data.append(["", "", ""])  # 空行分隔
                sentiment_table_data.append(["情绪极值", "数量", ""])
                sentiment_table_data.append(["超买状态", f"{overbought_count}个指数", ""])
                sentiment_table_data.append(["超卖状态", f"{oversold_count}个指数", ""])

            # 波动性排名
            volatility_data = []
            for code, info in market_indices.items():
                df = info["data"]
                if df is not None and len(df) >= 5 and "Amplitude" in df.columns:
                    last_5 = df.tail(5)
                    volatility = last_5["Amplitude"].mean()
                    volatility_data.append((info["name"], volatility))

            if volatility_data:
                volatility_data.sort(key=lambda x: x[1], reverse=True)
                if sentiment_table_data:
                    sentiment_table_data.append(["", "", ""])  # 空行分隔
                sentiment_table_data.append(["波动性排名(5日平均)", "指数名称", "振幅"])
                for idx, (name, vol) in enumerate(volatility_data[:5], 1):  # 显示前5名
                    sentiment_table_data.append([f"第{idx}名", name, f"{vol:.2f}%"])

            if sentiment_table_data:
                # 构建表格样式，处理空行
                table_style = [
                    ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]

                # 合并空行单元格
                for i, row in enumerate(sentiment_table_data):
                    if len(row) > 0 and row[0] == "":
                        table_style.append(("SPAN", (0, i), (-1, i)))

                sentiment_table = Table(sentiment_table_data, colWidths=[100, 80, 80])
                sentiment_table.setStyle(TableStyle(table_style))
                story.append(sentiment_table)

        story.append(PageBreak())

        # 第三部分：技术分析（个股或行业指数）
        if is_sector_report:
            story.append(Paragraph("三、行业指数技术分析", section_style))
        else:
            story.append(Paragraph("三、个股技术分析", section_style))

            # 个股分时图（价格+均价、成交量、量比）
            intraday_img = os.path.join(temp_dir, "intraday_timeshare.png")
            if os.path.exists(intraday_img):
                story.append(Paragraph("个股分时图", subtitle_style))
                story.append(Spacer(1, 8))
                try:
                    from PIL import Image as PILImage

                    pil_img = PILImage.open(intraday_img)
                    iw, ih = pil_img.size
                    ratio = min(500 / iw, 320 / ih)
                    img = Image(intraday_img, width=iw * ratio, height=ih * ratio)
                    img.hAlign = "CENTER"
                    story.append(img)
                    story.append(
                        Paragraph(
                            "分时价(蓝)、均价(橙)、涨跌区域着色；下方为成交量与量比。",
                            ParagraphStyle(name="TimeshareDesc", parent=normal_style, fontSize=9),
                        )
                    )
                    story.append(Spacer(1, 15))
                except Exception:
                    pass

            periods = [
                ("日线级别分析", "day"),
                ("周线级别分析", "week"),
                ("月线级别分析", "month"),
                ("30分钟级别分析", "30m"),
                ("5分钟级别分析", "5m"),
                ("1分钟级别分析", "1m"),
            ]

            meta_cutoff = (stock_data_map.get("_meta") or {}).get("cutoff_notes") or {}
            for cn_name, key in periods:
                df = stock_data_map.get(key)

                story.append(Paragraph(cn_name, subtitle_style))
                story.append(Spacer(1, 10))
                cutoff_note = meta_cutoff.get(key)
                if cutoff_note:
                    note_style = ParagraphStyle(
                        name="CutoffNote", parent=normal_style, fontSize=9, textColor=colors.grey
                    )
                    story.append(Paragraph(cutoff_note, note_style))
                    story.append(Spacer(1, 4))

                if df is not None and not df.empty and len(df) >= 3:
                    try:
                        last = df.iloc[-1]

                        # 合并所有指标到一个紧凑的表格
                        combined_data = [["指标", "数值", "状态"]]

                        # 基础价格指标
                        close_status = "上涨" if "MA5" in last and last["Close"] > last["MA5"] else "下跌"
                        combined_data.append(["收盘价", f"{last['Close']:.2f}", close_status])
                        if "MA5" in last:
                            combined_data.append(["MA5", f"{last['MA5']:.2f}", ""])
                        if "MA10" in last:
                            combined_data.append(["MA10", f"{last['MA10']:.2f}", ""])
                        if "MA20" in last:
                            combined_data.append(["MA20", f"{last['MA20']:.2f}", ""])

                        # 技术指标
                        if "RSI" in last:
                            rsi_status = "超买" if last["RSI"] > 70 else ("超卖" if last["RSI"] < 30 else "正常")
                            combined_data.append(["RSI(14)", f"{last['RSI']:.1f}", rsi_status])

                        if "MACD" in last:
                            macd_status = "多头" if last["MACD"] > 0 else "空头"
                            combined_data.append(["MACD", f"{last['MACD']:.3f}", macd_status])

                        if "K" in last:
                            k_status = "超买" if last["K"] > 80 else ("超卖" if last["K"] < 20 else "正常")
                            combined_data.append(["KDJ-K", f"{last['K']:.1f}", k_status])

                        if "D" in last:
                            combined_data.append(["KDJ-D", f"{last['D']:.1f}", ""])

                        if "J" in last:
                            combined_data.append(["KDJ-J", f"{last['J']:.1f}", ""])

                        if "WR" in last:
                            wr_status = "超买" if last["WR"] < 20 else ("超卖" if last["WR"] > 80 else "正常")
                            combined_data.append(["威廉指标", f"{last['WR']:.1f}", wr_status])

                        if "OBV" in last:
                            combined_data.append(["OBV", f"{last['OBV']:.0f}", "能量潮"])

                        # 成交量指标
                        if "Volume" in last:
                            vol_str = f"{last['Volume']:.0f}" if last["Volume"] < 1e8 else f"{last['Volume']/1e8:.2f}亿"
                            combined_data.append(["成交量", vol_str, ""])

                        if "Volume_Ratio" in last:
                            vr_status = (
                                "放量"
                                if last["Volume_Ratio"] > 1.5
                                else ("缩量" if last["Volume_Ratio"] < 0.8 else "正常")
                            )
                            combined_data.append(["量比", f"{last['Volume_Ratio']:.2f}", vr_status])

                        if "Amplitude" in last:
                            combined_data.append(["振幅", f"{last['Amplitude']:.2f}%", "波动性"])

                        # 创建合并后的紧凑表格
                        # 使用更小的列宽和字体，让表格更紧凑
                        table_combined = Table(combined_data, colWidths=[90, 75, 75])
                        table_combined.setStyle(
                            TableStyle(
                                [
                                    ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                                    ("FONTSIZE", (0, 0), (-1, -1), 8),  # 字体从9减小到8
                                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                                ]
                            )
                        )
                        story.append(table_combined)
                        story.append(Spacer(1, 8))  # 间距从10减小到8

                    except Exception:
                        story.append(Paragraph("数据计算中...", normal_style))

                # 添加图表
                img_path = os.path.join(temp_dir, f"{key}.png")
                if os.path.exists(img_path):
                    try:
                        from PIL import Image as PILImage

                        pil_img = PILImage.open(img_path)
                        img_width, img_height = pil_img.size
                        ratio = min(500 / img_width, 350 / img_height)

                        img = Image(img_path, width=img_width * ratio, height=img_height * ratio)
                        img.hAlign = "CENTER"
                        story.append(img)

                        if key in ["day", "week", "month"]:
                            story.append(Spacer(1, 5))
                            story.append(Paragraph("图表说明:", normal_style))
                            story.append(
                                Paragraph(
                                    "1. K线图上方为价格走势，包含MA5/10/20均线和布林带",
                                    ParagraphStyle(name="ChartDesc", parent=normal_style, fontSize=9),
                                )
                            )
                            story.append(
                                Paragraph(
                                    "2. 第二栏为MACD指标，包含DIF和DEA线",
                                    ParagraphStyle(name="ChartDesc", parent=normal_style, fontSize=9),
                                )
                            )
                            story.append(
                                Paragraph(
                                    "3. 第三栏为KDJ指标，超买超卖区间为80/20",
                                    ParagraphStyle(name="ChartDesc", parent=normal_style, fontSize=9),
                                )
                            )
                            story.append(
                                Paragraph(
                                    "4. 第四栏为成交量和量比分析，包含成交量柱状图、成交量均线和量比曲线",
                                    ParagraphStyle(name="ChartDesc", parent=normal_style, fontSize=9),
                                )
                            )
                            story.append(
                                Paragraph(
                                    "   量比>1.5表示放量，<0.5表示缩量，红/绿柱表示涨/跌",
                                    ParagraphStyle(name="ChartDesc", parent=normal_style, fontSize=9),
                                )
                            )
                        story.append(Spacer(1, 10))
                    except Exception:
                        story.append(Paragraph("[图表加载失败]", normal_style))
                else:
                    story.append(Paragraph("[图表生成失败或无数据]", normal_style))

                story.append(Spacer(1, 20))

                if key != "1m":
                    story.append(PageBreak())

        story.append(Spacer(1, 30))
        story.append(
            Paragraph(
                f"报告结束 - {stock_name} ({stock_code})",
                ParagraphStyle(name="ReportEnd", parent=normal_style, fontSize=12, alignment=1),
            )
        )

        doc.build(story)
        logger.info("PDF生成成功: %s", os.path.basename(save_path))
        return True

    except ReportGenerationError:
        raise
    except Exception as e:
        logger.exception("PDF生成失败: %s", e)
        raise ReportGenerationError(f"PDF生成失败: {e}") from e
