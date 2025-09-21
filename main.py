import asyncio
import os
import re

import requests
from aiogram import Bot as AioBot


TOKEN_VOZNJE = os.getenv("TOKEN_VOZNJE")
if not TOKEN_VOZNJE:
    raise RuntimeError("Environment variable TOKEN_VOZNJE is required")

CHANNEL_ID_VOZNJE = os.getenv("CHANNEL_ID_VOZNJE", "@muharedvoznje")
API_URL = "https://www.srbvoz.rs/wp-json/wp/v2/info_post?per_page=100"
LAST_ID_FILE = os.getenv("LAST_ID_FILE", "list.txt")


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
            news.append(
                {
                    "id": item["id"],
                    "date": item["date"].split("T")[0],
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

    new_news = [n for n in news if last_sent_id and n["id"] > last_sent_id]
    if not new_news and last_sent_id is None:
        new_news = news

    if not new_news:
        return

    latest = new_news[0]
    message = f"📅 {latest['date']}\n📰 {latest['title']}\n\n{latest['text']}"
    try:
        await bot.send_message(CHANNEL_ID_VOZNJE, message, parse_mode="HTML")
        write_last_sent_id(latest["id"])
    except Exception as exc:
        print(f"Send error: {exc}")


async def main() -> None:
    async with AioBot(token=TOKEN_VOZNJE) as bot:
        await send_latest_news(bot)


if __name__ == "__main__":
    asyncio.run(main())
