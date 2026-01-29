"""
交易时间检查模块
检查A股和港股是否为交易日
所有「今天」均按北京时区判断，避免服务器在 UTC 等时区时误判
"""

from datetime import datetime, date, timedelta

# 北京时区
try:
    from zoneinfo import ZoneInfo
    BEIJING = ZoneInfo("Asia/Shanghai")
except ImportError:
    BEIJING = None  # 无 zoneinfo 时用 UTC+8 近似

# 可选依赖：akshare
try:
    import akshare as ak
except Exception:
    ak = None


def get_beijing_now() -> datetime:
    """当前北京时间的 datetime（用于判断交易日、数据日期）。"""
    if BEIJING is not None:
        return datetime.now(BEIJING)
    return datetime.utcnow() + timedelta(hours=8)


def get_beijing_date() -> date:
    """当前北京时间的日期（用于判断「今天」是否为交易日、数据是否含当日）。"""
    return get_beijing_now().date()


def is_china_stock_market_open() -> bool:
    """
    检查今日是否为A股交易日（自动剔除法定节假日）

    Returns:
        bool: True表示今日是交易日，False表示休市
    """
    try:
        if ak is None:
            print("⚠️  akshare 未安装，跳过交易日检查")
            return True
        # 获取上证指数最新行情
        df = ak.stock_zh_index_daily(symbol="sh000001")
        if df is None or df.empty:
            return True  # 接口故障时默认运行，防止漏发

        # 比较最后交易日与北京「今天」
        import pandas as pd
        last_trade_date = pd.to_datetime(df.iloc[-1]["date"]).date()
        today = get_beijing_date()

        # 如果上证最后交易日期不是今天，说明今天休市
        if last_trade_date != today:
            return False
        return True
    except Exception as e:
        print(f"⚠️ 交易日检查异常: {e}")
        return True


def is_hk_stock_market_open() -> bool:
    """
    检查今日是否为港股交易日

    Returns:
        bool: True表示今日是交易日，False表示休市
    """
    try:
        if ak is None:
            print("⚠️  akshare 未安装，跳过港股交易日检查")
            return True
        # 使用恒生指数判断港股交易日
        df = ak.stock_hk_index_daily_sina(symbol="HSI")
        if df is None or df.empty:
            return True

        import pandas as pd
        last_trade_date = pd.to_datetime(df.iloc[-1]["date"]).date()
        today = get_beijing_date()

        if last_trade_date != today:
            return False
        return True
    except Exception as e:
        print(f"⚠️ 港股交易日检查异常: {e}")
        return True

