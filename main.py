import asyncio
import os
import re
from datetime import datetime

import requests
from aiogram import Bot as AioBot


TOKEN_VOZNJE = os.getenv("TOKEN_VOZNJE")
if not TOKEN_VOZNJE:
    raise RuntimeError("Environment variable TOKEN_VOZNJE is required")

CHANNEL_ID_VOZNJE = os.getenv("CHANNEL_ID_VOZNJE")
API_URL = "https://www.srbvoz.rs/wp-json/wp/v2/info_post?per_page=100"
LAST_ID_FILE = os.getenv("LAST_ID_FILE")
RESEND_LATEST_ON_START = os.getenv("RESEND_LATEST_ON_START", "true").lower() == "true"


def read_last_sent_id():
    try:
        with open(LAST_ID_FILE, "r", encoding="utf-8") as file:
            return int(file.read().strip())
    except Exception:
        return None


def write_last_sent_id(last_id: int) -> None:
    with open(LAST_ID_FILE, "w", encoding="utf-8") as file:
        file.write(str(last_id))


def get_news_from_api():
    try:
        response = requests.get(API_URL, timeout=10)
        if response.status_code != 200:
            return []

        data = response.json()
        news = []
        for item in data:
            published_raw = item.get("date", "")
            published_dt = None
            try:
                published_dt = datetime.fromisoformat(published_raw)
            except ValueError:
                pass

            if published_dt:
                date_display = published_dt.strftime("%d.%m.%Y")
                time_display = published_dt.strftime("%H:%M:%S")
            else:
                parts = published_raw.split("T") if published_raw else ["", ""]
                date_display = parts[0]
                time_display = parts[1] if len(parts) > 1 else ""

            news.append(
                {
                    "id": item["id"],
                    "date_iso": published_raw,
                    "date": date_display,
                    "time": time_display,
                    "title": item["title"]["rendered"],
                    "text": re.sub(r"<.*?>", "", item["content"]["rendered"]),
                }
            )
        return news
    except Exception as exc:
        print(f"API Error: {exc}")
        return []


async def send_latest_news(bot: AioBot) -> None:
    last_sent_id = read_last_sent_id()
    news = get_news_from_api()
    if not news:
        return

    if last_sent_id is not None:
        new_news = [n for n in news if n["id"] > last_sent_id]
    else:
        new_news = news

    if not new_news and RESEND_LATEST_ON_START:
        new_news = [news[0]]

    if not new_news:
        return

    latest = new_news[0]
    timestamp = latest["date"]
    if latest.get("time"):
        timestamp = f"{timestamp} {latest['time']}"

    message = f"📅 {timestamp}\n📰 {latest['title']}\n\n{latest['text']}"
    try:
        await bot.send_message(CHANNEL_ID_VOZNJE, message, parse_mode="HTML")
        write_last_sent_id(latest["id"])
    except Exception as exc:
        print(f"Send error: {exc}")


async def main() -> None:
    bot = AioBot(token=TOKEN_VOZNJE)
    try:
        await send_latest_news(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
