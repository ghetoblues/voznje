import asyncio
import os
import re
import requests
from aiogram import Bot as AioBot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiohttp import web  # <--- добавили

# === VOZNJE APP ===
TOKEN_VOZNJE = '8084953056:AAHgAlbN51iSWgNJLwJB4AJNfsIqHd-pO78'
CHANNEL_ID_VOZNJE = '@muharedvoznje'
bot_voznje = AioBot(token=TOKEN_VOZNJE)
scheduler = AsyncIOScheduler()
api_url = "https://www.srbvoz.rs/wp-json/wp/v2/info_post?per_page=100"

# === LAST ID ===
def read_last_sent_id():
    try:
        with open("list.txt", "r") as file:
            return int(file.read().strip())
    except:
        return None

def write_last_sent_id(last_id):
    with open("list.txt", "w") as file:
        file.write(str(last_id))

last_sent_id = read_last_sent_id()

# === FETCH NEWS ===
def get_news_from_api():
    try:
        response = requests.get(api_url)
        if response.status_code != 200:
            return []

        data = response.json()
        news = []
        for item in data:
            news.append({
                "id": item["id"],
                "date": item["date"].split("T")[0],
                "title": item["title"]["rendered"],
                "text": re.sub(r"<.*?>", "", item["content"]["rendered"]),
            })
        return news
    except Exception as e:
        print(f"API Error: {e}")
        return []

# === SEND TO TELEGRAM ===
async def send_news():
    global last_sent_id
    news = get_news_from_api()
    if news:
        new_news = [n for n in news if n["id"] > last_sent_id] if last_sent_id else news
        if new_news:
            latest = new_news[0]
            msg = f"📅 {latest['date']}\n📰 {latest['title']}\n\n{latest['text']}"
            try:
                await bot_voznje.send_message(CHANNEL_ID_VOZNJE, msg, parse_mode="HTML")
                last_sent_id = latest["id"]
                write_last_sent_id(last_sent_id)
            except Exception as e:
                print(f"Send error: {e}")

# === SCHEDULER ===
def start_polling_voznje():
    scheduler.add_job(
        send_news, IntervalTrigger(minutes=5), id="news_polling", replace_existing=True
    )
    scheduler.start()

# === FAKE HTTP SERVER ===
async def handle(request):
    return web.Response(text="Bot is running!")

def start_web_server():
    port = int(os.environ.get("PORT", 8000))
    app = web.Application()
    app.router.add_get("/", handle)
    return web._run_app(app, port=port)

# === MAIN ENTRY ===
async def main():
    await send_news()
    start_polling_voznje()
    web_server = asyncio.create_task(start_web_server())  # <-- запуск фиктивного сервера
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
