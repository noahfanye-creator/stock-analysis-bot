"""
A股数据获取模块
从新浪财经等数据源获取A股K线数据
"""

import re
import json
from typing import Optional

import pandas as pd
import requests

from src.utils.logger import get_logger
from src.utils.exceptions import DataFetchError

logger = get_logger(__name__)


def get_name(symbol: str) -> str:
    """获取股票名称 - 支持A股和港股"""
    try:
        # 港股使用免费数据源（AKShare/yfinance）
        if symbol.startswith("HK."):
            code = symbol.replace("HK.", "")

            # 使用免费数据源获取股票名称
            try:
                from src.data.hk_data_sources import HKDataSources

                name = HKDataSources.get_stock_name_fallback(code)
                if name:
                    return name
            except Exception as e:
                logger.warning("获取港股名称失败 %s: %s", symbol, e)

        # A股使用新浪财经接口
        if symbol.startswith("sh") or symbol.startswith("sz"):
            # 新浪财经实时数据接口
            url = f"http://hq.sinajs.cn/list={symbol}"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                ),
                "Referer": "https://finance.sina.com.cn",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = "gbk"

            if response.status_code == 200:
                content = response.text
                # 解析新浪财经返回的数据格式
                # 格式：var hq_str_sh600460="士兰微,29.80,29.89,30.50,30.98,29.75,..."
                if '="' in content:
                    data_str = content.split('="')[1].split('"')[0]
                    if data_str:
                        parts = data_str.split(",")
                        if len(parts) > 0:
                            return parts[0]  # 股票名称

        # 如果上面失败，尝试使用东方财富接口
        clean_code = re.sub(r"[a-zA-Z]", "", symbol)
        if clean_code:
            # 东方财富股票信息接口
            market_prefix = "1." if clean_code.startswith("6") else "0."
            url = (
                f"https://push2.eastmoney.com/api/qt/stock/get?" f"secid={market_prefix}{clean_code}&fields=f12,f13,f14"
            )
            headers = {
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) " "AppleWebKit/537.36"),
                "Referer": "https://quote.eastmoney.com/",
            }

            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    return data["data"].get("f14", symbol)

    except Exception as e:
        logger.warning("获取股票名称出错 %s: %s", symbol, e)

    return symbol


def fetch_kline_data_from_sina(symbol: str, scale: int = 240, datalen: int = 100) -> Optional[pd.DataFrame]:
    """从新浪财经获取K线数据

    Args:
        symbol: 股票代码，如 sh600460
        scale: K线周期，240=日线，30=30分钟，5=5分钟，1=1分钟
        datalen: 数据长度

    Returns:
        pd.DataFrame: K线数据，包含 Open, High, Low, Close, Volume
    """
    try:
        # 提取纯数字代码
        clean_code = re.sub(r"[a-zA-Z]", "", symbol)
        if not clean_code:
            raise DataFetchError(f"无效的股票代码: {symbol}")

        # 新浪财经历史数据接口
        # 日线数据
        if scale == 240:
            url = "https://quotes.sina.cn/cn/api/openapi.php/" "CN_MarketDataService.getKLineData"
            params = {
                "symbol": symbol.upper(),
                "scale": scale,
                "datalen": datalen,
                "ma": "no",
            }
        else:
            # 分钟数据
            url = "https://quotes.sina.cn/cn/api/openapi.php/" "StockV2Service.getMinLine"
            params = {"symbol": symbol.upper(), "scale": scale, "datalen": datalen}

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Referer": "https://finance.sina.com.cn",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        logger.debug("从新浪财经获取数据: %s scale=%s", symbol, scale)

        response = requests.get(url, headers=headers, params=params, timeout=15)

        if response.status_code != 200:
            raise DataFetchError(f"新浪财经 HTTP 错误: {response.status_code}")

        try:
            data = response.json()
        except Exception as parse_err:
            text = response.text
            if "day" in text or "d=" in text:
                try:
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start >= 0 and end > start:
                        data = json.loads(text[start:end])
                    else:
                        raise DataFetchError("新浪财经响应无法解析为 JSON") from parse_err
                except json.JSONDecodeError:
                    raise DataFetchError("新浪财经 JSON 解析失败") from parse_err
            else:
                raise DataFetchError("新浪财经响应不是有效 JSON") from parse_err

        # 解析新浪财经返回的数据结构
        klines = []

        if scale == 240:
            # 日线数据格式
            if "result" in data and "data" in data["result"]:
                for item in data["result"]["data"]:
                    try:
                        klines.append(
                            {
                                "Date": item["day"],
                                "Open": float(item["open"]),
                                "High": float(item["high"]),
                                "Low": float(item["low"]),
                                "Close": float(item["close"]),
                                "Volume": float(item.get("volume", 0)),
                            }
                        )
                    except Exception:
                        continue
        else:
            # 分钟数据格式
            if "result" in data and "data" in data["result"]:
                for item in data["result"]["data"]:
                    try:
                        klines.append(
                            {
                                "Date": f"{item['d']} {item['t']}:00",
                                "Open": float(item["o"]),
                                "High": float(item["h"]),
                                "Low": float(item["l"]),
                                "Close": float(item["c"]),
                                "Volume": float(item.get("v", 0)),
                            }
                        )
                    except Exception:
                        continue

        if not klines:
            raise DataFetchError(f"新浪财经未返回有效 K 线数据: {symbol}")

        df = pd.DataFrame(klines)
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        df.sort_index(inplace=True)
        logger.debug("新浪财经获取到 %s 条数据: %s", len(df), symbol)
        return df

    except DataFetchError:
        raise
    except Exception as e:
        raise DataFetchError(f"从新浪财经获取数据失败 {symbol}: {e}") from e


def fetch_kline_data_fallback(symbol: str, scale: int = 240, datalen: int = 100) -> Optional[pd.DataFrame]:
    """新浪K线备用接口（json_v2）"""
    try:
        url = (
            "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
            f"CN_MarketData.getKLineData?symbol={symbol}&scale={scale}"
            f"&ma=no&datalen={datalen}"
        )
        headers = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) " "AppleWebKit/537.36")}
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            raise DataFetchError(f"新浪备用接口 HTTP 错误: {response.status_code}")

        data = response.json()
        if not data:
            raise DataFetchError("新浪备用接口未返回数据")

        df = pd.DataFrame(data)
        df.rename(
            columns={
                "day": "Date",
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            },
            inplace=True,
        )

        cols = ["Open", "High", "Low", "Close", "Volume"]
        for col in cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        df.sort_index(inplace=True)

        return df if not df.empty else None
    except DataFetchError:
        raise
    except Exception as e:
        raise DataFetchError(f"备用接口获取失败 {symbol} scale={scale}: {e}") from e


def fetch_kline_data(symbol: str, scale: int = 240, datalen: int = 100) -> Optional[pd.DataFrame]:
    """获取K线数据 - 支持A股和港股（统一入口，自动降级，带缓存；仅从网络获取，不读不写数据库）

    Args:
        symbol: 股票代码，A股如 sh600460，港股如 HK.00700
        scale: K线周期，240=日线，30=30分钟，5=5分钟，1=1分钟
        datalen: 数据长度

    Returns:
        pd.DataFrame: K线数据
    """
    is_ashare = symbol.startswith("sh") or symbol.startswith("sz")

    # 交易时段内 A 股日线不读缓存，始终从接口拉取，保证报告数据为当日最新
    use_cache = True
    try:
        from src.utils.cache import get_cache
        from src.utils.trading_hours import is_china_stock_market_open, is_beijing_trading_time, get_beijing_date

        if is_ashare and scale == 240 and (is_china_stock_market_open() or is_beijing_trading_time()):
            use_cache = False
            logger.debug("交易时段 A 股日线 %s 跳过缓存，拉取最新数据", symbol)
    except Exception:
        pass

    # 非上述情况时从缓存获取
    if use_cache:
        try:
            cache = get_cache()
            if cache is not None:
                if scale == 240:
                    ttl_hours = 24
                elif scale in [30, 5]:
                    ttl_hours = 1
                else:
                    ttl_hours = 0.5
                cached_data = cache.get(
                    "fetch_kline_data",
                    ttl_hours=ttl_hours,
                    symbol=symbol,
                    scale=scale,
                    datalen=datalen,
                )
                if cached_data is not None:
                    # 日线且非交易时段：缓存可用；交易时段已在上面跳过缓存
                    if is_ashare and scale == 240:
                        today = get_beijing_date()
                        latest_date = cached_data.index.max().date() if not cached_data.empty else None
                        if latest_date != today:
                            logger.debug(
                                "缓存不包含北京今日 %s（最新：%s），跳过缓存",
                                symbol,
                                latest_date,
                            )
                        else:
                            logger.debug("缓存包含北京今日 %s，使用缓存", symbol)
                            return cached_data
                    else:
                        return cached_data
        except Exception:
            pass

    if symbol.startswith("HK."):
        from .hk_stock_fetcher import fetch_kline_data_from_hk_sources

        try:
            df = fetch_kline_data_from_hk_sources(symbol, scale, datalen)
        except DataFetchError as e:
            logger.warning("港股数据获取失败 %s: %s", symbol, e)
            df = None
    else:
        df = None
        if df is None:
            try:
                df = fetch_kline_data_from_sina(symbol, scale, datalen)
            except DataFetchError as e:
                logger.debug("新浪主接口失败 %s: %s，尝试备用", symbol, e)
            if df is None or df.empty:
                try:
                    df = fetch_kline_data_fallback(symbol, scale, datalen)
                except DataFetchError as e:
                    logger.debug("新浪备用接口失败 %s: %s", symbol, e)
            if (df is None or df.empty) and symbol.startswith(("sh", "sz")):
                logger.info("新浪财经接口不可用，尝试其他数据源: %s", symbol)
                try:
                    from ..a_share_data_sources import AShareDataSources

                    df = AShareDataSources.get_kline_with_fallback(symbol, scale, datalen)
                except Exception as e:
                    logger.warning("其他数据源获取失败 %s: %s", symbol, e)
            if (df is None or df.empty) and scale == 1:
                logger.info("所有数据源1分钟数据不可用，尝试替代方法: %s", symbol)
                try:
                    from .hk_stock_fetcher import fetch_alternative_1min_data

                    df = fetch_alternative_1min_data(symbol, days=5)
                    if df is not None and not df.empty:
                        logger.info("替代方法获取到 %s 条1分钟数据", len(df))
                except Exception as e:
                    logger.warning("替代方法失败: %s", e)

            # 仅在北京 15:00 收盘后才要求日线含「今天」；交易时段内日线多未更新今日，接受昨日为最新
            if df is not None and not df.empty and is_ashare and scale == 240:
                try:
                    from src.utils.trading_hours import is_beijing_after_market_close, get_beijing_date

                    if is_beijing_after_market_close():
                        today = get_beijing_date()
                        latest_date = df.index.max().date() if not df.empty else None
                        if latest_date != today:
                            logger.warning(
                                "北京已收盘但接口数据不包含今日 %s（最新日期：%s），返回None",
                                symbol,
                                latest_date,
                            )
                            return None
                except Exception as e:
                    logger.debug("检查数据日期失败 %s: %s", symbol, e)

    # 保存到缓存
    if df is not None and not df.empty:
        try:
            from src.utils.cache import get_cache

            cache = get_cache()
            if cache is not None:
                if scale == 240:
                    ttl_hours = 24
                elif scale in [30, 5]:
                    ttl_hours = 1
                else:
                    ttl_hours = 0.5
                cache.set(
                    "fetch_kline_data",
                    df,
                    ttl_hours=ttl_hours,
                    symbol=symbol,
                    scale=scale,
                    datalen=datalen,
                )
        except Exception:
            pass

    # 最终验证：仅在北京 15:00 收盘后才要求日线含「今天」
    if df is not None and not df.empty and is_ashare and scale == 240:
        try:
            from src.utils.trading_hours import is_beijing_after_market_close, get_beijing_date

            if is_beijing_after_market_close():
                today = get_beijing_date()
                latest_date = df.index.max().date() if not df.empty else None
                if latest_date != today:
                    logger.warning(
                        "最终验证失败：北京已收盘，数据不包含今日 %s（最新：%s），返回None",
                        symbol,
                        latest_date,
                    )
                    return None
                logger.debug("最终验证通过：数据包含北京今日 %s", symbol)
        except Exception as e:
            logger.debug("最终验证异常 %s: %s", symbol, e)

    return df if (df is not None and not df.empty) else None
