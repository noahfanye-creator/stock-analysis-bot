#!/usr/bin/env python3
"""
验证「报告数据为最新」相关逻辑：
1. 北京时区 get_beijing_date / get_beijing_now
2. 交易时段内 A 股日线跳过缓存（use_cache=False 时不读 cache）
"""
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, ".")


def test_beijing_time():
    """验证北京时区函数"""
    from src.utils.trading_hours import get_beijing_date, get_beijing_now

    now = get_beijing_now()
    today = get_beijing_date()
    assert hasattr(now, "date"), "get_beijing_now 应返回 datetime"
    assert today == now.date(), "get_beijing_date 应为 get_beijing_now().date()"
    print("  [OK] 北京时区 get_beijing_now / get_beijing_date")


def test_skip_cache_during_trading_hours():
    """验证：交易时段内 A 股日线请求不读缓存"""
    from src.data.fetchers.a_share_fetcher import fetch_kline_data

    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.set.return_value = None

    with patch("src.utils.trading_hours.is_china_stock_market_open", return_value=True):
        with patch("src.utils.cache.get_cache", return_value=mock_cache):
            try:
                fetch_kline_data("sh600000", scale=240, datalen=5)
            except Exception:
                pass  # 可能因网络/依赖失败，只关心是否读过缓存
    if mock_cache.get.called:
        print("  [FAIL] 交易时段 A 股日线仍调用了 cache.get，应跳过缓存")
        sys.exit(1)
    print("  [OK] 交易时段 A 股日线未读缓存（跳过缓存逻辑生效）")


def test_use_cache_outside_trading_hours():
    """验证：非交易时段会尝试读缓存"""
    from src.data.fetchers.a_share_fetcher import fetch_kline_data

    mock_cache = MagicMock()
    mock_cache.get.return_value = None  # 无缓存数据
    mock_cache.set.return_value = None

    with patch("src.utils.trading_hours.is_china_stock_market_open", return_value=False):
        with patch("src.utils.cache.get_cache", return_value=mock_cache):
            try:
                fetch_kline_data("sh600000", scale=240, datalen=5)
            except Exception:
                pass
    if not mock_cache.get.called:
        print("  [FAIL] 非交易时段应尝试 cache.get")
        sys.exit(1)
    print("  [OK] 非交易时段会尝试读缓存")


if __name__ == "__main__":
    print("验证 1: 北京时区")
    test_beijing_time()
    print("验证 2: 交易时段内 A 股日线跳过缓存")
    test_skip_cache_during_trading_hours()
    print("验证 3: 非交易时段使用缓存")
    test_use_cache_outside_trading_hours()
    print("\n全部通过。")
