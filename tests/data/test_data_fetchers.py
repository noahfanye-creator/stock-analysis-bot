"""
测试数据获取函数（使用mock）
"""

import pandas as pd
from unittest.mock import patch, MagicMock
from src.data.fetchers import get_name, fetch_kline_data, normalize_beijing_time, filter_trading_hours


class TestDataFetchers:
    """数据获取函数测试类"""

    @patch("src.data.fetchers.a_share_fetcher.requests.get")
    def test_get_name_success(self, mock_get):
        """测试获取股票名称成功"""
        # 模拟新浪财经API响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'var hq_str_sh600460="士兰微,29.80,29.89,30.50,30.98,29.75,...";'
        mock_response.encoding = "gbk"
        mock_get.return_value = mock_response

        name = get_name("sh600460")
        assert name == "士兰微"

    @patch("src.data.fetchers.a_share_fetcher.requests.get")
    def test_get_name_failure(self, mock_get):
        """测试获取股票名称失败"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        name = get_name("sh999999")
        # 失败时返回原始代码
        assert name == "sh999999"

    @patch("src.data.fetchers.a_share_fetcher.fetch_kline_data_from_sina")
    @patch("src.utils.trading_hours.is_beijing_after_market_close")
    @patch("src.utils.trading_hours.is_china_stock_market_open")
    def test_fetch_kline_data_basic(self, mock_market_open, mock_after_close, mock_fetch):
        """测试K线数据获取（基础功能）"""
        # Mock 市场状态为非交易日，避免日期检查
        mock_market_open.return_value = False
        # Mock 未收盘，避免要求数据包含今天的检查
        mock_after_close.return_value = False

        # 模拟返回数据
        mock_df = pd.DataFrame(
            {
                "Date": pd.date_range("2024-01-01", periods=10),
                "Open": [100] * 10,
                "High": [105] * 10,
                "Low": [95] * 10,
                "Close": [102] * 10,
                "Volume": [1000000] * 10,
            }
        )
        mock_df.set_index("Date", inplace=True)
        mock_fetch.return_value = mock_df

        # 调用（可能从缓存或网络获取）
        df = fetch_kline_data("sh600460", 240, 100)
        assert df is not None
        assert not df.empty

    def test_normalize_beijing_time(self):
        """测试北京时区标准化"""
        df = pd.DataFrame(
            {"Open": [100] * 5, "High": [105] * 5, "Low": [95] * 5, "Close": [102] * 5, "Volume": [1000000] * 5},
            index=pd.date_range("2024-01-01 09:00", periods=5, freq="h"),
        )

        result = normalize_beijing_time(df)
        assert result is not None
        assert not result.empty
        assert len(result) == len(df)

    def test_filter_trading_hours(self):
        """测试交易时间过滤"""
        # 创建包含交易时间和非交易时间的数据
        dates = pd.date_range("2024-01-15 09:00", periods=10, freq="h")
        df = pd.DataFrame(
            {"Open": [100] * 10, "High": [105] * 10, "Low": [95] * 10, "Close": [102] * 10, "Volume": [1000000] * 10},
            index=dates,
        )

        result = filter_trading_hours(df)
        assert result is not None
        # 过滤后数据应该更少或相等
        assert len(result) <= len(df)
        assert not result.empty

    def test_normalize_code_integration(self):
        """测试代码标准化集成"""
        from src.utils.code_normalizer import normalize_code

        assert normalize_code("600460") == "sh600460"
        assert normalize_code("300474") == "sz300474"
        assert normalize_code("00700") == "HK.00700"
