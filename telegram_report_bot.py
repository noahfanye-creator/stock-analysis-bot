#!/usr/bin/env python3
"""
Telegram 报告机器人 - 常驻进程
用户在对话中发送股票代码（单个或空格/逗号分隔多个），机器人生成报告并将 PDF 发回同一对话。
需长期运行：python telegram_report_bot.py
"""

import os
import sys
import time
import warnings

from dotenv import load_dotenv

# 抑制 py_mini_racer / pkg_resources 弃用警告（来自 akshare 依赖）
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

load_dotenv()

# 可选依赖
try:
    import requests
except ImportError:
    print("❌ 请安装 requests: pip install requests")
    sys.exit(1)

from src.utils.code_normalizer import parse_stock_list
from src.report import process_multiple_stocks
from src.config import Config
from src.notify.telegram import send_telegram_msg, send_telegram_document
from src.utils.logger import get_logger
from src.utils.trading_hours import get_beijing_now

logger = get_logger(__name__)

# 单条消息最多处理的股票数量
MAX_STOCKS_PER_MESSAGE = 5
GET_UPDATES_TIMEOUT = 30


def get_allowed_chat_ids():
    """允许触发报告生成的 chat_id 列表；默认仅 TELEGRAM_CHAT_ID。"""
    allow_list = os.getenv("TELEGRAM_REPORT_ALLOW_CHAT_IDS")
    if allow_list:
        return [s.strip() for s in allow_list.split(",") if s.strip()]
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    return [chat_id] if chat_id else []


def get_updates(token: str, offset: int = 0, timeout: int = GET_UPDATES_TIMEOUT):
    """拉取 Telegram 更新（长轮询）。"""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        r = requests.get(url, params={"offset": offset, "timeout": timeout}, timeout=timeout + 10)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            return []
        return data.get("result") or []
    except Exception as e:
        logger.warning("getUpdates 失败: %s", e)
        return []


def process_message(token: str, chat_id: str, text: str, update_id: int, allowed_chat_ids: list):
    """
    处理一条用户消息：解析股票代码，生成报告，将 PDF 发回该对话。
    """
    chat_id_str = str(chat_id)
    if allowed_chat_ids and chat_id_str not in allowed_chat_ids:
        send_telegram_msg("⛔ 未授权使用本机器人。", chat_id=chat_id_str)
        return

    raw = (text or "").strip()
    if not raw:
        send_telegram_msg(
            "请发送股票代码，例如：688630 或 688630 300474",
            chat_id=chat_id_str,
        )
        return

    codes = parse_stock_list(raw)
    if not codes:
        send_telegram_msg(
            "未识别到有效股票代码，请发送 6 位 A 股代码或港股代码，如 688630 或 00700。",
            chat_id=chat_id_str,
        )
        return

    if len(codes) > MAX_STOCKS_PER_MESSAGE:
        codes = codes[:MAX_STOCKS_PER_MESSAGE]
        send_telegram_msg(
            f"单次最多处理 {MAX_STOCKS_PER_MESSAGE} 只股票，已截取前 {MAX_STOCKS_PER_MESSAGE} 只。",
            chat_id=chat_id_str,
        )

    stocks_input = " ".join(codes)
    n = len(codes)
    send_telegram_msg(f"📊 正在生成 {n} 个报告，请稍候…", chat_id=chat_id_str)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    config = Config()
    reports_base = config.report_output_dir
    timestamp = get_beijing_now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(current_dir, reports_base, f"telegram_{update_id}_{timestamp}")

    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        logger.error("创建输出目录失败: %s", e)
        send_telegram_msg("❌ 创建输出目录失败，请稍后重试。", chat_id=chat_id_str)
        return

    try:
        successful_reports, failed_reports = process_multiple_stocks(
            stocks_input, output_dir, sector_input=None
        )
    except Exception as e:
        logger.exception("报告生成异常: %s", e)
        send_telegram_msg(f"❌ 报告生成异常：{e}", chat_id=chat_id_str)
        return

    success_count = 0
    for _code, _name, pdf_path in successful_reports:
        if pdf_path and os.path.isfile(pdf_path):
            if send_telegram_document(chat_id_str, pdf_path, token=token):
                success_count += 1

    failed_count = len(failed_reports)
    if failed_count > 0:
        summary = "；".join([f"{name}({code}): {reason}" for code, name, reason in failed_reports])
        send_telegram_msg(
            f"✅ 完成：成功 {success_count} 个，失败 {failed_count} 个\n\n失败详情：{summary}",
            chat_id=chat_id_str,
        )
    else:
        send_telegram_msg(f"✅ 报告推送完成，共 {success_count} 个。", chat_id=chat_id_str)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("未设置 TELEGRAM_BOT_TOKEN，退出")
        sys.exit(1)

    allowed = get_allowed_chat_ids()
    if not allowed:
        logger.error("未设置 TELEGRAM_CHAT_ID 或 TELEGRAM_REPORT_ALLOW_CHAT_IDS，退出")
        sys.exit(1)

    logger.info("Telegram 报告机器人已启动，等待消息…（仅允许 chat_id: %s）", allowed)
    offset = 0

    while True:
        try:
            updates = get_updates(token, offset=offset, timeout=GET_UPDATES_TIMEOUT)
            for u in updates:
                offset = u["update_id"] + 1
                msg = u.get("message")
                if not msg:
                    continue
                text = msg.get("text")
                if text is None:
                    continue
                chat_id = msg.get("chat", {}).get("id")
                if chat_id is None:
                    continue
                try:
                    process_message(token, chat_id, text, u["update_id"], allowed)
                except Exception as e:
                    logger.exception("处理消息异常: %s", e)
                    send_telegram_msg(f"❌ 处理出错：{e}", chat_id=str(chat_id))
        except KeyboardInterrupt:
            logger.info("已退出")
            break
        except Exception as e:
            logger.exception("轮询异常: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
