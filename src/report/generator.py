"""
报告生成模块
批量处理股票并生成PDF报告
"""

import os
import re
import shutil
import time
import zipfile
from typing import List, Tuple, Optional, Dict, Any

import pandas as pd

from src.utils.code_normalizer import normalize_code, parse_stock_list
from src.data.fetchers import (
    get_name,
    fetch_kline_data,
    get_market_indices_data,
    get_sector_indices_data,
    load_sector_index_map,
    normalize_beijing_time,
    filter_trading_hours,
)
from src.analysis import calculate_technical_indicators, resample_kline_data
from src.visualization import (
    create_candle_chart,
    create_indices_charts,
    create_intraday_timeshare_chart,
    create_pdf_with_market_analysis,
)
from src.config import Config
from src.utils.logger import get_logger
from src.utils.trading_hours import get_beijing_now
from src.utils.parallel import batch_process
from src.utils.exceptions import (
    DataFetchError,
    IndicatorCalculationError,
    ReportGenerationError,
)

logger = get_logger(__name__)


def _process_single_stock(
    code_input: str,
    output_folder: str,
    sector_input: Optional[str],
    sector_map: Dict[str, Any],
    index: int,
    total: int,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    处理单个股票（内部函数，用于并发处理）

    Args:
        code_input: 股票代码输入
        output_folder: 输出文件夹
        sector_input: 行业输入
        sector_map: 行业映射字典
        index: 当前索引
        total: 总数

    Returns:
        Tuple[stock_code, stock_name, pdf_path, error]: 处理结果
    """
    try:
        logger.info("\n" + "=" * 70)
        logger.info(f"第 {index}/{total} 个股票: {code_input}")
        logger.info("=" * 70)

        if not code_input:
            logger.warning("⚠️  跳过空代码")
            return (None, None, None, "空代码")

        name_to_code = sector_map.get("name_to_code", {})
        code_to_name = sector_map.get("code_to_name", {})

        is_sector_input = False
        stock_code = None
        stock_name = None

        # 1. 检查是否为行业代码（BK开头）
        if code_input.startswith("BK") and code_input in code_to_name:
            stock_code = code_input
            stock_name = code_to_name[code_input]
            is_sector_input = True
            logger.info(f"ℹ️  识别为行业代码: {stock_code} ({stock_name})")

        # 2. 检查是否为行业名称（完全匹配）
        elif code_input in name_to_code:
            stock_code = name_to_code[code_input]
            stock_name = code_input
            is_sector_input = True
            logger.info(f"ℹ️  识别为行业名称: {stock_name} ({stock_code})")

        # 3. 模糊匹配行业名称
        if not is_sector_input:
            potential_name = code_input.split(".")[0] if "." in code_input else code_input
            for s_name, s_code in name_to_code.items():
                if len(potential_name) >= 2 and (potential_name in s_name or s_name in potential_name):
                    stock_code = s_code
                    stock_name = s_name
                    is_sector_input = True
                    logger.info(f"ℹ️  模糊匹配到行业: {stock_name} ({stock_code})")
                    break

        # 4. 如果仍然不是行业，则作为普通股票处理
        if not is_sector_input:
            stock_code = normalize_code(code_input)
            stock_name = get_name(stock_code)
            logger.info(f"📈 识别为股票: {stock_code} ({stock_name or '未知'})")

        if not stock_name:
            stock_name = "未知股票" if not is_sector_input else "未知行业"

        timestamp = get_beijing_now().strftime("%H%M%S")
        temp_dir = os.path.join(output_folder, f"temp_{stock_code}_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)

        logger.info("\n1️⃣  获取市场指数数据...")
        is_hk = str(stock_code).startswith("HK.")
        indices_data = get_market_indices_data(is_hk=is_hk)

        # 获取行业板块指数
        current_sector = sector_input or (stock_code if is_sector_input else None)
        if current_sector:
            logger.info(f"   获取行业板块指数: {current_sector}")
            sector_indices_data = get_sector_indices_data(current_sector, count=150)
            if sector_indices_data:
                indices_data.update(sector_indices_data)

        logger.info("\n2️⃣  获取数据...")
        stock_data_map = {}
        data_source = "AKShare(行业)" if is_sector_input else ("新浪财经/东方财富" if is_hk else "新浪财经")

        # 从配置加载指标参数
        config = Config()
        indicator_params = config.indicator_params

        report_meta = {
            "generated_at": get_beijing_now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_source": data_source,
            "index_source": config.get("data_sources.index_source", "新浪财经"),
            "indicator_params": indicator_params,
        }

        # 数据抓取
        try:
            if is_sector_input:
                import akshare as ak

                df_day = ak.stock_board_industry_hist_em(
                    symbol=stock_name, period="daily", start_date="20230101", end_date="20261231", adjust=""
                )
                if df_day is not None and not df_day.empty:
                    df_day = df_day.rename(
                        columns={
                            "日期": "Date",
                            "开盘": "Open",
                            "收盘": "Close",
                            "最高": "High",
                            "最低": "Low",
                            "成交量": "Volume",
                        }
                    )
                    df_day["Date"] = pd.to_datetime(df_day["Date"])
                    df_day.set_index("Date", inplace=True)
                    df_day = calculate_technical_indicators(df_day)
                    stock_data_map["day"] = df_day
                    stock_data_map["week"] = resample_kline_data(df_day, "W")
                    stock_data_map["month"] = resample_kline_data(df_day, "M")

                    for p in ["30", "5"]:
                        for retry in range(3):
                            try:
                                df_min = ak.stock_board_industry_hist_min_em(symbol=stock_name, period=p)
                                if df_min is not None and not df_min.empty:
                                    df_min = df_min.rename(
                                        columns={
                                            "时间": "Date",
                                            "开盘": "Open",
                                            "收盘": "Close",
                                            "最高": "High",
                                            "最低": "Low",
                                            "成交量": "Volume",
                                        }
                                    )
                                    df_min["Date"] = pd.to_datetime(df_min["Date"])
                                    df_min.set_index("Date", inplace=True)
                                    df_min = calculate_technical_indicators(df_min)
                                    stock_data_map[f"{p}m"] = df_min
                                    break
                            except Exception:
                                time.sleep(2)
            else:
                df_day = fetch_kline_data(stock_code, 240, 150)
                if df_day is not None:
                    df_day = calculate_technical_indicators(df_day)
                    stock_data_map["day"] = df_day
                    stock_data_map["week"] = resample_kline_data(df_day, "W")
                    stock_data_map["month"] = resample_kline_data(df_day, "M")

                    for p in [30, 5, 1]:
                        df_min = fetch_kline_data(stock_code, p, 100)
                        if df_min is not None:
                            if not is_hk:
                                df_min = normalize_beijing_time(df_min)
                                df_min = filter_trading_hours(df_min)
                            df_min = calculate_technical_indicators(df_min)
                            stock_data_map[f"{p}m" if p != 1 else "1m"] = df_min
        except DataFetchError as e:
            logger.error("数据获取失败 %s: %s", stock_code, e)
            return (stock_code, stock_name, None, f"数据获取失败: {e}")
        except IndicatorCalculationError as e:
            logger.error("指标计算失败 %s: %s", stock_code, e)
            return (stock_code, stock_name, None, f"指标计算失败: {e}")
        except Exception as e:
            logger.error("数据获取异常 %s: %s", stock_code, e, exc_info=True)

        if "day" not in stock_data_map or stock_data_map["day"] is None:
            logger.error(f"❌ 无法获取核心数据，跳过 {stock_code}")
            return (stock_code, stock_name, None, "无数据")

        logger.info("\n3️⃣  生成图表...")
        create_indices_charts(indices_data, temp_dir)

        chart_config = config.chart_config
        max_points = chart_config.get("max_points", {})

        chart_configs = [
            ("day", stock_data_map.get("day"), f"{stock_name} 日线", max_points.get("day", 60)),
            ("week", stock_data_map.get("week"), f"{stock_name} 周线", max_points.get("week", 60)),
            ("month", stock_data_map.get("month"), f"{stock_name} 月线", max_points.get("month", 60)),
            ("30m", stock_data_map.get("30m"), f"{stock_name} 30分钟", max_points.get("minute", 100)),
            ("5m", stock_data_map.get("5m"), f"{stock_name} 5分钟", max_points.get("minute", 100)),
            ("1m", stock_data_map.get("1m"), f"{stock_name} 1分钟", max_points.get("minute", 100)),
        ]
        for key, df, title, max_points in chart_configs:
            if df is not None and len(df) >= 5:
                create_candle_chart(df, title, os.path.join(temp_dir, f"{key}.png"), max_points=max_points)

        # 个股分时图（仅当日 1m 数据足够时）
        df_1m = stock_data_map.get("1m")
        if df_1m is not None and len(df_1m) >= 5:
            create_intraday_timeshare_chart(df_1m, stock_name, os.path.join(temp_dir, "intraday_timeshare.png"))

        # 生成报告文件名（使用北京时区，服务器在 UTC 时也一致）
        safe_name = re.sub(r"[\\/*?:\"<>|]", "_", stock_name)
        file_timestamp = get_beijing_now().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(output_folder, f"{safe_name}_{stock_code}_{file_timestamp}.pdf")
        stock_data_map["_meta"] = report_meta

        try:
            ok = create_pdf_with_market_analysis(
                stock_code, stock_name, stock_data_map, indices_data, pdf_path, temp_dir
            )
        except ReportGenerationError as e:
            logger.error("PDF生成失败 %s (%s): %s", stock_code, stock_name, e)
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
            return (stock_code, stock_name, None, "PDF生成失败")
        if ok:
            logger.info("报告已生成: %s", pdf_path)
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
            return (stock_code, stock_name, pdf_path, None)
        logger.error("PDF生成失败 %s (%s)", stock_code, stock_name)
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        return (stock_code, stock_name, None, "PDF生成失败")

    except (DataFetchError, IndicatorCalculationError, ReportGenerationError) as e:
        logger.error("处理失败 %s: %s", code_input, e)
        return (None, None, None, str(e))
    except Exception as e:
        logger.error(f"❌ 处理股票失败 {code_input}: {e}", exc_info=True)
        return (None, None, None, str(e))


def process_multiple_stocks(
    stock_codes_input: str, output_folder: str, sector_input: Optional[str] = None
) -> Tuple[List[Tuple], List[Tuple]]:
    """
    批量处理多个股票

    Args:
        stock_codes_input: 股票代码列表（空格或逗号分隔）
        output_folder: 输出文件夹
        sector_input: 行业代码（如"BK1031"）或行业名称（如"光伏设备"），可选

    Returns:
        Tuple[List[Tuple], List[Tuple]]: (成功报告列表, 失败报告列表)
    """
    stock_codes = parse_stock_list(stock_codes_input)
    logger.info(f"📊 批量分析 {len(stock_codes)} 个股票")

    successful_reports = []
    failed_reports = []

    # 加载行业映射
    sector_map = load_sector_index_map()

    # 检查是否启用并发处理
    config = Config()
    parallel_config = config.get("parallel", {})
    use_parallel = parallel_config.get("enabled", False) and len(stock_codes) > 1

    if use_parallel:
        # 使用并发处理
        max_workers = parallel_config.get("max_workers", 3)
        batch_size = parallel_config.get("batch_size", 5)
        delay_between_batches = parallel_config.get("delay_between_batches", 1)

        logger.info(f"🚀 启用并发处理: 最大并发数={max_workers}, 批次大小={batch_size}")

        # 准备处理任务
        tasks = [
            (code_input, output_folder, sector_input, sector_map, i + 1, len(stock_codes))
            for i, code_input in enumerate(stock_codes)
        ]

        # 使用分批并发处理
        results = batch_process(
            tasks,
            lambda task: _process_single_stock(*task),
            batch_size=batch_size,
            max_workers=max_workers,
            delay_between_batches=delay_between_batches,
        )

        # 处理结果（results格式: [(task, result, error), ...]）
        for task, result, error in results:
            code_input = task[0]  # 第一个元素是code_input
            if error is None and result is not None:
                stock_code, stock_name, pdf_path, result_error = result
                if result_error is None and pdf_path:
                    successful_reports.append((stock_code, stock_name, pdf_path))
                else:
                    failed_reports.append((stock_code or code_input, stock_name or "未知", result_error or "处理失败"))
            else:
                error_msg = str(error) if error else "处理失败"
                failed_reports.append((code_input, "未知", error_msg))
    else:
        # 使用串行处理（原有逻辑）
        logger.info("📝 使用串行处理模式")

        for i, code_input in enumerate(stock_codes, 1):
            stock_code, stock_name, pdf_path, error = _process_single_stock(
                code_input, output_folder, sector_input, sector_map, i, len(stock_codes)
            )

            if error is None and pdf_path:
                successful_reports.append((stock_code, stock_name, pdf_path))
            else:
                failed_reports.append((stock_code or code_input, stock_name or "未知", error or "处理失败"))

            # 串行模式下的延迟（并发模式下由batch_process处理）
            if i < len(stock_codes):
                delays = config.delays
                if stock_code and str(stock_code).startswith("HK."):
                    delay = delays.get("hk_stock", 3)
                else:
                    delay = delays.get("normal", 1)
                logger.debug(f"💤 等待 {delay} 秒后处理下一个股票...")
                time.sleep(delay)

    return successful_reports, failed_reports


def create_zip_archive(reports_folder: str, zip_filename: Optional[str] = None) -> Optional[str]:
    """创建ZIP压缩包

    Args:
        reports_folder: 报告文件夹路径
        zip_filename: ZIP文件名（可选，默认自动生成）

    Returns:
        Optional[str]: ZIP文件路径，失败返回None
    """
    logger = get_logger(__name__)

    if not os.path.exists(reports_folder) or not os.listdir(reports_folder):
        logger.warning(f"⚠️  报告文件夹为空或不存在: {reports_folder}")
        return None

    if zip_filename is None:
        timestamp = get_beijing_now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"stock_reports_{timestamp}.zip"

    zip_path = os.path.join(reports_folder, zip_filename)

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(reports_folder):
                for file in files:
                    if file.endswith(".pdf"):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, reports_folder)
                        zipf.write(file_path, arcname)
                        logger.debug(f"📦 添加文件到ZIP: {arcname}")

        zip_size = os.path.getsize(zip_path) / (1024 * 1024)
        logger.info(f"✅ ZIP压缩包创建成功: {zip_path}")
        logger.info(f"📦 压缩包大小: {zip_size:.2f} MB")

        return zip_path

    except Exception as e:
        logger.error(f"❌ 创建ZIP压缩包失败: {e}", exc_info=True)
        return None
