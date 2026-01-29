"""
测试交易时间判断函数
使用 get_beijing_date 模拟「今天」，与实现一致（北京时区）
"""

from datetime import datetime
from unittest.mock import patch
import pandas as pd
from src.utils.trading_hours import is_china_stock_market_open, is_hk_stock_market_open


class TestTradingHours:
    """交易时间判断测试类"""

    @patch("src.utils.trading_hours.get_beijing_date")
    @patch("src.utils.trading_hours.ak")
    def test_china_market_open_weekday(self, mock_ak, mock_beijing_date):
        """测试A股市场工作日开盘"""
        mock_df = pd.DataFrame({"date": [datetime(2024, 1, 15).date()]})
        mock_ak.stock_zh_index_daily.return_value = mock_df
        mock_beijing_date.return_value = datetime(2024, 1, 15).date()

        result = is_china_stock_market_open()
        assert result is True

    @patch("src.utils.trading_hours.get_beijing_date")
    @patch("src.utils.trading_hours.ak")
    def test_china_market_closed_weekend(self, mock_ak, mock_beijing_date):
        """测试A股市场周末休市"""
        mock_df = pd.DataFrame({"date": [datetime(2024, 1, 12).date()]})
        mock_ak.stock_zh_index_daily.return_value = mock_df
        mock_beijing_date.return_value = datetime(2024, 1, 13).date()  # 周六

        result = is_china_stock_market_open()
        assert result is False

    @patch("src.utils.trading_hours.get_beijing_date")
    @patch("src.utils.trading_hours.ak")
    def test_hk_market_open_weekday(self, mock_ak, mock_beijing_date):
        """测试港股市场工作日开盘"""
        mock_df = pd.DataFrame({"date": [datetime(2024, 1, 15).date()]})
        mock_ak.stock_hk_index_daily_sina.return_value = mock_df
        mock_beijing_date.return_value = datetime(2024, 1, 15).date()

        result = is_hk_stock_market_open()
        assert result is True

    @patch("src.utils.trading_hours.get_beijing_date")
    @patch("src.utils.trading_hours.ak")
    def test_hk_market_closed_weekend(self, mock_ak, mock_beijing_date):
        """测试港股市场周末休市"""
        mock_df = pd.DataFrame({"date": [datetime(2024, 1, 12).date()]})
        mock_ak.stock_hk_index_daily_sina.return_value = mock_df
        mock_beijing_date.return_value = datetime(2024, 1, 13).date()  # 周六

        result = is_hk_stock_market_open()
        assert result is False
