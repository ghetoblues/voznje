import asyncio
import os
import re
from datetime import datetime

import requests
from aiogram import Bot

TOKEN_VOZNJE = os.environ["TOKEN_VOZNJE"]
CHANNEL_ID_VOZNJE = os.environ["CHANNEL_ID_VOZNJE"]
API_URL = os.environ["API_URL"]
GITHUB_GIST_ID = os.environ["GITHUB_GIST_ID"]
GITHUB_GIST_FILENAME = os.environ["GITHUB_GIST_FILENAME"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]


def gist_headers() -> dict:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_last_id_from_gist() -> int:
    url = f"https://api.github.com/gists/{GITHUB_GIST_ID}"
    response = requests.get(url, headers=gist_headers(), timeout=10)
    response.raise_for_status()
    files = response.json()["files"]
    content = files[GITHUB_GIST_FILENAME]["content"].strip()
    return int(content) if content else 0


def update_gist(last_id: int) -> None:
    url = f"https://api.github.com/gists/{GITHUB_GIST_ID}"
    payload = {
        "files": {
            GITHUB_GIST_FILENAME: {
                "content": str(last_id),
            }
        }
    }
    response = requests.patch(url, headers=gist_headers(), json=payload, timeout=10)
    response.raise_for_status()


def fetch_news() -> list[dict]:
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    data = response.json()

    news = []
    for item in data:
        published = datetime.fromisoformat(item["date"])
        text = re.sub(r"<.*?>", "", item["content"]["rendered"])
        news.append(
            {
                "id": item["id"],
                "timestamp": published.strftime("%d.%m.%Y %H:%M:%S"),
                "title": item["title"]["rendered"],
                "text": text,
            }
        )
    return sorted(news, key=lambda x: x["id"])


async def send_updates(bot: Bot) -> None:
    last_sent_id = await asyncio.to_thread(get_last_id_from_gist)
    news_items = await asyncio.to_thread(fetch_news)
    new_items = [item for item in news_items if item["id"] > last_sent_id]
    if not new_items:
        return

    for item in new_items:
        message = f"📅 {item['timestamp']}\n📰 {item['title']}\n\n{item['text']}"
        await bot.send_message(CHANNEL_ID_VOZNJE, message, parse_mode="HTML")

    await asyncio.to_thread(update_gist, new_items[-1]["id"])


async def main() -> None:
    bot = Bot(token=TOKEN_VOZNJE)
    try:
        await send_updates(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
