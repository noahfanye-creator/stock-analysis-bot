import os
from typing import Optional

import requests
from loguru import logger


def send_telegram_msg(message: str, chat_id: Optional[str] = None) -> bool:
    """
    发送消息到 Telegram Bot

    Args:
        message: 要发送的消息内容（支持 Markdown）
        chat_id: 可选，目标对话 ID；不传则使用环境变量 TELEGRAM_CHAT_ID
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    target_chat = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if not token or not target_chat:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN 或 chat_id 未设置，跳过发送消息")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("ok"):
            logger.info("✅ Telegram 消息发送成功")
            return True
        logger.error("❌ Telegram 消息发送失败: %s", data.get("description"))
        return False
    except Exception as e:
        logger.error("❌ 发送 Telegram 消息出错: %s", e)
        return False


def send_telegram_document(
    chat_id: str, file_path: str, caption: Optional[str] = None, token: Optional[str] = None
) -> bool:
    """
    发送文件到指定 Telegram 对话

    Args:
        chat_id: 目标对话 ID
        file_path: 本地文件路径（如 PDF）
        caption: 可选，文件说明
        token: 可选，Bot Token；不传则使用环境变量 TELEGRAM_BOT_TOKEN

    Returns:
        bool: 是否发送成功
    """
    bot_token = token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token or not chat_id:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN 或 chat_id 未设置，跳过发送文件")
        return False

    filename = os.path.basename(file_path)
    if not os.path.isfile(file_path):
        logger.error("❌ 文件不存在: %s", file_path)
        return False

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 50:
        logger.warning("⚠️ 跳过文件 %s (大小: %.1fMB，超过50MB限制)", filename, file_size_mb)
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
            response = requests.post(
                url,
                data=data,
                files={"document": (filename, f, "application/pdf")},
                timeout=30,
            )
        response.raise_for_status()
        if response.json().get("ok"):
            logger.info("✅ Telegram 发送成功: %s", filename)
            return True
        logger.error("❌ Telegram 发送失败: %s", filename)
        return False
    except Exception as e:
        logger.error("❌ 发送 %s 到 Telegram 出错: %s", filename, e)
        return False
